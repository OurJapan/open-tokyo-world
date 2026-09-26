# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import hashlib
import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_legacy_production as production
import verify_tree_prototypes as prototypes


class LegacyProductionContract(unittest.TestCase):
    def fixture(self, root, names):
        commit = 'a' * 40
        files = {}
        for name in names:
            data = b'raise RuntimeError("Source text must not execute")\n'
            blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            files[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                           'git_blob_sha1': blob, 'url': f'https://api.github.com/repos/{production.UPSTREAM}/git/blobs/{blob}',
                           'source_url': f'https://github.com/{production.UPSTREAM}/blob/{commit}/{name}'}
            if '..' not in Path(name).parts:
                target = root / 'inputs' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        manifest = root / 'manifest.json'
        manifest.write_text(json.dumps({'version': 1, 'upstream': {'commit': commit, 'repository': f'https://github.com/{production.UPSTREAM}'}, 'files': files}))
        return manifest

    def test_offline_fetch_preserves_text_and_refuses_corrupt_existing_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.fixture(root, ['work/example/build.py'])
            with patch.object(production, 'MANIFEST', manifest), patch.object(production, 'fetch_blob') as network:
                production.fetch(root / 'out', root / 'inputs')
                target = root / 'out/work/example/build.py'
                self.assertEqual(target.read_bytes(), (root / 'inputs/work/example/build.py').read_bytes())
                self.assertTrue(json.loads((root / 'out/source-record.json').read_text())['all_files_verified'])
                target.write_bytes(b'keep local changes')
                with self.assertRaisesRegex(ValueError, 'Pinned file mismatch'):
                    production.fetch(root / 'out', root / 'inputs')
                self.assertEqual(target.read_bytes(), b'keep local changes')
                network.assert_not_called()

    def test_all_paths_are_checked_before_copying_any_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.fixture(root, ['work/good.py', '../escape.py'])
            with patch.object(production, 'MANIFEST', manifest):
                with self.assertRaisesRegex(ValueError, 'Path escapes workspace'):
                    production.fetch(root / 'out', root / 'inputs')
            self.assertFalse((root / 'out').exists())

    def test_branch_url_is_rejected_before_fetch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.fixture(root, ['work/good.py'])
            data = json.loads(manifest.read_text())
            data['files']['work/good.py']['source_url'] = data['files']['work/good.py']['source_url'].replace('a' * 40, 'main')
            manifest.write_text(json.dumps(data))
            with patch.object(production, 'MANIFEST', manifest), patch.object(production, 'fetch_blob') as network:
                with self.assertRaisesRegex(ValueError, 'not pinned'):
                    production.fetch(root / 'out')
                network.assert_not_called()
            self.assertFalse((root / 'out').exists())

    def test_download_is_validated_before_installation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.fixture(root, ['work/build.py'])
            specification = json.loads(manifest.read_text())['files']['work/build.py']
            payload = (root / 'inputs/work/build.py').read_bytes()
            response = json.dumps({'encoding': 'base64', 'content': base64.b64encode(payload).decode()})
            with patch.object(production.subprocess, 'run') as run:
                run.return_value.returncode = 0
                run.return_value.stdout = response
                for key, wrong in [('bytes', 1), ('sha256', '0' * 64), ('git_blob_sha1', '0' * 40)]:
                    with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'differs from pinned'):
                        production.fetch_blob(root / 'out/build.py', {**specification, key: wrong})
                    self.assertFalse((root / 'out').exists())
                production.fetch_blob(root / 'out/build.py', specification)
                self.assertEqual((root / 'out/build.py').read_bytes(), payload)

    def test_access_failure_does_not_install_a_source_or_expose_cli_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.fixture(root, ['work/build.py'])
            specification = json.loads(manifest.read_text())['files']['work/build.py']
            with patch.object(production.subprocess, 'run') as run:
                run.return_value.returncode = 1
                run.return_value.stdout = 'untrusted CLI output'
                with self.assertRaisesRegex(ValueError, 'private upstream') as error:
                    production.fetch_blob(root / 'out/build.py', specification)
                self.assertNotIn('untrusted', str(error.exception))
            self.assertFalse((root / 'out').exists())

    def test_prototype_loader_never_executes_unreviewed_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            first = next(iter(prototypes.APPROVED))
            path = root / first
            path.parent.mkdir(parents=True)
            path.write_text('raise AssertionError("must never execute")')
            with self.assertRaisesRegex(ValueError, 'Unreviewed legacy source'):
                prototypes.load_reviewed_nodes(root)


if __name__ == '__main__':
    unittest.main()
