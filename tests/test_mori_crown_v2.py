import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import mori_crown_v2 as crown


class CrownV2Tests(unittest.TestCase):
    def test_four_peaks_match_contour_corners_and_valleys_lie_between(self):
        corners=crown.CORNER_DEGREES
        for i,angle in enumerate(corners):
            self.assertAlmostEqual(crown.top_height(math.radians(angle)),331.1)
            next_angle=corners[i+1] if i<3 else corners[0]+360
            self.assertAlmostEqual(crown.top_height(math.radians((angle+next_angle)/2)),323.4)
        # Former arbitrary 45-degree peak must no longer be a maximum.
        self.assertLess(crown.top_height(math.pi/4),328)

    def test_facade_below_cap_is_unchanged_and_mapping_stays_monotone(self):
        cx,cy=crown.CENTER
        for angle in range(360):
            x=cx+45*math.cos(math.radians(angle)); y=cy+45*math.sin(math.radians(angle))
            for z in (0,205,280,318,318.32):
                self.assertEqual(crown.corrected_z(x,y,z),z)
            zs=[crown.corrected_z(x,y,z/10) for z in range(3183,3320)]
            self.assertTrue(all(a<b for a,b in zip(zs,zs[1:])))

    def test_legacy_upper_edge_maps_to_new_edge(self):
        cx,cy=crown.CENTER
        for angle in range(360):
            a=math.radians(angle);x=cx+45*math.cos(a);y=cy+45*math.sin(a)
            old_top=323.4+7.7*math.sin(2*a)**2
            self.assertAlmostEqual(crown.corrected_z(x,y,old_top),crown.top_height(a))


if __name__=='__main__':unittest.main()
