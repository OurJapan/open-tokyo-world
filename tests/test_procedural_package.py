# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
from pathlib import Path
import sys
import tempfile
import unittest
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from package_procedural_components import FILES, verify_archive, write_archive


class ProceduralPackageContracts(unittest.TestCase):
    def test_package_roundtrip_has_only_approved_members(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'package.zip'
            files = {n: ('fixture ' + n).encode() for n in FILES}
            expected = write_archive(archive, files)
            self.assertEqual(verify_archive(archive), expected)
            with zipfile.ZipFile(archive) as package:
                self.assertEqual(set(package.namelist()), FILES | {'inventory.json'})
                for name, content in files.items():
                    self.assertEqual(package.read(name), content)

    def test_legacy_scene_or_log_cannot_be_added_to_package(self):
        with tempfile.TemporaryDirectory() as directory:
            files = {n: b'fixture' for n in FILES}
            files['city.blend'] = b'unapproved scene'
            with self.assertRaisesRegex(ValueError, 'file set'):
                write_archive(Path(directory) / 'package.zip', files)

    def test_missing_license_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            files = {n: b'fixture' for n in FILES if n != 'ASSET-LICENSE.md'}
            with self.assertRaisesRegex(ValueError, 'file set'):
                write_archive(Path(directory) / 'package.zip', files)

    def test_valid_crc_does_not_hide_changed_content(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / 'original.zip'; altered = Path(directory) / 'altered.zip'
            write_archive(original, {n: b'fixture' for n in FILES})
            with zipfile.ZipFile(original) as source, zipfile.ZipFile(altered, 'w') as target:
                for name in source.namelist():
                    target.writestr(name, b'changed' if name == 'kit.blend' else source.read(name))
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                verify_archive(altered)

    def test_duplicate_and_traversal_members_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for index, extra in enumerate(('kit.blend', '../outside.blend')):
                path = Path(directory) / f'bad-{index}.zip'
                write_archive(path, {n: b'fixture' for n in FILES})
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    with zipfile.ZipFile(path, 'a') as target:
                        target.writestr(extra, b'bad')
                with self.assertRaisesRegex(ValueError, 'ZIP members'):
                    verify_archive(path)


if __name__ == '__main__':
    unittest.main()
