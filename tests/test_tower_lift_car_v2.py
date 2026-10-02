import math
import unittest

from scripts.tower_lift_car_v2 import GROUPS, upper_car_geometry
from scripts.tower_structure_v1 import MeshBuilder


class RecordingBuilder(MeshBuilder):
    def __init__(self):
        super().__init__()
        self.parts = []

    def box(self, group, center, size):
        self.parts.append(("box", group, center, size))
        super().box(group, center, size)

    def beam(self, group, a, b, radius, sides=8):
        self.parts.append(("beam", group, a, b, radius))
        super().beam(group, a, b, radius, sides)


def bounds(part):
    if part[0] == "box":
        return tuple((c - s / 2, c + s / 2) for c, s in zip(part[2], part[3]))
    length = math.dist(part[2], part[3])
    extents = [part[4] * math.sqrt(max(0, 1 - ((b - a) / length) ** 2))
               for a, b in zip(part[2], part[3])]
    return tuple((min(a, b) - radius, max(a, b) + radius)
                 for a, b, radius in zip(part[2], part[3], extents))


def overlap(a, b):
    return all(min(x[1], y[1]) - max(x[0], y[0]) > 1e-8 for x, y in zip(a, b))


class UpperCarGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = RecordingBuilder()
        upper_car_geometry(cls.b)

    def test_closed_positive_solids_and_six_groups(self):
        self.assertEqual(set(self.b.groups), set(GROUPS))
        for mesh in self.b.groups.values():
            self.assertTrue(all(math.isfinite(v) for p in mesh["vertices"] for v in p))
            edges = {}
            for face in mesh["faces"]:
                for a, b in zip(face, face[1:] + face[:1]):
                    key = tuple(sorted((a, b)))
                    edges.setdefault(key, []).append((a, b))
            self.assertTrue(all(len(e) == 2 and e[0] == e[1][::-1] for e in edges.values()))
        for part in self.b.parts:
            if part[0] == "box":
                self.assertTrue(all(s > 0 for s in part[3]))
            else:
                self.assertGreater(math.dist(part[2], part[3]) * part[4] ** 2, 0)

    def test_three_full_height_panes_and_clear_interior(self):
        panes = [p for p in self.b.parts if p[0] == "box" and p[1] == "upper-car-glass"]
        self.assertEqual(len(panes), 3)
        self.assertEqual(sum(p[2][1] < -1.15 for p in panes), 1)
        self.assertEqual(sum(p[2][0] < -1.20 for p in panes), 2)
        for pane in panes:
            self.assertAlmostEqual(bounds(pane)[2][0], 201.05)
            self.assertAlmostEqual(bounds(pane)[2][1], 203.65)
            for part in self.b.parts:
                if part[1] not in ("upper-car-glass",):
                    self.assertFalse(overlap(bounds(pane), bounds(part)), (pane, part))
        clear = ((-.98, .98), (-.96, .96), (201.041, 203.55))
        self.assertFalse(any(overlap(bounds(p), clear) for p in self.b.parts))
        mirror = self.b.groups["upper-car-mirror"]["vertices"]
        self.assertAlmostEqual(min(p[2] for p in mirror), 203.70)
        self.assertAlmostEqual(max(p[2] for p in self.b.groups["upper-car-floor"]["vertices"]), 201)

    def test_t_guide_clearance_and_rope_crosshead(self):
        for sign in (-1, 1):
            for center, size in ((sign * 1.46, (.085, .018)), (sign * 1.515, (.025, .145))):
                rail = ((center - size[0] / 2, center + size[0] / 2),
                        (-size[1] / 2, size[1] / 2), (199.0, 205.0))
                self.assertFalse(any(overlap(bounds(p), rail) for p in self.b.parts))
            for z in (200.92, 203.93):
                liners = [p for p in self.b.parts if p[1] == "upper-car-dark"
                          and abs(p[2][2] - z) < 1e-8 and sign * p[2][0] > 1.3]
                self.assertEqual(len(liners), 3)
                self.assertTrue(any(abs(sign * p[2][0] + p[3][0] / 2 - 1.4175) < 1e-8
                                    for p in liners))
        crosshead = [p for p in self.b.parts if p[1] == "upper-car-rigging"
                     and p[0] == "box" and abs(bounds(p)[2][1] - 204.32) < 1e-8]
        self.assertEqual(len(crosshead), 1)
        for index in range(7):
            x = -.27 + .09 * index
            self.assertTrue(all(lo <= value <= hi for (lo, hi), value in
                                zip(bounds(crosshead[0]), (x, 0, 204.32))))
        vertices = [p for mesh in self.b.groups.values() for p in mesh["vertices"]]
        self.assertAlmostEqual(min(p[2] for p in vertices), 200.62)
        self.assertAlmostEqual(max(p[2] for p in vertices), 204.32)

    def test_floor_offset_moves_every_part(self):
        shifted = MeshBuilder()
        upper_car_geometry(shifted, floor_z=211.0)
        for group in GROUPS:
            for p, q in zip(self.b.groups[group]["vertices"], shifted.groups[group]["vertices"]):
                self.assertAlmostEqual(p[0], q[0])
                self.assertAlmostEqual(p[1], q[1])
                self.assertAlmostEqual(q[2] - p[2], 10.0)
        with self.assertRaises(ValueError):
            upper_car_geometry(MeshBuilder(), floor_z=float("nan"))


if __name__ == "__main__":
    unittest.main()
