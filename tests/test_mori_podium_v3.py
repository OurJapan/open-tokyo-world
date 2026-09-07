import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from mori_podium_v3 import truncated_lowrise_edges


class PodiumOpeningRegression(unittest.TestCase):
    def test_40m_whole_face_filter_is_detected_as_missing_roof_neighbor(self):
        triangles=[[(0,0,38.987),(1,0,38.987),(0,1,38.987)],
                   [(1,0,38.987),(0,0,38.987),(1,-1,40.681)]]
        self.assertEqual(len(truncated_lowrise_edges(triangles,[True,False])),1)
        self.assertEqual(truncated_lowrise_edges(triangles,[True,True]),[])

    def test_replacement_tower_junction_is_not_a_lowrise_roof(self):
        triangles=[[(0,0,26),(1,0,26),(0,1,26)],
                   [(1,0,26),(0,0,26),(1,-1,319.89)]]
        self.assertEqual(truncated_lowrise_edges(triangles,[True,False]),[])


if __name__=='__main__':unittest.main()
