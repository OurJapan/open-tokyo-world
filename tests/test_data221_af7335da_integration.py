from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from validate_data221_af7335da_integration import topology_extras


class ExtraTopologyTests(unittest.TestCase):
    def setUp(self):
        self.v=[(0,0,0),(1,0,0),(0,1,0),(0,0,1)]
        self.f=[(0,2,1),(0,1,3),(0,3,2),(1,2,3)]

    def test_closed_tetrahedron_vertex_links(self):
        self.assertEqual(topology_extras(self.v,self.f),{
            'duplicate_geometric_faces':0,'vertex_links_checked':4,'nonmanifold_vertex_links':0})

    def test_duplicate_face_is_detected_even_with_new_vertex_indices(self):
        extra=[self.v[i] for i in self.f[0]]
        report=topology_extras(self.v+extra,self.f+[(4,5,6)])
        self.assertEqual(report['duplicate_geometric_faces'],1)

    def test_pinched_vertex_is_detected_despite_two_faces_per_edge(self):
        # Two tetrahedral shells share one vertex; its link has two cycles.
        vertices=self.v+[(-1,0,0),(0,-1,0),(0,0,-1)]
        mapping={0:0,1:4,2:5,3:6}
        faces=self.f+[tuple(mapping[i] for i in face) for face in self.f]
        report=topology_extras(vertices,faces)
        self.assertEqual(report['duplicate_geometric_faces'],0)
        self.assertEqual(report['nonmanifold_vertex_links'],1)


if __name__=='__main__':unittest.main()
