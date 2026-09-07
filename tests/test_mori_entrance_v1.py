import copy
import json
import math
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import mori_entrance_v1 as entrance
import review


class EntranceTests(unittest.TestCase):
    def test_generated_members_are_closed_finite_nonzero_solids(self):
        for part in ('aluminum','ceiling','clear glass'):
            vertices,faces,materials,smooth=entrance.geometry(part)
            self.assertTrue(vertices and faces)
            self.assertEqual(len(faces),len(materials))
            self.assertEqual(len(faces),len(smooth))
            self.assertTrue(all(math.isfinite(c) for p in vertices for c in p))
            edges=Counter()
            for face in faces:
                self.assertEqual(len(face),len(set(face)))
                self.assertTrue(all(0<=i<len(vertices) for i in face))
                for a,b in zip(face,face[1:]+face[:1]):edges[a,b]+=1
                # Newell area covers convex prism caps and cylinder walls.
                normal=[0.,0.,0.]
                for a,b in zip(face,face[1:]+face[:1]):
                    p,q=vertices[a],vertices[b]
                    for k in range(3):normal[k]+=(p[(k+1)%3]-q[(k+1)%3])*(p[(k+2)%3]+q[(k+2)%3])
                self.assertGreater(sum(n*n for n in normal),1e-12)
            self.assertTrue(all(count==1 and edges[b,a]==1 for (a,b),count in edges.items()))

    def test_patch_cannot_target_accepted_podium_or_city_tiles(self):
        patch=json.loads((ROOT/'patches/mori-entrance-v1.json').read_text(encoding='utf8'))
        review.validate_patch(patch)
        for target in ('Mori JP podium / stone','PLATEAU_data221'):
            bad=copy.deepcopy(patch);bad['operations'][-1]['object']=target
            with self.assertRaises(ValueError):review.validate_patch(bad)


if __name__=='__main__':unittest.main()
