# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('plaza_levels', ROOT / 'scripts/audit_mori_plaza_levels.py')
levels = importlib.util.module_from_spec(spec)
spec.loader.exec_module(levels)


class PlazaLevelDiagnosis(unittest.TestCase):
    def test_shared_diagonal_is_not_a_boundary_and_walls_are_excluded(self):
        vertices = [(0,0,.11),(1,0,.11),(1,1,.11),(0,1,.11),(0,0,-.01)]
        count, edges = levels.top_boundary(vertices, [[0,1,2],[0,2,3],[0,4,1]])
        self.assertEqual(count, 2)
        self.assertEqual(edges, [(0,1),(0,3),(1,2),(2,3)])

    def test_samples_cover_edges_at_fixed_maximum_spacing(self):
        rows = list(levels.boundary_samples([(0,0,.11),(1.2,0,.11)], [(0,1)]))
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]['normal_xy'], [0,1])
        for row, expected in zip(rows, [.2,.6,1.]):
            self.assertAlmostEqual(row['xy'][0], expected)
            self.assertLessEqual(row['interval_m'], .5)

    def test_boundary_orientation_does_not_reverse_reported_step(self):
        paving = {'object':levels.PAVING,'z':.11}
        road = {'object':'pavement_0 unified road','z':.46}
        for a,b in [(paving,road),(road,paving)]:
            self.assertAlmostEqual(levels.road_pair(a,b)['rise_m'],.35)
        self.assertIsNone(levels.road_pair(paving, {'object':'ground','z':0}))
        self.assertIsNone(levels.road_pair(road, {'object':None,'z':None}))

    def test_nonfinite_measurement_is_not_reported_as_a_step(self):
        with self.assertRaisesRegex(ValueError, 'Invalid sampled height'):
            levels.road_pair({'object':levels.PAVING,'z':.11},
                             {'object':'asphalt 15s road detail','z':math.nan})

    def test_coordinate_conversion_matches_adopted_entrance_frame(self):
        for uv in [(0,32),(-22,52),(25,120)]:
            x,y,_ = levels.landscape.world(*uv)
            actual = levels.local_uv(x,y)
            for a,b in zip(actual,uv):self.assertAlmostEqual(a,b)

    def test_wrong_city_fails_before_blender_and_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/'source.blend'; source.write_bytes(b'wrong city')
            with patch.object(levels.subprocess,'run') as run:
                with self.assertRaisesRegex(ValueError,'pinned PR 40'):
                    levels.main(['--input',str(source),'--output',str(root/'result'),'--blender','unused'])
                run.assert_not_called()
            self.assertFalse((root/'result').exists())
            self.assertEqual(source.read_bytes(),b'wrong city')

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            marker=root/'keep.txt'; marker.write_text('keep')
            with patch.object(levels,'verify_input',return_value={'sha256':'pinned'}), patch.object(levels.subprocess,'run') as run:
                with self.assertRaises(FileExistsError):
                    levels.main(['--input',str(root/'scene.blend'),'--output',str(root),'--blender','unused'])
                run.assert_not_called()
            self.assertEqual(marker.read_text(),'keep')


if __name__ == '__main__':
    unittest.main()
