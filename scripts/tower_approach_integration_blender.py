# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Append the reviewed tree delta into a disposable west-path candidate."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import bpy
from mathutils import Vector,Matrix
from blender_worker import mesh_fingerprint
from component_contracts import material_snapshot, signature
from tower_approach_blender import licensed_sources, require, read
from tower_approach_plan import (COLLECTION, SOIL, EDGING, MATERIALS, added_names,
                                 check_plan, source_names, tree_name,bed_geometry)
from tower_approach import digest


def bounds(objects):
    points = [o.matrix_world @ Vector(p) for o in objects for p in o.bound_box]
    return {'minimum': [min(p[k] for p in points) for k in range(3)],
            'maximum': [max(p[k] for p in points) for k in range(3)]}


def append_delta(job):
    plan = check_plan(job['plan']); names = added_names(plan)
    require(COLLECTION not in bpy.data.collections and not (names & set(bpy.data.objects.keys())),
            'Candidate already applied; refusing duplicate additions')
    licensed_sources(plan)
    require(all(not bpy.data.objects[n].hide_viewport for n in source_names()),
            'Original viewport suppression already applied')
    existing_materials = {n:bpy.data.materials[n] for n in MATERIALS}
    prototypes = {(r['index'],part):bpy.data.objects[f"Street tree ginkgo {r['index']}{suffix}"].data
                  for r in plan['trees'] for part,suffix in [('bark',''),('foliage','.001')]}
    old_meshes = set(bpy.data.meshes); old_materials = set(bpy.data.materials)
    with bpy.data.libraries.load(job['delta'], link=False) as (source,target):
        require(COLLECTION in source.collections, 'Missing reviewed delta collection')
        target.collections = [COLLECTION]
    collection = target.collections[0]
    require(set(o.name for o in collection.objects) == names, 'Delta object scope differs')
    require(set(json.loads(collection['otw_source_viewport_suppression'])) == source_names(),
            'Delta suppression scope differs')
    # Appending creates suffixed duplicate datablocks. Validate their approved
    # contents first, then reuse the existing city prototypes and materials.
    # This avoids material-name drift without editing existing datablocks.
    provenance = read(ROOT/'assets/procedural-components/provenance.json')
    for row in plan['trees']:
        for part in ('bark','foliage'):
            obj = bpy.data.objects[tree_name(row['index'],part)]
            original = prototypes[row['index'],part]
            require(mesh_fingerprint(obj.data) == mesh_fingerprint(original), 'Delta prototype geometry differs')
            require(len(obj.data.materials) == len(original.materials), 'Delta material slots differ')
            for imported,approved in zip(obj.data.materials,original.materials):
                require(signature(material_snapshot(imported)) == provenance['material_signatures'][approved.name],
                        'Delta prototype shader differs')
            obj.data = original
    for name,material in [(SOIL,'Street tree pit soil'),(EDGING,'Tree pit edging')]:
        mesh = bpy.data.objects[name].data
        require(len(mesh.materials) == 1 and
                signature(material_snapshot(mesh.materials[0])) == provenance['material_signatures'][material],
                'Delta bed shader differs')
        mesh.materials[0] = existing_materials[material]
    bpy.context.scene.collection.children.link(collection)
    for name in source_names():
        bpy.data.objects[name].hide_viewport = True
    for mesh in set(bpy.data.meshes)-old_meshes:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for material in set(bpy.data.materials)-old_materials:
        if material.users == 0:
            bpy.data.materials.remove(material)
    require(set(bpy.data.materials) == old_materials, 'Unexpected appended material dependency')
    bpy.context.view_layer.update()
    bbox = bounds(collection.objects)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(job['output'])/'after.blend'),
                               check_existing=False, relative_remap=False)
    return {'ok':True, 'collection':COLLECTION, 'added_objects':sorted(names),
            'suppressed_sources':sorted(source_names()), 'world_bounds':bbox,
            'existing_prototypes_reused':6, 'existing_materials_reused':4}


def inspect_astra(job):
    feature = 'bldg_af7335da-7542-44dd-964d-8cccd2b046ff'
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(job['astra_target'],link=False) as (source,loaded):
        require(source.objects == [feature], 'Unexpected Astra target library scope')
        source_collections = list(source.collections)
        loaded.objects = [feature]
    bpy.context.scene.collection.objects.link(loaded.objects[0])
    bpy.context.view_layer.update()
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    require(len(meshes) == 1 and meshes[0].get('gml_id') == feature, 'Unexpected Astra target scope')
    target = meshes[0]
    require(target.name not in added_names(job['plan']) and
            COLLECTION not in {c.name for c in target.users_collection}, 'Astra namespace conflict')
    return {'ok':True, 'feature_id':feature, 'object':target.name,
            'library_collections':sorted(source_collections),
            'world_bounds':bounds(meshes), 'vertices':len(target.data.vertices),
            'polygons':len(target.data.polygons), 'scene_saved':False}


def revise_delta(job):
    """Retain approved components; expose soil and clear the one crown contact."""
    source = Path(job['source_delta']); original_sha = '7bec956402b45347bbee39876555ec2b500df2bc87d227aae19fdb2eb520fe13'
    require(digest(source) == original_sha,'Original production delta differs')
    output = Path(job['output'])/'approach-additions.blend'
    require(not output.exists() and output.resolve().is_relative_to(ROOT/'data/local'), 'Use a new local delta output')
    plan = check_plan(job['plan']); bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(source),link=False) as (library,loaded):
        loaded.collections = [COLLECTION]
    collection = loaded.collections[0]
    require(set(o.name for o in collection.objects) == added_names(plan),'Original delta scope differs')
    provenance = read(ROOT/'assets/procedural-components/provenance.json')
    prototypes = {r['id']:r for r in provenance['prototype_meshes']}
    for name in MATERIALS:
        require(signature(material_snapshot(bpy.data.materials[name])) == provenance['material_signatures'][name],
                'Unapproved delta shader')
    for row in plan['trees']:
        for part in ('bark','foliage'):
            obj = bpy.data.objects[tree_name(row['index'],part)]
            require(mesh_fingerprint(obj.data) == prototypes[f"ginkgo-{row['variant']}-{part}"]['mesh_sha256'],
                    'Unapproved delta tree geometry')
            obj.matrix_world = Matrix(row['source_matrix_world'])
            obj.scale.x *= row['display_xy_scale']; obj.scale.y *= row['display_xy_scale']
            obj.location.z = plan['beds']['soil_top_m']-.2*obj.scale.z
    for name,rim in [(SOIL,False),(EDGING,True)]:
        obj = bpy.data.objects[name]; old_mesh = obj.data
        mesh = bpy.data.meshes.new(name+' / exposed soil revision')
        vertices,faces = bed_geometry(plan,rim); mesh.from_pydata(vertices,[],faces); mesh.update()
        for material in old_mesh.materials: mesh.materials.append(material)
        obj.data = mesh; obj['otw_geometry_status'] = 'Original raised planter candidate fitted to model; not surveyed street furniture'
        if old_mesh.users == 0: bpy.data.meshes.remove(old_mesh)
    collection['otw_planter_revision'] = 'Visible soil above inherited sidewalk; 166 horizontal scale 0.95'
    bpy.data.libraries.write(str(output),{collection},fake_user=False,compress=True)
    require(digest(source) == original_sha,'Original production delta changed')
    return {'ok':True,'source_delta_sha256':original_sha,'delta_sha256':digest(output),
            'delta_bytes':output.stat().st_size,'scene_saved':False,
            'beds':plan['beds'],'tree_166_display_xy_scale':.95}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--job',required=True)
    parser.add_argument('--phase',required=True); parser.add_argument('--report',required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:]); job = read(args.job)
    result = {'ok':False}
    try:
        require(bpy.app.version_string == job['settings']['blender_version'], 'Blender version differs')
        require(not bpy.context.preferences.filepaths.use_scripts_auto_execute, 'Automatic scripts must be disabled')
        if args.phase == 'append': result = append_delta(job)
        elif args.phase == 'inspect-astra': result = inspect_astra(job)
        elif args.phase == 'revise-delta': result = revise_delta(job)
        else: raise ValueError('Unsupported integration phase')
    except Exception as exc:
        result['error'] = str(exc); raise
    finally:
        Path(args.report).write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


if __name__ == '__main__':
    main()
