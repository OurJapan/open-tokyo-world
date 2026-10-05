# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import json,math,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import tower_footway_geometry_v5 as g
from validate_tower_structure import check_mesh

def contains(mesh,p):
    for f in mesh['faces']:
        ps=[mesh['vertices'][i] for i in f]
        if len(ps)!=3 or max(v[2] for v in ps)-min(v[2] for v in ps)>1e-6:continue
        s=[(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]) for a,b in zip(ps,ps[1:]+ps[:1])]
        if min(s)>=-1e-7 or max(s)<=1e-7:return True
    return False

class FootwayClippingTests(unittest.TestCase):
    def test_clipping_keeps_outside_area_and_interpolated_height(self):
        p=[(-2,-2,0),(2,-2,4),(2,2,4),(-2,2,0)]
        outside,inside=g.cut(p,(-1,-1,1,1))
        self.assertAlmostEqual(sum(g.area(q) for q in outside)+g.area(inside),g.area(p))
        for q in inside:self.assertAlmostEqual(q[2],q[0]+2)
        self.assertAlmostEqual(g.area(inside),4*math.sqrt(2))

    def test_vertical_curb_is_clipped_without_xy_area_assumption(self):
        p=[(-3,0,.3),(3,0,.3),(3,0,.46),(-3,0,.46)]
        outside,inside=g.cut(p,(-1,-1,1,1))
        self.assertAlmostEqual(g.area(inside),.32)
        self.assertAlmostEqual(sum(g.area(q) for q in outside),.64)

    def test_out_of_scope_polygon_is_identical(self):
        p=[(-5,0,0),(-4,0,0),(-4,1,0)]
        outside,inside=g.subtract(p,[(0,0,2,2),(3,0,4,2)])
        self.assertEqual(outside,[p]);self.assertEqual(inside,[])

    def test_prepared_paving_is_closed_and_outward(self):
        plan=json.loads((ROOT/'areas/tokyo-tower/tower-footway-v5-plan.json').read_text(encoding='utf-8'))
        m=plan['replacement']['pavement_0 unified road']
        stats,_=check_mesh(m['vertices'],m['faces'],((-51.01,67.01),(-63.01,61.01),(.299,.461)))
        self.assertTrue(stats['closed_edge_incidence_two'])
        self.assertTrue(stats['consistent_outward_winding'])

    def test_carriageways_and_walk_route_are_separate_and_caps_clear(self):
        plan=json.loads((ROOT/'areas/tokyo-tower/tower-footway-v5-plan.json').read_text(encoding='utf-8'))
        road=plan['replacement']['asphalt 15s road detail'];walk=plan['replacement']['pavement_0 unified road']
        for p in ((51.9,-35),(58.8,-48),(59.8,-54)):
            self.assertTrue(contains(road,p),p);self.assertFalse(contains(walk,p),p)
        self.assertTrue(contains(walk,(50.5,44)))
        for p in ((44,-44),(44,44)):
            for m in plan['replacement'].values():self.assertFalse(contains(m,p))

if __name__=='__main__':unittest.main()
