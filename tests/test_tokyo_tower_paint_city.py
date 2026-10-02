import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('city_paint', ROOT / 'scripts/tokyo_tower_paint_city.py')
city = importlib.util.module_from_spec(spec)
spec.loader.exec_module(city)


class CityAllowedChanges(unittest.TestCase):
    def fixture(self):
        lock = {'targets': [{'object': 'orange', 'part_id': '005', 'paint_material': 'paint005'},
                            {'object': 'white', 'part_id': '006', 'paint_material': 'paint006'}]}
        old = {'objects': {n: {'mesh': 'old', 'materials': ['original'], 'properties': {'kept': 1},
                               'modifiers': {'render': False, 'viewport': True}, 'matrix': 'identity'}
                           for n in ['orange', 'white', 'tree', 'building']},
               'scene': {'camera': 'original'}, 'images': {'texture': 'hash'}, 'materials': {'paint': 'hash'}}
        new = copy.deepcopy(old)
        for t in lock['targets']:
            obj = new['objects'][t['object']]
            obj['materials'] = [t['paint_material'], 'original']
            new['materials'][t['paint_material']] = 'new shader'
            obj['properties'].update(otw_part_id=t['part_id'], source_object=t['object'])
        return old, new, lock

    def test_only_target_materials_and_identity_are_allowed(self):
        self.assertEqual(city.require_unchanged(*self.fixture()), 2)

    def test_other_geometry_image_material_camera_change_rejected(self):
        for area in ['tree', 'building', 'images', 'materials', 'scene']:
            with self.subTest(area=area):
                old, new, lock = self.fixture()
                if area in ['tree', 'building']:
                    new['objects'][area]['mesh'] = 'changed'
                else:
                    new[area]['extra'] = 'changed'
                with self.assertRaises(ValueError):
                    city.require_unchanged(old, new, lock)

    def test_target_modifier_transform_and_existing_property_rejected(self):
        for change in ['modifier', 'matrix', 'property', 'id', 'mesh']:
            with self.subTest(change=change):
                old, new, lock = self.fixture()
                obj = new['objects']['orange']
                if change == 'modifier': obj['modifiers']['render'] = True
                elif change == 'matrix': obj['matrix'] = 'moved'
                elif change == 'property': obj['properties']['kept'] = 2
                elif change == 'mesh': obj['mesh'] = 'changed'
                else: obj['properties']['otw_part_id'] = '006'
                with self.assertRaises(ValueError):
                    city.require_unchanged(old, new, lock)

    def test_added_or_removed_object_rejected(self):
        old, new, lock = self.fixture()
        del new['objects']['tree']
        with self.assertRaisesRegex(ValueError, 'membership'):
            city.require_unchanged(old, new, lock)

    def test_shader_mask_matches_existing_bands_away_from_boundaries(self):
        plan = city.paint.load(city.paint.PLAN)
        for original in [0, 1]:
            for z in [-1., 145., 154.1, 179., 180., 205., 206., 230., 232., 256., 258., 281., 283., 307., 309., 333.]:
                self.assertEqual(city.white_mask(z, original, plan), city.paint.paint_index(z, original, plan))


if __name__ == '__main__':
    unittest.main()
