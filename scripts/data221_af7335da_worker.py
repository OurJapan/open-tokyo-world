"""Headless model production and independent reopen for the reserved feature."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'starter/plateau')]
import blender_worker as review
import data221_af7335da_mesh as repair
import tile


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf8')


def source_triangles(inputs):
    tile.parent(tile.verify('tileset.json', (inputs/'tileset.json').read_bytes()))
    doc, buf, ids = tile.parse(tile.verify('data221.b3dm', (inputs/'data221.b3dm').read_bytes()))
    if ids[repair.BATCH] != repair.FEATURE:
        raise ValueError('Reserved batch identity mismatch')
    primitives, decoder = tile.decode(doc, buf)
    triangles = []
    for a, ix, _ in primitives:
        xyz = tile.enu(a['POSITION'], doc['extensions']['CESIUM_RTC']['center'])
        triangles.extend(xyz[ix[a['_BATCHID'][ix[:,0]] == repair.BATCH]].tolist())
    t = np.asarray(triangles)
    t[:,:,2] += .32-t[:,:,2].min()
    return t.tolist(), decoder


def records(obj):
    mesh = obj.data
    batch = mesh.attributes.get('_BATCHID')
    if batch is None or batch.domain != 'POINT' or batch.data_type != 'INT':
        raise ValueError('Missing retained per-vertex batch IDs')
    result = []
    for face in mesh.polygons:
        ids = {batch.data[i].value for i in face.vertices}
        if len(face.vertices) != 3 or len(ids) != 1:
            raise ValueError('Unexpected triangle/batch layout')
        result.append({'points': [list(mesh.vertices[i].co) for i in face.vertices],
                       'batch': ids.pop(), 'material': face.material_index,
                       'smooth': face.use_smooth,
                       'uv': {uv.name: [list(uv.data[i].uv) for i in face.loop_indices]
                              for uv in mesh.uv_layers}})
    return result


def record_hash(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def subset_mesh(name, rows, materials, weld):
    triangles = [r['points'] for r in rows]
    if weld:
        vertices, faces = repair.weld_exact(triangles)
    else:
        vertices = [p for t in triangles for p in t]
        faces = [(3*i,3*i+1,3*i+2) for i in range(len(rows))]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    for mat in materials:
        mesh.materials.append(mat)
    batch = mesh.attributes.new('_BATCHID', 'INT', 'POINT')
    for face, row in zip(mesh.polygons, rows):
        face.material_index = row['material']
        face.use_smooth = row['smooth']
        for i in face.vertices:
            batch.data[i].value = row['batch']
    for uv_name in rows[0]['uv']:
        uv = mesh.uv_layers.new(name=uv_name)
        for face, row in zip(mesh.polygons, rows):
            for loop, coord in zip(face.loop_indices, row['uv'][uv_name]):
                uv.data[loop].uv = coord
    mesh.update()
    return mesh


def stats(obj):
    return repair.surface_stats([tuple(v.co) for v in obj.data.vertices],
                                [tuple(f.vertices) for f in obj.data.polygons])


def snapshot():
    features = json.loads((ROOT/'areas/tokyo-tower/mori-plaza-connection-accepted-features.json').read_text(encoding='utf8'))
    state = review.validate({'features': features})
    if not state['ok']:
        raise ValueError('City state invalid: '+str(state['errors']))
    # Keep inherited camera/lighting datablock settings as well as transforms.
    state['camera_data'] = {c.name: [c.type,c.lens,c.clip_start,c.clip_end,c.shift_x,c.shift_y]
                            for c in bpy.data.cameras}
    state['light_data'] = {l.name: [l.type,l.energy,list(l.color)] for l in bpy.data.lights}
    return state


def build(job, out):
    bpy.ops.wm.open_mainfile(filepath=job['input'], use_scripts=False)
    if bpy.data.objects.get(repair.FEATURE):
        raise ValueError('Feature already exists; refusing duplicate addition')
    obj = bpy.data.objects.get(repair.AGGREGATE)
    if obj is None or obj.data.users != 1 or obj.modifiers or obj.parent or obj.constraints or obj.animation_data:
        raise ValueError('Unexpected aggregate dependencies')
    if obj.data.has_custom_normals or any(f.use_smooth for f in obj.data.polygons):
        raise ValueError('Only the pinned flat-shaded source is supported')
    if any(obj.matrix_world[i][j] != float(i == j) for i in range(4) for j in range(4)):
        raise ValueError('Unexpected aggregate transform')
    allowed = {'_BATCHID', 'position','material_index','sharp_face'} | {uv.name for uv in obj.data.uv_layers}
    if any(a.name not in allowed and not a.name.startswith('.') for a in obj.data.attributes):
        raise ValueError('Unexpected mesh attributes; do not silently discard')
    rows = records(obj)
    selected = [r for r in rows if r['batch'] == repair.BATCH]
    remainder = [r for r in rows if r['batch'] != repair.BATCH]
    source, decoder = source_triangles(Path(job['inputs']))
    error = repair.verify_source([r['points'] for r in selected], source)
    before = snapshot()
    write(out/'city-before.json', before)
    bpy.data.libraries.write(str(out/'before-neighborhood.blend'), {obj}, fake_user=True, compress=True)
    mesh = subset_mesh(repair.FEATURE, selected, list(obj.data.materials), True)
    target = bpy.data.objects.new(repair.FEATURE, mesh)
    for collection in obj.users_collection:
        collection.objects.link(target)
    for key, value in obj.items():
        target[key] = value
    target['gml_id'] = repair.FEATURE
    target['batch_id'] = repair.BATCH
    target['source_sha256'] = tile.FILES['data221.b3dm'][2]
    target['coordinate_mode'] = 'legacy-compatible-per-feature-ground-0.32'
    target['topology_repair'] = 'exact-position weld only; no face, UV, material or placement change'
    target.hide_render = obj.hide_render
    target.hide_viewport = obj.hide_viewport
    target_stats = stats(target)
    repair.require_closed(target_stats)
    if target_stats['vertices'] != 235 or target_stats['faces'] != repair.SOURCE_TRIANGLES:
        raise ValueError('Unexpected reserved topology')
    obj.data = subset_mesh(repair.AGGREGATE+' / retained features', remainder, list(obj.data.materials), False)
    if records(target) != selected or records(obj) != remainder:
        raise ValueError('Expanded face/UV/material/batch data changed')
    # Existing shaders use world Position/Normal and UV, so these data remain invariant.
    bpy.context.preferences.filepaths.save_version = 0
    bpy.data.libraries.write(str(out/'target.blend'), {target}, fake_user=True, compress=True)
    bpy.data.libraries.write(str(out/'after-neighborhood.blend'), {obj,target}, fake_user=True, compress=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'after.blend'), compress=True)
    write(out/'production.json', {'ok':True, 'feature':repair.FEATURE, 'source_max_error_m':error,
          'decoder_sha256':decoder, 'selected_records_sha256':record_hash(selected),
          'retained_records_sha256':record_hash(remainder), 'retained_faces':len(remainder),
          'before':repair.surface_stats([p for r in selected for p in r['points']],
                    [(3*i,3*i+1,3*i+2) for i in range(len(selected))]), 'after':target_stats})


def validate(job, out):
    bpy.ops.wm.open_mainfile(filepath=str(out/'after.blend'), use_scripts=False)
    before = json.loads((out/'city-before.json').read_text(encoding='utf8'))
    production = json.loads((out/'production.json').read_text(encoding='utf8'))
    after = snapshot()
    if set(after['objects']) != set(before['objects']) | {repair.FEATURE}:
        raise ValueError('Unexpected object addition/removal')
    unchanged = set(before['objects'])-{repair.AGGREGATE}
    if any(after['objects'][n] != before['objects'][n] for n in unchanged):
        raise ValueError('Unrelated city object changed')
    for key in ['assets','camera_data','light_data']:
        if before[key] != after[key]:
            raise ValueError('Changed city '+key)
    target = bpy.data.objects[repair.FEATURE]
    aggregate = bpy.data.objects[repair.AGGREGATE]
    if target.get('gml_id') != repair.FEATURE or target.get('source_sha256') != tile.FILES['data221.b3dm'][2]:
        raise ValueError('Lost source identity')
    if record_hash(records(target)) != production['selected_records_sha256']:
        raise ValueError('Target faces/UV/material/batch changed after saving')
    if record_hash(records(aggregate)) != production['retained_records_sha256']:
        raise ValueError('Other 22 features changed after saving')
    if any(r['batch'] == repair.BATCH for r in records(aggregate)):
        raise ValueError('Duplicate feature retained in aggregate')
    a, b = dict(before['objects'][repair.AGGREGATE]), dict(after['objects'][repair.AGGREGATE])
    a.pop('mesh'); b.pop('mesh')
    if a != b:
        raise ValueError('Aggregate placement or materials changed')
    source, _ = source_triangles(Path(job['inputs']))
    source_error = repair.verify_source([r['points'] for r in records(target)], source)
    repair.require_closed(stats(target))
    if stats(target) != production['after']:
        raise ValueError('Saved topology mismatch')
    write(out/'validation.json', {'ok':True, 'blender':bpy.app.version_string,
          'unchanged_city_objects':len(unchanged), 'unchanged_other_features':22,
          'unchanged_assets':len(after['assets']), 'same_faces_uv_material_batch':True,
          'same_original_cameras_lights':True, 'duplicate_target_faces':0,
          'source_max_error_m':source_error, 'after':stats(target),
          'counts_before':before['counts'], 'counts_after':after['counts'],
          'limitations':before['limits']})


def render(job, out, phase):
    # A small extraction of exactly the same data221 neighborhood in both states.
    # This avoids rendering a 3,308-object city concurrently with other workers.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    which = phase.removeprefix('render-')
    with bpy.data.libraries.load(str(out/(which+'-neighborhood.blend')), link=False) as (src,dst):
        dst.objects = list(src.objects)
    scene = bpy.context.scene
    for obj in dst.objects:
        scene.collection.objects.link(obj)
    light_data = bpy.data.lights.new('Review sun','SUN'); light_data.energy = 3
    light = bpy.data.objects.new('Review sun',light_data); scene.collection.objects.link(light)
    light.rotation_euler = (.35,-.5,-.5)
    world = bpy.data.worlds.new('Review world'); world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.45,.52,.65,1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .7
    scene.world = world
    camera_data = bpy.data.cameras.new('Review camera'); camera_data.type = 'ORTHO'; camera_data.clip_end = 2000
    camera = bpy.data.objects.new('Review camera',camera_data); scene.collection.objects.link(camera); scene.camera = camera
    scene.render.engine='CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=16
    scene.cycles.seed=0; scene.cycles.use_animated_seed=False; scene.cycles.use_adaptive_sampling=False
    scene.cycles.use_denoising=False; scene.render.threads_mode='FIXED'; scene.render.threads=2
    scene.render.resolution_x=800; scene.render.resolution_y=800; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False
    scene.view_settings.view_transform='Standard'; scene.view_settings.look='None'
    views=[]
    for view in job['views']:
        center=Vector(view['center']); camera.location=center+Vector(view['offset'])
        camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        camera_data.ortho_scale=view['scale']
        scene.render.filepath=str(out/(which+'-'+view['id']+'.png'))
        bpy.ops.render.render(write_still=True)
        image=bpy.data.images.load(scene.render.filepath,check_existing=False)
        pixels=np.array(image.pixels[:],dtype='<f4')
        if list(image.size)!=[800,800] or not np.isfinite(pixels).all() or pixels.std()<.01:
            raise ValueError('Invalid image')
        views.append({'id':view['id'],'sha256':hashlib.sha256(Path(scene.render.filepath).read_bytes()).hexdigest(),
                      'pixels_sha256':hashlib.sha256(pixels.tobytes()).hexdigest()})
        bpy.data.images.remove(image)
    write(out/(phase+'.json'), {'ok':True,'settings':{'engine':'CYCLES','device':'CPU','threads':2,'samples':16,'seed':0,'resolution':[800,800]},'views':views})


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--job',type=Path,required=True)
    parser.add_argument('--phase',choices=['build','validate','render-before','render-after'],required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if bpy.app.version != (4,5,1): raise ValueError('Blender 4.5.1 required')
    job=json.loads(args.job.read_text(encoding='utf8')); out=Path(job['output'])
    if args.phase=='build': build(job,out)
    elif args.phase=='validate': validate(job,out)
    else: render(job,out,args.phase)
