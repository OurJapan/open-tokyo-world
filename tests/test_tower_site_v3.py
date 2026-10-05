# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from tower_structure_v1 import MeshBuilder
from tower_site_v3 import edit_mesh,components,bounds,OLD
from tower_site_geometry_v3 import geometry
from validate_tower_structure import check_mesh,convex_intersects_box


class TowerSiteTests(unittest.TestCase):
    def test_portal_cut_retains_other_wall_solids_and_header(self):
        b=MeshBuilder()
        b.box('wall',(-9.07,4.4,146.71),(.035,2.4,3.2))
        b.box('wall',(9.07,4.4,146.71),(.035,2.4,3.2))
        m=b.groups['wall'];edited,count=edit_mesh('Photo based main deck / wall',m['vertices'],m['faces'])
        self.assertEqual(count,1)
        _,parts=check_mesh(edited['vertices'],edited['faces'],((-20,20),(-20,20),(140,150)))
        self.assertFalse(any(convex_intersects_box(p,((-9.2,-8.9),(3.63,5.17),(145.2,147.4))) for p in parts))
        self.assertTrue(any(p['bounds'][0][0]>9 for p in parts))
        self.assertTrue(any(p['bounds'][0][1]<-9 and p['bounds'][2][0]>=147.5 for p in parts))

    def test_south_edit_preserves_canopy_and_front_columns(self):
        b=MeshBuilder()
        b.box('metal',(0,-31,5.4),(16,.07,.07))
        b.box('metal',(0,-31,7.4),(26,3,.1))
        b.box('metal',(8,32.7,3.625),(.64,.66,7.25))
        m=b.groups['metal'];edited,count=edit_mesh(OLD+'foottown-metal',m['vertices'],m['faces'])
        self.assertEqual(count,1)
        self.assertEqual(len(list(components(edited['vertices'],edited['faces']))),2)

    def test_additions_are_closed_and_leave_shaft_and_roof_entry_clear(self):
        for name,m in geometry().items():
            _,parts=check_mesh(m['vertices'],m['faces'],((-70,40),(-72,30),(-.1,149)))
            for volume in (((-2.35,2.35),(-2.35,2.35),(16.21,26)),((-12,-4.8),(3.1,5.7),(16.3,18.4))):
                self.assertFalse(any(convex_intersects_box(p,volume) for p in parts),name)

    def test_no_added_site_paving_buries_existing_south_foundations(self):
        m=geometry()['site-paving'];_,parts=check_mesh(m['vertices'],m['faces'],((-70,40),(-72,30),(-.1,149)))
        for x in (-46.6067,46.6067):
            self.assertFalse(any(convex_intersects_box(p,((x-6.2,x+6.2),(-52.8,-40.4),(0,2.1))) for p in parts))


if __name__=='__main__':unittest.main()
