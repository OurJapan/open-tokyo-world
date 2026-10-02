"""Make and reopen one independently editable building in a preserved city."""
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
import data221_0551e688_mesh as repair
import data221_af7335da_worker as core
import tile

write = core.write
records = core.records
record_hash = core.record_hash


def source_triangles(inputs):
    tile.parent(tile.verify('tileset.json', (inputs/'tileset.json').read_bytes()))
    doc, buf, ids = tile.parse(tile.verify('data221.b3dm', (inputs/'data221.b3dm').read_bytes()))
    if ids[repair.BATCH] != repair.FEATURE:
        raise ValueError('Reserved source identity mismatch')
    primitives, decoder = tile.decode(doc, buf)
    triangles = []
    for attributes, indices, _ in primitives:
        xyz = tile.enu(attributes['POSITION'], doc['extensions']['CESIUM_RTC']['center'])
        triangles.extend(xyz[indices[attributes['_BATCHID'][indices[:, 0]] == repair.BATCH]].tolist())
    result = np.asarray(triangles)
    result[:, :, 2] += .32-result[:, :, 2].min()
    return result.tolist(), decoder


def topology(obj):
    return repair.verify_topology([tuple(v.co) for v in obj.data.vertices],
                                  [tuple(f.vertices) for f in obj.data.polygons])


def uv_settings(mesh):
    return {'active_index': mesh.uv_layers.active_index,
            'layers': [(u.name, u.active_render, u.active_clone) for u in mesh.uv_layers]}


def inherit_uv_settings(source, dest):
    dest.uv_layers.active_index = source.uv_layers.active_index
    for src, dst in zip(source.uv_layers, dest.uv_layers):
        dst.active_render, dst.active_clone = src.active_render, src.active_clone


def materials(obj):
    return [core.review.material_fingerprint(s.material) for s in obj.material_slots]


def surface_state(obj):
    return {'records': record_hash(records(obj)), 'materials': materials(obj),
            'transform': [float(v) for row in obj.matrix_world for v in row],
            'uv_settings': json.loads(json.dumps(uv_settings(obj.data))),
            'gml_id': obj.get('gml_id'), 'hide_render': obj.hide_render,
            'hide_viewport': obj.hide_viewport}


def normal_check(obj, rows):
    xyz = np.asarray([r['points'] for r in rows])
    expected = np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0])
    expected /= np.linalg.norm(expected, axis=1)[:, None]
    actual = np.asarray([tuple(f.normal) for f in obj.data.polygons])
    actual /= np.linalg.norm(actual, axis=1)[:, None]
    cosine = np.einsum('ij,ij->i', expected, actual)
    if not np.isfinite(cosine).all() or cosine.min() < .999999:
        raise ValueError('Face normal changed')
    return {'faces': len(rows), 'minimum_cosine': float(cosine.min()),
            'maximum_angle_degrees': float(np.degrees(np.arccos(np.clip(cosine, -1, 1))).max())}


def shader_inputs(obj):
    result = []
    allowed = {'BSDF_PRINCIPLED', 'OUTPUT_MATERIAL', 'NEW_GEOMETRY', 'SEPXYZ',
               'MATH', 'COMBXYZ', 'TEX_BRICK', 'MIX_RGB', 'TEX_IMAGE'}
    for material in obj.data.materials:
        if not material.use_nodes:
            raise ValueError('Unexpected material')
        sources = []
        for node in material.node_tree.nodes:
            if node.type not in allowed:
                raise ValueError('Unreviewed shader node: '+node.type)
            if node.type == 'NEW_GEOMETRY':
                for output in node.outputs:
                    if output.is_linked:
                        if output.name not in {'Position', 'Normal'}:
                            raise ValueError('Object topology dependent shader input')
                        sources.append(output.name)
            if node.type == 'TEX_BRICK' and not node.inputs['Vector'].is_linked:
                raise ValueError('Implicit Generated coordinates would change on split')
            if node.type == 'TEX_IMAGE' and not node.inputs['Vector'].is_linked:
                sources.append('active render UV (implicit Image Texture vector)')
        result.append({'material': material.name, 'coordinate_inputs': sources})
    return result


def build(job, out):
    bpy.ops.wm.open_mainfile(filepath=job['input'], use_scripts=False)
    if repair.FEATURE in bpy.data.objects:
        raise ValueError('Target already exists; refusing duplicate addition')
    obj = bpy.data.objects.get(repair.AGGREGATE)
    previous = bpy.data.objects.get(repair.PREVIOUS_FEATURE)
    if previous is None or previous.get('gml_id') != repair.PREVIOUS_FEATURE:
        raise ValueError('Expected preserved predecessor building')
    if obj is None or obj.data.users != 1 or obj.modifiers or obj.parent or obj.constraints or obj.animation_data:
        raise ValueError('Unexpected aggregate dependencies')
    if obj.data.shape_keys or obj.vertex_groups or obj.data.has_custom_normals or any(f.use_smooth for f in obj.data.polygons):
        raise ValueError('Unsupported mesh deformation or normals')
    if any(s.link != 'DATA' for s in obj.material_slots):
        raise ValueError('Object material overrides are not supported')
    if any(obj.matrix_world[i][j] != float(i == j) for i in range(4) for j in range(4)):
        raise ValueError('Unexpected aggregate transform')
    allowed = {'_BATCHID', 'position', 'material_index', 'sharp_face'} | {u.name for u in obj.data.uv_layers}
    if any(a.name not in allowed and not a.name.startswith('.') for a in obj.data.attributes):
        raise ValueError('Unexpected mesh attribute')
    shader_evidence = shader_inputs(obj)
    rows = records(obj)
    selected = [r for r in rows if r['batch'] == repair.BATCH]
    remainder = [r for r in rows if r['batch'] != repair.BATCH]
    source, decoder = source_triangles(Path(job['inputs']))
    error = repair.verify_source([r['points'] for r in selected], source)
    if len(rows) != 2694 or len({r['batch'] for r in remainder}) != 21:
        raise ValueError('Unexpected prior aggregate state')
    before = core.snapshot()
    write(out/'city-before.json', before)
    write(out/'original-target-records.json', selected)
    bpy.data.libraries.write(str(out/'before-neighborhood.blend'), {obj, previous}, fake_user=True, compress=True)
    original_mesh = obj.data
    mesh = core.subset_mesh(repair.FEATURE, selected, list(original_mesh.materials), True)
    inherit_uv_settings(original_mesh, mesh)
    target = obj.copy()
    target.data = mesh
    target.name = repair.FEATURE
    for collection in obj.users_collection:
        collection.objects.link(target)
    target['gml_id'] = repair.FEATURE
    target['batch_id'] = repair.BATCH
    target['source_sha256'] = tile.FILES['data221.b3dm'][2]
    target['coordinate_mode'] = 'legacy-compatible-per-feature-ground-0.32'
    target['topology_repair'] = 'exact coordinate sharing; source faces/UV/materials/winding retained'
    target_topology = topology(target)
    obj.data = core.subset_mesh(repair.AGGREGATE+' / retained features', remainder, list(original_mesh.materials), False)
    inherit_uv_settings(original_mesh, obj.data)
    if records(target) != selected or records(obj) != remainder:
        raise ValueError('Expanded geometry/UV/material/batch changed')
    if materials(target) != before['objects'][repair.AGGREGATE]['materials']:
        raise ValueError('Target material definitions changed')
    for mesh in (target.data, obj.data):
        if uv_settings(mesh) != uv_settings(original_mesh):
            raise ValueError('Active UV settings changed')
    for other in bpy.context.selected_objects:
        other.select_set(False)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.context.preferences.filepaths.save_version = 0
    bpy.data.libraries.write(str(out/'target.blend'), {target}, fake_user=True, compress=True)
    bpy.data.libraries.write(str(out/'after-neighborhood.blend'), {obj, previous, target}, fake_user=True, compress=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'after.blend'), compress=True)
    write(out/'production.json', {'ok': True, 'feature': repair.FEATURE,
        'source_max_error_m': error, 'edit_coordinate_displacement_m': 0,
        'decoder_sha256': decoder, 'selected_records_sha256': record_hash(selected),
        'retained_records_sha256': record_hash(remainder), 'retained_faces': len(remainder),
        'retained_aggregate_features': len({r['batch'] for r in remainder}),
        'original_uv_settings': uv_settings(original_mesh), 'shader_evidence': shader_evidence,
        'before': repair.surface_stats([p for r in selected for p in r['points']],
            [(3*i,3*i+1,3*i+2) for i in range(len(selected))]),
        'after': target_topology, 'normals': normal_check(target, selected),
        'exported_surfaces': {o.name: surface_state(o) for o in (obj, previous, target)}})


def validate(job, out):
    bpy.ops.wm.open_mainfile(filepath=str(out/'after.blend'), use_scripts=False)
    before = json.loads((out/'city-before.json').read_text(encoding='utf8'))
    production = json.loads((out/'production.json').read_text(encoding='utf8'))
    after = core.snapshot()
    if set(after['objects']) != set(before['objects']) | {repair.FEATURE}:
        raise ValueError('Unexpected object addition/removal')
    unchanged = set(before['objects'])-{repair.AGGREGATE}
    if any(after['objects'][n] != before['objects'][n] for n in unchanged):
        raise ValueError('Unrelated city object changed')
    for key in ['assets', 'camera_data', 'light_data']:
        if before[key] != after[key]:
            raise ValueError('Changed city '+key)
    target, aggregate = bpy.data.objects[repair.FEATURE], bpy.data.objects[repair.AGGREGATE]
    if target.get('gml_id') != repair.FEATURE or target.get('source_sha256') != tile.FILES['data221.b3dm'][2]:
        raise ValueError('Lost source identity')
    rows, rest = records(target), records(aggregate)
    if record_hash(rows) != production['selected_records_sha256'] or record_hash(rest) != production['retained_records_sha256']:
        raise ValueError('Saved face/UV/material/batch data changed')
    if any(r['batch'] == repair.BATCH for r in rest):
        raise ValueError('Target retained in aggregate')
    original_state = dict(before['objects'][repair.AGGREGATE])
    for name in (repair.AGGREGATE, repair.FEATURE):
        saved_state = dict(after['objects'][name])
        expected = dict(original_state)
        saved_state.pop('mesh'); expected.pop('mesh')
        if saved_state != expected:
            raise ValueError('Placement/material/visibility changed: '+name)
        if uv_settings(bpy.data.objects[name].data) != production['original_uv_settings']:
            # JSON deserializes tuples to lists.
            if json.dumps(uv_settings(bpy.data.objects[name].data)) != json.dumps(production['original_uv_settings']):
                raise ValueError('Saved UV settings changed')
    source, _ = source_triangles(Path(job['inputs']))
    error = repair.verify_source([r['points'] for r in rows], source)
    saved_topology = topology(target)
    if saved_topology != production['after']:
        raise ValueError('Saved topology changed')
    if bpy.context.view_layer.objects.active != target or bpy.context.selected_objects != [target]:
        raise ValueError('Saved city active target selection lost')
    write(out/'validation.json', {'ok': True, 'blender': bpy.app.version_string,
        'unchanged_city_objects': len(unchanged), 'previous_feature_unchanged': repair.PREVIOUS_FEATURE,
        'unchanged_other_aggregate_features': len({r['batch'] for r in rest}),
        'unchanged_assets': len(after['assets']), 'same_original_cameras_lights': True,
        'same_faces_uv_material_batch': True, 'same_material_definitions_and_uv_selection': True,
        'source_max_error_m': error, 'after': saved_topology, 'normals': normal_check(target, rows),
        'selected_target': target.name, 'counts_before': before['counts'], 'counts_after': after['counts'],
        'limits': before['limits']+['The general-city manifold/normal limitation above excludes the target-specific checks recorded here.',
                                  'Geometric self-intersections and real-world accuracy not certified.']})


def render(job, out, phase):
    which = phase.removeprefix('render-')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(out/(which+'-neighborhood.blend')), link=False) as (src, dst):
        dst.objects = list(src.objects)
    scene = bpy.context.scene
    for obj in dst.objects:
        scene.collection.objects.link(obj)
    if which == 'before':
        obj = bpy.data.objects[repair.AGGREGATE]
        selected = [r for r in records(obj) if r['batch'] == repair.BATCH]
        target = obj.copy()
        target.data = core.subset_mesh('Review original target', selected, list(obj.data.materials), False)
        inherit_uv_settings(obj.data, target.data)
        target.name = 'Review original target'
        scene.collection.objects.link(target)
    else:
        target = bpy.data.objects[repair.FEATURE]
    neighborhood = [o for o in scene.objects if o != target]
    light_data = bpy.data.lights.new('Review sun', 'SUN'); light_data.energy = 3
    light = bpy.data.objects.new('Review sun', light_data); scene.collection.objects.link(light)
    light.rotation_euler = (.35, -.5, -.5)
    world = bpy.data.worlds.new('Review world'); world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.45, .52, .65, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .7
    scene.world = world
    camera_data = bpy.data.cameras.new('Review camera'); camera_data.type = 'ORTHO'; camera_data.clip_end = 2000
    camera = bpy.data.objects.new('Review camera', camera_data); scene.collection.objects.link(camera); scene.camera = camera
    scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = 16
    scene.cycles.seed = 0; scene.cycles.use_animated_seed = False; scene.cycles.use_adaptive_sampling = False
    scene.cycles.use_denoising = False; scene.render.threads_mode = 'FIXED'; scene.render.threads = 2
    scene.render.resolution_x = 800; scene.render.resolution_y = 800; scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'; scene.render.film_transparent = False
    scene.view_settings.view_transform = 'Standard'; scene.view_settings.look = 'None'
    views = []
    for view in job['views']:
        isolated = view['isolated']
        for obj in neighborhood:
            obj.hide_render = isolated
        target.hide_render = which == 'before' and not isolated
        center = Vector(view['center']); camera.location = center+Vector(view['offset'])
        camera.rotation_euler = (center-camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera_data.ortho_scale = view['scale']
        scene.render.filepath = str(out/(which+'-'+view['id']+'.png'))
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(scene.render.filepath, check_existing=False)
        pixels = np.array(image.pixels[:], dtype='<f4')
        if list(image.size) != [800,800] or not np.isfinite(pixels).all() or pixels.std() < .01:
            raise ValueError('Invalid image')
        views.append({'id': view['id'], 'isolated': isolated,
            'sha256': hashlib.sha256(Path(scene.render.filepath).read_bytes()).hexdigest(),
            'pixels_sha256': hashlib.sha256(pixels.tobytes()).hexdigest()})
        bpy.data.images.remove(image)
    if which == 'after':
        # Small usable edit scene, with the target selected and neighborhood visible.
        for obj in neighborhood: obj.hide_render = False
        for obj in scene.objects: obj.select_set(False)
        target.select_set(True); bpy.context.view_layer.objects.active = target
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    region = area.spaces.active.region_3d
                    region.view_location = Vector((-438,326,11)); region.view_distance = 100
                    region.view_rotation = camera.rotation_euler.to_quaternion()
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(out/'edit-neighborhood.blend'), compress=True)
    write(out/(phase+'.json'), {'ok': True, 'settings': {'engine':'CYCLES','device':'CPU','threads':2,
        'samples':16,'seed':0,'resolution':[800,800]}, 'views': views})


def reopen_edit(job, out):
    bpy.ops.wm.open_mainfile(filepath=str(out/'edit-neighborhood.blend'), use_scripts=False)
    matches = [o for o in bpy.context.scene.objects if o.get('gml_id') == repair.FEATURE]
    if len(matches) != 1 or bpy.context.view_layer.objects.active != matches[0] or bpy.context.selected_objects != matches:
        raise ValueError('Edit scene ID selection lost')
    target = matches[0]
    expected = json.loads((out/'production.json').read_text(encoding='utf8'))
    if topology(target) != expected['after'] or record_hash(records(target)) != expected['selected_records_sha256']:
        raise ValueError('Edit scene geometry changed')
    saved_surfaces = {o.name: surface_state(o) for o in bpy.context.scene.objects if o.type == 'MESH'}
    if saved_surfaces != expected['exported_surfaces']:
        raise ValueError('Edit scene predecessor/aggregate/material/transform differs')
    mesh_count = len(saved_surfaces)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(out/'target.blend'), link=False) as (src, dst):
        if src.objects != [repair.FEATURE]:
            raise ValueError('Target library contains unexpected objects')
        dst.objects = list(src.objects)
    standalone = dst.objects[0]
    if surface_state(standalone) != expected['exported_surfaces'][repair.FEATURE] or topology(standalone) != expected['after']:
        raise ValueError('Target library changed after saving')
    write(out/'edit-reopen.json', {'ok': True, 'selected': standalone.name, 'after': topology(standalone),
        'mesh_objects': mesh_count, 'all_exported_surfaces_preserved': True, 'target_library_reopened': True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--phase', choices=['build','validate','render-before','render-after','reopen-edit'], required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if bpy.app.version != (4,5,1): raise ValueError('Blender 4.5.1 required')
    job = json.loads(args.job.read_text(encoding='utf8')); out = Path(job['output'])
    if args.phase == 'build': build(job, out)
    elif args.phase == 'validate': validate(job, out)
    elif args.phase == 'reopen-edit': reopen_edit(job, out)
    else: render(job, out, args.phase)
