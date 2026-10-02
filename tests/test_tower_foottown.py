import math
import unittest

from scripts import tower_foottown_v1 as foottown


class RecordingBuilder:
    def __init__(self):
        self.parts = []

    def box(self, group, center, size):
        self.parts.append(("box", group, tuple(center), tuple(size)))

    def beam(self, group, start, end, radius, sides=8):
        self.parts.append(("beam", group, tuple(start), tuple(end), radius, sides))


def bounds(part):
    if part[0] == "box":
        return tuple((c - s / 2, c + s / 2) for c, s in zip(part[2], part[3]))
    return tuple((min(a, b) - part[4], max(a, b) + part[4])
                 for a, b in zip(part[2], part[3]))


def overlaps(first, second):
    return all(min(a[1], b[1]) - max(a[0], b[0]) > 1e-8
               for a, b in zip(first, second))


class FootTownGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        builder = RecordingBuilder()
        foottown.geometry(builder)
        cls.parts = builder.parts

    def test_four_groups_and_finite_nondegenerate_footprint(self):
        self.assertEqual({part[1] for part in self.parts}, set(foottown.GROUPS))
        for part in self.parts:
            with self.subTest(part=part):
                self.assertTrue(all(math.isfinite(value) for point in part[2:4] for value in point))
                if part[0] == "box":
                    self.assertTrue(all(value > 0.0 for value in part[3]))
                else:
                    self.assertGreater(math.dist(part[2], part[3]), 0.0)
                    self.assertTrue(math.isfinite(part[4]) and part[4] > 0.0)
                    self.assertGreaterEqual(part[5], 3)
                extent = bounds(part)
                self.assertGreaterEqual(extent[0][0], -36.5 - 1e-8)
                self.assertLessEqual(extent[0][1], 36.5 + 1e-8)
                self.assertGreaterEqual(extent[1][0], -29.0 - 1e-8)
                self.assertLessEqual(extent[1][1], 29.0 + 1e-8)
                self.assertGreaterEqual(extent[2][0], 0.35 - 1e-8)
                # Even a 10 m square around each +/-47.5 m tower foot is clear.
                for x in (-47.5, 47.5):
                    for y in (-47.5, 47.5):
                        self.assertFalse(overlaps(extent, ((x - 5, x + 5), (y - 5, y + 5), (0, 30))))

    def test_roof_surrounds_shaft_opening_and_reserves_centre(self):
        roof = [part for part in self.parts if part[1] == "foottown-roof"]
        self.assertEqual(len(roof), 4)
        roof_extents = [bounds(part) for part in roof]
        self.assertEqual(tuple((min(extent[axis][0] for extent in roof_extents),
                                max(extent[axis][1] for extent in roof_extents))
                               for axis in (0, 1)),
                         ((-36.5, 36.5), (-29.0, 29.0)))
        self.assertAlmostEqual(sum(part[3][0] * part[3][1] for part in roof),
                               73.0 * 58.0 - 4.7 * 4.7)
        aperture = ((-2.35, 2.35), (-2.35, 2.35), (15.99, 16.21))
        for index, extent in enumerate(roof_extents):
            self.assertAlmostEqual(extent[2][1], 16.2)
            self.assertFalse(overlaps(extent, aperture))
            self.assertFalse(any(overlaps(extent, other) for other in roof_extents[index + 1:]))
        centre = ((-6.0, 6.0), (-8.0, 8.0), (16.2, 100.0))
        interior = ((-30.0, 30.0), (-20.0, 20.0), (0.5, 16.0))
        for part in self.parts:
            self.assertFalse(overlaps(bounds(part), centre), part)
            self.assertFalse(overlaps(bounds(part), interior), part)
        rails = [part for part in self.parts if part[0] == "beam"]
        self.assertTrue(rails)
        self.assertAlmostEqual(max(bounds(part)[2][1] for part in rails), 17.3)

    def test_windows_are_openings_in_shell(self):
        walls = [bounds(part) for part in self.parts if part[1] == "foottown-shell"]
        glazing = [part for part in self.parts if part[1] == "foottown-glazing"]
        self.assertTrue(glazing)
        for pane in glazing:
            self.assertFalse(any(overlaps(bounds(pane), wall) for wall in walls), pane)
        # Every level has glazing, and the south entrance reaches ground level.
        for bottom, top in zip(foottown.FLOOR_LEVELS, foottown.FLOOR_LEVELS[1:]):
            self.assertTrue(any(bottom < pane[2][2] < top for pane in glazing))
        self.assertTrue(any(abs(pane[2][0]) < 3.6 and pane[2][1] < -28.0
                            and bounds(pane)[2][0] < 0.6 for pane in glazing))


if __name__ == "__main__":
    unittest.main()
