import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('tower_paint', ROOT / 'scripts/tokyo_tower_paint_bands.py')
paint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paint)


def area_xz(vertices, face):
    p = [vertices[i] for i in face]
    return sum(a[0] * b[2] - b[0] * a[2] for a, b in zip(p, p[1:] + p[:1])) / 2


class TowerPaintGeometry(unittest.TestCase):
    def test_seven_equal_bands_preserve_lower_stairs_and_top(self):
        plan = paint.load(paint.PLAN)
        self.assertEqual(len(paint.boundaries(plan)), 6)
        for i in range(7):
            z = 154 + (i + .5) * 179 / 7
            self.assertEqual(paint.paint_index(z, 0, plan), i % 2)
            self.assertEqual(paint.paint_index(z, 1, plan), i % 2)
        self.assertEqual(paint.paint_index(145, 1, plan), 1)
        self.assertEqual(paint.paint_index(145, 0, plan), 0)
        self.assertEqual(paint.paint_index(333, 0, plan), 0)

    def test_slanted_face_area_winding_and_original_vertices(self):
        vertices = [(0., 0., 0.), (2., 0., 1.), (3., 0., 4.), (1., 0., 3.)]
        before = copy.deepcopy(vertices)
        face = [0, 1, 2, 3]
        pieces = paint.split_polygon(vertices, face, [1.5, 2.5], {})
        self.assertEqual(len(pieces), 3)
        self.assertEqual(vertices[:4], before)
        self.assertAlmostEqual(sum(area_xz(vertices, f) for f in pieces), area_xz(before, face))
        self.assertTrue(all(area_xz(vertices, f) > 0 for f in pieces))
        for piece in pieces:
            zs = [vertices[i][2] for i in piece]
            self.assertFalse(any(min(zs) < h < max(zs) for h in [1.5, 2.5]))

    def test_adjacent_faces_reuse_shared_intersection(self):
        v = [(0, 0, 0), (1, 0, 0), (1, 0, 2), (0, 0, 2), (2, 0, 0), (2, 0, 2)]
        cache = {}
        a = paint.split_polygon(v, [0, 1, 2, 3], [1], cache)
        b = paint.split_polygon(v, [1, 4, 5, 2], [1], cache)
        shared = cache[(1, 1, 2)]
        self.assertTrue(all(shared in face for face in a + b))
        self.assertEqual(sum(p == (1., 0., 1) for p in v), 1)

    def test_boundary_through_vertex_and_coplanar_edge(self):
        v = [(0, 0, 0), (2, 0, 1), (0, 0, 2)]
        pieces = paint.split_polygon(v, [0, 1, 2], [1], {})
        self.assertEqual(len(pieces), 2)
        self.assertEqual(len(v), 4)
        self.assertTrue(all(len(set(f)) == len(f) == 3 for f in pieces))
        v2 = [(0, 0, 1), (2, 0, 1), (0, 0, 2)]
        self.assertEqual(paint.split_polygon(v2, [0, 1, 2], [1], {}), [[0, 1, 2]])

    def test_no_unnecessary_split_or_duplicate_vertices(self):
        v = [(0, 0, 0), (2, 0, 0), (2, 0, 2), (0, 0, 2)]
        first = paint.split_polygon(v, [0, 1, 2, 3], [1], {})
        count = len(v)
        second = [q for f in first for q in paint.split_polygon(v, f, [1], {})]
        self.assertEqual(first, second)
        self.assertEqual(len(v), count)


if __name__ == '__main__':
    unittest.main()
