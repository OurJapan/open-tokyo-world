# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('city_catalog', ROOT / 'scripts/city_catalog.py')
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


class CityCatalog(unittest.TestCase):
    def test_classification_requires_exactly_one_group(self):
        row = {'object': 'tree 1', 'collections': ['trees']}
        groups = [{'id': 'plants', 'selector': {'prefixes': ['tree ']}}]
        self.assertEqual(catalog.classify(row, groups), 'plants')
        with self.assertRaisesRegex(ValueError, 'Missing or overlapping'):
            catalog.classify(row, [])
        groups.append({'id': 'other', 'selector': {'collections': ['trees']}})
        with self.assertRaisesRegex(ValueError, 'Missing or overlapping'):
            catalog.classify(row, groups)

    def test_unknown_and_source_claims_do_not_become_grants(self):
        unknown = catalog.associate_record('tree', None, {})
        claimed = catalog.associate_record('building', 'https://example.test/tile', {})
        self.assertEqual(unknown['kind'], 'unconfirmed')
        self.assertEqual(claimed['kind'], 'source-claim')
        self.assertNotIn('license', unknown)
        self.assertNotIn('license', claimed)

    def test_same_name_record_is_not_exact_input_record(self):
        grants = {'Mori': {'kind': 'same-name-record', 'scope': 'original additions only'}}
        self.assertEqual(catalog.associate_record('Mori', None, grants)['kind'], 'same-name-record')

    def test_tower_record_rejects_another_input_version(self):
        with self.assertRaisesRegex(ValueError, 'another city version'):
            catalog.load_grants('0' * 64)

    def test_record_lookup_excludes_empty_tower_and_missing_mori_part(self):
        config = catalog.read(catalog.CONFIG)
        grants = catalog.load_grants(config['input']['sha256'])
        self.assertEqual(sum(v['kind'] == 'same-input-record' for v in grants.values()), 77)
        self.assertNotIn('Tokyo Tower decks and interior / wood', grants)
        # This standalone-only part can have a record, but is not fabricated as
        # a city object: membership is determined by the actual inventory.
        self.assertEqual(grants['Mori independent / floors and roof']['kind'], 'same-name-record')

    def test_html_scene_strings_cannot_close_data_script(self):
        value = {'object': '</script><img src=x onerror=alert(1)>', 'note': 'A&B > C'}
        encoded = catalog.json_for_html(value)
        self.assertNotIn('</script>', encoded)
        self.assertNotIn('<img', encoded)
        self.assertEqual(json.loads(encoded), value)

    def test_manifest_is_pinned_and_references_exist(self):
        config = catalog.read(catalog.CONFIG)
        # This historical inventory remains pinned to PR 12 as the shared city advances.
        city = catalog.read(ROOT / 'manifests/mori-plaza-edge-accepted.json')
        self.assertEqual(config['input']['sha256'], city['sha256'])
        self.assertEqual(config['input']['bytes'], city['bytes'])
        ids = [g['id'] for g in config['groups']]
        self.assertEqual(len(ids), len(set(ids)))
        for group in config['groups']:
            for ref in group['references']:
                self.assertTrue((ROOT / ref).is_file(), ref)

    def test_wrong_input_or_existing_catalog_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'wrong.blend'; source.write_bytes(b'wrong')
            existing = root / 'existing'; existing.mkdir(); (existing / 'notes.json').write_text('keep')
            for output in (existing, root / 'new'):
                with patch.object(catalog, 'run_phase') as worker:
                    with self.assertRaises(ValueError):
                        catalog.main(['--blender', 'unused', '--input', str(source), '--output', str(output)])
                    worker.assert_not_called()
            self.assertEqual(source.read_bytes(), b'wrong')
            self.assertEqual((existing / 'notes.json').read_text(), 'keep')
            self.assertFalse((root / 'new').exists())


if __name__ == '__main__':
    unittest.main()
