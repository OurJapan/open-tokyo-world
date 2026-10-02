# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import mori_plaza_west_path_v1 as path
from review import validate_patch


class WestPathTests(unittest.TestCase):
    def test_measured_north_segment_meets_paving(self):
        for u, v, z in [(-20.270, 64.458, .30), (-24.851, 64.142, .30), (-23.238, 68.049, .46)]:
            x, y, _ = path.world(u, v)
            self.assertEqual(path.factor(x, y), 0)
            self.assertAlmostEqual(path.height(x, y, z), .11)

    def test_existing_core_and_side_transition_are_not_lowered_twice(self):
        for u, v in [(-22, 50), (-24, 52), (-28, 53)]:
            x, y, _ = path.world(u, v)
            z = .11 + (.46 - .11) * path.previous.factor(x, y)
            self.assertAlmostEqual(path.height(x, y, z), z)
        # Float32 XY may lie microscopically outside the previous flat core,
        # while its saved height rounds just below .11. Never divide that error
        # by a nearly zero old transition factor and lower the adopted plane.
        x, y, _ = path.world(-26.000001, 48.1836056)
        saved = path.outline.f32(.11)
        self.assertEqual(path.height(x, y, saved), saved)

    def test_outer_edge_returns_to_saved_height(self):
        for u, v in [(-30, 61), (-14, 61), (-22, 47), (-22, 75)]:
            x, y, _ = path.world(u, v)
            z = .11 + (.30 - .11) * path.previous.factor(x, y)
            self.assertAlmostEqual(path.factor(x, y), 1)
            self.assertAlmostEqual(path.height(x, y, z), z)
        x, y, _ = path.world(-22, 73)
        self.assertAlmostEqual(path.height(x, y, .30), .205)

    def test_partition_conserves_area_and_bounds(self):
        poly = [path.world(u, v, .30) for u, v in [(-35, 40), (-9, 40), (-9, 80), (-35, 80)]]
        outside, selected = path.partition(poly)
        self.assertAlmostEqual(sum(map(path.outline.area, outside + selected)), 1040)
        self.assertAlmostEqual(sum(map(path.outline.area, selected)), 16 * 28)
        for part in selected:
            for point in part:
                u, v = path.local(*point[:2])
                self.assertLessEqual(abs(u + 22), 8.000001)
                self.assertLessEqual(abs(v - 61), 14.000001)

    def test_flat_riser_disappears_and_exterior_is_kept(self):
        poly = [path.world(-22, v, z) for v, z in [(60, .30), (62, .30), (62, .46), (60, .46)]]
        self.assertEqual(path.lowered(poly), [])
        outside = [path.world(u, v, .30) for u, v in [(-60, 40), (-50, 40), (-50, 45)]]
        self.assertEqual(path.partition(outside), ([outside], []))

    def test_patch_requires_exact_targets_hashes_and_single_increment(self):
        patch = json.loads((ROOT / 'patches/mori-plaza-west-path-v1.json').read_text())
        validate_patch(patch)
        for change in ('scope', 'hash', 'stack'):
            altered = copy.deepcopy(patch)
            if change == 'scope':
                altered['operations'][0]['road_mesh_sha256']['ground'] = '0' * 64
            elif change == 'hash':
                altered['operations'][0]['road_mesh_sha256']['asphalt 15s road detail'] = 'unknown'
            else:
                altered['operations'] *= 2
            with self.assertRaises(ValueError):
                validate_patch(altered)

    def test_seam_plan_requires_adopted_input_and_flat_core(self):
        ring = [path.world(u, v)[:2] for u, v in [(-24, 60), (-23.998, 60), (-23.998, 62), (-24, 62)]]
        plan = {'version': 1, 'input_sha256': path.INPUT_SHA256,
                'paving_triangles': [[ring[0], ring[1], ring[2]], [ring[0], ring[2], ring[3]]],
                'paving_rings': [ring], 'audit': {}}
        path.validate_plan(plan)
        for change in ('input', 'extent', 'orientation'):
            altered = copy.deepcopy(plan)
            if change == 'input':
                altered['input_sha256'] = '0' * 64
            elif change == 'extent':
                altered['paving_rings'][0][0] = path.world(-40, 60)[:2]
            else:
                altered['paving_triangles'][0].reverse()
            with self.assertRaises(ValueError):
                path.validate_plan(altered)

    def test_gap_plan_preserves_existing_seam_and_excludes_distant_ground(self):
        try:
            import shapely as sh
        except ImportError:
            self.skipTest('Production Shapely is optional in portable checks')
        from prepare_mori_plaza_west_path import make_plan
        def rectangle(left, bottom, right, top):
            return [path.world(u, v)[:2] for u, v in [(left, bottom), (right, bottom), (right, top), (left, top)]]
        names = sorted(path.ROADS)
        surfaces = {name: [] for name in names}
        surfaces['OTW Mori Central Green / paving'] = [rectangle(-24, 60, -23, 62)]
        surfaces[names[0]] = [rectangle(-22.997, 60, -22, 62)]
        surfaces[path.previous.SEAM] = [rectangle(-23, 60, -22.997, 61)]
        plan = make_plan(surfaces)
        actual = sh.union_all([sh.Polygon(p) for p in plan['paving_triangles']])
        vertices, faces = path.seam_mesh(plan)
        world_vertices = [[p[i] + path.SEAM_ORIGIN[i] for i in range(3)] for p in vertices]
        saved_top = sh.union_all([sh.Polygon([world_vertices[i][:2] for i in face])
                                  for face in faces if all(abs(world_vertices[i][2] - .11) < 1e-6 for i in face)])
        self.assertLess(actual.symmetric_difference(saved_top).area, 1e-7)
        self.assertEqual(plan['audit']['mesh_origin_m'], path.SEAM_ORIGIN)
        prior = sh.Polygon(surfaces[path.previous.SEAM][0])
        self.assertLess(actual.intersection(prior).area, .000001)
        self.assertGreater(actual.area, .0025)
        nearby = sh.Polygon(surfaces['OTW Mori Central Green / paving'][0]).union(prior).buffer(.0101, join_style=2).intersection(
            sh.Polygon(surfaces[names[0]][0]).buffer(.0101, join_style=2))
        self.assertLess(actual.difference(nearby).area, 1e-7)
        self.assertTrue(actual.covers(sh.Point(path.world(-22.9985, 61.5)[:2])))
        surfaces[names[0]] = [rectangle(-22.95, 60, -22, 62)]
        with self.assertRaises(ValueError):
            make_plan(surfaces)


if __name__ == '__main__':
    unittest.main()
