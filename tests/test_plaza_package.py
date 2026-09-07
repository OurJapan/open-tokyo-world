# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('plaza_package', Path(__file__).resolve().parents[1]/'starter/plaza/package.py')
pkg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pkg)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root, self.run = self.base/'repo', self.base/'run'
        for name in pkg.SOURCES:
            path = self.root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'# independent test fixture\n')
        for name in ('LICENSE.md', 'MIT-LICENSE.txt', 'NOTICE.md'):
            (self.root/name).write_bytes(b'test notice')
        for name in ('ASSET-LICENSE.md', 'provenance.json'):
            (self.root/'starter/plaza'/name).write_bytes(b'{}')
        for name in pkg.OUTPUTS:
            path = self.run/name
            path.parent.mkdir(parents=True, exist_ok=True)
            if name.endswith('.png'):
                # Header fixture only; packaging does not claim to decode pixels.
                path.write_bytes(b'\x89PNG\r\n\x1a\n'+struct.pack('>I',13)+b'IHDR'+struct.pack('>II',800,600)+b'\x00'*9)
            elif name.endswith('validation.json'):
                path.write_bytes(pkg.encoded({'ok':True,'separate_process_open':True,'mesh_count':6,
                    'render_pixels':[800,600],'paving_brightness':1 if name.startswith('before') else .9,
                    'mesh_fingerprints':dict.fromkeys(pkg.OBJECTS,'a'*64),
                    'blender_version':'4.5.1 LTS','triangles':12}))
            else:
                path.write_bytes(b'{}')
        self.report = {'ok':True,'paving_brightness':.9,
            'source_sha256':{n:pkg.digest((self.root/n).read_bytes()) for n in pkg.SOURCES},
            'output_sha256':{n:pkg.digest((self.run/n).read_bytes()) for n in pkg.OUTPUTS},
            'runs':{label:json.loads((self.run/label/'validation.json').read_bytes()) for label in ('before','after')}}
        self.save_report()

    def save_report(self):
        (self.run/'run.json').write_bytes(pkg.encoded(self.report))

    def test_roundtrip_allowlist_and_no_overwrite(self):
        (self.run/'private.log').write_text('DO NOT SHARE')
        (self.run/'review.html').write_text('<script>DO NOT SHARE</script>')
        (self.run/'city.blend').write_bytes(b'not included')
        self.report['private_path'] = 'DO NOT SHARE'
        self.save_report()
        archive = pkg.package(self.run,self.base/'out',self.root)
        original = archive.read_bytes()
        with zipfile.ZipFile(archive) as z:
            inventory=json.loads(z.read('inventory.json'))
            self.assertEqual(set(z.namelist()),{r['path'] for r in inventory['files']}|{'inventory.json'})
            for row in inventory['files']:
                data=z.read(row['path'])
                self.assertEqual(len(data),row['bytes'])
                self.assertEqual(pkg.digest(data),row['sha256'])
                self.assertNotIn(b'DO NOT SHARE',data)
        with self.assertRaises(FileExistsError):
            pkg.package(self.run,self.base/'out',self.root)
        self.assertEqual(original,archive.read_bytes())

    def test_changed_image_rejected_before_output(self):
        (self.run/'after/preview.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Output changed'):
            pkg.package(self.run,self.base/'out',self.root)
        self.assertFalse((self.base/'out').exists())

    def test_changed_source_rejected(self):
        (self.root/pkg.SOURCES[0]).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Source changed'):
            pkg.collect(self.run,self.root)

    def test_failed_and_legacy_run_rejected(self):
        self.report['ok']=False;self.save_report()
        with self.assertRaisesRegex(ValueError,'Run did not succeed'):
            pkg.collect(self.run,self.root)
        self.report['ok']=True;del self.report['output_sha256'];self.save_report()
        with self.assertRaisesRegex(ValueError,'regenerate'):
            pkg.collect(self.run,self.root)

    def test_mismatched_validation_rejected(self):
        self.report['runs']['after']['paving_brightness']=1;self.save_report()
        with self.assertRaisesRegex(ValueError,'Brightness mismatch'):
            pkg.collect(self.run,self.root)

    def test_missing_file_rejected(self):
        (self.run/'after/validation.json').unlink()
        with self.assertRaises(FileNotFoundError):
            pkg.collect(self.run,self.root)

    def test_changed_notice_even_with_updated_hash_rejected(self):
        (self.run/'provenance.json').write_bytes(b'{"extra":"private"}')
        self.report['output_sha256']['provenance.json']=pkg.digest((self.run/'provenance.json').read_bytes())
        self.save_report()
        with self.assertRaisesRegex(ValueError,'Source notice differs'):
            pkg.collect(self.run,self.root)


if __name__ == '__main__':
    unittest.main()
