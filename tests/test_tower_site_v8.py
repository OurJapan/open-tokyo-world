# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import tower_site_geometry_v8 as geo
from tower_footway_geometry_v5 import area


class SiteGradeTests(unittest.TestCase):
    def test_shared_lot_and_door_anchors(self):
        for x in (-36,-24,-7,0,7,24,36):
            self.assertAlmostEqual(.115+geo.grade(x,-33),4.4)
            self.assertAlmostEqual(.115+geo.grade(x,-55),3.2)

    def test_no_interior_soil_or_outside_displacement(self):
        for p in ((0,0),(35,-28),(-35,-15),(61,-40),(-61,-40),(0,-91),(0,-11)):
            self.assertEqual(geo.grade(*p),0.)
        self.assertGreater(geo.grade(40,-28),4.)

    def test_boundary_is_continuous_and_nonnegative(self):
        for x in range(-65,66):
            for y in range(-95,0):
                self.assertGreaterEqual(geo.grade(x,y),0.)
                self.assertLessEqual(geo.grade(x,y),4.285)
        for x,y,dx,dy in ((60,-40,-1,0),(-60,-40,1,0),(40,-90,0,1),(40,-12,0,-1)):
            self.assertEqual(geo.grade(x,y),0.)
            self.assertLess(geo.grade(x+dx*.001,y+dy*.001),1e-6)

    def test_convex_mask_preserves_outside_area_and_height(self):
        poly=[(-2,-2,0),(2,-2,4),(2,2,4),(-2,2,0)]
        mask=[(-1,-1),(1,-1),(1,1),(-1,1)]
        parts=geo.clip_convex(poly,mask)
        self.assertAlmostEqual(sum(area(p) for p in parts),12*math.sqrt(2))
        for p in parts:
            for x,y,z in p:self.assertAlmostEqual(z,x+2)

    def test_subdivision_preserves_surface(self):
        triangle=((0,0,0),(7,0,7),(0,3,6))
        pieces=list(geo.subdivide(triangle))
        self.assertAlmostEqual(sum(area(p) for p in pieces),area(triangle))
        for tri in pieces:
            for x,y,z in tri:self.assertAlmostEqual(z,x+2*y)
            self.assertLessEqual(max(math.dist(a[:2],b[:2]) for a,b in zip(tri,(*tri[1:],tri[0]))),1.)

    def test_incline_keeps_cap_top_while_moving_base_outward(self):
        caps=[{'center':(40,40)}];slopes=[(-.3,-.3)]
        self.assertEqual(geo.incline((42,42,7),caps,slopes),(42,42,7))
        self.assertEqual(geo.incline((40,40,0),caps,slopes),(42.1,42.1,0))

    def test_plinth_lower_rings_are_below_north_terrain(self):
        vs=[(40,40,.0 if i%16<4 else 7.) for i in range(64)]
        result=geo.cladding_vertices(vs,[{'center':(40,40)}],[(-.3,-.3)])
        for i,p in enumerate(result):
            self.assertEqual(p[2],-2.1 if i%16<4 else 7.)


if __name__=='__main__':unittest.main()
