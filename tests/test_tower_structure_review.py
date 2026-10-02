# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Portable CLI scope and input contracts for the tower structure operation."""
import copy
from contextlib import nullcontext, redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import review
import tower_structure_v1 as tower


def patch():
    return {'version': 1, 'purpose': 'reviewed-change',
            'reason': 'Bounded tower structure review fixture',
            'source_refs': ['Fixed structure evidence fixture'], 'operations': [{
                'op': 'tower_structure_v1', 'feature_id': tower.FEATURE,
                'object': tower.ANCHOR, 'expected_mesh_sha256': tower.BASELINE_HASHES[tower.ANCHOR],
                'target_mesh_sha256': dict(tower.BASELINE_HASHES), 'added_objects': sorted(tower.ADDED)}]}


class TowerStructureReviewContracts(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name)
        self.source = self.folder/'input.blend'
        self.source.write_bytes(b'portable tower structure source')
        self.input_hash = review.digest(self.source)
        self.output = self.folder/'review'
        self.patch = patch()
        review.write_json(self.folder/'lock.json', {
            'bytes': self.source.stat().st_size, 'sha256': self.input_hash, 'blender_version': '4.5.1 LTS'})
        review.write_json(self.folder/'cameras.json', {'version': 1, 'views': [{
            'id': 'tower-front', 'matrix_world': [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],
            'lens_mm': 35, 'sensor_width_mm': 36, 'sensor_height_mm': 24,
            'sensor_fit': 'AUTO', 'shift_x': 0, 'shift_y': 0, 'clip_start': .1, 'clip_end': 1000}]})
        review.write_json(self.folder/'features.json', {'version': 1, 'features': [{
            'id': tower.FEATURE, 'collections': ['Tokyo Tower structure']}]})
        self.before = {'ok': True, 'assets': [], 'objects': {
            'protected building': {'mesh': 'unchanged building'},
            **{name: {'mesh': value} for name, value in tower.BASELINE_HASHES.items()}}}
        self.after = copy.deepcopy(self.before)
        self.after['objects'].update({name: {'mesh': 'repaired '+name} for name in tower.CHANGED})
        self.after['objects'].update({name: {'mesh': 'new structure part'} for name in tower.ADDED})
        self.phases = []
        self.jobs = []
        self.enterContext(mock.patch.object(review.subprocess, 'run', return_value=SimpleNamespace(stdout='0'*40)))
        self.run_job = self.enterContext(mock.patch.object(review, 'run_job', side_effect=self.fake_run))

    def fake_run(self, blender, phase, output, job, source, timeout):
        self.phases.append(phase)
        self.jobs.append(review.read_json(job))
        if phase == 'prepare':
            (output/'before.blend').write_bytes(b'prepared before fixture')
            (output/'after.blend').write_bytes(b'prepared tower fixture')
        elif phase in ('validate-before', 'validate-after'):
            review.write_json(output/(phase+'.json'), self.before if phase == 'validate-before' else self.after)
        return {'seconds': 0, 'report_sha256': '0'*64}

    def invoke(self, allow_fixture=True, extra_args=()):
        review.write_json(self.folder/'patch.json', self.patch)
        argv = ['review.py', '--blender', str(self.folder/'unused-blender'),
                '--input', str(self.source), '--lock', str(self.folder/'lock.json'),
                '--cameras', str(self.folder/'cameras.json'), '--features', str(self.folder/'features.json'),
                '--patch', str(self.folder/'patch.json'), '--output', str(self.output), *extra_args]
        # Keep the real runner's size/hash checks, while avoiding a legacy city asset in portable tests.
        input_pin = mock.patch.object(tower, 'INPUT_SHA256', self.input_hash) if allow_fixture else nullcontext()
        with input_pin, mock.patch.object(sys, 'argv', argv), redirect_stdout(io.StringIO()):
            review.main()

    def assert_preflight_rejected(self, message):
        with self.assertRaisesRegex(ValueError, message):
            self.invoke()
        self.run_job.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_single_operation_changes_only_fixed_scope_and_renders_without_external_plan(self):
        self.assertLessEqual(set(tower.CHANGED), set(tower.BASELINE_HASHES))
        self.invoke()
        self.assertEqual(self.phases, ['prepare', 'validate-before', 'validate-after', 'render-before', 'render-after'])
        for job in self.jobs:
            self.assertEqual(job['patch'], self.patch)
            self.assertFalse({'geometry_source','road_inputs','landscape_plan','connection_plan','shiba_plan'} & set(job))
        summary = review.read_json(self.output/'run.json')
        self.assertTrue(summary['ok'])
        self.assertEqual(set(summary['changed_objects']), set(tower.CHANGED) | set(tower.ADDED))
        self.assertEqual(summary['input_sha256'], self.input_hash)
        for name in ('tower_structure_v1.py','tower_foottown_v1.py'):
            self.assertEqual(summary['code_files']['scripts/'+name], review.digest(ROOT/'scripts'/name))
        validator = ROOT/'scripts/validate_tower_structure.py'
        if validator.is_file():
            self.assertEqual(summary['code_files']['scripts/validate_tower_structure.py'], review.digest(validator))

    def test_other_city_is_rejected_even_when_lock_matches(self):
        with self.assertRaisesRegex(ValueError, 'Tower structure requires the pinned PR56 city input'):
            self.invoke(allow_fixture=False)
        self.run_job.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_extra_keys_other_anchor_feature_and_wrong_anchor_hash_are_rejected(self):
        wrong_hash = '0'*64 if tower.BASELINE_HASHES[tower.ANCHOR] != '0'*64 else '1'*64
        for key, value in [('translation_m',[0,0,1]), ('object','unrelated object'), ('feature_id','otw:other'),
                           ('expected_mesh_sha256',None), ('expected_mesh_sha256','A'*64), ('expected_mesh_sha256',wrong_hash)]:
            with self.subTest(key=key,value=value):
                self.patch = patch()
                self.patch['operations'][0][key] = value
                self.assert_preflight_rejected('tower structure|Tower structure')

    def test_baseline_target_names_and_hashes_must_match_exactly(self):
        for change in ('missing','extra','wrong-hash','invalid-hash','not-dict'):
            with self.subTest(change=change):
                self.patch = patch()
                op = self.patch['operations'][0]
                if change == 'missing':
                    del op['target_mesh_sha256'][tower.ANCHOR]
                elif change == 'extra':
                    op['target_mesh_sha256']['unrelated object'] = '0'*64
                elif change == 'not-dict':
                    op['target_mesh_sha256'] = []
                else:
                    op['target_mesh_sha256'][tower.ANCHOR] = '0'*64 if change == 'wrong-hash' else None
                self.assert_preflight_rejected('Wrong tower structure baseline targets or hashes')

    def test_additions_require_exact_names_and_no_duplicates(self):
        names = sorted(tower.ADDED)
        cases = [names+['unrelated object'], None, {name:True for name in names}]
        if names:
            cases += [names[1:], names+[names[0]]]
        for value in cases:
            with self.subTest(additions=value):
                self.patch = patch()
                self.patch['operations'][0]['added_objects'] = value
                self.assert_preflight_rejected('Wrong tower structure additions')

    def test_missing_evidence_and_stacked_operations_are_rejected(self):
        self.patch['source_refs'] = []
        self.assert_preflight_rejected('Tower structure must be a standalone evidence-backed increment')
        for extra in [copy.deepcopy(patch()['operations'][0]),
                      {'op':'translate_object','feature_id':tower.FEATURE,'object':tower.ANCHOR,'translation_m':[0,0,1]}]:
            self.patch = patch()
            self.patch['operations'].append(extra)
            self.assert_preflight_rejected('Tower structure must be a standalone evidence-backed increment')

    def test_unchanged_city_objects_cannot_change_with_the_tower(self):
        self.after['objects']['protected building']['mesh'] = 'unauthorized change'
        with self.assertRaisesRegex(ValueError, 'Unexpected changed objects: protected building'):
            self.invoke()
        self.assertEqual(self.phases, ['prepare', 'validate-before', 'validate-after'])
        self.assertFalse(review.read_json(self.output/'run.json')['ok'])

    def test_unrequested_geometry_sources_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Podium operation requires exactly one geometry source'):
            self.invoke(extra_args=['--geometry-source', str(self.folder/'unused.npz')])
        self.run_job.assert_not_called()
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
