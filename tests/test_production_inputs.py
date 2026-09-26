# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import import_legacy_inputs as importer
import replay_production_inputs as replay


class RecoveredInputsContract(unittest.TestCase):
    def fixture(self, root):
        files = {}
        for name, data, kind in [('work/a.json', b'{"x":1}', 'production-input'),
                                 ('work/b.json', b'{"y":2}', 'production-input'),
                                 ('outputs/prior.blend', b'original scene', 'intermediate-scene')]:
            path = root / 'original' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            files[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'kind': kind}
        manifest = root / 'inputs.json'
        manifest.write_text(json.dumps({'version': 1, 'files': files, 'distribution': 'local-only'}))
        return manifest

    def test_default_import_excludes_scenes_and_keeps_original_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); manifest = self.fixture(root)
            with patch.object(importer, 'MANIFEST', manifest):
                result = importer.import_inputs(root / 'original', root / 'copy')
            self.assertEqual(result['files'], 2)
            self.assertFalse((root / 'copy/outputs').exists())
            self.assertEqual((root / 'original/work/a.json').read_bytes(), b'{"x":1}')
            self.assertEqual((root / 'copy/work/a.json').read_bytes(), b'{"x":1}')

    def test_missing_late_input_fails_before_any_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); manifest = self.fixture(root)
            (root / 'original/work/b.json').unlink()
            with patch.object(importer, 'MANIFEST', manifest), self.assertRaisesRegex(ValueError, 'Missing file'):
                importer.import_inputs(root / 'original', root / 'copy')
            self.assertFalse((root / 'copy').exists())

    def test_changed_destination_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); manifest = self.fixture(root)
            target = root / 'copy/work/b.json'; target.parent.mkdir(parents=True)
            target.write_bytes(b'keep edits')
            with patch.object(importer, 'MANIFEST', manifest), self.assertRaisesRegex(ValueError, 'Pinned file mismatch'):
                importer.import_inputs(root / 'original', root / 'copy')
            self.assertEqual(target.read_bytes(), b'keep edits')
            self.assertFalse((root / 'copy/work/a.json').exists())

    def test_explicit_scene_import_checks_and_copies_all(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); manifest = self.fixture(root)
            with patch.object(importer, 'MANIFEST', manifest):
                result = importer.import_inputs(root / 'original', root / 'copy', include_scenes=True)
            self.assertEqual(result['files'], 3)
            self.assertEqual((root / 'copy/outputs/prior.blend').read_bytes(), b'original scene')

    def test_path_escape_is_rejected_before_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); manifest = self.fixture(root)
            data = json.loads(manifest.read_text())
            data['files']['../escape'] = data['files']['work/a.json']
            manifest.write_text(json.dumps(data))
            with patch.object(importer, 'MANIFEST', manifest), self.assertRaisesRegex(ValueError, 'Path escapes workspace'):
                importer.import_inputs(root / 'original', root / 'copy')
            self.assertFalse((root / 'copy').exists())

    def test_json_comparison_ignores_formatting_but_keeps_array_order(self):
        with tempfile.TemporaryDirectory() as folder:
            a, b = Path(folder) / 'a.json', Path(folder) / 'b.json'
            a.write_text('{"first":[1,2],"second":3}')
            b.write_text('{\n "second":3, "first":[1,2]\n}')
            self.assertEqual(replay.content_signature(a), replay.content_signature(b))
            b.write_text('{"first":[2,1],"second":3}')
            self.assertNotEqual(replay.content_signature(a), replay.content_signature(b))

    def test_replay_rejects_existing_output_before_loading_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'new replay output'):
                replay.preflight(Path('missing-sources'), Path('missing-inputs'), Path(folder))


if __name__ == '__main__':
    unittest.main()
