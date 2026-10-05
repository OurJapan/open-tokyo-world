# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import json,math,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import tower_registration_geometry_v6 as geo

class RegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=json.loads((ROOT/'areas/tokyo-tower/tower-registration-v6-plan.json').read_text(encoding='utf-8'))

    def test_visible_caps_match_mapped_rectangles(self):
        for c in self.plan['caps']:
            sx,sy=c['quadrant']
            for dx in (-5.25,5.25):
                for dy in (-5.25,5.25):
                    p=geo.point((44*sx+dx,44*sy+dy,2),self.plan['caps'],True)
                    self.assertLess(min(math.dist(p[:2],q) for q in c['rectangle']),1e-8)
            self.assertLess(max(c['size']),7.)
            self.assertGreater(min(c['size']),6.7)

    def test_upper_frame_is_exactly_retained(self):
        for z in (30.,52.,150.,333.):
            for x,y in ((0.,0.),(-30.,30.),(30.,-30.)):
                self.assertEqual(geo.point((x,y,z),self.plan['caps']),(x,y,z))

    def test_blend_reaches_upper_frame_without_a_step(self):
        for sx in (-1,1):
            for sy in (-1,1):
                p=(sx*35.,sy*35.,29.99999)
                self.assertLess(math.dist(geo.point(p,self.plan['caps']),p),1e-9)

    def test_source_identity_and_height_are_explicit(self):
        self.assertEqual({c['way_id'] for c in self.plan['caps']},{str(n) for n in range(1244967004,1244967008)})
        for c in self.plan['caps']:
            self.assertEqual(c['version'],'2')
            sx,sy=c['quadrant']
            for z in (0.,2.,2.28,15.,29.):
                self.assertEqual(geo.point((44*sx,44*sy,z),self.plan['caps'])[2],z)

if __name__=='__main__':unittest.main()
