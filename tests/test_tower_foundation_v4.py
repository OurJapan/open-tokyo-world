# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import tower_foundation_geometry_v4 as g
from validate_tower_structure import check_mesh


class FoundationTerrainTests(unittest.TestCase):
    def test_upper_frame_and_vertical_levels_are_preserved(self):
        for z in (52.,145.1,246.,333.):
            p=(12.3,-7.2,z)
            self.assertEqual(g.lower_point(p),p)
        self.assertAlmostEqual(g.lower_point((46.6066666667,-46.6066666667,2))[0],44)
        self.assertEqual(g.lower_point((30.,-30.,17.))[2],17.)

    def test_foundation_caps_keep_size_and_match_88m_axes(self):
        for sign in (-1,1):
            center=g.foundation_point((sign*47.5,sign*47.5,1))
            self.assertEqual(center,(sign*44.,sign*44.,1))
        a=g.foundation_point((42.25,42.25,0));b=g.foundation_point((52.75,52.75,2))
        self.assertEqual(tuple(b[i]-a[i] for i in range(3)),(10.5,10.5,2))

    def test_apron_retains_doorway_and_removes_high_side_wall(self):
        for y in (-36,-33,-29):
            for x in (-7,0,7):self.assertAlmostEqual(g.surface_height(x,y,.3),4.4)
        for y in (-70,-65,-55,-40,-29):
            for sign in (-1,1):self.assertAlmostEqual(g.surface_height(sign*g.width(y),y,.3),.315)

    def test_saved_surface_recipe_is_closed_and_outward(self):
        ground=[[.3 for p in row] for row in g.grid()]
        m=g.paving_mesh(ground)
        stats,parts=check_mesh(m['vertices'],m['faces'],((-37,37),(-71,-28),(-.1,4.5)))
        self.assertEqual(stats['components'],2)
        self.assertTrue(stats['closed_edge_incidence_two'])

    def test_apron_avoids_south_building_corner_and_moved_caps(self):
        self.assertLess(g.width(-70),10)
        self.assertLess(max(g.width(y) for y in range(-70,-28)),44.-10.5/2)


if __name__=='__main__':unittest.main()
