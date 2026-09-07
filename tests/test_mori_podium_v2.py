import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import mori_podium_v2 as podium
import review


class PodiumTests(unittest.TestCase):
    def test_source_size_and_content_are_both_locked(self):
        for data in (b'wrong archive',b'\0'*podium.SOURCE_BYTES):
            with self.assertRaises(ValueError):podium.validate_source_bytes(data)

    def test_podium_patch_cannot_replace_city_tiles(self):
        p=json.loads((ROOT/'patches/mori-podium-v2.json').read_text(encoding='utf8'))
        review.validate_patch(p)
        for key,value in [('object','PLATEAU_data221'),('feature_id','otw:other'),('expected_mesh_sha256','bad')]:
            bad=copy.deepcopy(p);bad['operations'][-1][key]=value
            with self.assertRaises(ValueError):review.validate_patch(bad)


if __name__=='__main__':unittest.main()
