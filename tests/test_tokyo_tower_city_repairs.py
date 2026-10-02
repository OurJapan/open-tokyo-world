"""Scope guards for the combined city repair, including inherited tree state."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('repairs', ROOT / 'scripts/tokyo_tower_city_repairs.py')
repairs = importlib.util.module_from_spec(spec); spec.loader.exec_module(repairs)


class CityRepairScope(unittest.TestCase):
    def fixture(self):
        names = ['orange', 'white', 'posts', 'glass', 'gasket', 'floor', 'tree', 'building']
        old = {'objects': {name: {'mesh': 'original', 'materials': ['paint'], 'properties': {},
               'rna': {'dimensions': [1, 1, 4]}, 'modifiers': ['kept']} for name in names},
               'scene': {}, 'images': {'image': 'hash'}, 'materials': {'paint': 'hash'}, 'collections': {}}
        new = copy.deepcopy(old)
        lock = {'targets': [{'object': n, 'part_id': str(i), 'paint_material': n + 'paint'}
                            for i, n in enumerate(names[:2])]}
        for t in lock['targets']:
            new['objects'][t['object']]['materials'] = [t['paint_material'], 'paint']
            new['objects'][t['object']]['properties'] = {'otw_part_id': t['part_id'], 'source_object': t['object']}
            new['materials'][t['paint_material']] = 'new'
        for name in names[2:5]:
            new['objects'][name]['mesh'] = 'extended'
            new['objects'][name]['rna']['dimensions'][-1] += .03
        return old, new, lock, names[2:5]

    def test_only_five_parts_can_change(self):
        self.assertEqual(repairs.require_repairs(*self.fixture()), 3)

    def test_unchanged_city_and_tree_geometry_remains_mandatory(self):
        for name in ['floor', 'tree', 'building']:
            args = self.fixture(); args[1]['objects'][name]['mesh'] = 'damaged'
            with self.subTest(name=name), self.assertRaises(ValueError):
                repairs.require_repairs(*args)

    def test_junction_modifier_material_or_identity_change_fails(self):
        for field in ['modifiers', 'materials', 'properties']:
            args = self.fixture(); args[1]['objects']['posts'][field] = ['wrong']
            with self.subTest(field=field), self.assertRaises(ValueError):
                repairs.require_repairs(*args)

    def test_texture_world_membership_change_fails(self):
        for key in ['scene', 'images', 'collections']:
            args = self.fixture(); args[1][key]['extra'] = 'bad'
            with self.subTest(key=key), self.assertRaises(ValueError):
                repairs.require_repairs(*args)

    def test_bounded_bevel_roundoff(self):
        old = [[0., 0., 246.22], [0., 0., 250.]]
        new = [[1e-9, 0., 246.22 + 2 ** -16], [1e-9, 0., 250.]]
        result = repairs.evaluated_coordinate_check(new, old, 246.22, .01)
        self.assertTrue(result['upper_z_exact'])

    def test_real_evaluated_changes_are_rejected(self):
        old = [[0., 0., 246.22], [0., 0., 250.]]
        for index, axis, displacement in [(0, 0, 1e-6), (0, 2, .00002), (1, 2, 1e-6)]:
            new = copy.deepcopy(old); new[index][axis] += displacement
            with self.subTest(index=index, axis=axis), self.assertRaises(ValueError):
                repairs.evaluated_coordinate_check(new, old, 246.22, .01)


if __name__ == '__main__':
    unittest.main()
