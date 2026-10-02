import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('local_building_export',ROOT/'adapters/open-tokyo-world/export_local_building.py')
export=importlib.util.module_from_spec(spec);spec.loader.exec_module(export)


class LocalExportTests(unittest.TestCase):
    def test_fresh_ignored_output_only_and_existing_outputs_preserved(self):
        with tempfile.TemporaryDirectory(prefix='otw-local-export-') as temporary:
            root=Path(temporary);out=root/'data/local/new-export'
            self.assertEqual(export.checked_output(root,out),out.resolve())
            out.mkdir(parents=True);marker=out/'keep.txt';marker.write_text('preserve',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'already exists'):export.checked_output(root,out)
            self.assertEqual(marker.read_text(encoding='utf8'),'preserve')
            with self.assertRaisesRegex(ValueError,'inside data/local'):export.checked_output(root,root/'public')

    def test_glb_refuses_remote_resources_and_truncated_containers(self):
        with tempfile.TemporaryDirectory(prefix='otw-local-glb-') as temporary:
            path=Path(temporary)/'model.glb'
            for document in [{'asset':{'version':'2.0'}},{'images':[{'uri':'https://example.invalid/texture.png'}]}]:
                payload=json.dumps(document).encode();payload+=b' '*((-len(payload))%4)
                path.write_bytes(struct.pack('<IIIII',0x46546c67,2,20+len(payload),len(payload),0x4e4f534a)+payload)
                if 'images' in document:
                    with self.assertRaisesRegex(ValueError,'embed'):export.glb_document(path)
                else:self.assertEqual(export.glb_document(path)['asset']['version'],'2.0')
            path.write_bytes(b'partial')
            with self.assertRaisesRegex(ValueError,'header'):export.glb_document(path)


if __name__=='__main__':unittest.main()
