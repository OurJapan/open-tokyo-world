import copy
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import mori_crown_material as material
import review


class CrownMaterialTests(unittest.TestCase):
    def test_body_and_boundary_faces_are_excluded(self):
        for heights in ([313,318.312,318.312,313], [318.32]*4, [317,324,324,317]):
            self.assertFalse(material.is_crown_face(heights))
        self.assertTrue(material.is_crown_face([318.320007,323.4,324,318.320007]))

    def test_target_and_both_hashes_are_required(self):
        patch=json.loads((ROOT/'patches/mori-crown-material-v1.json').read_text())
        review.validate_patch(patch)
        for key,value in [('object','neighbor'),('expected_material_sha256',''),('expected_mesh_sha256','bad')]:
            altered=copy.deepcopy(patch);altered['operations'][-1][key]=value
            with self.assertRaises(ValueError):review.validate_patch(altered)


if __name__=='__main__':unittest.main()
