"""Replay tower paint bands with local materials, retaining city geometry.

Only a pinned local city is supported. All saves go to a new output directory.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tokyo_tower_paint_bands as paint

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'assets/tokyo-tower/paint-bands-city-v1.json'


def plain(value):
    if hasattr(value, 'to_dict'):
        return plain(value.to_dict())
    if hasattr(value, 'to_list'):
        return plain(value.to_list())
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    # mathutils vectors use the sequence protocol without exposing __iter__.
    try:
        return [plain(v) for v in value]
    except TypeError as error:
        raise TypeError('Unsupported snapshot value: ' + type(value).__name__) from error


def pointers(value):
    def is_id(prop):
        # Do not access non-ID PropertyGroup getters: e.g. obj.cycles creates
        # an empty custom-property group merely when read.
        base = prop.fixed_type
        while base:
            if base.identifier == 'ID':
                return True
            base = base.base
        return False
    return {p.identifier: getattr(value, p.identifier).name if getattr(value, p.identifier) else None
            for p in value.bl_rna.properties if p.type == 'POINTER' and is_id(p)}


def animation(obj):
    a = obj.animation_data
    if not a:
        return None
    return {'rna': paint.rna_values(a), 'pointers': pointers(a),
            'nla': [[t.name, [paint.rna_values(s) | pointers(s) for s in t.strips]] for t in a.nla_tracks],
            'drivers': [[c.data_path, c.array_index, c.driver.type, c.driver.expression] for c in a.drivers]}


def snapshot():
    """Raw scene invariants; packed images are hashed without decoding 383 textures."""
    import bpy
    mesh_cache, objects = {}, {}
    for ob in bpy.context.scene.objects:
        item = {'type': ob.type, 'properties': plain(dict(ob.items())), 'rna': paint.rna_values(ob),
                'pointers': {k: v for k, v in pointers(ob).items() if k != 'data'},
                'matrix': [list(r) for r in ob.matrix_world], 'hide_get': ob.hide_get(),
                'collections': sorted(c.name for c in ob.users_collection), 'animation': animation(ob),
                'modifiers': [[m.type, paint.rna_values(m), pointers(m)] for m in ob.modifiers],
                'constraints': [[c.type, paint.rna_values(c), pointers(c)] for c in ob.constraints]}
        if ob.type == 'MESH':
            key = ob.data.as_pointer()
            if key not in mesh_cache:
                mesh_cache[key] = paint.mesh_state(ob.data)
            item['mesh'] = mesh_cache[key]
            item['materials'] = [m.name if m else None for m in ob.data.materials]
        elif ob.data:
            item['data'] = [paint.rna_values(ob.data), pointers(ob.data)]
        objects[ob.name] = item
    s = bpy.context.scene
    value = {'objects': objects,
             'materials': {m.name: [paint.rna_values(m), paint.tree_record(m.node_tree) if m.use_nodes else None]
                           for m in bpy.data.materials},
             'images': {im.name: {'source': im.source, 'filepath': im.filepath,
                                  'packed_sha256': hashlib.sha256(im.packed_file.data).hexdigest() if im.packed_file else None,
                                  'colorspace': im.colorspace_settings.name} for im in bpy.data.images},
             'worlds': {w.name: [paint.rna_values(w), paint.tree_record(w.node_tree) if w.use_nodes else None] for w in bpy.data.worlds},
             'scene': {'frame': s.frame_current, 'camera': s.camera.name if s.camera else None,
                       'world': s.world.name if s.world else None, 'render': paint.rna_values(s.render),
                       'cycles': paint.rna_values(s.cycles), 'view': paint.rna_values(s.view_settings),
                       'markers': [[m.name, m.frame, m.camera.name if m.camera else None] for m in s.timeline_markers]},
             'collections': {c.name: [sorted(o.name for o in c.objects), sorted(x.name for x in c.children),
                                       c.hide_render, c.hide_viewport, plain(dict(c.items()))] for c in bpy.data.collections},
             'actions': {a.name: [[f.data_path, f.array_index,
                                  [[list(k.co), list(k.handle_left), list(k.handle_right), k.interpolation] for k in f.keyframe_points]]
                                 for f in a.fcurves] for a in bpy.data.actions}}
    return json.loads(json.dumps(plain(value)))


def require_unchanged(before, after, lock):
    """Allow only two material assignments, their new shaders and identity tags."""
    names = {t['object']: t for t in lock['targets']}
    if set(before['objects']) != set(after['objects']):
        raise ValueError('City object membership changed')
    for key in before:
        if key not in ('objects', 'scene', 'materials') and before[key] != after[key]:
            raise ValueError('City component changed: ' + key)
    added = {t['paint_material'] for t in lock['targets']}
    if set(after['materials']) != set(before['materials']) | added:
        raise ValueError('Unexpected material membership')
    if any(after['materials'][k] != v for k, v in before['materials'].items()):
        raise ValueError('Original city material changed')
    # Blender save only updates the output filepath, which is not scene.render.filepath.
    if before['scene'] != after['scene']:
        raise ValueError('City camera, render settings, timeline or world changed')
    count = 0
    for name, old in before['objects'].items():
        new = after['objects'][name]
        if name not in names:
            if old != new:
                raise ValueError('Out-of-scope object changed: ' + name)
            count += 1
            continue
        target = names[name]
        expected = copy.deepcopy(old)
        expected['properties'] = old['properties'] | {'otw_part_id': target['part_id'], 'source_object': name}
        expected['materials'] = [target['paint_material'], old['materials'][0]]
        if 'pointers' in expected:
            expected['pointers']['active_material'] = target['paint_material']
        if expected != new:
            raise ValueError('Target geometry, transform, modifier or other property changed: ' + name)
    return count


def check_targets(lock):
    import bpy
    objects = []
    for t in lock['targets']:
        ob = bpy.context.scene.objects.get(t['object'])
        if ob is None or ob.type != 'MESH' or ob.get('otw_feature_id') != lock['feature_id']:
            raise ValueError('Target alias/feature mismatch')
        if ob.get('otw_part_id') or ob.get('source_object'):
            raise ValueError('Already identified/modified city target')
        if ob.parent or ob.constraints or ob.animation_data or ob.data.users != 1:
            raise ValueError('Unsupported target dependency')
        if [list(r) for r in ob.matrix_world] != [[float(i == j) for j in range(4)] for i in range(4)]:
            raise ValueError('Target placement is not identity')
        if len(ob.data.vertices) != t['raw_vertices'] or len(ob.data.polygons) != t['raw_faces']:
            raise ValueError('Raw target topology differs')
        if len(ob.modifiers) != 1 or ob.modifiers[0].type != 'BEVEL' or not ob.modifiers[0].show_viewport or ob.modifiers[0].show_render:
            raise ValueError('Expected viewport-on/render-off bevel')
        if ob.data.uv_layers or ob.data.has_custom_normals or any(f.use_smooth for f in ob.data.polygons):
            raise ValueError('Unsupported raw target shading/UV')
        objects.append(ob)
    return objects


def white_mask(z, original_color, plan):
    """Mirror the shader's six comparisons; lower white stairs stay white."""
    return max(sum(z > h for h in paint.boundaries(plan)) % 2,
               int(original_color == 1 and z < plan['legacy_band_bottom_m']))


def paint_material(palette, original_color, target, plan):
    import bpy
    # These original paint shaders differ only in base color and roughness.
    def neutral_tree(material):
        record = paint.tree_record(material.node_tree)
        for node in record[0]:
            if node[1] == 'ShaderNodeBsdfPrincipled':
                for name, rna in node[3]:
                    if name in ('Base Color', 'Roughness'):
                        rna['default_value'] = None
        return record
    if neutral_tree(palette[0]) != neutral_tree(palette[1]):
        raise ValueError('Paint shaders differ in unsupported channels')
    if bpy.data.materials.get(target['paint_material']):
        raise ValueError('Paint material already exists')
    source_bsdfs = [m.node_tree.nodes.get('Principled BSDF') for m in palette]
    if any(n.inputs[k].is_linked for n in source_bsdfs for k in ('Base Color', 'Roughness')):
        raise ValueError('Expected constant original palette inputs')
    colors = [tuple(n.inputs['Base Color'].default_value) for n in source_bsdfs]
    roughness = [n.inputs['Roughness'].default_value for n in source_bsdfs]
    result = palette[original_color].copy()
    result.name = target['paint_material']
    nodes, links = result.node_tree.nodes, result.node_tree.links
    def node(kind, name):
        n = nodes.new(kind); n.name = name; n.label = name
        return n
    def math_node(operation, name, a, b):
        n = node('ShaderNodeMath', name); n.operation = operation
        for i, value in enumerate((a, b)):
            if isinstance(value, (int, float)):
                n.inputs[i].default_value = value
            else:
                links.new(value, n.inputs[i])
        return n.outputs[0]
    coordinates = node('ShaderNodeTexCoord', 'OTW object coordinates')
    xyz = node('ShaderNodeSeparateXYZ', 'OTW local height')
    links.new(coordinates.outputs['Object'], xyz.inputs[0])
    z = xyz.outputs['Z']
    crossings = [math_node('GREATER_THAN', f'OTW boundary {i+1}', z, h)
                 for i, h in enumerate(paint.boundaries(plan))]
    total = crossings[0]
    for i, crossing in enumerate(crossings[1:]):
        total = math_node('ADD', f'OTW band sum {i+1}', total, crossing)
    mask = math_node('MODULO', 'OTW white band parity', total, 2.)
    if original_color == 1:
        lower = math_node('LESS_THAN', 'OTW keep lower white stairs', z, plan['legacy_band_bottom_m'])
        mask = math_node('MAXIMUM', 'OTW final white mask', mask, lower)
    color = node('ShaderNodeMixRGB', 'OTW original paint colors')
    color.blend_type = 'MIX'
    color.inputs[1].default_value, color.inputs[2].default_value = colors
    links.new(mask, color.inputs[0])
    rough_delta = math_node('MULTIPLY', 'OTW roughness difference', mask, roughness[1]-roughness[0])
    rough = math_node('ADD', 'OTW original paint roughness', rough_delta, roughness[0])
    bsdf = nodes.get('Principled BSDF')
    links.new(color.outputs[0], bsdf.inputs['Base Color'])
    links.new(rough, bsdf.inputs['Roughness'])
    return result


def evaluated_state(obj):
    import bpy
    graph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(graph), preserve_all_data_layers=True, depsgraph=graph)
    mesh.transform(obj.matrix_world); mesh.update()
    state = paint.mesh_state(mesh)
    bpy.data.meshes.remove(mesh)
    return {k: v for k, v in state.items() if k != 'name'}


def build(city, reference, out, lock):
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(reference), use_scripts=False)
    expected = {t['object']: paint.object_record(bpy.data.objects[t['object'] + ' / licensed']) for t in lock['targets']}
    material_nodes = {t['object']: paint.tree_record(bpy.data.objects[t['object'] + ' / licensed'].data.materials[0].node_tree)
                      for t in lock['targets']}
    bpy.ops.wm.open_mainfile(filepath=str(city), use_scripts=False)
    targets = check_targets(lock)
    matches = {}
    original_evaluated = {}
    for ob in targets:
        state = evaluated_state(ob)
        if state['sha256'] != expected[ob.name]['mesh']['sha256'] or paint.tree_record(ob.data.materials[0].node_tree) != material_nodes[ob.name]:
            raise ValueError('City evaluated geometry/material differs from fixed-ID reference')
        matches[ob.name] = {'evaluated_mesh_match': True, 'material_match': True, 'placement_identity': True}
        original_evaluated[ob.name] = state
    before = snapshot()
    paint.write(out / 'city-before.json', before)
    palette = [o.data.materials[0] for o in targets]
    plan = paint.load(paint.PLAN)
    for color, (ob, target) in enumerate(zip(targets, lock['targets'])):
        material = paint_material(palette, color, target, plan)
        ob.data.materials[0] = material
        ob.data.materials.append(palette[color])
        ob['otw_part_id'] = target['part_id']; ob['source_object'] = ob.name
    bpy.context.view_layer.update()
    if any(evaluated_state(ob) != original_evaluated[ob.name] for ob in targets):
        raise ValueError('Evaluated viewport geometry changed')
    after = snapshot()
    require_unchanged(before, after, lock)
    shutil.copyfile(city, out / 'before.blend')
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'after.blend'), compress=True, relative_remap=False)
    paint.write(out / 'build.json', {'ok': True, 'matches': matches, 'original_evaluated': original_evaluated,
                                    'paint_materials': {t['paint_material']: after['materials'][t['paint_material']] for t in lock['targets']},
                                    'code_sha256': paint.sha(Path(__file__)), 'lock_sha256': paint.sha(LOCK),
                                    'city_sha256': paint.sha(city), 'candidate_sha256': paint.sha(out / 'after.blend')})


def validate(city, out, lock):
    import bpy
    before = paint.load(out / 'city-before.json')
    bpy.ops.wm.open_mainfile(filepath=str(city), use_scripts=False)
    if before != snapshot():
        raise ValueError('Baseline snapshot differs')
    bpy.ops.wm.open_mainfile(filepath=str(out / 'after.blend'), use_scripts=False)
    after = snapshot()
    unchanged = require_unchanged(before, after, lock)
    if paint.sha(out / 'before.blend') != lock['city_sha256']:
        raise ValueError('Before copy differs')
    build_record = paint.load(out / 'build.json')
    for t in lock['targets']:
        obj = bpy.data.objects[t['object']]
        if evaluated_state(obj) != build_record['original_evaluated'][obj.name]:
            raise ValueError('Saved viewport geometry changed')
        if after['materials'][t['paint_material']] != build_record['paint_materials'][t['paint_material']]:
            raise ValueError('Saved paint shader changed')
        # The saved render geometry must remain raw: the original bevel stays off.
        if obj.modifiers[0].show_render or not obj.modifiers[0].show_viewport:
            raise ValueError('Bevel display mode changed')
    paint.write(out / 'validation.json', {'ok': True, 'saved_reopened': True, 'city_objects': len(after['objects']),
        'unchanged_objects': unchanged, 'unchanged_images': len(after['images']),
        'unchanged_packed_images': sum(v['packed_sha256'] is not None for v in after['images'].values()),
        'original_materials_world_cameras_lights_collections_actions_preserved': True,
        'target_modifiers_preserved': True, 'target_ids_bound': [t['part_id'] for t in lock['targets']],
        'all_raw_meshes_unchanged': True, 'target_evaluated_meshes_unchanged': True,
        'new_materials': [t['paint_material'] for t in lock['targets']], 'candidate_sha256': paint.sha(out / 'after.blend'),
        'limits': ['Not a general audit of every Blender RNA dependency or animation driver variable.',
                   'Band elevations are inherited model estimates; parallel tree candidate is not included.']})


CITY_VIEWS = [('city-full', (0, 0, 165), (360, -470, 105), 55),
              ('city-band-205', (0, 0, 205.142857143), (-60, -80, 12), 80)]


def render(out, label, selected_view=None):
    import bpy
    from mathutils import Vector
    bpy.ops.wm.open_mainfile(filepath=str(out / (label + '.blend')), use_scripts=False)
    scene = bpy.context.scene
    scene.timeline_markers.clear()
    scene.frame_set(1)
    data = bpy.data.cameras.new('City paint review camera')
    cam = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    data.clip_start, data.clip_end = .1, 4000
    data.sensor_width, data.sensor_fit = 36, 'HORIZONTAL'
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples, scene.cycles.seed = 8, 0
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.use_animated_seed = False
    scene.cycles.use_denoising = True
    scene.render.threads_mode, scene.render.threads = 'FIXED', 2
    scene.render.resolution_x = scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1
    scene.render.use_border = False
    scene.render.use_motion_blur = False
    scene.render.use_compositing = scene.render.use_sequencer = False
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    record_path = out / (label + '-renders.json')
    records = paint.load(record_path) if selected_view and record_path.exists() else {}
    for name, target, offset, lens in CITY_VIEWS:
        if selected_view and name != selected_view:
            continue
        point = Vector(target)
        cam.location = point + Vector(offset)
        cam.rotation_euler = (point - cam.location).to_track_quat('-Z', 'Y').to_euler()
        data.lens = lens
        path = out / (label + '-' + name + '.png')
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        if scene.camera != cam:
            raise ValueError('City camera was overridden')
        records[name] = {'image_sha256': paint.sha(path), 'camera': paint.object_record(cam),
                         'lights': {o.name: paint.object_record(o) for o in scene.objects if o.type == 'LIGHT'},
                         'world': paint.tree_record(scene.world.node_tree),
                         'view_transform': paint.rna_values(scene.view_settings),
                         'size': [640, 640], 'engine': 'CYCLES', 'device': 'CPU',
                         'samples': 8, 'seed': 0, 'threads': 2, 'denoising': True,
                         'adaptive_sampling': False, 'scene_objects_before_review_camera': len(scene.objects)-1}
    paint.write(out / (label + '-renders.json'), plain(records))


def main():
    import bpy
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase', choices=['build', 'validate', 'render-before', 'render-after', 'compare'], required=True)
    p.add_argument('--city', type=Path, required=True)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--view', choices=[v[0] for v in CITY_VIEWS])
    a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
    city, reference, out = a.city.resolve(), a.reference.resolve(), a.output.resolve()
    lock = paint.load(LOCK)
    if bpy.app.version != (4, 5, 1) or paint.sha(city) != lock['city_sha256'] or city.stat().st_size != lock['city_bytes']:
        raise ValueError('Wrong city or Blender version')
    if paint.sha(reference) != lock['reference_sha256']:
        raise ValueError('Wrong fixed-ID reference')
    if out in (city.parent, reference.parent):
        raise ValueError('Output must be separate from inputs')
    if a.phase == 'build':
        if out.exists():
            raise ValueError('Use a new output directory')
        out.mkdir(parents=True)
        build(city, reference, out, lock)
    elif a.phase == 'validate':
        validate(city, out, lock)
    elif a.phase.startswith('render-'):
        render(out, a.phase.removeprefix('render-'), a.view)
    else:
        paint.VIEWS = CITY_VIEWS
        paint.compare(out)
        review = out / 'review.html'
        content = review.read_text(encoding='utf-8').replace('77部品を保持。ローカルレビュー用の独立モデルであり、共通cityへは未適用。',
            'PR47＋PR49のcityコピーへ2部品だけを統合したローカル候補。既存ベベルのレンダーOFFを保持。共有city・通常登録へは未適用。')
        content = content.replace('モデル原作 ark4ez / OurJapan, CC BY 4.0。',
            '東京タワー対象部品の原作 ark4ez / OurJapan（CC BY 4.0）。街全体の再配布許諾を示すものではありません。')
        content = content.replace('東京タワー：上部塗装帯の面分割', '東京タワー：塗装帯のcity統合（形状保持）')
        content = content.replace('既存推定境界で面を分割し塗り分け。', '専用材質で既存推定境界に沿って塗り分け。')
        review.write_text(content, encoding='utf-8')
    if paint.sha(city) != lock['city_sha256'] or paint.sha(reference) != lock['reference_sha256']:
        raise ValueError('Input changed')


if __name__ == '__main__':
    main()
