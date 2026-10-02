"""Small closed-mesh checks for the saved-surface validator (Blender 4.5.1)."""
import importlib.util
from pathlib import Path
import unittest

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('paint', ROOT / 'scripts/tokyo_tower_paint_bands.py')
paint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paint)


class SavedSurfaceChecks(unittest.TestCase):
    def fixture(self, reverse=False):
        plan = paint.load(paint.PLAN)
        # Deliberately twisted side faces exercise the retained tessellation.
        v = [(0, 0, 178), (2, 0, 178), (2, 2, 178), (0, 2, 178),
             (0, 0, 182), (2, 0, 182), (2.002, 2, 181.998), (0, 2, 182)]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        old = bpy.data.meshes.new('Original twisted closed fixture')
        old.from_pydata(v, [], f)
        old.calc_loop_triangles()
        verts, faces, origins, tri_origins, cache = list(v), [], [], [], {}
        for face in old.polygons:
            heights = [v[i][2] for i in face.vertices]
            crosses = any(min(heights) < h < max(heights) for h in paint.boundaries(plan))
            if crosses:
                for tri in old.loop_triangles:
                    if tri.polygon_index == face.index:
                        for piece in paint.split_polygon(verts, list(tri.vertices), paint.boundaries(plan), cache):
                            faces.append(piece)
                            origins.append(face.index)
                            tri_origins.append(tri.index)
            else:
                faces.append(list(face.vertices))
                origins.append(face.index)
                tri_origins.append(-1)
        if reverse:
            faces[2] = list(reversed(faces[2]))
        current = bpy.data.meshes.new('Split fixture')
        current.from_pydata(verts, [], faces)
        for _ in range(2):
            current.materials.append(bpy.data.materials.new('Fixture paint'))
        for face in current.polygons:
            face.material_index = paint.paint_index(sum(verts[i][2] for i in face.vertices) / len(face.vertices), 0, plan)
        current.update()
        return old, current, np.asarray(origins), np.asarray(tri_origins), 0, plan

    def test_twisted_original_surface_is_preserved(self):
        result = paint.geometry_check(*self.fixture())
        self.assertEqual(result['original_vertices_unchanged'], 8)
        self.assertEqual(result['split_source_faces_checked'], 4)
        self.assertEqual(result['edge_counts'], {'wire': 0, 'boundary': 0, 'more_than_two_faces': 0})

    def test_moved_vertex_is_rejected(self):
        args = self.fixture()
        args[1].vertices[0].co.x += .1
        with self.assertRaisesRegex(ValueError, 'vertex moved'):
            paint.geometry_check(*args)

    def test_wrong_paint_is_rejected(self):
        args = self.fixture()
        args[1].polygons[0].material_index = 1
        with self.assertRaisesRegex(ValueError, 'paint assignment'):
            paint.geometry_check(*args)

    def test_reversed_split_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Flipped'):
            paint.geometry_check(*self.fixture(reverse=True))

    def test_wrong_triangle_mapping_is_rejected(self):
        args = self.fixture()
        args[3][2] = -1
        with self.assertRaisesRegex(ValueError, 'triangle coverage'):
            paint.geometry_check(*args)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SavedSurfaceChecks)
    if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():
        raise RuntimeError('Paint surface smoke checks failed')
