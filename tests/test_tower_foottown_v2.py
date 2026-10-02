# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Portable scope and saved-geometry contracts for the FootTown increment."""
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
import tower_foottown_v2 as tower


def patch():
    return {'version': 1, 'purpose': 'reviewed-change',
            'reason': 'Bounded FootTown review fixture',
            'source_refs': ['Fixed structure evidence fixture'], 'operations': [{
                'op': 'tower_foottown_v2', 'feature_id': tower.FEATURE,
                'object': tower.ANCHOR, 'expected_mesh_sha256': tower.BASELINE_HASHES[tower.ANCHOR],
                'target_mesh_sha256': dict(tower.BASELINE_HASHES), 'added_objects': sorted(tower.ADDED)}]}


class FootTownReviewContracts(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name)
        self.source = self.folder/'input.blend'
        self.source.write_bytes(b'portable FootTown source')
        self.input_hash = review.digest(self.source)
        self.output = self.folder/'review'
        self.patch = patch()
        review.write_json(self.folder/'lock.json', {
            'bytes': self.source.stat().st_size, 'sha256': self.input_hash, 'blender_version': '4.5.1 LTS'})
        review.write_json(self.folder/'cameras.json', {'version': 1, 'views': [{
            'id': 'tower-front', 'matrix_world': [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],
            'lens_mm': 35, 'sensor_width_mm': 36, 'sensor_height_mm': 24,
            'sensor_fit': 'AUTO', 'shift_x': 0, 'shift_y': 0, 'clip_start': .1, 'clip_end': 1000}]})
        review.write_json(self.folder/'features.json', {'version': 1, 'features': []})
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
        for name in ('tower_foottown_v2.py','tower_foottown_geometry_v2.py','tower_structure_v1.py','validate_tower_foottown.py','validate_tower_structure.py'):
            self.assertEqual(summary['code_files']['scripts/'+name], review.digest(ROOT/'scripts'/name))
        validator = ROOT/'scripts/validate_tower_foottown.py'
        if validator.is_file():
            self.assertEqual(summary['code_files']['scripts/validate_tower_foottown.py'], review.digest(validator))

    def test_other_city_is_rejected_even_when_lock_matches(self):
        with self.assertRaisesRegex(ValueError, 'FootTown requires the pinned PR59 city input'):
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
                self.assert_preflight_rejected('FootTown')

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
                self.assert_preflight_rejected('FootTown baseline targets or hashes differ')

    def test_additions_require_exact_names_and_no_duplicates(self):
        names = sorted(tower.ADDED)
        cases = [names+['unrelated object'], None, {name:True for name in names}]
        if names:
            cases += [names[1:], names+[names[0]]]
        for value in cases:
            with self.subTest(additions=value):
                self.patch = patch()
                self.patch['operations'][0]['added_objects'] = value
                self.assert_preflight_rejected('FootTown additions differ')

    def test_missing_evidence_and_stacked_operations_are_rejected(self):
        self.patch['source_refs'] = []
        self.assert_preflight_rejected('FootTown must be a standalone evidence-backed increment')
        for extra in [copy.deepcopy(patch()['operations'][0]),
                      {'op':'translate_object','feature_id':tower.FEATURE,'object':tower.ANCHOR,'translation_m':[0,0,1]}]:
            self.patch = patch()
            self.patch['operations'].append(extra)
            self.assert_preflight_rejected('FootTown must be a standalone evidence-backed increment')

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

    def test_feature_remapping_is_rejected_before_modifying_metadata(self):
        review.write_json(self.folder/'features.json', {'version': 1, 'features': [
            {'id': tower.FEATURE, 'collections': ['OTW Tokyo Tower structure v1']}]})
        self.assert_preflight_rejected('FootTown preserves existing feature tags without remapping')

    def test_deletion_missing_additions_and_shared_material_mutation_are_rejected(self):
        unchanged_after = copy.deepcopy(self.after)
        for failure in ('deletion', 'missing-addition', 'shared-material'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as folder:
                self.output = Path(folder)/'review'
                self.after = copy.deepcopy(unchanged_after)
                if failure == 'deletion':
                    del self.after['objects']['protected building']
                    message = 'Unexpected object deletion'
                elif failure == 'missing-addition':
                    del self.after['objects'][sorted(tower.ADDED)[0]]
                    message = 'Unexpected or missing object creation'
                else:
                    self.after['objects']['protected building']['materials'] = ['changed shared glass']
                    message = 'Unexpected changed objects'
                with self.assertRaisesRegex(ValueError, message):
                    self.invoke()
                self.assertFalse(review.read_json(self.output/'run.json')['ok'])


class FootTownSavedGeometry(unittest.TestCase):
    def setUp(self):
        from tower_structure_v1 import MeshBuilder
        import validate_tower_foottown as validator
        self.validator = validator
        self.builder = MeshBuilder()
        # An independent minimal acceptance fixture, not a producer replay.
        for group in tower.GROUPS:
            if group != 'foottown-roof':
                self.builder.box(group, (30, 0, 4), (.1, .1, .1))
        for x, y in ((-18,-14), (18,-14), (-18,14), (18,14)):
            self.builder.box('foottown-roof', (x,y,16.1), (4,4,.2))
        for x, y, low, high in ([(x,26.97,.02,3.385) for x in (-16,-5.5,5.5,16)] +
                                 [(x,-28.885,4.465,7.015) for x in (-5,5)]):
            for lo, hi in ((x-.775,x-.012), (x+.012,x+.775)):
                self.builder.box('foottown-glazing', ((lo+hi)/2,y,(low+high)/2), (hi-lo,.025,high-low))
        self.builder.box('foottown-shell', (0,0,.01), (73,58,.02))
        self.builder.box('foottown-roof', (0,30.05,.01), (56,6.5,.02))
        for x in (-24,-8,8,24):
            self.builder.box('foottown-metal', (x,32.70,3.625), (.64,.66,7.25))
        for x in (-7.3,0,7.3):
            for y,width,top in ((-31.6,.20,7.43),(-30.15,.22,4.30)):
                self.builder.box('foottown-metal', (x,y,top/2), (width,width,top))
        for x in (-16,-5.5,5.5,16):
            self.builder.box('foottown-metal', (x,27.045,.0125), (4.27,.22,.015))
        for i in range(25):
            self.builder.box('foottown-roof', (-14.2+(i+.5)*6.2/25,-30.4,.02+(i+1)*4.38/25-.045),
                             (6.2/25+.018,1.4,.09))
        self.builder.box('foottown-roof', (0,-30.2,4.3), (16,2.4,.2))
        for y in (-29.67,-31.13):
            self.builder.box('foottown-metal', (-14.2,y,.03), (.22,.22,.06))

    def check(self):
        return self.validator.check_geometry({group: (mesh['vertices'], mesh['faces'])
                                             for group, mesh in self.builder.groups.items()})

    def test_saved_solids_roof_elevation_and_openings(self):
        report = self.check()
        self.assertEqual(len(report['meshes']), 7)
        self.assertEqual(report['roof_elevation_m'], 16.2)
        self.assertEqual(report['ground_connections']['grounded_main_columns'], 4)
        self.assertAlmostEqual(report['ground_connections']['south_first_tread_top_m'], .1952)
        self.assertTrue(all(mesh['closed_edge_incidence_two'] and mesh['consistent_outward_winding']
                            for mesh in report['meshes'].values()))

    def test_roof_shaft_and_existing_stair_entrance_cannot_be_blocked(self):
        for position, label in [((0,0,20), 'roof lift shaft'),
                                ((-8,4.4,17), 'roof stair approach'),
                                ((-4.3,4.4,17), 'roof stair doorway')]:
            with self.subTest(label=label):
                mesh = copy.deepcopy(self.builder.groups)
                self.builder.box('foottown-shell', position, (.2,.2,.2))
                with self.assertRaisesRegex(ValueError, 'FootTown blocks '+label):
                    self.check()
                self.builder.groups = mesh

    def test_missing_face_reversed_solid_and_nonfinite_vertex_are_rejected(self):
        baseline = copy.deepcopy(self.builder.groups)
        for failure, message in [('missing-face','not closed'), ('reversed','Inward'), ('nonfinite','Non-finite')]:
            with self.subTest(failure=failure):
                self.builder.groups = copy.deepcopy(baseline)
                mesh = self.builder.groups['foottown-shell']
                if failure == 'missing-face':
                    mesh['faces'].pop()
                elif failure == 'reversed':
                    mesh['faces'] = [tuple(reversed(face)) for face in mesh['faces']]
                else:
                    mesh['vertices'][0] = (float('nan'),0,4)
                with self.assertRaisesRegex(ValueError, message):
                    self.check()

    def test_floating_apron_column_threshold_and_stair_are_rejected(self):
        baseline = copy.deepcopy(self.builder.groups)
        cases = [('foottown-roof',lambda x,y,z:y>26 and z<.03,'main apron'),
                 ('foottown-metal',lambda x,y,z:abs(x-24)<.4 and abs(y-32.7)<.4,'main canopy column'),
                 ('foottown-metal',lambda x,y,z:abs(x)<.15 and abs(y+31.6)<.15,'south support column'),
                 ('foottown-metal',lambda x,y,z:abs(x+14.2)<.15 and abs(y+29.67)<.15,'south stair support base'),
                 ('foottown-metal',lambda x,y,z:abs(x-16)<2.2 and abs(y-27.045)<.2 and z<.03,'main door threshold'),
                 ('foottown-roof',lambda x,y,z:y< -29.5 and z<.21,'south stair starts')]
        for group, select, message in cases:
            with self.subTest(message=message):
                self.builder.groups = copy.deepcopy(baseline)
                mesh = self.builder.groups[group]
                mesh['vertices'] = [(x,y,z+.4) if select(x,y,z) else (x,y,z) for x,y,z in mesh['vertices']]
                with self.assertRaisesRegex(ValueError,message):
                    self.check()

    def test_opaque_door_infill_and_missing_door_leaf_are_rejected(self):
        baseline = copy.deepcopy(self.builder.groups)
        self.builder.box('foottown-cladding', (5.5,27.08,2), (1.5,.2,1.5))
        with self.assertRaisesRegex(ValueError, 'blocks main door opening'):
            self.check()
        self.builder.groups = baseline
        mesh = self.builder.groups['foottown-glazing']
        mesh['vertices'] = mesh['vertices'][:-8]
        mesh['faces'] = mesh['faces'][:-6]
        with self.assertRaisesRegex(ValueError, 'Missing or duplicate FootTown south door leaf'):
            self.check()

    def test_new_roof_building_cannot_cross_existing_stair_headroom(self):
        from tower_structure_v1 import MeshBuilder
        stairs = MeshBuilder()
        stairs.box('stairs-treads', (0,4,21.955), (1,.6,.09))
        tread = stairs.groups['stairs-treads']
        meshes = lambda: {name: (mesh['vertices'],mesh['faces']) for name,mesh in self.builder.groups.items()}
        report = self.validator.check_geometry(meshes(), (tread['vertices'],tread['faces']))
        self.assertEqual(report['existing_stair_headroom_surfaces'], 1)
        self.builder.box('foottown-shell', (0,4,22.5), (.2,.2,.2))
        with self.assertRaisesRegex(ValueError, 'blocks existing stair headroom'):
            self.validator.check_geometry(meshes(), (tread['vertices'],tread['faces']))


if __name__ == '__main__':
    unittest.main()



