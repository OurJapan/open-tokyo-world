# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Pinned PR60 increment: append one south stair/landing handrail connector.

Run with Blender 4.5.1 --background --factory-startup --disable-autoexec
--python-exit-code 1 --python scripts/tower_south_handrail.py --
--phase build|validate|render-before|render-after --input PR60_AFTER --output DIR.
The full city is private input; only one existing metal mesh is edited.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review import digest, require, compare_reports, validate_cameras
from tower_structure_v1 import MeshBuilder
from tower_foottown_geometry_v2 import METAL, south_handrail_junction

INPUT_SHA256 = 'e4ecbdf02fb6217e67c111f284a2d905bb31f3521fbd380818e687ba5d85da97'
TARGET = 'OTW Tokyo Tower structure / foottown-metal'
MESH_SHA256 = '1ca6dd5944c2ba44958af009e32855fa775afd13a864978bd66ac3c54d21ce2e'
ROOT = Path(__file__).resolve().parents[1]


def connector():
    builder = MeshBuilder()
    south_handrail_junction(builder)
    return builder.groups[METAL]


def points_and_faces(mesh):
    return ([tuple(v.co) for v in mesh.vertices], [tuple(p.vertices) for p in mesh.polygons])


def metadata():
    import bpy
    from validate_tower_foottown import json_value, protected_metadata
    import tower_foottown_v2 as detail
    old_scope=(detail.CHANGED,detail.ADDED,detail.COLLECTION)
    try:
        detail.CHANGED={TARGET}; detail.ADDED=set(); detail.COLLECTION='no excluded collection'
        protected=protected_metadata()
    finally:
        detail.CHANGED,detail.ADDED,detail.COLLECTION=old_scope
    return {
        'protected_mesh_flags_and_metadata': protected,
        'objects': {o.name: {'props': {k: json_value(o[k]) for k in o.keys()},
            'collections': sorted(c.name for c in o.users_collection),
            'hide_viewport': o.hide_viewport, 'hide_local': o.hide_get(),
            'parent': o.parent.name if o.parent else None,
            'modifiers': [(m.name,m.type) for m in o.modifiers],
            'constraints': [(c.name,c.type) for c in o.constraints]}
            for o in bpy.context.scene.objects},
        'collections': {c.name: {'props': {k: json_value(c[k]) for k in c.keys()},
            'children': sorted(x.name for x in c.children),
            'hide_render': c.hide_render, 'hide_viewport': c.hide_viewport}
            for c in bpy.data.collections},
        'counts': {k: len(getattr(bpy.data,k)) for k in
            ('objects','meshes','materials','images','collections','actions')},
    }


def open_scene(path):
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    require(Path(bpy.data.filepath).resolve() == path.resolve(), 'Wrong open scene')
    bpy.context.scene.frame_set(1)


def mesh_flags(mesh):
    return {'smooth': [p.use_smooth for p in mesh.polygons],
            'face_hidden': [p.hide for p in mesh.polygons],
            'vertex_hidden': [v.hide for v in mesh.vertices],
            'edge_hidden': [e.hide for e in mesh.edges],
            'material_indices': [p.material_index for p in mesh.polygons]}


def build(source, output):
    import bpy
    from blender_worker import mesh_fingerprint
    open_scene(source)
    obj=bpy.data.objects[TARGET]; mesh=obj.data
    require(mesh_fingerprint(mesh)==MESH_SHA256, 'Pinned metal mesh differs')
    require(mesh.users==1 and not obj.modifiers and not obj.animation_data and
            not mesh.uv_layers and not mesh.shape_keys, 'Unsupported target data')
    require(all(not x for key, values in mesh_flags(mesh).items() for x in values),
            'Target mesh requires attribute-preserving edit')
    old_vertices, old_faces=points_and_faces(mesh); extra=connector(); n=len(old_vertices)
    # Edit the existing datablock: retain its identity, single material and flags.
    mesh.clear_geometry()
    mesh.from_pydata(old_vertices+extra['vertices'],[],
                     old_faces+[tuple(n+i for i in f) for f in extra['faces']])
    mesh.update()
    # PR60 retains two unassigned material datablocks. Blender would discard
    # them on the next save; keep their original shaders with persistence flags.
    retained=[m.name for m in bpy.data.materials if m.users==0]
    for name in retained:
        bpy.data.materials[name].use_fake_user=True
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'after.blend'), check_existing=False)
    return {'ok': True, 'changed_object': TARGET, 'added_vertices': 16, 'added_polygons': 10,
            'unused_materials_retained_with_fake_users':retained}


def validate(source, output):
    import bpy
    from blender_worker import mesh_fingerprint, material_fingerprint, validate as scene_validate
    from validate_tower_foottown import check_geometry
    import tower_foottown_v2 as detail
    import numpy as np
    features=json.loads((ROOT/'areas/tokyo-tower/foottown-v2-features.json').read_text())
    open_scene(source)
    before=scene_validate({'features':features}); before_meta=metadata()
    shaders={m.name:material_fingerprint(m) for m in bpy.data.materials}
    original_fake_users={m.name:m.use_fake_user for m in bpy.data.materials}
    unused={m.name for m in bpy.data.materials if m.users==0}
    original=bpy.data.objects[TARGET].data
    require(mesh_fingerprint(original)==MESH_SHA256, 'Pinned metal mesh differs')
    old_vertices, old_faces=points_and_faces(original); old_flags=mesh_flags(original)
    open_scene(output/'after.blend')
    after=scene_validate({'features':features})
    changed=compare_reports(before,after,{TARGET},set())
    require(metadata()==before_meta, 'Object identity, metadata, visibility or datablock counts changed')
    require(shaders=={m.name:material_fingerprint(m) for m in bpy.data.materials},
            'An original material datablock or shader changed')
    require(all(m.use_fake_user==(True if m.name in unused else original_fake_users[m.name])
                for m in bpy.data.materials), 'Unexpected material persistence flag change')
    mesh=bpy.data.objects[TARGET].data; vertices,faces=points_and_faces(mesh); extra=connector()
    require(vertices[:len(old_vertices)]==old_vertices and faces[:len(old_faces)]==old_faces,
            'Existing target geometry changed')
    expected=np.asarray(extra['vertices'],dtype=np.float32).astype(float).tolist()
    require([list(v) for v in vertices[len(old_vertices):]]==expected and
            faces[len(old_faces):]==[tuple(len(old_vertices)+i for i in f) for f in extra['faces']],
            'Saved addition differs from the one approved connector')
    flags=mesh_flags(mesh)
    require(all(flags[k][:len(v)]==v for k,v in old_flags.items()), 'Existing target flags changed')
    meshes={group:points_and_faces(bpy.data.objects[detail.object_name(group)].data) for group in detail.GROUPS}
    stairs=points_and_faces(bpy.data.objects[detail.OLD_PREFIX+'stairs-treads'].data)
    geometry=check_geometry(meshes,stairs)
    return {'ok':True, 'changed_objects':changed, 'protected_objects':len(before['objects'])-1,
            'objects':len(after['objects']), 'added_vertices':len(vertices)-len(old_vertices),
            'added_polygons':len(faces)-len(old_faces), 'old_target_geometry_and_flags_unchanged':True,
            'object_metadata_and_datablock_counts_unchanged':True, 'material_shaders_and_image_assets_unchanged':True,
            'unused_materials_retained_with_fake_users':sorted(unused),
            'geometry':geometry, 'warnings':after['warnings'],
            'gap_model_m':(0.2**2+0.25**2)**.5,
            'limits':after['limits']+['Inherited frame and dimensions are inferred, not surveyed.',
                'Capped solids intersect at joints; no structural engineering certification.']}


def render(source,output,phase):
    from blender_worker import render as scene_render
    config=json.loads((ROOT/'areas/tokyo-tower/foottown-v2-cameras.json').read_text())
    config['views'].extend(json.loads((ROOT/'areas/tokyo-tower/south-handrail-cameras.json').read_text())['views'])
    validate_cameras(config)
    open_scene(source if phase=='render-before' else output/'after.blend')
    return scene_render({'output':str(output), 'cameras':config, 'settings':
        {'device':'OPTIX','width':640,'height':424,'samples':16,'seed':0}},phase)


def main():
    import bpy
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',required=True,choices=('build','validate','render-before','render-after'))
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    source=args.input.resolve(); output=args.output.resolve(); output.mkdir(parents=True,exist_ok=True)
    report_path=output/(args.phase+'.json')
    require(not report_path.exists(), 'Refusing to overwrite a phase report')
    require(bpy.app.version_string=='4.5.1 LTS' and not bpy.context.preferences.filepaths.use_scripts_auto_execute,
            'Use Blender 4.5.1 LTS with autoexec disabled')
    require(source!=output/'after.blend' and digest(source)==INPUT_SHA256, 'Immutable PR60 input differs')
    if args.phase=='build':
        require(not (output/'after.blend').exists(), 'Refusing to overwrite candidate')
    candidate_hash=digest(output/'after.blend') if args.phase!='build' else None
    if args.phase=='build': result=build(source,output)
    elif args.phase=='validate': result=validate(source,output)
    else: result=render(source,output,args.phase)
    require(digest(source)==INPUT_SHA256, 'Input changed')
    if candidate_hash:
        require(digest(output/'after.blend')==candidate_hash, 'Candidate changed during read-only phase')
    result.update(input_sha256=INPUT_SHA256,candidate_sha256=digest(output/'after.blend'),
        blender_version=bpy.app.version_string,source_and_candidate_protected=True,
        code_sha256={name:digest(ROOT/'scripts'/name) for name in
            ('tower_south_handrail.py','tower_foottown_geometry_v2.py','tower_structure_v1.py',
             'validate_tower_foottown.py','validate_tower_structure.py','blender_worker.py','review.py')})
    report_path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print('OK: '+args.phase)


if __name__=='__main__':
    main()
