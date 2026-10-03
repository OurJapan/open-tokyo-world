import math
import unittest

from scripts.tower_structure_v1 import MeshBuilder
from scripts import tower_foottown_geometry_v2 as foot


class RecordingBuilder(MeshBuilder):
    def __init__(self):
        super().__init__()
        self.parts = []

    def box(self, group, center, size):
        self.parts.append(("box", group, center, size))
        super().box(group, center, size)

    def beam(self, group, a, b, radius, sides=8):
        self.parts.append(("beam", group, a, b, radius))
        super().beam(group, a, b, radius, sides)


def bounds(p):
    if p[0] == "box":
        return tuple((c-s/2, c+s/2) for c,s in zip(p[2], p[3]))
    length=math.dist(p[2],p[3])
    radii=[p[4]*math.sqrt(max(0,1-((c-a)/length)**2)) for a,c in zip(p[2],p[3])]
    return tuple((min(a,c)-r,max(a,c)+r) for a,c,r in zip(p[2],p[3],radii))


def overlaps(a,b):
    return all(min(x[1],y[1])-max(x[0],y[0])>1e-8 for x,y in zip(a,b))


class FootTownV2GeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b=RecordingBuilder()
        foot.geometry(cls.b)

    def test_closed_finite_geometry_and_bounded_extent(self):
        self.assertEqual(set(self.b.groups),set(foot.GROUPS))
        self.assertEqual(set(foot.MATERIALS),set(foot.GROUPS))
        for mesh in self.b.groups.values():
            self.assertTrue(all(math.isfinite(c) for v in mesh["vertices"] for c in v))
            edges={}
            for face in mesh["faces"]:
                for a,b in zip(face,face[1:]+face[:1]):
                    edges.setdefault(tuple(sorted((a,b))),[]).append((a,b))
            self.assertTrue(all(len(v)==2 and v[0]==v[1][::-1] for v in edges.values()))
        for p in self.b.parts:
            bb=bounds(p)
            self.assertGreaterEqual(bb[0][0],-36.5-1e-8)
            self.assertLessEqual(bb[0][1],36.5+1e-8)
            self.assertGreaterEqual(bb[1][0],-33.5-1e-8)
            self.assertLessEqual(bb[1][1],33.5+1e-8)
            self.assertGreaterEqual(bb[2][0],-1e-8)
            self.assertLessEqual(bb[2][1],26)

    def test_world_fixed_shaft_and_stair_entry_remain_clear(self):
        clearances=(foot.ROOF_ACCESS_CLEAR,
                    ((-2.35,2.35),(-2.35,2.35),(16.0,26.0)),
                    ((-4.8,-3.96),(3.71,5.09),(16.21,18.29)))
        for p in self.b.parts:
            for clear in clearances:
                self.assertFalse(overlaps(bounds(p),clear),p)

    def test_north_entrance_has_four_recessed_door_pairs_without_solid_wall(self):
        opaque=[p for p in self.b.parts if p[1] in (foot.SHELL,foot.CLADDING)]
        for x in foot.MAIN_ENTRY_CENTRES:
            doorway=((x-.775,x+.775),(26.75,27.25),(.02,3.35))
            self.assertFalse(any(overlaps(bounds(p),doorway) for p in opaque))
            panes=[p for p in self.b.parts if p[0]=="box" and p[1]==foot.GLASS
                   and abs(p[2][1]-26.97)<.002 and abs(p[2][0]-x)<.775
                   and bounds(p)[2][0]<1]
            self.assertEqual(len(panes),2)
            self.assertTrue(all(abs(bounds(p)[2][0]-.02)<1e-8 for p in panes))
            self.assertAlmostEqual(max(bounds(p)[0][1] for p in panes)-
                                   min(bounds(p)[0][0] for p in panes),1.55)
        # Main canopy reaches north; the distinct second-floor landing is south.
        self.assertTrue(any(p[1]==foot.METAL and bounds(p)[1][1]>33 for p in self.b.parts))
        landing=[p for p in self.b.parts if p[0]=="box" and p[1]==foot.ROOF
                 and abs(p[2][1]+30.2)<1e-8]
        self.assertEqual(len(landing),1)
        self.assertAlmostEqual(bounds(landing[0])[2][1],4.4)

    def test_screen_has_real_openings_and_core_roof_preserves_shaft(self):
        screen=[p for p in self.b.parts if p[1]==foot.SCREEN]
        self.assertGreater(len(screen),1400)
        self.assertTrue(all(p[0]=="beam" for p in screen))
        self.assertTrue(all(p[4]==.004 for p in screen))
        self.assertTrue(all(p[2][1]>29 for p in screen))
        core_roof=[p for p in self.b.parts if p[0]=="box" and p[1]==foot.ROOF
                   and abs(bounds(p)[2][1]-24.2)<1e-8]
        self.assertEqual(len(core_roof),4)
        self.assertAlmostEqual(sum(p[3][0]*p[3][1] for p in core_roof),14*7.1-4.7**2)

    def test_ground_contact_and_south_access_rises_from_current_scene_ground(self):
        boxes=[p for p in self.b.parts if p[0]=="box"]
        floor=[p for p in boxes if p[1]==foot.ROOF and abs(p[2][1]-30.05)<1e-8]
        self.assertEqual(len(floor),1)
        self.assertEqual(bounds(floor[0])[2],(0,.02))
        base=[p for p in boxes if p[1]==foot.SHELL and p[3][:2]==(73,58)]
        self.assertEqual(len(base),1)
        self.assertEqual(bounds(base[0])[2],(0,.02))
        columns=[p for p in boxes if p[1]==foot.METAL and p[3][:2]==(.64,.66)]
        self.assertEqual(len(columns),4)
        self.assertTrue(all(bounds(p)[2]==(0,7.25) for p in columns))
        thresholds=[p for p in boxes if p[1]==foot.METAL
                    and abs(p[2][1]-27.045)<1e-8 and abs(p[2][2]-.0125)<1e-8]
        self.assertEqual(len(thresholds),4)
        self.assertTrue(all(abs(p[3][2]-.015)<1e-8 for p in thresholds))
        treads=sorted((p for p in boxes if p[1]==foot.ROOF
                       and abs(p[2][1]+30.4)<1e-8),key=lambda p:p[2][2])
        self.assertEqual(len(treads),25)
        heights=[.02]+[bounds(p)[2][1] for p in treads]
        self.assertAlmostEqual(heights[-1],4.4)
        self.assertTrue(all(abs(c-a-4.38/25)<1e-8 for a,c in zip(heights,heights[1:])))

    def test_south_duct_handedness_and_two_lower_core_windows(self):
        boxes=[p for p in self.b.parts if p[0]=="box"]
        ducts=[p for p in boxes if p[1]==foot.METAL and abs(p[2][1]+29.25)<1e-8]
        tall=[p for p in ducts if p[3][2]==6.88]
        low=[p for p in ducts if p[3][2]==2.42]
        separate=[p for p in ducts if p[3][2]==4.70]
        self.assertEqual(len(tall),1)
        self.assertEqual(len(low),1)
        self.assertEqual(len(separate),1)
        # Looking north at the south facade, world +X is the viewer's right.
        self.assertGreater(tall[0][2][0],low[0][2][0])
        self.assertLess(separate[0][2][0],low[0][2][0])
        lower=[p for p in boxes if p[1]==foot.GLASS and abs(p[2][1]+4.345)<1e-8
               and 19.8< p[2][2]<20.45]
        self.assertEqual(len(lower),2)

    def test_south_outer_handrail_connects_to_landing_without_blocking_access(self):
        # Traverse actual generated rail endpoints from the stair foot to the
        # far landing end. Before this repair the two chains stop 0.32 m apart.
        rails=[p for p in self.b.parts if p[0]=='beam' and p[1]==foot.METAL
               and p[4]==.032 and max(p[2][1],p[3][1]) < -29]
        graph={}
        for p in rails:
            a,c=(tuple(round(v,6) for v in point) for point in p[2:4])
            graph.setdefault(a,set()).add(c)
            graph.setdefault(c,set()).add(a)
        visited=set(); pending=[(-14.2,-31.13,1.07)]
        while pending:
            point=pending.pop()
            if point in visited:
                continue
            visited.add(point); pending.extend(graph.get(point,set())-visited)
        self.assertIn((8.0,-31.38,5.45),visited)
        passage=((-7.7,7.7),(-31.2,-29.2),(4.5,6.5))
        self.assertFalse(any(overlaps(bounds(p),passage) for p in rails))


if __name__ == "__main__":
    unittest.main()
