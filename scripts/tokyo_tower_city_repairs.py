# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Replay both tower repairs on the pinned PR47/49/51 city, without replacement."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tokyo_tower_paint_city as city
import tokyo_tower_topdeck_junction as deck

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'assets/tokyo-tower/city-repairs-v1.json'
VIEWS = [
    ('city-full', (0, 0, 165), (360, -470, 105), 55, None),
    ('band-205', (0, 0, 205.142857143), (-60, -80, 12), 80, None),
    ('band-230', (0, 0, 230.714285714), (-55, -75, 12), 80, None),
    ('base-trees', (15, 35, 34), (180, -230, 75), 55, None),
    ('topdeck', (0, 0, 248), (30, -40, 3), 50, 23),
    ('sill', (0, -7.95, 246.25), (1, -7, .5), 50, 2.4),
]


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(value):
    return city.hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def snapshot():
    """PR51's static disabled seeds retain stored pose, not derived caches."""
    import bpy
    from tower_approach_plan import source_names
    value = city.snapshot()
    for name in source_names():
        ob = bpy.data.objects[name]
        require(not ob.parent and not ob.constraints and not ob.animation_data and not ob.modifiers,
                'Unsupported disabled seed dependency')
        item = value['objects'][name]
        basis = city.plain(ob.matrix_basis)
        item['matrix'] = basis
        for key in ('matrix_world', 'matrix_local'):
            if key in item['rna']:
                item['rna'][key] = basis
        # The prior compatibility check proves re-enabling restores dimensions.
        # Raw mesh and every stored transform channel are still compared.
        item['rna'].pop('dimensions', None)
    return value


def require_tree_baseline(old, new, reviewed, added, suppressed, collection):
    require(set(new['objects']) == set(old['objects']) | added, 'Tree membership differs')
    require(not set(old['objects']) & added, 'Tree additions already present')
    require(set(new['collections']) == set(old['collections']) | {collection}, 'Tree collections differ')
    for key in old:
        if key not in ('objects', 'collections'):
            require(old[key] == new[key], 'Tree append changed ' + key)
    for name, item in old['objects'].items():
        expected = copy.deepcopy(item)
        if name in suppressed:
            require(not item['rna']['hide_viewport'], 'Seed already suppressed')
            expected['rna']['hide_viewport'] = True
        require(new['objects'][name] == expected, 'Tree append changed ' + name)
    for name, item in old['collections'].items():
        require(new['collections'][name] == item, 'Existing collection changed')
    for name in added:
        require(new['objects'][name] == reviewed['objects'][name], 'PR51 tree changed: ' + name)
    require(new['collections'][collection] == reviewed['collections'][collection], 'PR51 collection changed')


def require_repairs(old, new, lock, junction_names):
    """Geometry is checked separately; keep every other field strictly scoped."""
    normalized = copy.deepcopy(new)
    for name in junction_names:
        item = normalized['objects'][name]
        item['mesh'] = old['objects'][name]['mesh']
        # Only the height-derived dimensions can change with the lower ends.
        item['rna']['dimensions'] = old['objects'][name]['rna']['dimensions']
    return city.require_unchanged(old, normalized, lock) - len(junction_names)


def scope_parts():
    return city.paint.load(ROOT / 'assets/tokyo-tower/provenance.json')['parts']


def references(path):
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    exporter = city.paint.module(ROOT / 'assets/tokyo-tower/export.py', 'tower_export')
    parts = city.paint.validate_scene(city.paint.load(ROOT / 'assets/tokyo-tower/provenance.json'), exporter)
    return {pid: {'mesh': city.paint.mesh_state(ob.data),
                  'coordinates': deck.coordinates(ob.data).tolist() if pid in {'tokyo-tower-part-009', 'tokyo-tower-part-010', 'tokyo-tower-part-011'} else None,
                  'materials': [city.paint.tree_record(m.node_tree) for m in ob.data.materials]}
            for pid, ob in parts.items()}


def evaluated_coordinate_check(current, expected, floor, depth):
    """Bound the diagnosed bevel roundoff; raw coordinates remain exact."""
    import math
    require(len(current) == len(expected) and len(current) > 0, 'Evaluated vertex membership changed')
    limits = (2e-9, 2e-9, 2 ** -16)  # XY observed nanometres; one float32 ULP at z246.
    maximum = [0., 0., 0.]; different = upper = 0
    for actual, wanted in zip(current, expected):
        require(len(actual) == len(wanted) == 3, 'Invalid evaluated coordinate')
        delta = [abs(float(a) - float(b)) for a, b in zip(actual, wanted)]
        require(all(math.isfinite(d) and d <= bound for d, bound in zip(delta, limits)), 'Evaluated displacement exceeds bevel roundoff')
        if wanted[2] > floor + depth:
            require(delta[2] == 0, 'Evaluated upper Z moved')
            upper += any(delta)
        different += any(delta)
        maximum = [max(a, b) for a, b in zip(maximum, delta)]
    return {'max_coordinate_difference_m': maximum, 'different_vertices': different,
            'upper_vertices_with_nanometre_xy_roundoff': upper, 'upper_z_exact': True}


def match_evaluated(ob, reference, floor, depth):
    import bpy
    import numpy as np
    graph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(ob.evaluated_get(graph), preserve_all_data_layers=True, depsgraph=graph)
    try:
        actual_hash = city.paint.mesh_state(mesh)['sha256']
        comparison = evaluated_coordinate_check(deck.coordinates(mesh), reference['coordinates'], floor, depth)
        mesh.vertices.foreach_set('co', np.asarray(reference['coordinates'], dtype=np.float32).ravel())
        mesh.update()
        require(city.paint.mesh_state(mesh)['sha256'] == reference['mesh']['sha256'],
                'Evaluated topology, attributes or shading differs beyond coordinate roundoff')
        return comparison | {'city_sha256': actual_hash, 'isolated_sha256': reference['mesh']['sha256'],
                             'exact_hash_match': actual_hash == reference['mesh']['sha256'],
                             'restored_coordinate_hash_matches': True}
    finally:
        bpy.data.meshes.remove(mesh)


def identify(reference):
    """Bind all 77 canonical IDs without renumbering or tagging unrelated parts."""
    import bpy
    from mathutils import Matrix
    parts = {}
    for part in scope_parts():
        pid, name = part['part_id'], part['object']
        ob = bpy.context.scene.objects.get(name)
        require(ob is not None and ob.type == 'MESH', 'Missing canonical part: ' + pid)
        # Many legacy detail objects have no feature tag; the pinned input,
        # provenance alias and full world-space mesh/material match identify them.
        require(ob.get('otw_feature_id') in (None, 'otw:jp:tokyo:minato:tokyo-tower'), 'Feature mismatch: ' + pid)
        require(ob.get('otw_part_id', pid) == pid, 'Conflicting persistent ID: ' + pid)
        if pid in {'tokyo-tower-part-005', 'tokyo-tower-part-006', 'tokyo-tower-part-009', 'tokyo-tower-part-010', 'tokyo-tower-part-011'}:
            require(ob.matrix_world == Matrix.Identity(4), 'Target placement differs: ' + pid)
        require(city.evaluated_state(ob)['sha256'] == reference[pid]['mesh']['sha256'], 'Part geometry differs: ' + pid)
        require([city.paint.tree_record(m.node_tree) for m in ob.data.materials] == reference[pid]['materials'],
                'Part material differs: ' + pid)
        parts[pid] = ob
    require(len(parts) == 77, 'Expected 77 unique canonical parts')
    return parts


def build(a, pin):
    import bpy
    import tower_approach_integration_blender as trees
    import tower_approach_plan as tp
    out = a.output
    out.mkdir(parents=True, exist_ok=False)
    reference, repaired = references(a.reference), references(a.topdeck)
    print('REFERENCE_IDS_OK 77', flush=True)
    bpy.ops.wm.open_mainfile(filepath=str(a.trees), use_scripts=False)
    reviewed = snapshot()
    bpy.ops.wm.open_mainfile(filepath=str(a.base), use_scripts=False)
    original = snapshot()
    tree_stage = out / 'tree-baseline'
    tree_stage.mkdir()
    tree_plan = tp.check_plan(city.paint.load(ROOT / 'areas/tokyo-tower/approach-trees-v1.json'))
    trees.append_delta({'plan': tree_plan, 'delta': str(a.delta), 'output': str(tree_stage)})
    baseline = snapshot()
    require_tree_baseline(original, baseline, reviewed, tp.added_names(tree_plan), tp.source_names(), tp.COLLECTION)
    print('PR51_BASELINE_OK', flush=True)
    shutil.copyfile(tree_stage / 'after.blend', out / 'before.blend')
    # Reopen the baseline before editing: both comparisons start from saved data.
    bpy.ops.wm.open_mainfile(filepath=str(out / 'before.blend'), use_scripts=False)
    require(snapshot() == baseline, 'Saved tree baseline differs')
    parts = identify(reference)
    print('CITY_PART_MAPPING_OK 77', flush=True)
    before = snapshot()
    lock, junction = city.paint.load(city.LOCK), city.paint.load(deck.PLAN)
    floor = max(v.co.z for v in parts[junction['floor_part_id']].data.vertices)
    require(floor == junction['floor_top_m'], 'Floor height differs')
    before_rays = deck.contact_rays(parts, junction, floor)
    require(all(row['base_ray_hits'] == 0 for row in before_rays.values()), 'Baseline gap differs')
    evaluated = {t['object']: city.evaluated_state(bpy.data.objects[t['object']]) for t in lock['targets']}
    objects = city.check_targets(lock)
    palette = [ob.data.materials[0] for ob in objects]
    for index, (ob, target) in enumerate(zip(objects, lock['targets'])):
        ob.data.materials[0] = city.paint_material(palette, index, target, city.paint.load(city.paint.PLAN))
        ob.data.materials.append(palette[index])
        ob['otw_part_id'] = target['part_id']; ob['source_object'] = ob.name
    bpy.context.view_layer.update()
    city.require_unchanged(before, snapshot(), lock)
    changes, evaluated_matches = {}, {}
    for target in junction['targets']:
        pid = target['part_id']; ob = parts[pid]
        require(not ob.parent and not ob.constraints and not ob.animation_data and not ob.data.shape_keys and ob.data.users == 1,
                'Unsupported junction dependency')
        raw = dict(target, vertices=320, lower_vertices=160)
        indices, delta = deck.lower_end_indices(deck.coordinates(ob.data), floor, raw, junction['lower_end_depth_m'])
        old = ob.data.copy()
        for index in indices:
            ob.data.vertices[index].co.z += delta
        ob.data.update(); bpy.context.view_layer.update()
        changes[pid] = deck.geometry_check(old, ob.data, floor, raw, junction['lower_end_depth_m'])
        bpy.data.meshes.remove(old)
        evaluated_matches[pid] = match_evaluated(ob, repaired[pid], floor, junction['lower_end_depth_m'])
    after = snapshot()
    names = [parts[t['part_id']].name for t in junction['targets']]
    preserved = require_repairs(before, after, lock, names)
    city.paint.write(out / 'before-state.json', before)
    city.paint.write(out / 'expected-state.json', after)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'after.blend'), compress=True, relative_remap=False)
    city.paint.write(out / 'build.json', {'ok': True, 'inputs': pin['inputs'], 'script_sha256': city.paint.sha(__file__),
        'plan_sha256': city.paint.sha(PLAN), 'canonical_parts': {p['part_id']: p['object'] for p in scope_parts()},
        'parts': changes, 'before_rays': before_rays, 'body_evaluated': evaluated,
        'repaired_evaluated': {pid: value['city_sha256'] for pid, value in evaluated_matches.items()},
        'isolated_evaluated_comparison': evaluated_matches,
        'baseline_sha256': city.paint.sha(out / 'before.blend'), 'candidate_sha256': city.paint.sha(out / 'after.blend'),
        'city_objects': len(after['objects']), 'unchanged_objects': preserved,
        'pr51_added_objects': sorted(tp.added_names(tree_plan)), 'tree_baseline_reopened': True})


def validate(a, pin):
    import bpy
    out = a.output; report = city.paint.load(out / 'build.json')
    require(city.paint.sha(out / 'before.blend') == report['baseline_sha256'], 'Before bytes differ')
    require(city.paint.sha(out / 'after.blend') == report['candidate_sha256'], 'After bytes differ')
    before = city.paint.load(out / 'before-state.json')
    bpy.ops.wm.open_mainfile(filepath=str(out / 'before.blend'), use_scripts=False)
    require(snapshot() == before, 'Reopened baseline differs')
    bpy.ops.wm.open_mainfile(filepath=str(out / 'after.blend'), use_scripts=False)
    after = snapshot()
    require(after == city.paint.load(out / 'expected-state.json'), 'Reopened candidate differs')
    parts = {p['part_id']: bpy.data.objects[p['object']] for p in scope_parts()}
    lock, junction = city.paint.load(city.LOCK), city.paint.load(deck.PLAN)
    names = [parts[t['part_id']].name for t in junction['targets']]
    unchanged = require_repairs(before, after, lock, names)
    for t in lock['targets']:
        require(city.evaluated_state(parts[t['part_id']]) == report['body_evaluated'][t['object']], 'Paint geometry changed')
    floor = max(v.co.z for v in parts[junction['floor_part_id']].data.vertices)
    old_names = [before['objects'][n]['mesh']['name'] for n in names]
    with bpy.data.libraries.load(str(out / 'before.blend'), link=False) as (available, loaded):
        loaded.meshes = old_names
    stats = {}
    for target, old in zip(junction['targets'], loaded.meshes):
        pid = target['part_id']; ob = parts[pid]
        stats[pid] = deck.geometry_check(old, ob.data, floor, dict(target, vertices=320, lower_vertices=160), junction['lower_end_depth_m'])
        require(city.evaluated_state(ob)['sha256'] == report['repaired_evaluated'][pid], 'Saved evaluated repair differs')
    for mesh in loaded.meshes:
        bpy.data.meshes.remove(mesh)
    rays = deck.contact_rays(parts, junction, floor)
    require(all(r['base_ray_hits'] == r['members'] for r in rays.values()), 'Open junction remains')
    require(city.paint.sha(out / 'after.blend') == report['candidate_sha256'], 'Validation modified candidate')
    city.paint.write(out / 'validation.json', {'ok': True, 'saved_reopened': True, 'city_objects': len(after['objects']),
        'unchanged_objects': unchanged, 'canonical_part_mappings_preserved': 77,
        'part_ids_bound_in_city': [t['part_id'] for t in lock['targets']],
        'all_other_existing_properties_preserved': True, 'all_modifiers_preserved': True,
        'raw_vertices_changed': sum(row['moved_vertices'] for row in stats.values()),
        'evaluated_junction_matches_isolated_with_bounded_bevel_roundoff': report['isolated_evaluated_comparison'],
        'paint_evaluated_geometry_preserved': True, 'pr51_objects_preserved': len(report['pr51_added_objects']),
        'images_preserved': len(after['images']), 'original_materials_preserved': len(before['materials']),
        'collections_preserved': len(after['collections']), 'actions_preserved': len(after['actions']),
        'world_cameras_lights_scene_preserved': True, 'parts': stats, 'contact_rays': rays,
        'baseline_sha256': report['baseline_sha256'], 'candidate_sha256': report['candidate_sha256'],
        'script_sha256': city.paint.sha(__file__), 'limits': pin['limits']})


def render(a, label):
    import bpy
    from mathutils import Vector
    bpy.ops.wm.open_mainfile(filepath=str(a.output / (label + '.blend')), use_scripts=False)
    s = bpy.context.scene; s.timeline_markers.clear(); s.frame_set(1)
    data = bpy.data.cameras.new('Tower integration review camera')
    cam = bpy.data.objects.new(data.name, data); s.collection.objects.link(cam); s.camera = cam
    data.clip_start, data.clip_end = .1, 4000
    data.sensor_width, data.sensor_fit = 36, 'HORIZONTAL'
    s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.seed = 0
    s.cycles.use_animated_seed = False; s.cycles.use_adaptive_sampling = False; s.cycles.use_denoising = True
    s.render.threads_mode = 'FIXED'; s.render.threads = 2
    s.render.resolution_x = s.render.resolution_y = 640; s.render.resolution_percentage = 100
    s.render.pixel_aspect_x = s.render.pixel_aspect_y = 1
    s.render.use_border = False; s.render.use_motion_blur = False
    s.render.use_compositing = s.render.use_sequencer = False; s.render.film_transparent = False
    s.render.image_settings.file_format = 'PNG'; s.render.image_settings.color_mode = 'RGBA'; s.render.image_settings.color_depth = '8'
    records = city.paint.load(a.output / (label + '-renders.json')) if (a.output / (label + '-renders.json')).exists() else {}
    for name, target, offset, lens, scale in VIEWS:
        if a.view and name != a.view: continue
        point = Vector(target); cam.location = point + Vector(offset)
        cam.rotation_euler = (point - cam.location).to_track_quat('-Z', 'Y').to_euler()
        data.type = 'ORTHO' if scale else 'PERSP'; data.lens = lens
        if scale: data.ortho_scale = scale
        s.cycles.samples = 32 if name == 'sill' else 8
        path = a.output / (label + '-' + name + '.png'); s.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        require(s.camera == cam, 'Review camera overridden')
        records[name] = {'image_sha256': city.paint.sha(path), 'camera': city.paint.object_record(cam),
            'lights': {o.name: city.paint.object_record(o) for o in s.objects if o.type == 'LIGHT'},
            'world': city.paint.tree_record(s.world.node_tree), 'view_transform': city.paint.rna_values(s.view_settings),
            'size': [640, 640], 'engine': 'CYCLES', 'device': 'CPU', 'samples': s.cycles.samples,
            'seed': 0, 'threads': 2, 'denoising': True, 'adaptive_sampling': False}
        city.paint.write(a.output / (label + '-renders.json'), city.plain(records))


def main():
    import bpy
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--phase', choices=['build', 'validate', 'render-before', 'render-after', 'compare'], required=True)
    for label in ('base', 'trees', 'delta', 'reference', 'topdeck', 'output'):
        ap.add_argument('--' + label, type=Path, required=True)
    ap.add_argument('--view', choices=[v[0] for v in VIEWS])
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:]); pin = city.paint.load(PLAN)
    require(bpy.app.version == (4, 5, 1), 'Blender 4.5.1 required')
    require(not bpy.context.preferences.filepaths.use_scripts_auto_execute, 'Disable automatic scripts')
    a.output = a.output.resolve()
    require(a.output.is_relative_to(ROOT / 'data/local'), 'Output must be inside worktree data/local')
    for label, sha in pin['inputs'].items():
        require(city.paint.sha(getattr(a, label)) == sha, 'Wrong pinned input: ' + label)
    if a.phase == 'build': build(a, pin)
    elif a.phase == 'validate': validate(a, pin)
    elif a.phase == 'compare':
        deck.VIEWS = VIEWS; deck.compare(a.output)
        review = a.output / 'review.html'
        review.write_text(review.read_text(encoding='utf-8').replace('Tokyo Tower top-deck window bases', 'Tokyo Tower city repairs')
            .replace('Tokyo Tower: top-deck window bases', 'Tokyo Tower: paint and top-deck city integration')
            .replace('Original model: ark4ez / OurJapan, CC BY 4.0.', 'Tower original: ark4ez / OurJapan, CC BY 4.0. City context retains existing third-party conditions; no city redistribution license is granted.'), encoding='utf-8')
    else: render(a, a.phase.removeprefix('render-'))
    for label, sha in pin['inputs'].items():
        require(city.paint.sha(getattr(a, label)) == sha, 'Input changed: ' + label)
    print('CITY_REPAIRS_OK', a.phase, flush=True)


if __name__ == '__main__':
    main()
