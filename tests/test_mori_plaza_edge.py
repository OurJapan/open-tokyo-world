import unittest,sys,json
from pathlib import Path
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'scripts'))
from mori_plaza_edge_v1 import subtract_scope,area
from review import validate_patch
class PlazaEdgeTests(unittest.TestCase):
 def test_approved_footprints_are_preserved(self):
  for p in [[(-10,7.5,.3),(10,7.5,.3),(10,22,.3),(-10,22,.3)],[(-7,22,.3),(7,22,.3),(5,32,.11),(-5,32,.11)]]:
   kept,cut=subtract_scope(p);self.assertAlmostEqual(sum(map(area,cut)),0);self.assertAlmostEqual(sum(map(area,kept)),area(p))
 def test_two_disjoint_sides_preserve_area(self):
  p=[(-20,20,.3),(20,20,.3),(20,40,.3),(-20,40,.3)];kept,cut=subtract_scope(p)
  self.assertEqual(len(cut),2);self.assertAlmostEqual(sum(map(area,cut)),364);self.assertAlmostEqual(sum(map(area,kept))+sum(map(area,cut)),800)
 def test_no_new_objects_allowed(self):
  p=json.loads((r/'patches/mori-plaza-edge-v1.json').read_text(encoding='utf8'));validate_patch(p)
  p['operations'][0]['added_objects']=['unexpected']
  with self.assertRaises(ValueError):validate_patch(p)
