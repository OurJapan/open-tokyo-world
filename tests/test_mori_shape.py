import importlib.util
import math
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('mori_shape',Path(__file__).resolve().parents[1]/'scripts/mori_shape.py')
shape=importlib.util.module_from_spec(spec);spec.loader.exec_module(shape)


class MoriShapeTests(unittest.TestCase):
    def test_crown_does_not_move_lower_facade_or_top_edge(self):
        cx,cy=shape.CENTER
        for degrees in range(0,360,5):
            x=cx+45*math.cos(math.radians(degrees));y=cy+45*math.sin(math.radians(degrees))
            for z in (0,100,205,323.4,331.1):
                self.assertEqual(shape.crown_offset(x,y,z),0)
            for z in range(206,324):
                self.assertTrue(-8<=shape.crown_offset(x,y,z)<=0)
        self.assertLess(shape.crown_offset(cx+45,cy,310),-7)

    def test_crown_vertical_mapping_does_not_fold(self):
        cx,cy=shape.CENTER
        for degrees in range(0,360,5):
            x=cx+45*math.cos(math.radians(degrees));y=cy+45*math.sin(math.radians(degrees))
            values=[z/10+shape.crown_offset(x,y,z/10) for z in range(2000,3320)]
            self.assertTrue(all(a<b for a,b in zip(values,values[1:])))


if __name__=='__main__':unittest.main()
