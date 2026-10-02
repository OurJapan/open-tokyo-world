# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Portable CLI integration checks for the west-path review operation."""
import copy
from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import mori_plaza_outline_v1 as outline
import mori_plaza_west_path_v1 as west
import review


class WestPathReviewContracts(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.source = self.folder/'input.blend'
        self.source.write_bytes(b'portable west-path source')
        self.input_hash = review.digest(self.source)
        self.plan = self.folder/'plan.json'
        review.write_json(self.plan, {'geometry_fixture': True})
        self.plan_hash = review.digest(self.plan)
        self.roads = self.folder/'roads'
        self.roads.mkdir()
        self.output = self.folder/'review'
        review.write_json(self.folder/'lock.json', {
            'bytes': self.source.stat().st_size, 'sha256': self.input_hash,
            'blender_version': '4.5.1 LTS'})
        review.write_json(self.folder/'cameras.json', {'version': 1, 'views': [{
            'id': 'west-path', 'matrix_world': [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],
            'lens_mm': 35, 'sensor_width_mm': 36, 'sensor_height_mm': 24,
            'sensor_fit': 'AUTO', 'shift_x': 0, 'shift_y': 0,
            'clip_start': .1, 'clip_end': 1000}]})
        review.write_json(self.folder/'features.json', {'version': 1, 'features': [{
            'id': west.FEATURE, 'collections': ['Mori JP podium']}]})
        patch = review.read_json(ROOT/'patches/mori-plaza-west-path-v1.json')
        patch['operations'][0]['plan_sha256'] = self.plan_hash
        review.write_json(self.folder/'patch.json', patch)
        self.before = {'ok': True, 'assets': [], 'objects': {
            west.ANCHOR: {'mesh': 'unchanged anchor'},
            'neighbor': {'mesh': 'unchanged neighbor'},
            **{name: {'mesh': 'original '+name} for name in west.ROADS}}}
        self.after = copy.deepcopy(self.before)
        self.after['objects'].update({name: {'mesh': 'adjusted '+name} for name in west.ROADS})
        self.after['objects'].update({name: {'mesh': 'new seam'} for name in west.ADDED})
        self.phases = []
        self.jobs = []
        self.mutate_plan = False
        # Only geometry acquisition, Blender work and Git metadata are mocked.
        # CLI checks, job construction, report comparison and final hashes run normally.
        self.enterContext(mock.patch.object(west, 'INPUT_SHA256', self.input_hash))
        self.load_plan = self.enterContext(mock.patch.object(west, 'load_plan', return_value={}))
        self.verify_sources = self.enterContext(mock.patch.object(outline, 'verify_sources'))
        self.enterContext(mock.patch.object(review.subprocess, 'run', return_value=SimpleNamespace(stdout='0'*40)))
        self.run_job = self.enterContext(mock.patch.object(review, 'run_job', side_effect=self.fake_run))

    def fake_run(self, blender, phase, output, job, source, timeout):
        self.phases.append(phase)
        self.jobs.append(review.read_json(job))
        if phase == 'prepare':
            (output/'before.blend').write_bytes(b'prepared before fixture')
            (output/'after.blend').write_bytes(b'prepared west-path fixture')
        elif phase in ('validate-before', 'validate-after'):
            review.write_json(output/(phase+'.json'), self.before if phase == 'validate-before' else self.after)
        elif phase == 'render-after' and self.mutate_plan:
            # Same JSON meaning, different bytes: the source lock must still fail.
            self.plan.write_text(self.plan.read_text(encoding='utf-8')+' ', encoding='utf-8')
        return {'seconds': 0, 'report_sha256': '0'*64}

    def invoke(self, include_plan=True, include_roads=True):
        argv = ['review.py', '--blender', str(self.folder/'unused-blender'),
                '--input', str(self.source), '--lock', str(self.folder/'lock.json'),
                '--cameras', str(self.folder/'cameras.json'), '--features', str(self.folder/'features.json'),
                '--patch', str(self.folder/'patch.json'), '--output', str(self.output)]
        if include_plan:
            argv += ['--connection-plan', str(self.plan)]
        if include_roads:
            argv += ['--road-inputs', str(self.roads)]
        with mock.patch.object(sys, 'argv', argv), redirect_stdout(io.StringIO()):
            review.main()

    def test_single_operation_transfers_inputs_accepts_only_its_scope_and_renders(self):
        self.invoke()
        self.assertEqual(self.phases, ['prepare', 'validate-before', 'validate-after', 'render-before', 'render-after'])
        self.load_plan.assert_called_once_with(self.plan, self.plan_hash)
        self.assertEqual(self.verify_sources.call_args_list, [mock.call(self.roads), mock.call(self.roads)])
        for job in self.jobs:
            self.assertEqual(job['connection_plan'], str(self.plan.resolve()))
            self.assertEqual(job['road_inputs'], str(self.roads.resolve()))
            self.assertEqual([op['op'] for op in job['patch']['operations']], ['mori_plaza_west_path_v1'])
            self.assertNotIn('shiba_plan', job)
        summary = review.read_json(self.output/'run.json')
        self.assertTrue(summary['ok'])
        self.assertEqual(set(summary['changed_objects']), west.ROADS | west.ADDED)
        self.assertEqual(summary['connection_plan_sha256'], self.plan_hash)
        self.assertEqual(set(summary['output_blends']), {'before.blend', 'after.blend'})

    def test_missing_plan_or_road_inputs_stops_before_blender(self):
        for include_plan, include_roads, message in [
                (False, True, 'Connection operation requires exactly one local plan'),
                (True, False, 'Plaza road operation requires exactly one road-input directory')]:
            with self.subTest(plan=include_plan, roads=include_roads):
                with self.assertRaisesRegex(ValueError, message):
                    self.invoke(include_plan, include_roads)
                self.run_job.assert_not_called()
                self.assertFalse(self.output.exists())

    def test_unrelated_object_change_is_rejected_before_render(self):
        self.after['objects']['neighbor']['mesh'] = 'unauthorized change'
        with self.assertRaisesRegex(ValueError, 'Unexpected changed objects: neighbor'):
            self.invoke()
        self.assertEqual(self.phases, ['prepare', 'validate-before', 'validate-after'])
        self.assertFalse(review.read_json(self.output/'run.json')['ok'])

    def test_plan_mutation_during_render_is_rejected_before_success(self):
        self.mutate_plan = True
        with self.assertRaisesRegex(ValueError, 'Connection plan changed during review'):
            self.invoke()
        self.assertEqual(self.phases[-2:], ['render-before', 'render-after'])
        self.assertFalse(review.read_json(self.output/'run.json')['ok'])
        self.assertFalse((self.output/'review.html').exists())


if __name__ == '__main__':
    unittest.main()
