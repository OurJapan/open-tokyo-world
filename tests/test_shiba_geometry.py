"""Independent geometry and invalid-input checks without Blender or local assets."""
import copy
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import shiba_momijidani_v1 as shiba
import validate_shiba_momijidani as saved


def box(z0,z1):
    # Eight independently specified corners and twelve outward-facing triangles.
    return {'vertices':[[x,y,z] for z in (z0,z1) for x,y in [(40,-120),(50,-120),(50,-110),(40,-110)]],
            'faces':[[0,2,1],[0,3,2],[4,5,6],[4,6,7],
                     [0,1,5],[0,5,4],[1,2,6],[1,6,5],
                     [2,3,7],[2,7,6],[3,0,4],[3,4,7]]}


def plan():
    return {'version':1,'input_sha256':shiba.INPUT_SHA256,
            'sources':{'osm':{'sha256':shiba.OSM_SHA256},
                       'road_mask':{'input_sha256':shiba.INPUT_SHA256,'sha256':'a'*64,
                                    'roads':[{'name':name,'mesh_sha256':'b'*64} for name in sorted(shiba.ROAD_OBJECTS)]}},
            'boundary':[[30,-175],[130,-175],[130,0],[30,0]],
            'forest_floor':box(.12,.16),'path_surface':box(.49,.53),
            'trees':[{'x':60.,'y':-80.,'radius':3.,'height':8.,'seed':12}],
            'shrubs':[{'x':80.,'y':-90.,'radius':.6,'height':.8,'seed':13}],
            'audit':{'placement_mask_polygons':[{'exterior':[[31,-170],[35,-170],[35,-165],[31,-165],[31,-170]],'holes':[]}]}}


class ShibaPlanTests(unittest.TestCase):
    def test_bounded_fixture_is_valid(self):
        candidate=plan()
        self.assertIs(shiba.validate_plan(candidate),candidate)

    def test_other_input_source_and_version_are_rejected(self):
        for key,value in [('version',2),('input_sha256','0'*64)]:
            candidate=plan();candidate[key]=value
            with self.assertRaises(ValueError):shiba.validate_plan(candidate)
        candidate=plan();candidate['sources']['osm']['sha256']='0'*64
        with self.assertRaises(ValueError):shiba.validate_plan(candidate)

    def test_road_mask_requires_fixed_input_hashes_and_exact_road_scope(self):
        for key,value in [('input_sha256','0'*64),('sha256','not-a-hash'),('roads',[])]:
            candidate=plan();candidate['sources']['road_mask'][key]=value
            with self.assertRaises(ValueError):shiba.validate_plan(candidate)
        candidate=plan();candidate['sources']['road_mask']['roads'][0]['name']='unrelated road'
        with self.assertRaises(ValueError):shiba.validate_plan(candidate)
        candidate=plan();candidate['sources']['road_mask']['roads'][0]['mesh_sha256']=True
        with self.assertRaises(ValueError):shiba.validate_plan(candidate)

    def test_boundary_and_surface_coordinates_must_be_finite_numbers(self):
        for bad in (float('nan'),float('inf'),float('-inf'),True):
            for target in ('boundary','forest_floor','path_surface'):
                with self.subTest(target=target,value=bad):
                    candidate=plan()
                    points=candidate[target] if target=='boundary' else candidate[target]['vertices']
                    points[0][0]=bad
                    with self.assertRaises(ValueError):shiba.validate_plan(candidate)

    def test_xy_scope_and_surface_elevation_are_bounded(self):
        for target,index,value in [('boundary',0,23.),('boundary',1,-183.),
                                   ('forest_floor',0,137.),('forest_floor',2,.2),
                                   ('path_surface',1,5.),('path_surface',2,.54)]:
            candidate=plan();points=candidate[target] if target=='boundary' else candidate[target]['vertices']
            points[0][index]=value
            with self.assertRaises(ValueError):shiba.validate_plan(candidate)

    def test_invalid_indices_degenerate_faces_and_empty_meshes_are_rejected(self):
        for face in ([0,1,99],[-1,1,2],[True,1,2],[0.,1,2],[0,0,1],[0,1],[]):
            candidate=plan();candidate['forest_floor']['faces'][0]=face
            with self.assertRaises(ValueError):shiba.validate_plan(candidate)
        for key in ('vertices','faces'):
            candidate=plan();candidate['path_surface'][key]=[]
            with self.assertRaises(ValueError):shiba.validate_plan(candidate)

    def test_planting_seed_dimensions_locations_and_counts_are_restricted(self):
        for kind in ('trees','shrubs'):
            for key,value in [('seed',True),('seed',3.5),('x',float('nan')),('height',True),
                              ('radius',100),('height',100),('x',29),('y',1)]:
                with self.subTest(kind=kind,key=key,value=value):
                    candidate=plan();candidate[kind][0][key]=value
                    with self.assertRaises(ValueError):shiba.validate_plan(candidate)
            candidate=plan();candidate[kind]=[]
            with self.assertRaises(ValueError):shiba.validate_plan(candidate)


class SavedGeometryTests(unittest.TestCase):
    def test_saved_closed_surface_and_exact_plan_match(self):
        candidate=plan();mesh=candidate['forest_floor']
        vertices=[tuple(struct.unpack('<f',struct.pack('<f',v))[0] for v in p) for p in mesh['vertices']]
        result=saved.check_mesh(vertices,mesh['faces'],candidate['boundary'],closed=True)
        self.assertTrue(result['closed_edge_incidence_two'])
        result=saved.match_surface(vertices,mesh['faces'],mesh)
        self.assertAlmostEqual(result['top_area_m2'],100.)
        changed=copy.deepcopy(vertices);changed[0]=(41.,-120.,vertices[0][2])
        with self.assertRaises(ValueError):saved.match_surface(changed,mesh['faces'],mesh)

    def test_saved_missing_face_wrong_winding_and_degenerate_face_are_rejected(self):
        candidate=plan();mesh=candidate['forest_floor']
        for faces in [mesh['faces'][1:], [list(reversed(mesh['faces'][0]))]+mesh['faces'][1:],
                      [[0,0,1]]+mesh['faces'][1:]]:
            with self.assertRaises(ValueError):saved.check_mesh(mesh['vertices'],faces,candidate['boundary'],closed=True)

    def test_saved_boundary_and_planting_envelopes_are_independently_enforced(self):
        candidate=plan();mesh=candidate['forest_floor']
        with self.assertRaises(ValueError):
            saved.check_mesh(mesh['vertices'],mesh['faces'],[[45,-175],[130,-175],[130,0],[45,0]])
        self.assertTrue(saved.in_ring((30,-90),candidate['boundary']))
        self.assertFalse(saved.in_ring((29.99,-90),candidate['boundary']))
        plants=candidate['trees']
        self.assertEqual(saved.match_planting_envelopes([(60,-80,5),(63,-80,5)],plants,True)['represented_plantings'],1)
        with self.assertRaises(ValueError):saved.match_planting_envelopes([(63.01,-80,5)],plants)

    def test_center_margin_protects_complete_crown_from_paths_and_buildings(self):
        candidate=plan();saved.validate_placement_masks(candidate)
        candidate['trees'][0]['x']=33.
        with self.assertRaises(ValueError):saved.validate_placement_masks(candidate)
        candidate=plan();candidate['audit']['placement_mask_polygons'][0]['exterior']=[
            [60,-80],[61,-80],[61,-79],[60,-79],[60,-80]]
        with self.assertRaises(ValueError):saved.validate_placement_masks(candidate)

    def test_road_triangle_contact_handles_both_windings_and_boundary(self):
        triangle=[(0,0,0),(2,0,0),(0,2,0)]
        for ring in (triangle,list(reversed(triangle))):
            self.assertTrue(saved.in_triangle_xy((.5,.5),ring))
            self.assertTrue(saved.in_triangle_xy((1,1),ring))
            self.assertFalse(saved.in_triangle_xy((1.01,1.01),ring))

    def test_each_saved_trunk_and_shrub_has_ground_contact(self):
        for kind in ('trees','shrubs'):
            plants=plan()[kind]
            item=plants[0];x,y=item['x'],item['y']
            self.assertEqual(saved.check_planting_contact([(x,y,.16)],plants,kind)['grounded_plantings'],1)
            with self.assertRaises(ValueError):saved.check_planting_contact([(x,y,.17)],plants,kind)
            radius=item['height']*.027 if kind=='trees' else item['radius']*.85
            with self.assertRaises(ValueError):saved.check_planting_contact([(x+radius+.001,y,.16)],plants,kind)
            extra=copy.deepcopy(plants);extra.append({**item,'x':x+15})
            with self.assertRaises(ValueError):saved.check_planting_contact([(x,y,.16)],extra,kind)
            with self.assertRaises(ValueError):saved.match_planting_envelopes([(x,y,.16)],extra,coverage=True)

    def test_legacy_downward_road_tops_remain_protected(self):
        upward=[(30,-100,.3),(35,-100,.3),(30,-95,.3)]
        self.assertTrue(saved.horizontal_road_projection(upward))
        self.assertTrue(saved.horizontal_road_projection(list(reversed(upward))))
        self.assertFalse(saved.horizontal_road_projection([(30,-100,.3),(35,-100,.3),(35,-100,.46)]))
        for z in (.0,2.):
            self.assertFalse(saved.horizontal_road_projection([(x,y,z) for x,y,_ in upward]))


if __name__=='__main__':unittest.main()
