# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Scope preservation and closed-bed geometry checks for the actual city increment."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from tower_approach_plan import check_plan, added_names, bed_geometry, clipped_area_2d, COLLECTION
from tower_approach import compare


class ApproachPlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT/'areas/tokyo-tower/approach-trees-v1.json').read_text(encoding='utf-8'))

    def test_plan_has_eight_trees_and_eighteen_independent_objects(self):
        check_plan(self.plan)
        self.assertEqual(len(added_names(self.plan)),18)
        self.assertTrue(all(-30 < r['source_matrix_world'][0][3] < 75 for r in self.plan['trees']))
        self.assertNotIn(162,[r['index'] for r in self.plan['trees']])

    def test_duplicate_or_unreviewed_seed_is_rejected(self):
        self.plan['trees'][1] = self.plan['trees'][0]
        with self.assertRaisesRegex(ValueError,'eight seed'):
            check_plan(self.plan)

    def test_seed_outside_target_extent_is_rejected(self):
        self.plan['trees'][0]['source_matrix_world'][0][3] = -430
        with self.assertRaisesRegex(ValueError,'extent'):
            check_plan(self.plan)

    def test_nonfinite_seed_is_rejected(self):
        self.plan['trees'][0]['source_matrix_world'][2][3] = float('nan')
        with self.assertRaisesRegex(ValueError,'Non-finite'):
            check_plan(self.plan)

    def test_unreviewed_bed_height_is_rejected(self):
        self.plan['beds']['rim_top_m'] = .3
        with self.assertRaisesRegex(ValueError,'bed dimensions'):
            check_plan(self.plan)

    def test_beds_are_closed_outward_and_have_expected_volume(self):
        for rim in (False,True):
            vertices, faces = bed_geometry(self.plan,rim)
            incidences = {}; volume = 0.0
            for face in faces:
                for a,b in zip(face,face[1:]+face[:1]):
                    edge = tuple(sorted((a,b))); incidences[edge] = incidences.get(edge,0)+1
                a = vertices[face[0]]
                for i in range(1,len(face)-1):
                    b,c = vertices[face[i]],vertices[face[i+1]]
                    cross = (b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0])
                    volume += sum(x*y for x,y in zip(a,cross))/6
            self.assertEqual(set(incidences.values()),{2})
            expected = 8*((1.2**2-1.04**2)*.46 if rim else 1.04**2*.44)
            self.assertAlmostEqual(volume,expected,places=7)

    def test_continuous_overlap_detects_small_corner_between_grid_samples(self):
        triangle = [(.599,.599),(.7,.599),(.599,.7)]
        self.assertGreater(clipped_area_2d(triangle,(-.6,-.6),(.6,.6)),0)

    def test_touching_edge_has_no_projected_area(self):
        self.assertEqual(clipped_area_2d([(.6,-.1),(.8,-.1),(.6,.1)],(-.6,-.6),(.6,.6)),0)


class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.before = {'objects':{'road':{'mesh':'unchanged','hide_render':False}},'assets':[],
                       'scene_state':{'world':'daylight'},'collections':{'legacy':{'hide_render':True}}}
        self.after = copy.deepcopy(self.before)
        self.after['objects']['new tree'] = {'mesh':'approved'}
        self.after['collections'][COLLECTION] = {'hide_render':False}

    def test_additive_candidate_is_accepted(self):
        self.assertEqual(compare(self.before,self.after,{'new tree'})['unchanged_existing_objects'],1)

    def test_road_mutation_is_rejected(self):
        self.after['objects']['road']['mesh'] = 'modified'
        with self.assertRaisesRegex(ValueError,'Existing objects changed'):
            compare(self.before,self.after,{'new tree'})

    def test_deleted_object_is_rejected(self):
        del self.after['objects']['road']
        with self.assertRaisesRegex(ValueError,'added/removed'):
            compare(self.before,self.after,{'new tree'})

    def test_unscoped_addition_is_rejected(self):
        self.after['objects']['extra'] = {}
        with self.assertRaisesRegex(ValueError,'added/removed'):
            compare(self.before,self.after,{'new tree'})

    def test_legacy_collection_mass_reveal_is_rejected(self):
        self.after['collections']['legacy']['hide_render'] = False
        with self.assertRaisesRegex(ValueError,'Existing collection changed'):
            compare(self.before,self.after,{'new tree'})

    def test_asset_or_lighting_change_is_rejected(self):
        self.after['scene_state']['world'] = 'different lighting'
        with self.assertRaisesRegex(ValueError,'assets or scene state'):
            compare(self.before,self.after,{'new tree'})

    def test_selected_original_viewport_suppression_is_accepted(self):
        name = 'Street tree ginkgo 158'
        self.before['objects'][name] = {'mesh':'approved','hide_viewport':False}
        self.after['objects'][name] = {'mesh':'approved','hide_viewport':True}
        result = compare(self.before,self.after,{'new tree'})
        self.assertEqual(result['original_source_viewport_suppression'],[name])

    def test_suppression_cannot_conceal_original_geometry_change(self):
        name = 'Street tree ginkgo 158'
        self.before['objects'][name] = {'mesh':'approved','hide_viewport':False}
        self.after['objects'][name] = {'mesh':'changed','hide_viewport':True}
        with self.assertRaisesRegex(ValueError,'Existing objects changed'):
            compare(self.before,self.after,{'new tree'})


if __name__ == '__main__':
    unittest.main()
