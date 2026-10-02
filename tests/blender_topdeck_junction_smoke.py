"""Saved-coordinate validator must reject plausible out-of-scope edits."""
import importlib.util
from pathlib import Path
import unittest
import bpy

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('junction', ROOT / 'scripts/tokyo_tower_topdeck_junction.py')
junction = importlib.util.module_from_spec(spec); spec.loader.exec_module(junction)


class JunctionValidation(unittest.TestCase):
    def fixture(self):
        vertices = [(x, y, z) for z in [10.03125, 14.] for x, y in [(-1, -1), (1, -1), (1, 1), (-1, 1)]]
        faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        old = bpy.data.meshes.new('Original'); old.from_pydata(vertices, [], faces); old.update()
        current = old.copy()
        for v in current.vertices[:4]:
            v.co.z = 10
        current.update()
        return old, current, 10., {'lower_vertices': 4}, .01

    def test_contact_passes_without_changing_topology(self):
        result = junction.geometry_check(*self.fixture())
        self.assertEqual(result['new_gap_m'], 0)
        self.assertEqual(result['moved_vertices'], 4)

    def test_changed_upper_end_fails(self):
        args = self.fixture(); args[1].vertices[4].co.z += .01
        with self.assertRaisesRegex(ValueError, 'Upper end'):
            junction.geometry_check(*args)

    def test_changed_horizontal_position_fails(self):
        args = self.fixture(); args[1].vertices[0].co.x += .01
        with self.assertRaisesRegex(ValueError, 'horizontal'):
            junction.geometry_check(*args)

    def test_remaining_gap_fails(self):
        args = self.fixture()
        for v in args[1].vertices[:4]:
            v.co.z += .005
        with self.assertRaisesRegex(ValueError, 'meet floor'):
            junction.geometry_check(*args)

    def test_distorted_lower_profile_fails(self):
        args = self.fixture(); args[1].vertices[0].co.z += .005
        with self.assertRaisesRegex(ValueError, 'profile distorted'):
            junction.geometry_check(*args)

    def test_material_assignment_change_fails(self):
        args = self.fixture(); args[1].polygons[0].material_index = 1
        with self.assertRaisesRegex(ValueError, 'Non-coordinate'):
            junction.geometry_check(*args)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(JunctionValidation))
    if not result.wasSuccessful():
        raise RuntimeError('Junction validation smoke checks failed')
