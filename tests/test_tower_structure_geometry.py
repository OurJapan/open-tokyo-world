# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Geometry acceptance and corruption checks without Blender or city assets."""
import copy
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import tower_structure_v1 as tower
import validate_tower_structure as saved


def cube():
    return ([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
             (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)],
            [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4],
             [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]])


class TowerGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Producer output is test input only. The validator independently checks
        # constraints and never calls a geometry producer or compares its output.
        cls.meshes = {}
        cls.parts = {}
        for name, mesh in tower.geometry().items():
            vertices = [tuple(struct.unpack('<f', struct.pack('<f', v))[0] for v in p) for p in mesh['vertices']]
            faces = [list(f) for f in mesh['faces']]
            cls.meshes[name] = (vertices, faces)
            _, cls.parts[name] = saved.check_mesh(vertices, faces, saved.BOUNDS[name])

    def test_float32_geometry_satisfies_independent_physical_constraints(self):
        result = saved.check_geometry(self.meshes)
        self.assertEqual(len(result['objects']), 17)
        self.assertEqual(result['stairs']['treads'], 598)
        self.assertEqual(result['stairs']['landing_connections_checked'], 92)
        self.assertEqual(result['upper_guides']['top_m'], 246.1)
        self.assertTrue(result['foottown']['doorway_open'])
        self.assertEqual(result['base_connections']['plates'], 16)

    def test_closed_solid_rejects_nan_missing_face_inward_winding_and_degeneracy(self):
        vertices, faces = cube()
        envelope = ((0, 1), (0, 1), (0, 1))
        stats, _ = saved.check_mesh(vertices, faces, envelope)
        self.assertAlmostEqual(stats['volume_m3'], 1.)
        broken = []
        bad = list(vertices); bad[0] = (float('nan'), 0, 0)
        broken.append((bad, faces))
        broken.append((vertices, faces[1:]))
        broken.append((vertices, [list(reversed(f)) for f in faces]))
        broken.append((vertices, [list(reversed(faces[0]))]+faces[1:]))
        broken.append((vertices, [[0, 0, 2]]+faces[1:]))
        broken.append((vertices, [[0, 3, 99]]+faces[1:]))
        bad = list(vertices); bad[0] = (-.1, 0, 0)
        broken.append((bad, faces))
        for points, polygons in broken:
            with self.subTest(points=points[0], face=polygons[0]):
                with self.assertRaises(ValueError):
                    saved.check_mesh(points, polygons, envelope)

    def test_missing_tread_floating_landing_and_disconnected_flight_are_rejected(self):
        parts = self.parts['stairs-treads']
        with self.assertRaisesRegex(ValueError, '598 treads'):
            saved.check_stairs(parts[1:])
        for change in ('elevation', 'connection'):
            bad = copy.deepcopy(parts)
            landing = next(p for p in bad if saved.near(p['size'][2], .13))
            extent = list(landing['bounds'])
            if change == 'elevation':
                extent[2] = tuple(v+.05 for v in extent[2])
            else:
                extent[0] = tuple(v+1 for v in extent[0])
            landing['bounds'] = extent
            with self.assertRaisesRegex(ValueError, 'landing'):
                saved.check_stairs(bad)

    def test_upper_enclosure_truncated_rail_and_cabin_piercing_rope_are_rejected(self):
        vertices, faces = copy.deepcopy(self.meshes['upper-shaft-frame'])
        points, polygons = cube()
        offset = len(vertices)
        vertices.extend((x*3.6-1.8, y*.1+1.7, z*3+180) for x, y, z in points)
        faces.extend([[i+offset for i in face] for face in polygons])
        _, parts = saved.check_mesh(vertices, faces, saved.BOUNDS['upper-shaft-frame'])
        with self.assertRaisesRegex(ValueError, 'Wide vertical wall'):
            saved.check_open_upper(vertices, faces, parts)
        for cuboid in (True, False):
            rails = copy.deepcopy(self.parts['upper-guide-rails'])
            part = next(p for p in rails if p['cuboid'] == cuboid)
            extent = list(part['bounds'])
            extent[2] = (extent[2][0]-1, extent[2][1])
            part['bounds'] = extent
            with self.assertRaisesRegex(ValueError, 'endpoint|rope'):
                saved.check_guides(rails)

    def test_roof_hole_plate_contact_and_doorway_are_enforced(self):
        for change in ('roof', 'door'):
            parts = copy.deepcopy(self.parts)
            if change == 'roof':
                parts['foottown-roof'][0]['bounds'] = ((-36.5, 36.5), (-29, 29), (16, 16.2))
            else:
                parts['roof-access'][0]['bounds'] = ((-4.8, -4.64), (3.7, 5.1), (16.2, 18.3))
            with self.assertRaises(ValueError):
                saved.check_foottown(parts)
        plates = copy.deepcopy(self.parts['base-connections'])
        plate = next(p for p in plates if p['cuboid'])
        extent = list(plate['bounds']); extent[2] = (2.0, 2.19); plate['bounds'] = extent
        with self.assertRaisesRegex(ValueError, 'contact level'):
            saved.check_plates(plates)

    def test_retained_geometry_and_display_flags_are_exact(self):
        vertices, faces = cube()
        data = {'vertices': vertices, 'faces': faces, 'polygon_flags': [(0, False)]*6,
                'matrix_world': [[int(r == c) for c in range(4)] for r in range(4)], 'materials': ['original'],
                'modifiers': [{'rna_type': 'BevelModifier', 'width': .006, 'segments': 2, 'show_render': False}]}
        self.assertTrue(saved.compare_retained(data, copy.deepcopy(data))['coordinates_faces_material_indices_smooth_flags_exact'])
        for key, value in [('vertices', (0.1, 0, 0)), ('faces', [0, 2, 3, 1]),
                           ('polygon_flags', (0, True)), ('polygon_flags', (1, False)), ('materials', 'other')]:
            bad = copy.deepcopy(data); bad[key][0] = value
            with self.subTest(key=key, value=value):
                with self.assertRaisesRegex(ValueError, 'Retained tower'):
                    saved.compare_retained(data, bad)
        for key, value in (('width', .007), ('segments', 3), ('show_render', True)):
            bad = copy.deepcopy(data); bad['modifiers'][0][key] = value
            with self.assertRaisesRegex(ValueError, 'Retained tower modifiers differ'):
                saved.compare_retained(data, bad)
        bad = copy.deepcopy(data); bad['modifiers'] = []
        with self.assertRaisesRegex(ValueError, 'Retained tower modifiers differ'):
            saved.compare_retained(data, bad)

    def test_modifier_snapshot_keeps_profile_and_rejects_unknown_or_nonfinite_state(self):
        def rna(kind, values):
            properties = [SimpleNamespace(identifier=key, type=typ, is_array=isinstance(value, tuple))
                          for key, (typ, value) in values.items()]
            return SimpleNamespace(bl_rna=SimpleNamespace(identifier=kind, properties=properties),
                                   **{key: value for key, (_, value) in values.items()})
        point = rna('CurveProfilePoint', {'location': ('FLOAT', (0., 1.)), 'handle_type_1': ('ENUM', 'AUTO')})
        profile = rna('CurveProfile', {'preset': ('ENUM', 'LINE'), 'points': ('COLLECTION', [point])})
        modifier = rna('BevelModifier', {'width': ('FLOAT', .006), 'show_render': ('BOOLEAN', False),
                                        'execution_time': ('FLOAT', .03), 'custom_profile': ('POINTER', profile)})
        snapshot = saved.snapshot_modifier_rna(modifier)
        self.assertNotIn('execution_time', snapshot)
        self.assertEqual(snapshot['custom_profile']['points'][0]['location'], [0., 1.])
        point.location = (.1, 1.)
        self.assertNotEqual(snapshot, saved.snapshot_modifier_rna(modifier))
        modifier.width = float('nan')
        with self.assertRaisesRegex(ValueError, 'non-finite'):
            saved.snapshot_modifier_rna(modifier)
        with self.assertRaisesRegex(ValueError, 'Unsupported retained modifier RNA'):
            saved.snapshot_modifier_rna(rna('NodesModifier', {}))


if __name__ == '__main__':
    unittest.main()
