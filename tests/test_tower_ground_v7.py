# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import json,math,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import tower_ground_geometry_v7 as geo
from validate_tower_structure import check_mesh

class GroundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=json.loads((ROOT/'areas/tokyo-tower/tower-ground-v7-plan.json').read_text(encoding='utf-8'))

    def test_caps_are_four_closed_outward_flared_shells(self):
        m=geo.cap_mesh(self.plan['caps'],self.plan)
        _,parts=check_mesh(m['vertices'],m['faces'],((-55,55),(-55,55),(-2,7.01)))
        self.assertEqual(len(parts),4)
        for i,c in enumerate(self.plan['caps']):
            vertices=m['vertices'][i*16:(i+1)*16]
            self.assertTrue(all(p[2]==7 for p in vertices[12:]))
            for j in range(4):
                self.assertAlmostEqual(math.dist(vertices[j][:2],c['center'])/math.dist(vertices[12+j][:2],c['center']),.72)
                self.assertLess(min(math.dist(vertices[12+j][:2],p) for p in c['rectangle']),1e-8)

    def test_steel_lift_preserves_horizontal_and_upper_positions(self):
        for z in (0,2,7,12,22,29.9999,30,145,333):
            p=(44.,-42.,z);q=geo.lift(p)
            self.assertEqual(p[:2],q[:2])
            if z>=30:self.assertEqual(p,q)
            if z<=2:self.assertEqual(q[2]-z,5)
        self.assertLess(abs(geo.lift((0,0,29.9999))[2]-29.9999),1e-8)

    def test_eight_closed_stairs_and_monotone_risers(self):
        m=geo.details(self.plan['caps'],self.plan)['stairs']
        _,parts=check_mesh(m['vertices'],m['faces'],((-55,55),(-55,55),(-2,2)))
        heights=sorted(p['bounds'][2][1] for p in parts)
        self.assertEqual(len(heights),8)
        self.assertAlmostEqual(heights[-1],.76)
        for a,b in zip(heights,heights[1:]):self.assertAlmostEqual(b-a,.275)
        for a,b in zip(self.plan['sections'],self.plan['sections'][1:]):
            self.assertAlmostEqual(math.dist(a[0],a[1]),2)
            self.assertGreater(math.dist(a[0],b[0]),1)

    def test_ground_meets_unchanged_city_at_boundary(self):
        xmin,ymin,xmax,ymax=self.plan['scopes'][0]
        for t in (0,.25,.5,.75,1):
            for x,y in ((xmin,ymin+(ymax-ymin)*t),(xmax,ymin+(ymax-ymin)*t),(xmin+(xmax-xmin)*t,ymin),(xmin+(xmax-xmin)*t,ymax)):
                self.assertEqual(geo.profile(x,y,self.plan),0)

    def test_apron_preserves_doorway_and_outer_ground_edge(self):
        from tower_foundation_geometry_v4 import width
        self.assertAlmostEqual(geo.apron_height(0,-29,.3),4.4)
        self.assertAlmostEqual(geo.apron_height(0,-55,.3),3.2)
        for y in (-70,-60,-55,-40,-29):
            self.assertAlmostEqual(geo.apron_height(width(y),y,.3),.315)

    def test_terrain_triangles_do_not_span_the_depression(self):
        for d in self.plan['replacement'].values():
            vs=d['vertices']
            for f in d['faces']:
                if len(f)!=3:continue
                for a,b in zip(f,(*f[1:],f[0])):
                    self.assertLessEqual(math.dist(vs[a][:2],vs[b][:2]),.6000001)

    def test_parking_audit_removes_whole_obstructed_bays_only(self):
        c=json.loads((ROOT/'areas/tokyo-tower/tower-ground-v7-input.json').read_text(encoding='utf-8'))
        ids={r['bay'] for r in c['parking_audit'] if r['cap_overlap_m2']+r['apron_overlap_m2']>0}
        self.assertEqual(ids,set(c['remove_parking_bays']))
        self.assertEqual(len(c['parking_audit'])-len(ids),7)

if __name__=='__main__':unittest.main()
