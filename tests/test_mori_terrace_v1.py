import sys,unittest,math
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from mori_terrace_v1 import geometry,DECK,ORIGIN
class TerraceGeometry(unittest.TestCase):
 def test_closed_finite_components_and_footprint(self):
  for part in ('soil','leaf','wood','gasket'):
   g=geometry(part);edges=Counter()
   for f in g.faces:
    for a,b in zip(f,f[1:]+f[:1]):edges[(a,b)]+=1
   for (a,b),count in edges.items():self.assertEqual(count,edges[(b,a)],(part,a,b))
   for x,y,z in g.vertices:
    self.assertTrue(all(math.isfinite(t) for t in (x,y,z)))
    u=(2*(x-ORIGIN[0])-(y-ORIGIN[1]))/math.sqrt(5);v=((x-ORIGIN[0])+2*(y-ORIGIN[1]))/math.sqrt(5)
    self.assertTrue(.5<u<16 and 2<v<15.5,(part,u,v))
    self.assertGreaterEqual(z,DECK)
 def test_repeatable_generation(self):
  self.assertEqual(geometry('leaf').vertices,geometry('leaf').vertices)
if __name__=='__main__':unittest.main()
