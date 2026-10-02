import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import data221_af7335da_mesh as m


class ReservedFeatureTopologyTests(unittest.TestCase):
    def setUp(self):
        self.vertices=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(0.,0.,1.)]
        self.faces=[(0,2,1),(0,1,3),(0,3,2),(1,2,3)]
        self.triangles=[[self.vertices[i] for i in f] for f in self.faces]

    def test_exact_weld_preserves_each_corner_and_closes_surface(self):
        vertices,faces=m.weld_exact(self.triangles)
        self.assertEqual([[vertices[i] for i in f] for f in faces],self.triangles)
        stats=m.surface_stats(vertices,faces)
        m.require_closed(stats)
        self.assertEqual(stats['vertices'],4)
        self.assertEqual(stats['boundary_edges'],0)
        self.assertAlmostEqual(stats['signed_volume_m3'],1/6)

    def test_nearby_vertices_are_not_silently_snapped(self):
        t=[list(face) for face in self.triangles]
        t[0][0]=(0,0,1e-7)
        vertices,faces=m.weld_exact(t)
        self.assertEqual(len(vertices),5)
        with self.assertRaises(ValueError):m.require_closed(m.surface_stats(vertices,faces))

    def test_missing_face_and_reversed_face_are_rejected(self):
        for faces in [self.faces[:-1],[self.faces[0][::-1]]+self.faces[1:]]:
            with self.subTest(faces=faces),self.assertRaises(ValueError):
                m.require_closed(m.surface_stats(self.vertices,faces))

    def test_two_closed_shells_are_not_one_building(self):
        v=self.vertices+[(x+3,y,z) for x,y,z in self.vertices]
        f=self.faces+[tuple(i+4 for i in face) for face in self.faces]
        with self.assertRaises(ValueError):m.require_closed(m.surface_stats(v,f))

    def test_invalid_geometry_is_rejected(self):
        for tri in [[(0,0,0)]*3,[(math.nan,0,0),(1,0,0),(0,1,0)]]:
            with self.subTest(tri=tri),self.assertRaises(ValueError):m.weld_exact([tri])
        with self.assertRaises(ValueError):m.surface_stats([(0,0,0),(1,0,0),(2,0,0)],[(0,1,2)])

    def test_pinned_source_accepts_float32_rounding_only(self):
        with patch.object(m,'SOURCE_TRIANGLES',4):
            self.assertEqual(m.verify_source(self.triangles,self.triangles),0)
            shifted=[[(x+2e-5,y,z) for x,y,z in t] for t in self.triangles]
            self.assertLess(m.verify_source(shifted,self.triangles),5e-5)
            shifted[0][0]=(0.001,0,0)
            with self.assertRaises(ValueError):m.verify_source(shifted,self.triangles)
            with self.assertRaises(ValueError):m.verify_source(self.triangles[:-1],self.triangles)
            with self.assertRaises(ValueError):m.verify_source([self.triangles[0][::-1]]+self.triangles[1:],self.triangles)
            with self.assertRaises(ValueError):m.verify_source([self.triangles[0][:2]]+self.triangles[1:],self.triangles)


if __name__=='__main__':unittest.main()
