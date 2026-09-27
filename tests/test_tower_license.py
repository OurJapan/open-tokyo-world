import copy,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as S
ROOT=Path(__file__).resolve().parents[1];HERE=ROOT/'assets/tokyo-tower'
spec=importlib.util.spec_from_file_location('tower_export',HERE/'export.py');export=importlib.util.module_from_spec(spec);spec.loader.exec_module(export)

class LicenseContract(unittest.TestCase):
    def test_historical_snapshot_hashes(self):
        scope=json.loads((HERE/'provenance.json').read_text(encoding='utf8'))
        self.assertTrue(scope['consent']['authority_confirmed'])
        self.assertEqual(len(scope['historical_code']),9)
        for c in scope['historical_code']:
            self.assertEqual(hashlib.sha256((ROOT/c['path']).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),c['sha256_lf'])
        self.assertEqual(len({p['object'] for p in scope['parts']}),77)
        self.assertTrue(all(p['vertices']>0 for p in scope['parts']))
        self.assertEqual(len(scope['excluded_empty_objects']),5)

    def test_wrong_baseline_fails(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'input';p.write_bytes(b'bad')
            with self.assertRaises(ValueError):export.source_check(p,{'bytes':3,'sha256':'0'*64})

    def identity_fixture(self):
        scope=json.loads((HERE/'provenance.json').read_text(encoding='utf8'))
        objects=[{'otw_part_id':p['part_id'],'source_object':p['object'],
                  'otw_feature_id':scope['feature_id'],'license':'CC-BY-4.0'} for p in scope['parts']]
        records={p['object']:{'part_id':p['part_id'],'source_object':p['object']} for p in scope['parts']}
        return scope,objects,records

    def test_identity_survives_reordering_and_display_rename(self):
        scope,objects,records=self.identity_fixture()
        scope['parts'].reverse();objects.reverse()
        renamed={f'New display name {i}':r for i,r in enumerate(records.values())}
        self.assertEqual(len(export.validate_part_identity(objects,renamed,scope)),77)

    def test_manifest_rejects_duplicate_or_missing_ids(self):
        scope,_,_=self.identity_fixture()
        for change in ('duplicate','missing'):
            with self.subTest(change=change):
                bad=copy.deepcopy(scope)
                if change=='duplicate':bad['parts'][1]['part_id']=bad['parts'][0]['part_id']
                else:del bad['parts'][0]['part_id']
                with self.assertRaises(ValueError):export.part_index(bad)

    def test_saved_identity_rejects_tampering(self):
        scope,objects,records=self.identity_fixture()
        for change in ('duplicate','missing','swapped','feature','license','record-source','record-missing'):
            with self.subTest(change=change):
                obs=copy.deepcopy(objects);rec=copy.deepcopy(records)
                if change=='duplicate':obs[1]['otw_part_id']=obs[0]['otw_part_id']
                elif change=='missing':obs.pop()
                elif change=='swapped':obs[0]['otw_part_id'],obs[1]['otw_part_id']=obs[1]['otw_part_id'],obs[0]['otw_part_id']
                elif change=='feature':obs[0]['otw_feature_id']='other'
                elif change=='license':obs[0]['license']='other'
                elif change=='record-source':next(iter(rec.values()))['source_object']='other'
                else:rec.pop(next(iter(rec)))
                with self.assertRaises(ValueError):export.validate_part_identity(obs,rec,scope)

    def test_nested_image_rejected(self):
        inner=S(animation_data=None,as_pointer=lambda:1,nodes=[S(image=object(),type='TEX_IMAGE')])
        outer=S(animation_data=None,as_pointer=lambda:2,nodes=[S(image=None,type='GROUP',node_tree=inner)])
        with self.assertRaisesRegex(ValueError,'Image dependency'):export.material_check(S(use_nodes=True,node_tree=outer))

    def test_shader_script_rejected(self):
        tree=S(animation_data=None,as_pointer=lambda:1,nodes=[S(image=None,type='SCRIPT')])
        with self.assertRaisesRegex(ValueError,'Shader script'):export.material_check(S(use_nodes=True,node_tree=tree))

    def test_animated_material_rejected(self):
        tree=S(animation_data=object(),as_pointer=lambda:1,nodes=[])
        with self.assertRaisesRegex(ValueError,'Animated'):export.material_check(S(use_nodes=True,node_tree=tree))

if __name__=='__main__':unittest.main()
