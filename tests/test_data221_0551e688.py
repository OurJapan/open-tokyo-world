from pathlib import Path
import sys
import unittest
import copy
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import data221_0551e688_mesh as m
from review_data221_0551e688 import compare_images, VIEWS


class BatchZeroTests(unittest.TestCase):
    def setUp(self):
        self.vertices = [(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(0.,0.,1.)]
        self.faces = [(0,2,1),(0,1,3),(0,3,2),(1,2,3)]
        self.triangles = [[self.vertices[i] for i in face] for face in self.faces]

    def test_source_rejects_other_feature_size_and_winding(self):
        with self.assertRaises(ValueError): m.verify_source(self.triangles,self.triangles)
        with patch.object(m,'SOURCE_TRIANGLES',4):
            self.assertEqual(m.verify_source(self.triangles,self.triangles),0)
            reversed_face = [self.triangles[0][::-1]]+self.triangles[1:]
            with self.assertRaises(ValueError): m.verify_source(reversed_face,self.triangles)

    def test_exact_weld_preserves_corner_stream_and_validates_source_contract(self):
        vertices,faces = m.weld_exact(self.triangles)
        self.assertEqual([[vertices[i] for i in f] for f in faces],self.triangles)
        with patch.object(m,'SOURCE_TRIANGLES',4), patch.object(m,'WELDED_VERTICES',4):
            self.assertEqual(m.verify_topology(vertices,faces)['extras']['nonmanifold_vertex_links'],0)
        with self.assertRaises(ValueError): m.verify_topology(vertices,faces)

    def test_duplicate_reverse_faces_are_detected_geometrically(self):
        extras = m.topology_extras(self.vertices,self.faces+[self.faces[0][::-1]])
        self.assertEqual(extras['duplicate_geometric_faces'],1)
        with self.assertRaises(ValueError): m.verify_topology(self.vertices,self.faces+[self.faces[0]])

    def test_point_touching_closed_shells_have_nonmanifold_vertex(self):
        vertices = self.vertices+[(-1.,0.,0.),(0.,-1.,0.),(0.,0.,-1.)]
        remap = {0:0,1:4,2:5,3:6}
        faces = self.faces+[tuple(remap[i] for i in face[::-1]) for face in self.faces]
        self.assertEqual(m.surface_stats(vertices,faces)['components'],1)
        self.assertEqual(m.topology_extras(vertices,faces)['nonmanifold_vertex_links'],1)
        with self.assertRaises(ValueError): m.verify_topology(vertices,faces)

    def test_render_comparison_rejects_missing_duplicate_or_changed_views(self):
        report = {'settings': {'samples':16}, 'views': [
            {'id':v['id'], 'pixels_sha256':v['id']} for v in VIEWS]}
        self.assertEqual(len(compare_images(report, report)),4)
        for altered in (report['views'][:-1], report['views']+[report['views'][0]], list(reversed(report['views']))):
            with self.assertRaises(ValueError): compare_images(report, dict(report,views=altered))
        changed = copy.deepcopy(report); changed['views'][0]['pixels_sha256'] = 'different'
        with self.assertRaises(ValueError): compare_images(report, changed)


if __name__ == '__main__': unittest.main()
