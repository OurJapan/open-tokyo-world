# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import copy
import json
from pathlib import Path
import sys
import unittest
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import mori_plaza_connection_v1 as connection
from review import validate_patch


class PlazaConnectionTests(unittest.TestCase):
    def test_both_measured_rises_disappear_in_core(self):
        for u,v,z in [(-21.8641867,50.2447274,.3),(-22.7547261,49.8004309,.46)]:
            x,y,_ = connection.world(u,v)
            self.assertEqual(connection.factor(x,y),0)
            self.assertAlmostEqual(.11+(z-.11)*connection.factor(x,y),.11)

    def test_transition_reaches_old_height_continuously(self):
        for u,v in [(-30,50),(-14,50),(-22,42),(-22,58)]:
            x,y,_ = connection.world(u,v)
            self.assertAlmostEqual(connection.factor(x,y),1)
        for sign in (-1,1):
            x,y,_ = connection.world(-22+sign*6,50)
            self.assertAlmostEqual(connection.factor(x,y),.5)

    def test_partition_conserves_xy_area_across_all_cells(self):
        poly = [connection.world(u,v,.3) for u,v in [(-34,38),(-10,38),(-10,62),(-34,62)]]
        outside, selected = connection.partition(poly)
        self.assertAlmostEqual(sum(map(connection.outline.area,outside+selected)),576)
        self.assertAlmostEqual(sum(map(connection.outline.area,selected)),256)
        changed=[connection.lowered(p) for p in selected]
        self.assertAlmostEqual(sum(abs(connection.outline.signed_area(p)) for p in changed),256,delta=.0001)
        self.assertTrue(all(connection.outline.signed_area(p)>0 for p in changed))

    def test_core_riser_is_removed_and_transition_riser_remains(self):
        for u,collapsed in [(-22,True),(-28,False)]:
            poly=[connection.world(u,v,z) for v,z in [(49,.3),(51,.3),(51,.46),(49,.46)]]
            self.assertEqual(not bool(connection.lowered(poly)),collapsed)

    def test_exterior_face_is_preserved(self):
        poly=[connection.world(u,v,.3) for u,v in [(-60,40),(-50,40),(-50,45)]]
        self.assertEqual(connection.partition(poly),([poly],[]))

    def test_patch_rejects_broader_scope_and_stacking(self):
        patch=json.loads((ROOT/'patches/mori-plaza-connection-v1.json').read_text())
        validate_patch(patch)
        broad=copy.deepcopy(patch)
        broad['operations'][0]['road_mesh_sha256']['ground']='0'*64
        with self.assertRaises(ValueError):validate_patch(broad)
        patch['operations']*=2
        with self.assertRaises(ValueError):validate_patch(patch)

    def test_millimetric_seam_has_closed_consistent_topology(self):
        ring=[connection.world(u,v)[:2] for u,v in [(-22,49),(-21.996,49),(-21.996,51),(-22,51)]]
        plan={'version':1,'input_sha256':connection.INPUT_SHA256,
              'paving_triangles':[[ring[0],ring[1],ring[2]],[ring[0],ring[2],ring[3]]],
              'paving_rings':[ring],'audit':{}}
        connection.validate_plan(plan)
        vertices,faces=connection.paving_mesh(plan)
        edges=Counter()
        for face in faces:
            self.assertGreater(connection.outline.area([vertices[i] for i in face]),1e-10)
            for a,b in zip(face,face[1:]+face[:1]):edges[(a,b)]+=1
        for (a,b),n in edges.items():self.assertEqual(n,edges[(b,a)])
        bad=copy.deepcopy(plan);bad['input_sha256']='0'*64
        with self.assertRaises(ValueError):connection.validate_plan(bad)
        bad=copy.deepcopy(plan);bad['paving_rings'][0][0]=connection.world(-40,50)[:2]
        with self.assertRaises(ValueError):connection.validate_plan(bad)

    def test_gap_fill_excludes_existing_surfaces_and_distant_open_ground(self):
        try:import shapely as sh
        except ImportError:self.skipTest('Production Shapely is optional in portable checks')
        from prepare_mori_plaza_connection import gap_geometry
        left,right=sh.box(0,0,1,2),sh.box(1.004,0,2,2)
        fill=gap_geometry(left,right,sh.box(0,.1,2,1.9))
        self.assertAlmostEqual(fill.area,.004*1.8)
        self.assertEqual(fill.intersection(left.union(right)).area,0)
        self.assertTrue(gap_geometry(left,sh.box(1.1,0,2,2),sh.box(0,0,2,2)).is_empty)


if __name__=='__main__':unittest.main()
