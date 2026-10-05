"""Acceptance invariants for the bounded road plan; no Blender or Shapely needed."""
import json,math,sys,unittest
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import tower_footway_geometry_v5 as xy
from tower_site_geometry_v8 import grade
from road_geometry_v2 import partition,route_uv,scope_distance

class RoadGeometryPlanTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.plan=json.loads((ROOT/'areas/tokyo-tower/road-geometry-v2-plan.json').read_text(encoding='utf-8'))

 def test_walking_surface_has_closed_consistent_shell(self):
  r=self.plan['replacement']['pavement_0 unified road'];counts=Counter();directed=Counter();volume=0
  for f in r['faces']:
   for a,b in zip(f,f[1:]+f[:1]):counts[tuple(sorted((a,b)))]+=1;directed[(a,b)]+=1
   a=r['vertices'][f[0]]
   for i in range(1,len(f)-1):
    b,c=(r['vertices'][f[j]] for j in (i,i+1));volume+=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
  self.assertEqual(set(counts.values()),{2});self.assertTrue(all(directed[(b,a)]==n for (a,b),n in directed.items()));self.assertGreater(volume,0)

 def test_replacement_retains_adopted_grade_and_scope(self):
  for name,r in self.plan['replacement'].items():
   bases=[.3,.46] if name.startswith('pavement') else [.11] if name.startswith('parking') else [.3]
   for p in r['vertices']:
    self.assertTrue(xy.inside(p,self.plan['scopes']));self.assertLess(min(abs(p[2]-grade(*p[:2])-z) for z in bases),1e-6)

 def test_clipping_preserves_outside_3d_plane(self):
  plan={'scopes':[(0,0,2,2)]};poly=[(-1,-1,.3),(3,-1,.3),(3,3,.3),(-1,3,.3)]
  parts,removed=partition(poly,plan)
  self.assertAlmostEqual(sum(xy.area(p) for p in parts),12);self.assertAlmostEqual(sum(xy.area(p) for p in removed),4)
  outside=[(90,90,.3),(91,90,.3),(91,91,.3)];self.assertEqual(partition(outside,plan),([outside],[]))

 def test_route_coordinates_follow_distance_and_side(self):
  routes=[{'points':[(0,0),(0,10)]}]
  self.assertEqual(route_uv((2,3,0),routes),(3.,-2.));self.assertEqual(route_uv((-2,7,0),routes),(7.,2.))

 def test_adjoining_scopes_have_no_internal_boundary_ramp(self):
  self.assertEqual(scope_distance((-37,-60)),5.)
  self.assertEqual(scope_distance((-72,-40)),0.)

if __name__=='__main__':unittest.main()
