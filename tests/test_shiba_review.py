# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Portable scope and preflight contracts for Shiba Momijidani reviews."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import review
import shiba_momijidani_v1 as shiba


def patch():
    return {'version':1, 'purpose':'reviewed-change', 'reason':'Bounded Shiba additions',
            'source_refs':['docs/shiba-momijidani-v1.md'], 'operations':[{
                'op':'shiba_momijidani_v1', 'feature_id':shiba.ANCHOR_FEATURE,
                'object':shiba.ANCHOR, 'expected_mesh_sha256':'a'*64,
                'plan_sha256':'b'*64, 'added_objects':sorted(shiba.ADDED)}]}


class ShibaReviewContracts(unittest.TestCase):
    def test_fixed_anchor_and_complete_addition_set_are_accepted(self):
        review.validate_patch(patch())
        self.assertFalse(shiba.CHANGED)
        self.assertNotEqual(shiba.FEATURE, shiba.ANCHOR_FEATURE)

    def test_other_anchors_invalid_hashes_and_extra_keys_are_rejected(self):
        for key,value in [('feature_id',shiba.FEATURE), ('object','ground'),
                          ('expected_mesh_sha256','a'*63), ('expected_mesh_sha256',None),
                          ('plan_sha256','B'*64), ('plan_sha256',42),
                          ('translation_m',[0,0,1])]:
            with self.subTest(key=key,value=value):
                candidate=patch();candidate['operations'][0][key]=value
                with self.assertRaises(ValueError):review.validate_patch(candidate)

    def test_missing_extra_duplicate_and_nonlist_additions_are_rejected(self):
        names=sorted(shiba.ADDED)
        self.assertTrue(names)
        for value in [[],names[1:],names+['unrelated object'],names+[names[0]],
                      names[0],{name:True for name in names},[None]]:
            with self.subTest(additions=value):
                candidate=patch();candidate['operations'][0]['added_objects']=value
                with self.assertRaises(ValueError):review.validate_patch(candidate)

    def test_missing_evidence_and_mixed_operations_are_rejected(self):
        candidate=patch();candidate['source_refs']=[]
        with self.assertRaises(ValueError):review.validate_patch(candidate)
        for extra in [copy.deepcopy(patch()['operations'][0]),
                      {'op':'translate_object','feature_id':shiba.ANCHOR_FEATURE,
                       'object':shiba.ANCHOR,'translation_m':[0,0,1]}]:
            candidate=patch();candidate['operations'].append(extra)
            with self.assertRaises(ValueError):review.validate_patch(candidate)

    def test_exact_additions_preserve_every_existing_object_and_asset(self):
        before={'ok':True,'objects':{shiba.ANCHOR:{'mesh':'anchor'},
                                    'neighbor':{'mesh':'neighbor'}},'assets':[]}
        after=copy.deepcopy(before)
        after['objects'].update({name:{'feature_id':shiba.FEATURE} for name in shiba.ADDED})
        self.assertEqual(review.compare_reports(before,after,[],shiba.ADDED),sorted(shiba.ADDED))
        for name in before['objects']:
            changed=copy.deepcopy(after);changed['objects'][name]['mesh']='changed'
            with self.assertRaises(ValueError):review.compare_reports(before,changed,[],shiba.ADDED)
        missing=copy.deepcopy(after);missing['objects'].pop(next(iter(shiba.ADDED)))
        with self.assertRaises(ValueError):review.compare_reports(before,missing,[],shiba.ADDED)
        extra=copy.deepcopy(after);extra['objects']['unexpected']={}
        with self.assertRaises(ValueError):review.compare_reports(before,extra,[],shiba.ADDED)
        deleted=copy.deepcopy(after);deleted['objects'].pop('neighbor')
        with self.assertRaises(ValueError):review.compare_reports(before,deleted,[],shiba.ADDED)
        changed=copy.deepcopy(after);changed['assets']=[{'name':'external texture'}]
        with self.assertRaises(ValueError):review.compare_reports(before,changed,[],shiba.ADDED)

    def arguments(self,folder,with_patch=True,with_plan=True):
        folder=Path(folder)
        source=folder/'input.blend';source.write_bytes(b'portable preflight fixture')
        review.write_json(folder/'lock.json',{'bytes':source.stat().st_size,
                          'sha256':review.digest(source),'blender_version':'4.5.1'})
        camera={'version':1,'views':[{'id':'overview','matrix_world':[
                [1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],'lens_mm':35,
                'sensor_width_mm':36,'sensor_height_mm':24,'sensor_fit':'AUTO',
                'shift_x':0,'shift_y':0,'clip_start':.1,'clip_end':1000}]}
        review.write_json(folder/'cameras.json',camera)
        review.write_json(folder/'features.json',{'version':1,'features':[
                          {'id':shiba.ANCHOR_FEATURE,'collections':['Tokyo Tower structure']}]})
        review.write_json(folder/'plan.json',{'preflight_fixture':True})
        candidate=patch();candidate['operations'][0]['plan_sha256']=review.digest(folder/'plan.json')
        review.write_json(folder/'patch.json',candidate)
        argv=['review.py','--blender',str(folder/'unused-blender'),
              '--input',str(source),'--lock',str(folder/'lock.json'),
              '--cameras',str(folder/'cameras.json'),'--features',str(folder/'features.json'),
              '--output',str(folder/'output')]
        if with_patch:argv+=['--patch',str(folder/'patch.json')]
        if with_plan:argv+=['--shiba-plan',str(folder/'plan.json')]
        return argv

    def test_plan_is_required_only_with_shiba_operation(self):
        for with_patch,with_plan in [(True,False),(False,True)]:
            with self.subTest(patch=with_patch,plan=with_plan),tempfile.TemporaryDirectory() as folder:
                argv=self.arguments(folder,with_patch,with_plan)
                with mock.patch.object(sys,'argv',argv),mock.patch.object(review,'run_job') as run:
                    with self.assertRaisesRegex(ValueError,'Shiba operation requires exactly one local plan'):
                        review.main()
                    run.assert_not_called()
                self.assertFalse((Path(folder)/'output').exists())

    def test_changed_plan_is_rejected_before_blender(self):
        with tempfile.TemporaryDirectory() as folder:
            argv=self.arguments(folder)
            (Path(folder)/'plan.json').write_text('{}',encoding='utf-8')
            with mock.patch.object(sys,'argv',argv),mock.patch.object(review,'run_job') as run:
                with self.assertRaisesRegex(ValueError,'Shiba plan hash differs'):review.main()
                run.assert_not_called()
            self.assertFalse((Path(folder)/'output').exists())

    def test_other_city_is_rejected_even_when_its_lock_matches(self):
        with tempfile.TemporaryDirectory() as folder:
            argv=self.arguments(folder)
            # Plan geometry has its own tests; isolate the runner's input pin here.
            with mock.patch.object(sys,'argv',argv),mock.patch.object(shiba,'validate_plan'),\
                    mock.patch.object(review,'run_job') as run:
                with self.assertRaisesRegex(ValueError,'Shiba requires the accepted city input'):review.main()
                run.assert_not_called()
            self.assertFalse((Path(folder)/'output').exists())

    def test_runner_does_not_authorize_anchor_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            argv=self.arguments(folder)
            input_hash=review.digest(Path(folder)/'input.blend')
            phases=[]

            def fake_run(blender,phase,output,job,source,timeout):
                phases.append(phase)
                if phase.startswith('validate-'):
                    report={'ok':True,'objects':{shiba.ANCHOR:{'mesh':'original'}},'assets':[]}
                    if phase=='validate-after':
                        report['objects'][shiba.ANCHOR]['mesh']='unauthorized change'
                        report['objects'].update({name:{'feature_id':shiba.FEATURE} for name in shiba.ADDED})
                    review.write_json(output/(phase+'.json'),report)
                return {'seconds':0,'report_sha256':'0'*64}

            with mock.patch.object(sys,'argv',argv),mock.patch.object(shiba,'validate_plan'),\
                    mock.patch.object(shiba,'INPUT_SHA256',input_hash),\
                    mock.patch.object(review,'run_job',side_effect=fake_run):
                with self.assertRaisesRegex(ValueError,'Unexpected changed objects'):review.main()
            self.assertEqual(phases,['prepare','validate-before','validate-after'])
            self.assertFalse(review.read_json(Path(folder)/'output/run.json')['ok'])


if __name__=='__main__':unittest.main()
