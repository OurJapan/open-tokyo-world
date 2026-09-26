# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import mori_plaza_outline_v1 as outline
from review import validate_patch


def rectangle(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def scope(remove, protect=()):
    return {'remove': [(p, outline.bounds(p)) for p in remove],
            'protect': [(p, outline.bounds(p)) for p in protect],
            'bounds': outline.bounds([p for poly in remove for p in poly])}


class PlazaOutlineTests(unittest.TestCase):
    def test_exact_seed_match_retains_duplicate_non_target_record(self):
        rectangles = outline.legacy_rectangles([(-420.123456, 290.22), (-404.3333, 318.14)], 9)
        ring = rectangles[0]
        seed = [{'z': outline.f32(.30), 'ring': list(reversed(ring))},
                {'z': outline.f32(.30), 'ring': ring[1:] + ring[:1]}]
        matched, remaining = outline.match_seed(seed, rectangles, .30)
        self.assertEqual(matched, [0])
        self.assertEqual(remaining, [1])
        seed[0]['ring'][0] = (seed[0]['ring'][0][0] + .01, seed[0]['ring'][0][1])
        with self.assertRaises(ValueError):
            outline.match_seed(seed[:1], rectangles, .30)

    def test_seed_top_elevation_is_part_of_attribution(self):
        rectangle_list = outline.legacy_rectangles([(0, 0), (10, 0)], 11.1)
        with self.assertRaises(ValueError):
            outline.match_seed([{'z': 7.23, 'ring': rectangle_list[0]}], rectangle_list, .23)

    def test_overlapping_outline_and_protected_crossing_conserve_area(self):
        poly = [(x, y, .3) for x, y in rectangle(0, 0, 10, 10)]
        selected = scope([rectangle(1, 1, 6, 9), rectangle(4, 1, 9, 9)], [rectangle(4, -1, 6, 11)])
        kept, removed = outline.split_scope(poly, selected)
        self.assertAlmostEqual(sum(map(outline.area, removed)), 48)
        self.assertAlmostEqual(sum(map(outline.area, kept)), 52)
        for fragment in removed:
            _, protected = outline.subtract_convex(fragment, rectangle(4, -1, 6, 11))
            self.assertLess(outline.area(protected), 1e-8)

    def test_vertical_curb_faces_are_clipped_without_double_counting(self):
        poly = [(0, 5, .3), (10, 5, .3), (10, 5, .46), (0, 5, .46)]
        selected = scope([rectangle(2, 2, 8, 8)])
        kept, removed = outline.split_scope(poly, selected)
        self.assertAlmostEqual(sum(map(outline.area, removed)), .96)
        self.assertAlmostEqual(sum(map(outline.area, kept)), .64)

    def test_scope_boundary_coplanar_wall_is_not_duplicated(self):
        poly = [(2, 2, .3), (8, 2, .3), (8, 2, .46), (2, 2, .46)]
        kept, removed = outline.split_scope(poly, scope([rectangle(2, 2, 8, 8)]))
        self.assertAlmostEqual(sum(map(outline.area, kept + removed)), outline.area(poly))

    def test_outside_or_elevated_road_and_fully_protected_faces_are_exact(self):
        selected = scope([rectangle(1, 1, 9, 9)], [rectangle(3, 3, 7, 7)])
        for poly in [[(x, y, z) for x, y in p] for p, z in
                     [(rectangle(20, 20, 21, 21), .3), (rectangle(2, 2, 8, 8), 7.3),
                      (rectangle(4, 4, 6, 6), .3)]]:
            kept, removed = outline.split_scope(poly, selected)
            self.assertEqual(kept, [poly])
            self.assertEqual(removed, [])

    def test_padding_is_outward_for_either_winding(self):
        ring = rectangle(0, 0, 10, 4)
        for original in (ring, list(reversed(ring))):
            padded = outline.padded_ring(original, .005)
            self.assertAlmostEqual(outline.signed_area(padded), 10.01 * 4.01)
            self.assertGreater(outline.signed_area(padded), 0)
        with self.assertRaises(ValueError):
            outline.padded_ring([(0, 0), (10, 0), (5, 1), (10, 4), (0, 4)], .005)

    def test_changed_external_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'fixture.json'
            file.write_bytes(b'fixed')
            spec = {'fixture.json': (5, hashlib.sha256(b'fixed').hexdigest())}
            with patch.dict(outline.SOURCE_FILES, spec, clear=True):
                outline.verify_sources(directory)
                file.write_bytes(b'other')
                with self.assertRaisesRegex(ValueError, 'hash differs'):
                    outline.verify_sources(directory)

    def test_patch_scope_cannot_add_objects_or_modify_other_roads(self):
        candidate = json.loads((ROOT / 'patches/mori-plaza-outline-v1.json').read_text(encoding='utf-8'))
        validate_patch(candidate)
        for key, value in [('added_objects', ['unapproved']), ('road_mesh_sha256', {'other': 'a'*64})]:
            bad = copy.deepcopy(candidate)
            bad['operations'][0][key] = value
            with self.assertRaises(ValueError):
                validate_patch(bad)
