"""Close the isolated top-deck window bases onto their existing floor.

Only the lower ends of fixed parts009-011 move. The completed paint meshes,
floor, upper endpoints and all existing bevel profiles are retained.
"""
import argparse
import html
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tokyo_tower_paint_bands as state

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'assets/tokyo-tower/topdeck-junction-v1.json'
VIEWS = [
    ('sill', (0, -7.95, 246.25), (1, -7, .5), 2.4, 800, 600),
    ('topdeck', (0, 0, 248), (30, -40, 3), 23, 800, 600),
    ('full', (0, 0, 166), (430, -550, 130), 382, 640, 800),
]


def lower_end_indices(vertices, floor, target, end_depth):
    """Require the pinned two-ended member geometry before selecting an end."""
    import math
    if len(vertices) != target['vertices'] or not all(math.isfinite(v) for p in vertices for v in p):
        raise ValueError('Changed or non-finite target vertices')
    bottom = min(p[2] for p in vertices)
    if abs(bottom - target['lower_z_m']) > 1e-6 or not 0 < bottom - floor < .1:
        raise ValueError('Unexpected lower endpoint or floor height')
    indices = [i for i, p in enumerate(vertices) if p[2] <= bottom + end_depth]
    if len(indices) != target['lower_vertices']:
        raise ValueError('Changed lower end profile')
    selected = set(indices)
    if min(p[2] for i, p in enumerate(vertices) if i not in selected) - bottom < 3:
        raise ValueError('Unexpected middle vertices')
    return indices, floor - bottom


def checked_scene(plan):
    import bpy
    from mathutils import Matrix
    exporter = state.module(ROOT / 'assets/tokyo-tower/export.py', 'tower_export')
    parts = state.validate_scene(state.load(ROOT / 'assets/tokyo-tower/provenance.json'), exporter)
    for pid in [plan['floor_part_id']] + [t['part_id'] for t in plan['targets']]:
        ob = parts[pid]
        if ob.matrix_world != Matrix.Identity(4) or ob.data.shape_keys or ob.data.users != 1:
            raise ValueError('Target transform or shared/animated mesh changed')
        if ob.hide_render or ob.hide_get() or ob.hide_viewport:
            raise ValueError('Junction part is hidden')
    floor = max(v.co.z for v in parts[plan['floor_part_id']].data.vertices)
    if floor != plan['floor_top_m']:
        raise ValueError('Floor elevation changed')
    return parts, floor


def coordinates(mesh):
    import numpy as np
    return state.array(mesh.vertices, 'co', 3, np.float32).reshape(-1, 3)


def geometry_check(old, new, floor, target, depth):
    """Validate saved coordinates against original, independently of mutation."""
    import numpy as np
    a, b = coordinates(old), coordinates(new)
    if a.shape != b.shape or not np.isfinite(b).all() or not np.array_equal(a[:, :2], b[:, :2]):
        raise ValueError('Vertex membership or horizontal coordinates changed')
    low = a[:, 2] <= float(a[:, 2].min()) + depth
    if int(low.sum()) != target['lower_vertices'] or not np.array_equal(a[~low], b[~low]):
        raise ValueError('Upper end moved or lower profile membership changed')
    if b[:, 2].min() != floor:
        raise ValueError('Window base does not meet floor')
    delta = float(floor - a[:, 2].min())
    if not np.array_equal(b[low, 2], (a[low, 2] + delta).astype(np.float32)):
        raise ValueError('Lower end profile distorted')
    if state.edge_counts(new) != {'wire': 0, 'boundary': 0, 'more_than_two_faces': 0}:
        raise ValueError('Target acquired open or nonmanifold edges')
    # Restoring just positions on an in-memory copy must reproduce the complete
    # old mesh fingerprint: topology, material indices, UVs, attributes, normals.
    import bpy
    restored = new.copy()
    try:
        restored.vertices.foreach_set('co', a.ravel())
        restored.update()
        if state.mesh_state(old)['sha256'] != state.mesh_state(restored)['sha256']:
            raise ValueError('Non-coordinate mesh state changed')
    finally:
        bpy.data.meshes.remove(restored)
    return {'moved_vertices': int(low.sum()), 'fixed_vertices': int((~low).sum()),
            'old_gap_m': float(a[:, 2].min() - floor), 'new_gap_m': float(b[:, 2].min() - floor),
            'xy_unchanged': True, 'upper_end_unchanged': True, 'lower_profile_translated': True,
            'topology_shading_attributes_unchanged': True, 'edge_incidence': state.edge_counts(new)}


def contact_rays(parts, plan, floor):
    """Probe every saved member just above the floor, across its radial section."""
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    results = {}
    for target in plan['targets']:
        ob = parts[target['part_id']]
        mesh = ob.data
        adjacency = [[] for _ in mesh.vertices]
        for edge in mesh.edges:
            a, b = edge.vertices
            adjacency[a].append(b); adjacency[b].append(a)
        seen, centers = set(), []
        for index in range(len(mesh.vertices)):
            if index in seen:
                continue
            stack, component = [index], []
            seen.add(index)
            while stack:
                vertex = stack.pop(); component.append(vertex)
                for other in adjacency[vertex]:
                    if other not in seen:
                        seen.add(other); stack.append(other)
            pts = [mesh.vertices[i].co for i in component]
            centers.append(sum(pts, Vector()) / len(pts))
        if len(centers) != target['components']:
            raise ValueError('Member component count changed')
        tree = BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())
        hits = 0
        for center in centers:
            outward = Vector((center.x, center.y, 0)).normalized()
            origin = Vector((center.x, center.y, floor + .015)) + outward * .3
            hit, normal, index, distance = tree.ray_cast(origin, -outward, .6)
            hits += hit is not None
        results[target['part_id']] = {'members': len(centers), 'base_ray_hits': hits, 'ray_height_above_floor_m': .015}
    return results


def build(source, out, plan):
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
    parts, floor = checked_scene(plan)
    state.write(out / 'before-state.json', state.scene_record())
    before_rays = contact_rays(parts, plan, floor)
    if any(r['base_ray_hits'] for r in before_rays.values()):
        raise ValueError('Baseline no longer has the inspected open bases')
    changes = {}
    for target in plan['targets']:
        ob = parts[target['part_id']]
        indices, delta = lower_end_indices(coordinates(ob.data), floor, target, plan['lower_end_depth_m'])
        for index in indices:
            ob.data.vertices[index].co.z += delta
        ob.data.update()
        changes[target['part_id']] = {'moved_vertices': len(indices), 'lower_end_translation_m': delta}
    bpy.context.view_layer.update()
    state.write(out / 'build.json', {'ok': True, 'input_sha256': state.sha(source),
        'script_sha256': state.sha(__file__), 'plan_sha256': state.sha(PLAN), 'blender': bpy.app.version_string,
        'floor_top_m': floor, 'changes': changes, 'before_rays': before_rays})
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'after.blend'), compress=True)


def validate(source, out, plan):
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
    checked_scene(plan)
    before = state.scene_record()
    if before != state.load(out / 'before-state.json'):
        raise ValueError('Original build state differs')
    bpy.ops.wm.open_mainfile(filepath=str(out / 'after.blend'), use_scripts=False)
    parts, floor = checked_scene(plan)
    after = state.scene_record()
    if before['materials'] != after['materials'] or before['world'] != after['world']:
        raise ValueError('Material or world state changed')
    if set(before['objects']) != set(after['objects']):
        raise ValueError('Object membership changed')
    target_names = {parts[t['part_id']].name for t in plan['targets']}
    for name, old in before['objects'].items():
        current = after['objects'][name]
        fields = set(old) - ({'mesh'} if name in target_names else set())
        if any(old[k] != current[k] for k in fields):
            raise ValueError('Out-of-scope state changed: ' + name)
    rays = contact_rays(parts, plan, floor)
    if any(r['base_ray_hits'] != r['members'] for r in rays.values()):
        raise ValueError('An open base remains after saved reopening')
    names = [before['objects'][parts[t['part_id']].name]['mesh']['name'] for t in plan['targets']]
    with bpy.data.libraries.load(str(source), link=False) as (available, requested):
        requested.meshes = names
    stats = {}
    for target, old in zip(plan['targets'], requested.meshes):
        stats[target['part_id']] = geometry_check(old, parts[target['part_id']].data, floor, target, plan['lower_end_depth_m'])
    for old in requested.meshes:
        bpy.data.meshes.remove(old)
    state.write(out / 'validation.json', {'ok': True, 'saved_reopened': True, 'part_ids_preserved': 77,
        'unchanged_mesh_objects': 74, 'unchanged_camera_light': 2, 'all_materials_world_unchanged': True,
        'paint_parts005_006_unchanged': True, 'floor_unchanged': True, 'parts': stats, 'contact_rays': rays,
        'candidate_sha256': state.sha(out / 'after.blend'), 'candidate_bytes': (out / 'after.blend').stat().st_size,
        'input_sha256': state.sha(source), 'script_sha256': state.sha(__file__), 'plan_sha256': state.sha(PLAN),
        'limits': plan['limits']})


def render(source, out, label, plan):
    import bpy
    from mathutils import Vector
    bpy.ops.wm.open_mainfile(filepath=str(source if label == 'before' else out / 'after.blend'), use_scripts=False)
    checked_scene(plan)
    s = bpy.context.scene
    s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 32; s.cycles.seed = 0
    s.cycles.use_denoising = True; s.cycles.use_adaptive_sampling = False
    s.render.threads_mode = 'FIXED'; s.render.threads = 2
    s.render.resolution_percentage = 100; s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGBA'
    records = {}
    for name, target, offset, scale, width, height in VIEWS:
        point = Vector(target); cam = s.camera
        cam.location = point + Vector(offset)
        cam.rotation_euler = (point - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = scale
        s.render.resolution_x, s.render.resolution_y = width, height
        path = out / (label + '-' + name + '.png'); s.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        records[name] = {'image_sha256': state.sha(path), 'camera': state.object_record(cam),
            'light': state.object_record(bpy.data.objects['Tower review sun']), 'world': state.tree_record(s.world.node_tree),
            'view_transform': state.rna_values(s.view_settings), 'engine': 'CYCLES', 'device': 'CPU', 'samples': 32,
            'seed': 0, 'threads': 2, 'denoise': True, 'adaptive_sampling': False, 'size': [width, height]}
    state.write(out / (label + '-renders.json'), records)


def compare(out):
    import bpy
    import numpy as np
    before, after = state.load(out / 'before-renders.json'), state.load(out / 'after-renders.json')
    records, rows = {}, []
    for name, *_ in VIEWS:
        if {k: v for k, v in before[name].items() if k != 'image_sha256'} != {k: v for k, v in after[name].items() if k != 'image_sha256'}:
            raise ValueError('Comparison settings differ')
        pixels = []
        for label, config in [('before', before), ('after', after)]:
            path = out / (label + '-' + name + '.png')
            if state.sha(path) != config[name]['image_sha256']:
                raise ValueError('Image hash differs')
            image = bpy.data.images.load(str(path), check_existing=False)
            values = np.empty(len(image.pixels), dtype=np.float32); image.pixels.foreach_get(values)
            if list(image.size) != config[name]['size'] or not np.isfinite(values).all():
                raise ValueError('Invalid rendered image')
            pixels.append(values.reshape(-1, 4)); bpy.data.images.remove(image)
        delta = np.abs(pixels[0] - pixels[1])
        records[name] = {'matching_settings': True, 'size': before[name]['size'], 'changed_pixels': int(np.any(delta > 1e-6, axis=1).sum()),
            'mean_rgba_difference': float(delta.mean()), 'max_rgba_difference': float(delta.max())}
        rows.append(f'<h2>{html.escape(name)}</h2><div class="pair"><figure><figcaption>Before</figcaption><img src="before-{name}.png"></figure><figure><figcaption>After</figcaption><img src="after-{name}.png"></figure></div>')
    state.write(out / 'comparison.json', records)
    (out / 'review.html').write_text('<!doctype html><meta charset="utf-8"><title>Tokyo Tower top-deck window bases</title>'
        '<style>body{font:16px system-ui;max-width:1500px;margin:32px auto;background:#eee;color:#222}.pair{display:flex;gap:12px}figure{margin:0;flex:1;min-width:0}img{width:100%}h2{margin-top:32px}</style>'
        '<h1>Tokyo Tower: top-deck window bases</h1><p>Original model: ark4ez / OurJapan, CC BY 4.0. Changes: lower endpoints of parts009-011 meet the existing floor; prior paint repair retained.</p>'
        '<p>Simplified existing-part closure, not surveyed sill construction. Floor elevation and circular plan remain estimates. Lower white-shell gap and roof clearance are unchanged.</p>' + ''.join(rows), encoding='utf-8')


def main():
    import bpy
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--phase', choices=['build', 'validate', 'render-before', 'render-after', 'compare'], required=True)
    ap.add_argument('--input', required=True, type=Path)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:])
    source, out, plan = args.input.resolve(), args.output.resolve(), state.load(PLAN)
    if bpy.app.version != (4, 5, 1):
        raise ValueError('Blender 4.5.1 required')
    if source.stat().st_size != plan['input_bytes'] or state.sha(source) != plan['input_sha256']:
        raise ValueError('Wrong completed paint candidate')
    if source.parent == out or source == out / 'after.blend':
        raise ValueError('Output must be separate from original input')
    if args.phase == 'build':
        out.mkdir(parents=True, exist_ok=False)
        build(source, out, plan)
    elif args.phase == 'validate':
        validate(source, out, plan)
    elif args.phase == 'compare':
        compare(out)
    else:
        render(source, out, args.phase.removeprefix('render-'), plan)
    if state.sha(source) != plan['input_sha256']:
        raise ValueError('Original input changed')
    print('TOPDECK_JUNCTION_OK ' + args.phase, flush=True)


if __name__ == '__main__':
    main()
