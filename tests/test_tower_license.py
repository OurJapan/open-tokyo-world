import hashlib,importlib.util,json,tempfile,unittest
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
