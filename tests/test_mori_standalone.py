import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mori_profile',ROOT/'starter/mori/profile.py')
profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile)
runner_spec=importlib.util.spec_from_file_location('mori_run',ROOT/'starter/mori/run.py')
runner=importlib.util.module_from_spec(runner_spec);runner_spec.loader.exec_module(runner)

class ReplacementContract(unittest.TestCase):
    def test_all_notices_bundled_and_parts_matched(self):
        import hashlib
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);record=runner.bundle_notices(out)
            self.assertEqual(len(record),8)
            for name,h in record.items():self.assertEqual(hashlib.sha256((out/name).read_bytes()).hexdigest(),h)
            scope=json.loads((out/'provenance.json').read_text(encoding='utf8'))
            (out/'replacement.json').write_text(json.dumps({'parts':[p['object'] for p in scope['parts']]}))
            self.assertTrue(runner.validate_part_scope(out))

    def test_missing_license_file_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)
            with self.assertRaises(FileNotFoundError):runner.bundle_notices(out,here=out/'absent/starter/mori')
            self.assertFalse((out/'NOTICE.md').exists())

    def test_unlisted_part_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);runner.bundle_notices(out)
            scope=json.loads((out/'provenance.json').read_text(encoding='utf8'))
            parts=[p['object'] for p in scope['parts']];parts[-1]='unverified third-party part'
            (out/'replacement.json').write_text(json.dumps({'parts':parts}))
            with self.assertRaisesRegex(ValueError,'Generated parts'):runner.validate_part_scope(out)

    def test_index_is_resolved_by_id_not_batch_five(self):
        self.assertEqual(profile.target_index(['other',profile.FEATURE]),1)

    def test_absent_or_duplicate_id_rejected(self):
        for ids in [[],['other'],[profile.FEATURE,profile.FEATURE]]:
            with self.assertRaises(ValueError):profile.target_index(ids)

    def test_corrupt_input_stops_before_blender(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);inputs=p/'inputs';inputs.mkdir()
            (inputs/'tileset.json').write_bytes(b'corrupt')
            out=p/'out'
            result=subprocess.run([sys.executable,str(ROOT/'starter/mori/run.py'),'--blender',sys.executable,'--inputs',str(inputs),'--output',str(out)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            record=json.loads((out/'run.json').read_text())
            self.assertFalse(record['ok'])
            self.assertIn('Pinned source mismatch',record['error'])
            self.assertFalse((out/'build.log').exists())

    def test_existing_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);marker=out/'keep';marker.write_text('original')
            result=subprocess.run([sys.executable,str(ROOT/'starter/mori/run.py'),'--blender',sys.executable,'--output',str(out)],capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(marker.read_text(),'original')
            self.assertFalse((out/'inputs').exists())

if __name__=='__main__':unittest.main()
