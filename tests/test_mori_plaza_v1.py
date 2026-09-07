import unittest,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from mori_plaza_v1 import subtract_rectangle,area
from review import compare_reports
class PlazaContracts(unittest.TestCase):
 def test_clip_retains_crossing_polygon_area(self):
  p=[(-20,0,.3),(20,0,.3),(20,30,.3),(-20,30,.3)]
  outside,inside=subtract_rectangle(p)
  self.assertAlmostEqual(area(inside),290)
  self.assertAlmostEqual(sum(area(x) for x in outside)+area(inside),area(p))
 def test_disjoint_and_vertical_faces(self):
  for p in [[(30,0,0),(31,0,0),(30,2,0)],[(-11,10,0),(-9,10,0),(-9,10,.5),(-11,10,.5)]]:
   out,inside=subtract_rectangle(p);self.assertAlmostEqual(sum(area(x) for x in out)+area(inside),area(p))
 def test_only_exact_declared_additions_allowed(self):
  b={'ok':True,'objects':{'building':{'mesh':'same'}},'assets':[]};a=copy.deepcopy(b);a['objects']['plaza']={}
  with self.assertRaises(ValueError):compare_reports(b,a,[])
  self.assertEqual(compare_reports(b,a,[],['plaza']),['plaza'])
  a['objects']['other']={}
  with self.assertRaises(ValueError):compare_reports(b,a,[],['plaza'])
 def test_declared_addition_cannot_hide_deletion_or_mutation(self):
  b={'ok':True,'objects':{'building':{'mesh':'same'}},'assets':[]}
  for objs in [{'plaza':{}},{'building':{'mesh':'changed'},'plaza':{}}]:
   with self.assertRaises(ValueError):compare_reports(b,dict(b,objects=objs),[],['plaza'])
if __name__=='__main__':unittest.main()
