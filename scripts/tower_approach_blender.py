# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Isolated build/read-only validation worker; never overwrites a source scene."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from blender_worker import array_prop, mesh_fingerprint, validate, render
from component_contracts import material_snapshot, signature
from city_catalog_blender import enabled_meshes
from tower_approach_plan import (FEATURE, COLLECTION, SOIL, EDGING, MATERIALS,
                                 check_plan, added_names, source_names, tree_name, bed_geometry, clipped_area_2d)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def licensed_sources(plan):
    provenance = read(ROOT / 'assets/procedural-components/provenance.json')
    require(provenance['status'] == 'consent-confirmed' and provenance['license'] == 'CC-BY-4.0',
            'Missing existing component consent')
    prototypes = {r['id']: r for r in provenance['prototype_meshes']}
    for name in MATERIALS:
        require(signature(material_snapshot(bpy.data.materials[name])) == provenance['material_signatures'][name],
                'Approved procedural material differs: '+name)
    for row in plan['trees']:
        for part, suffix in [('bark',''),('foliage','.001')]:
            obj = bpy.data.objects[f"Street tree ginkgo {row['index']}{suffix}"]
            pin = prototypes[f"ginkgo-{row['variant']}-{part}"]
            require(mesh_fingerprint(obj.data) == pin['mesh_sha256'], 'Approved prototype differs: '+obj.name)
            require([m.name for m in obj.data.materials] == pin['materials'], 'Prototype material assignment differs')
            # Disabled viewport objects may have an unevaluated identity
            # matrix_world after reopen. These pinned seeds have no parent,
            # animation or constraints, so matrix_basis is their stored pose.
            require(np.allclose(np.array(obj.matrix_basis), row['source_matrix_world'], rtol=0, atol=1e-7),
                    'Seed matrix differs: '+obj.name)
            require(not obj.modifiers and not obj.animation_data and not obj.parent and not obj.constraints,
                    'Unsupported seed dependency')
    return prototypes


def build(job):
    plan = check_plan(job['plan']); output = Path(job['output'])
    require(COLLECTION not in bpy.data.collections and not (added_names(plan) & set(bpy.data.objects.keys())),
            'Candidate already applied; refusing duplicate additions')
    prototypes = licensed_sources(plan)
    visible = enabled_meshes()
    for row in plan['trees']:
        for suffix in ('','.001'):
            require(f"Street tree ginkgo {row['index']}{suffix}" not in visible,
                    'Original tree already visible; duplicate restoration refused')
    collection = bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(collection)
    collection['otw_source_viewport_suppression'] = json.dumps(sorted(source_names()))
    for row in plan['trees']:
        for part, suffix in [('bark',''),('foliage','.001')]:
            source = bpy.data.objects[f"Street tree ginkgo {row['index']}{suffix}"]
            matrix = source.matrix_basis.copy()
            # Render-disabled collections can remain visible in the editor.
            # Suppress only these sixteen sources, preserving their geometry
            # and the legacy collection's settings and all other contents.
            source.hide_viewport = True
            obj = source.copy(); obj.name = tree_name(row['index'], part)
            collection.objects.link(obj); obj.hide_render = False; obj.hide_viewport = False
            # The approved trunk mesh starts at local z=.2, not z=0.
            obj.matrix_world = matrix
            obj.location.z = plan['beds']['soil_top_m'] - .2*obj.scale.z
            obj['otw_feature_id'] = FEATURE; obj['otw_part_id'] = f"seed-{row['index']}/{part}"
            obj['otw_seed_object'] = source.name
            obj['otw_component_id'] = f"ginkgo-{row['variant']}-{part}"
            obj['otw_component_license'] = 'CC-BY-4.0'
            obj['otw_component_attribution'] = 'ark4ez / OurJapan'
            obj['otw_placement_status'] = 'Existing illustrative layout; height fitted to candidate soil bed, not surveyed'
    for name, material, rim in [(SOIL,'Street tree pit soil',False),(EDGING,'Tree pit edging',True)]:
        vertices, faces = bed_geometry(plan, rim)
        mesh = bpy.data.meshes.new(name); mesh.from_pydata(vertices, [], faces); mesh.update()
        mesh.materials.append(bpy.data.materials[material])
        obj = bpy.data.objects.new(name, mesh); collection.objects.link(obj)
        obj['otw_feature_id'] = FEATURE; obj['otw_part_id'] = 'flush-edging' if rim else 'soil-beds'
        obj['otw_geometry_status'] = 'Original candidate geometry; model fit, not surveyed street furniture'
    bpy.context.view_layer.update()
    require(set(o.name for o in collection.objects) == added_names(plan), 'Unexpected additions')
    # Compact collection for integration; no city textures, cameras or lights.
    bpy.data.libraries.write(str(output / 'approach-additions.blend'), {collection}, fake_user=False, compress=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output / 'after.blend'), check_existing=False, relative_remap=False)
    return {'ok': True, 'added_objects': sorted(added_names(plan)), 'collection': COLLECTION,
            'feature_id': FEATURE, 'tree_count': len(plan['trees']),
            'added_vertices': sum(len(o.data.vertices) for o in collection.objects),
            'added_polygons': sum(len(o.data.polygons) for o in collection.objects)}


def scene_state():
    scene = bpy.context.scene
    lights = {o.name: {'type':o.data.type,'energy':o.data.energy,'color':list(o.data.color)}
              for o in scene.objects if o.type == 'LIGHT'}
    return {'world': scene.world.name if scene.world else None, 'lights':lights,
            'markers':[(m.name,m.frame,m.camera.name if m.camera else None) for m in scene.timeline_markers],
            'active_camera':scene.camera.name if scene.camera else None,
            'render_engine':scene.render.engine, 'view_transform':scene.view_settings.view_transform,
            'look':scene.view_settings.look, 'exposure':scene.view_settings.exposure,
            'gamma':scene.view_settings.gamma, 'frame_range':[scene.frame_start,scene.frame_end]}


def extended_validate(job, after):
    result = validate(job)
    for name, row in result['objects'].items():
        obj = bpy.data.objects[name]
        row['collections'] = sorted(c.name for c in obj.users_collection)
        row['hide_viewport'] = obj.hide_viewport
        if name in source_names():
            row['transform'] = [float(v) for r in obj.matrix_basis for v in r]
            row['transform_basis'] = 'stored matrix_basis; pinned unparented static source'
        row['properties'] = {k: obj[k] for k in obj.keys() if isinstance(obj[k], (str,int,float,bool))}
        if obj.type == 'MESH':
            row['smooth_sha256'] = hashlib.sha256(array_prop(obj.data.polygons, 'use_smooth', 1, np.bool_).tobytes()).hexdigest()
    result['collections'] = {c.name:{'hide_render':c.hide_render,'hide_viewport':c.hide_viewport,
                            'children':sorted(ch.name for ch in c.children),
                            'objects':sorted(o.name for o in c.objects)} for c in bpy.data.collections}
    result['scene_state'] = scene_state()
    if after:
        result['placement'] = check_placement(job['plan'])
        require(result['placement']['ok'], 'Placement check failed')
    return result


def surface(name):
    obj = bpy.data.objects[name]
    return BVHTree.FromPolygons([obj.matrix_world @ v.co for v in obj.data.vertices],
                               [list(p.vertices) for p in obj.data.polygons])


def height(tree, x, y):
    location, _, _, _ = tree.ray_cast(Vector((x,y,100)), Vector((0,0,-1)), 110)
    return None if location is None else location.z


def world_triangles(name):
    obj = bpy.data.objects[name]; mesh = obj.data; mesh.calc_loop_triangles()
    coords = array_prop(mesh.vertices,'co',3,np.float32).reshape(-1,3)
    matrix = np.asarray(obj.matrix_world,dtype=np.float64)
    world = coords @ matrix[:3,:3].T + matrix[:3,3]
    indices = array_prop(mesh.loop_triangles,'vertices',3,np.int32).reshape(-1,3)
    return world[indices]


def rectangle_overlap(triangles, x, y):
    low, high = (x-.6,y-.6),(x+.6,y+.6)
    mins, maxs = triangles[:,:,:2].min(axis=1), triangles[:,:,:2].max(axis=1)
    candidates = triangles[np.all(maxs >= low,axis=1) & np.all(mins <= high,axis=1)]
    areas = [clipped_area_2d(triangle,low,high) for triangle in candidates]
    return sum(areas), len(candidates)


def check_closed_beds(plan):
    for name,rim in [(SOIL,False),(EDGING,True)]:
        mesh = bpy.data.objects[name].data
        expected,_ = bed_geometry(plan,rim)
        actual = array_prop(mesh.vertices,'co',3,np.float32).reshape(-1,3)
        require(actual.shape == np.asarray(expected).shape and np.allclose(actual,expected,rtol=0,atol=5e-6),
                'Saved bed dimensions differ from plan')
        bm = bmesh.new(); bm.from_mesh(mesh)
        try:
            require(all(e.is_manifold for e in bm.edges), 'Open planting-bed mesh')
            require(all(f.calc_area() > 1e-8 for f in bm.faces), 'Zero-area planting-bed face')
            require(bm.calc_volume(signed=True) > 0, 'Inward planting-bed normals')
        finally:
            bm.free()


def validate_additions(job):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    path = str(Path(job['output'])/'approach-additions.blend')
    with bpy.data.libraries.load(path,link=False) as (source,target):
        require(COLLECTION in source.collections,'Missing saved delta collection')
        target.collections = [COLLECTION]
    bpy.context.scene.collection.children.link(target.collections[0])
    plan = job['plan']; names = added_names(plan)
    require(set(o.name for o in bpy.context.scene.objects) == names,'Saved delta object scope differs')
    require(names <= enabled_meshes(),'Saved delta objects hidden')
    require(all(bpy.data.objects[name].visible_get() for name in names),'Saved delta hidden in editor')
    require(not bpy.data.images and not bpy.data.texts,'Unexpected images or embedded scripts in delta')
    require(set(bpy.data.materials.keys()) == set(MATERIALS),'Unexpected delta materials')
    require(not any(d.library for group in ('objects','meshes','materials','node_groups')
                    for d in getattr(bpy.data,group)),'Linked delta data')
    provenance = read(ROOT/'assets/procedural-components/provenance.json')
    prototypes = {r['id']:r for r in provenance['prototype_meshes']}
    for name in MATERIALS:
        require(signature(material_snapshot(bpy.data.materials[name])) == provenance['material_signatures'][name],
                'Delta material differs from licensed component')
    for row in plan['trees']:
        for part in ('bark','foliage'):
            obj = bpy.data.objects[tree_name(row['index'],part)]
            require(mesh_fingerprint(obj.data) == prototypes[f"ginkgo-{row['variant']}-{part}"]['mesh_sha256'],
                    'Delta prototype differs')
            require(obj.get('otw_feature_id') == FEATURE,'Delta feature ID missing')
    check_closed_beds(plan)
    require(len(bpy.data.meshes) == 8,'Expected six shared prototypes and two bed meshes')
    return {'ok':True,'objects':len(names),'unique_meshes':len(bpy.data.meshes),'materials':len(bpy.data.materials),
            'images':len(bpy.data.images),'embedded_scripts':len(bpy.data.texts),
            'scope':'Append-only local collection; city textures, buildings, cameras and lights excluded.'}


def check_placement(plan):
    licensed_sources(plan)
    enabled = enabled_meshes(); require(added_names(plan) <= enabled, 'Additions not render-enabled')
    require(all(bpy.data.objects[name].visible_get() for name in added_names(plan)),'Additions hidden in editor')
    require(all(bpy.data.objects[name].hide_viewport and not bpy.data.objects[name].visible_get()
                for name in source_names()),'Original source still visible in editor')
    pavement = surface('pavement_0 unified road'); asphalt = surface('asphalt 15s road detail')
    soil = surface(SOIL); ground = surface('ground')
    road_triangles = world_triangles('asphalt 15s road detail')
    foundation_triangles = world_triangles('Tokyo Tower structure / stone')
    tower_obstacles = {name:surface(name) for name in ('Tokyo Tower structure / stone','Tokyo Tower structure / orange')}
    nearby_buildings = []
    for obj in bpy.context.scene.objects:
        building = 'PLATEAU' in obj.name or obj.name == 'roof' or obj.name in {f'wall{i}' for i in range(8)}
        if obj.type != 'MESH' or obj.name not in enabled or not building:
            continue
        corners = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
        if (min(v.x for v in corners) < 76 and max(v.x for v in corners) > -11 and
                min(v.y for v in corners) < 81 and max(v.y for v in corners) > 24):
            nearby_buildings.append((obj.name,surface(obj.name)))
    rows = []
    for seed in plan['trees']:
        bark = bpy.data.objects[tree_name(seed['index'],'bark')]
        foliage = bpy.data.objects[tree_name(seed['index'],'foliage')]
        x, y, _ = bark.matrix_world.translation
        require(abs(x-seed['source_matrix_world'][0][3]) < 1e-6 and abs(y-seed['source_matrix_world'][1][3]) < 1e-6,
                'Horizontal seed placement changed')
        require(abs(height(ground,x,y)-plan['beds']['bottom_m']) < 1e-4, 'Bed does not meet ground')
        base_z = min((bark.matrix_world @ v.co).z for v in bark.data.vertices)
        soil_z = height(soil,x,y); require(abs(base_z-soil_z) < 1e-4, 'Tree root floats or penetrates soil')
        crown_z = min((foliage.matrix_world @ v.co).z for v in foliage.data.vertices)
        require(crown_z >= 2.5, 'Insufficient lower foliage clearance')
        asphalt_area, asphalt_candidates = rectangle_overlap(road_triangles,x,y)
        foundation_area, foundation_candidates = rectangle_overlap(foundation_triangles,x,y)
        require(asphalt_area < 1e-7,'Planting bed overlaps asphalt projection')
        require(foundation_area < 1e-7,'Planting bed overlaps tower foundation projection')
        shell_overlaps = {}
        for part in ('bark','foliage'):
            tree_bvh = surface(tree_name(seed['index'],part))
            for name,obstacle in tower_obstacles.items():
                overlaps = tree_bvh.overlap(obstacle)
                require(not overlaps,'Tree intersects tower structure: '+str(seed['index'])+'/'+part+'/'+name)
                shell_overlaps[part+'/'+name] = len(overlaps)
        road_hits = []
        for dx in np.linspace(-.60,.60,7):
            for dy in np.linspace(-.60,.60,7):
                if height(asphalt,x+dx,y+dy) is not None:
                    road_hits.append([float(dx),float(dy)])
        require(not road_hits, 'Planting bed overlaps asphalt samples')
        pavers = [height(pavement,x+dx,y+dy) for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]]
        pavers = [v for v in pavers if v is not None]
        require(pavers and max(abs(v-plan['beds']['rim_top_m']) for v in pavers) < 1e-4,
                'Bed edging does not align with adjacent pavement')
        for name, tree in nearby_buildings:
            require(all(height(tree,x+dx,y+dy) is None for dx,dy in [(0,0),(-.6,0),(.6,0),(0,-.6),(0,.6)]),
                    'Tree bed inside PLATEAU building: '+name)
        rows.append({'seed':seed['index'],'xy':[x,y],'root_z':base_z,'soil_z':soil_z,
                     'foliage_min_z':crown_z,'adjacent_pavement_z':pavers,
                     'asphalt_samples':49,'road_hits':road_hits,'asphalt_overlap_area_m2':asphalt_area,
                     'foundation_overlap_area_m2':foundation_area,'tower_shell_overlap_pairs':shell_overlaps,
                     'asphalt_candidate_triangles':asphalt_candidates,'foundation_candidate_triangles':foundation_candidates})
    check_closed_beds(plan)
    return {'ok':True,'trees':rows,'nearby_building_meshes_checked':len(nearby_buildings),
            'editor_visible_additions':len(added_names(plan)),'editor_hidden_original_sources':len(source_names()),
            'limits':['Projected asphalt/foundation intersections and tower shell pairs checked; not a complete solid-volume collision proof.',
                      'PLATEAU and legacy roof/wall building clearance uses five column samples per bed.',
                      'Local model surface heights only; no surveyed terrain or species accuracy claim.']}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--job',required=True)
    parser.add_argument('--phase',required=True); parser.add_argument('--report',required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:]); job = read(args.job)
    result = {'ok':False}
    try:
        require(bpy.app.version_string == job['settings']['blender_version'], 'Blender version differs')
        if args.phase == 'build': result = build(job)
        elif args.phase == 'validate-additions': result = validate_additions(job)
        elif args.phase.startswith('validate-'): result = extended_validate(job, args.phase == 'validate-after')
        elif args.phase.startswith('render-'): result = render(job,args.phase)
        else: raise ValueError('Unknown phase')
        require(result['ok'], 'Worker validation failed')
    except Exception as exc:
        result['error'] = str(exc); raise
    finally:
        Path(args.report).write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n',encoding='utf-8')


if __name__ == '__main__':
    main()
