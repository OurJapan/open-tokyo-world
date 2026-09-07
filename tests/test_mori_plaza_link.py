import sys,unittest,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from mori_plaza_link_v1 import subtract_rectangle,area,FOOTPRINT,surface,geometry,local
from review import validate_patch

class PlazaLinkTests(unittest.TestCase):
 def test_clip_partition_and_taper(self):
  poly=[(-9,20,.3),(9,20,.3),(9,35,.3),(-9,35,.3)]
  outside,inside=subtract_rectangle(poly)
  self.assertAlmostEqual(area(inside),120)
  self.assertAlmostEqual(sum(map(area,outside))+area(inside),area(poly))
  self.assertTrue(all(22-1e-8<=p[1]<=32+1e-8 and abs(p[0])<=7-.2*(p[1]-22)+1e-8 for p in inside))
 def test_previous_footprint_untouched(self):
  poly=[(-10,7.5,.3),(10,7.5,.3),(10,22,.3),(-10,22,.3)]
  outside,inside=subtract_rectangle(poly)
  self.assertEqual(area(inside),0)
  self.assertAlmostEqual(sum(map(area,outside)),290)
 def test_join_and_scope(self):
  self.assertAlmostEqual(surface(22),.3);self.assertAlmostEqual(surface(32),.11)
  for part in ('paving','planters','planting'):
   for p in geometry(part).vertices:
    u,v,z=local(p)
    self.assertTrue(21.999<v<32.001 and abs(u)<7.001-.2*(v-22))
 def test_scope_cannot_replace_accepted_objects(self):
  d=json.loads((ROOT/'patches/mori-plaza-link-v1.json').read_text(encoding='utf8'));validate_patch(d)
  d['operations'][0]['added_objects'][0]='OTW Mori entry plaza / paving'
  with self.assertRaises(ValueError):validate_patch(d)

if __name__=='__main__':unittest.main()
