import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('junction', ROOT / 'scripts/tokyo_tower_topdeck_junction.py')
junction = importlib.util.module_from_spec(spec)
spec.loader.exec_module(junction)


class JunctionPreconditions(unittest.TestCase):
    def setUp(self):
        # Two levels in the lower bevel, plus the untouched upper endpoint.
        self.points = [(0, 0, 10.03), (1, 0, 10.036), (0, 0, 14), (1, 0, 14)]
        self.target = {'vertices': 4, 'lower_z_m': 10.03, 'lower_vertices': 2}

    def test_lower_bevel_moves_together_without_selecting_upper_end(self):
        indices, delta = junction.lower_end_indices(self.points, 10, self.target, .01)
        self.assertEqual(indices, [0, 1])
        self.assertAlmostEqual(delta, -.03)

    def test_repeated_application_is_rejected(self):
        points = [(x, y, z - .03 if z < 11 else z) for x, y, z in self.points]
        with self.assertRaisesRegex(ValueError, 'endpoint'):
            junction.lower_end_indices(points, 10, self.target, .01)

    def test_floor_above_member_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'floor height'):
            junction.lower_end_indices(self.points, 10.1, self.target, .01)

    def test_changed_profile_is_rejected(self):
        self.points[1] = (1, 0, 10.1)
        with self.assertRaisesRegex(ValueError, 'profile'):
            junction.lower_end_indices(self.points, 10, self.target, .01)

    def test_nonfinite_geometry_is_rejected(self):
        self.points[0] = (float('nan'), 0, 10.03)
        with self.assertRaisesRegex(ValueError, 'non-finite'):
            junction.lower_end_indices(self.points, 10, self.target, .01)

    def test_manifest_keeps_paint_floor_and_other_parts_outside_targets(self):
        plan = junction.state.load(junction.PLAN)
        self.assertEqual({t['part_id'] for t in plan['targets']},
                         {'tokyo-tower-part-009', 'tokyo-tower-part-010', 'tokyo-tower-part-011'})
        self.assertEqual(plan['input_sha256'], '361f45888ca17db9cee112bf76a55d21f2e9820f4d385f575101ffc152400f5f')
        self.assertEqual(plan['floor_part_id'], 'tokyo-tower-part-012')


if __name__ == '__main__':
    unittest.main()
