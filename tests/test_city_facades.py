# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import review_city_facades as facade


class FacadeScope(unittest.TestCase):
    def setUp(self):
        self.config = {'targets': {'wall0': {'mesh': 'mesh', 'material': 'old'}},
                       'removed_image': {'type': 'image', 'name': 'atlas', 'packed_sha256': 'pinned'}}
        self.before = {'ok': True, 'counts': {'objects': 2, 'vertices': 10, 'polygons': 5},
                       'objects': {'wall0': {'mesh': 'mesh', 'materials': ['old'], 'transform': [0]},
                                   'road': {'mesh': 'road', 'materials': ['road'], 'transform': [0]}},
                       'assets': [self.config['removed_image'], {'type': 'image', 'name': 'official', 'packed_sha256': 'kept'}]}
        self.after = copy.deepcopy(self.before)
        self.after['objects']['wall0']['materials'] = ['new']
        self.after['assets'] = copy.deepcopy(self.before['assets'][1:])

    def test_only_material_and_exact_atlas_removal_allowed(self):
        self.assertEqual(facade.compare(self.before, self.after, self.config), ['wall0'])

    def test_target_geometry_uv_or_transform_change_rejected(self):
        for field, value in [('mesh', 'changed-geometry-or-uv'), ('transform', [1])]:
            with self.subTest(field=field):
                changed = copy.deepcopy(self.after)
                changed['objects']['wall0'][field] = value
                with self.assertRaisesRegex(ValueError, 'outside material scope'):
                    facade.compare(self.before, changed, self.config)

    def test_non_target_changes_rejected(self):
        self.after['objects']['road']['materials'] = ['new road']
        with self.assertRaisesRegex(ValueError, 'Unexpected object change'):
            facade.compare(self.before, self.after, self.config)

    def test_object_addition_and_deletion_rejected(self):
        for name, add in [('extra', True), ('road', False)]:
            changed = copy.deepcopy(self.after)
            if add: changed['objects'][name] = {}
            else: del changed['objects'][name]
            with self.assertRaisesRegex(ValueError, 'Object set changed'):
                facade.compare(self.before, changed, self.config)

    def test_official_image_modification_or_loss_rejected(self):
        for assets in [[], [{'type': 'image', 'name': 'official', 'packed_sha256': 'altered'}]]:
            changed = copy.deepcopy(self.after)
            changed['assets'] = assets
            with self.assertRaisesRegex(ValueError, 'Unexpected asset change'):
                facade.compare(self.before, changed, self.config)

    def test_removing_same_name_different_atlas_rejected(self):
        self.before['assets'][0] = dict(self.before['assets'][0], packed_sha256='other')
        with self.assertRaisesRegex(ValueError, 'Pinned atlas asset differs'):
            facade.compare(self.before, self.after, self.config)

    def test_missing_material_change_or_retained_atlas_rejected(self):
        unchanged = copy.deepcopy(self.after)
        unchanged['objects']['wall0']['materials'] = ['old']
        with self.assertRaisesRegex(ValueError, 'material change missing'):
            facade.compare(self.before, unchanged, self.config)
        self.after['assets'] = copy.deepcopy(self.before['assets'])
        with self.assertRaisesRegex(ValueError, 'Unexpected asset change'):
            facade.compare(self.before, self.after, self.config)

    def test_failed_validation_rejected(self):
        self.after['ok'] = False
        with self.assertRaisesRegex(ValueError, 'Scene validation failed'):
            facade.compare(self.before, self.after, self.config)

    def test_pinned_manifest_matches_historical_city_and_audit(self):
        config = facade.read_json(facade.CONFIG)
        city = facade.read_json(ROOT / 'manifests/mori-plaza-edge-accepted.json')
        self.assertEqual(config['input']['sha256'], city['sha256'])
        self.assertEqual(config['input']['bytes'], city['bytes'])
        self.assertEqual(set(config['targets']), {'wall' + str(i) for i in range(8)})
        self.assertFalse(config['public_city_distribution'])
        self.assertFalse(set(config['legacy_empty_objects']) & set(config['targets']))
        facade.validate_cameras(facade.read_json(facade.CAMERAS))

    def test_wrong_input_and_existing_output_fail_before_blender(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'wrong.blend'
            source.write_bytes(b'wrong city')
            for output in [root / 'new', root]:
                with patch.object(facade, 'run_phase') as worker:
                    with self.assertRaises(ValueError):
                        facade.main(['--blender', 'unused', '--input', str(source), '--output', str(output)])
                    worker.assert_not_called()
            self.assertFalse((root / 'new').exists())
            self.assertEqual(source.read_bytes(), b'wrong city')


if __name__ == '__main__':
    unittest.main()
