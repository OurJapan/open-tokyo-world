import copy
import json
import math
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import mori_facade_v2 as facade
import review


class FacadeTests(unittest.TestCase):
    def test_face_centers_have_narrow_strips_but_corners_do_not(self):
        cx,cy=facade.CENTER
        for a in facade.STRIP_ANGLES:
            r=math.radians(a)
            self.assertTrue(facade.on_strip(cx+40*math.cos(r),cy+40*math.sin(r)))
            self.assertFalse(facade.on_strip(cx+40*math.cos(r)-2*math.sin(r),cy+40*math.sin(r)+2*math.cos(r)))
        for a in facade.CORNER_DEGREES:
            self.assertFalse(facade.on_strip(cx+40*math.cos(math.radians(a)),cy+40*math.sin(math.radians(a))))

    def test_facade_patch_cannot_target_other_buildings(self):
        p=json.loads((ROOT/'patches/mori-facade-v2.json').read_text(encoding='utf8'))
        review.validate_patch(p)
        bad=copy.deepcopy(p);bad['operations'][-1]['object']='Tokyo Tower'
        with self.assertRaises(ValueError):review.validate_patch(bad)


if __name__=='__main__':unittest.main()
