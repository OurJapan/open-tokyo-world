import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mori_profile',ROOT/'starter/mori/profile.py')
profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile)

class ReplacementContract(unittest.TestCase):
    def test_index_is_resolved_by_id_not_batch_five(self):
        self.assertEqual(profile.target_index(['other',profile.FEATURE]),1)

    def test_absent_or_duplicate_id_rejected(self):
        for ids in [[],['other'],[profile.FEATURE,profile.FEATURE]]:
            with self.assertRaises(ValueError):profile.target_index(ids)

    def test_corrupt_input_stops_before_blender(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);inputs=p/'inputs';inputs.mkdir()
            (inputs/'tileset.json').write_bytes(b'corrupt')
            out=p/'out'
            result=subprocess.run([sys.executable,str(ROOT/'starter/mori/run.py'),'--blender',sys.executable,'--inputs',str(inputs),'--output',str(out)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            record=json.loads((out/'run.json').read_text())
            self.assertFalse(record['ok'])
            self.assertIn('Pinned source mismatch',record['error'])
            self.assertFalse((out/'build.log').exists())

    def test_existing_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);marker=out/'keep';marker.write_text('original')
            result=subprocess.run([sys.executable,str(ROOT/'starter/mori/run.py'),'--blender',sys.executable,'--output',str(out)],capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(marker.read_text(),'original')
            self.assertFalse((out/'inputs').exists())

if __name__=='__main__':unittest.main()
