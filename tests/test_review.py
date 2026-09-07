import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('review',Path(__file__).resolve().parents[1]/'scripts/review.py')
review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)


class Contracts(unittest.TestCase):
    def camera(self):
        return {'version':1,'views':[{'id':'front','matrix_world':[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],'lens_mm':35,'sensor_width_mm':36,'sensor_height_mm':24,'sensor_fit':'AUTO','shift_x':0,'shift_y':0,'clip_start':0.1,'clip_end':100}]}

    def test_camera_path_traversal_and_duplicate_rejected(self):
        c=self.camera(); c['views'][0]['id']='../../outside'
        with self.assertRaises(ValueError): review.validate_cameras(c)
        c=self.camera();c['views'].append(copy.deepcopy(c['views'][0]))
        with self.assertRaises(ValueError): review.validate_cameras(c)

    def test_degenerate_and_nonfinite_cameras_rejected(self):
        for value in (0,float('nan'),-1):
            c=self.camera();c['views'][0]['matrix_world'][0][0]=value
            with self.assertRaises(ValueError):review.validate_cameras(c)

    def test_unknown_operation_and_missing_real_evidence_rejected(self):
        p={'version':1,'purpose':'reviewed-change','reason':'example','source_refs':[],'operations':[{'op':'translate_object','feature_id':'otw:test','object':'Cube','translation_m':[0,0,1]}]}
        with self.assertRaises(ValueError):review.validate_patch(p)
        p['purpose']='fixture-test';review.validate_patch(p)
        p['operations'][0]['op']='execute_python'
        with self.assertRaises(ValueError):review.validate_patch(p)

    def test_out_of_scope_shared_change_fails(self):
        base={'ok':True,'objects':{'target':{'mesh':'a'},'neighbor':{'mesh':'b'}},'assets':[]}
        after=copy.deepcopy(base);after['objects']['neighbor']['mesh']='changed'
        with self.assertRaises(ValueError):review.compare_reports(base,after,['target'])

    def test_object_deletion_and_asset_change_fail(self):
        base={'ok':True,'objects':{'target':{}},'assets':[]}
        with self.assertRaises(ValueError):review.compare_reports(base,{'ok':True,'objects':{},'assets':[]},['target'])
        after=copy.deepcopy(base);after['assets']=[{'name':'new'}]
        with self.assertRaises(ValueError):review.compare_reports(base,after,['target'])

    def test_hash_detects_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input';p.write_bytes(b'original');h=review.digest(p);p.write_bytes(b'modified')
            self.assertNotEqual(h,review.digest(p))

    def test_shape_adapter_requires_exact_feature_hash_and_evidence(self):
        p={'version':1,'purpose':'reviewed-change','reason':'visual hypothesis','source_refs':['https://pcparch.com/work/azabudai-hills'],'operations':[{'op':'mori_shape_v1','feature_id':'otw:jp:tokyo:minato:azabudai-mori-jp','object':'Mori continuous pearl glass / recessed spandrel','expected_mesh_sha256':'a'*64}]}
        review.validate_patch(p)
        for key,value in [('feature_id','otw:other'),('expected_mesh_sha256','missing')]:
            changed=copy.deepcopy(p);changed['operations'][0][key]=value
            with self.assertRaises(ValueError):review.validate_patch(changed)
        p['source_refs']=[]
        with self.assertRaises(ValueError):review.validate_patch(p)


if __name__=='__main__':unittest.main()
