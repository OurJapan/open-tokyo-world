# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import mori_plaza_east_bend_v1 as bend


class EastBendTests(unittest.TestCase):
    def test_measured_contacts_and_fixed_model_heights(self):
        # Coordinates from the retained boundary audit, not generated test inputs.
        for u, v in [(-5.11, 85.03), (-9.52, 87.19)]:
            x, y, _ = bend.world(u, v)
            for z in (.30, .46):
                self.assertAlmostEqual(bend.height(x, y, z), .11)

    def test_all_west_scope_and_entrance_remain_outside(self):
        for u in range(-30, -13):
            for v in range(42, 76):
                x, y, _ = bend.world(u, v)
                for z in (.11, .205, .30, .46):
                    self.assertEqual(bend.height(x, y, z), z)
        extent = bend.scope_bounds()
        self.assertGreater(extent[0], -405.517)  # Separate building's enclosing bound.
        self.assertGreater(extent[1], 81.863)  # PR51 crowns' maximum north coordinate.

    def test_partition_conserves_area_and_exact_remote_faces(self):
        poly = [bend.world(u,v,.30) for u,v in [(-20,73),(4,73),(4,97),(-20,97)]]
        outside, selected = bend.partition(poly)
        self.assertAlmostEqual(sum(map(bend.outline.area, outside+selected)), 576, places=6)
        self.assertAlmostEqual(sum(map(bend.outline.area, selected)), 256, places=6)
        far = [bend.world(u,v,.30) for u,v in [(-22,60),(-20,60),(-20,62)]]
        self.assertEqual(bend.partition(far), ([far], []))
        for fragment in selected:
            for p in fragment:
                u,v = bend.local(*p[:2])
                self.assertLessEqual(abs(u+8), 8.000001)
                self.assertLessEqual(abs(v-85), 8.000001)

    def test_transition_joins_continuously(self):
        for u,v in [(-16,85),(0,85),(-8,77),(-8,93)]:
            for z in (.30,.46):
                self.assertAlmostEqual(bend.height(*bend.world(u,v)[:2],z),z)
        self.assertAlmostEqual(bend.height(*bend.world(-8,91)[:2],.46),.285)
        poly = [bend.world(u,v,.30) for u,v in [(-18,75),(2,75),(2,95),(-18,95)]]
        _,pieces = bend.partition(poly)
        corner_heights = {}
        for piece in pieces:
            for x,y,z in bend.lowered(piece):
                if (x,y) in corner_heights:
                    self.assertEqual(z,corner_heights[x,y])
                corner_heights[x,y] = z

    def test_downward_top_reoriented_and_flat_riser_removed(self):
        poly = [bend.world(u,v,.30) for u,v in [(-9,84),(-9,86),(-7,86),(-7,84)]]
        self.assertLess(bend.outline.signed_area(poly),0)
        self.assertGreater(bend.outline.signed_area(bend.lowered(poly)),0)
        riser = [bend.world(-8,v,z) for v,z in [(84,.30),(86,.30),(86,.46),(84,.46)]]
        self.assertEqual(bend.lowered(riser),[])

    def test_gap_plan_excludes_large_gaps_and_protected_seam(self):
        try:
            import shapely as sh
        except ImportError:
            self.skipTest('Optional pinned production geometry environment')
        from prepare_mori_plaza_east_bend import make_plan
        def rect(a,b,c,d):
            return [bend.world(u,v)[:2] for u,v in [(a,b),(c,b),(c,d),(a,d)]]
        surfaces = {n:[] for n in bend.ROADS}
        surfaces['OTW Mori Central Green / paving'] = [rect(-9,84,-8,86)]
        surfaces[sorted(bend.ROADS)[0]] = [rect(-7.997,84,-7,86)]
        surfaces[bend.previous.SEAM] = [rect(-8,84,-7.997,85)]
        plan = make_plan(surfaces)
        fill = sh.union_all([sh.Polygon(p) for p in plan['paving_triangles']])
        self.assertTrue(fill.covers(sh.Point(bend.world(-7.9985,85.5)[:2])))
        self.assertLess(fill.intersection(sh.Polygon(surfaces[bend.previous.SEAM][0])).area,1e-6)
        bad=copy.deepcopy(plan);bad['input_sha256']='0'*64
        with self.assertRaises(ValueError):bend.validate_plan(bad)
        surfaces[sorted(bend.ROADS)[0]]=[rect(-7.95,84,-7,86)]
        with self.assertRaises(ValueError):make_plan(surfaces)


if __name__ == '__main__':
    unittest.main()
