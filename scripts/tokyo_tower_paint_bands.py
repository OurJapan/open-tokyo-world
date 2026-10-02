"""Split existing tower surfaces at their intended paint boundaries.

No new as-built dimensions: 154..333 / seven bands is the retained legacy design.
Pure geometry functions are importable without Blender; the CLI runs in Blender.
"""
import argparse
import hashlib
import html
import importlib.util
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'assets/tokyo-tower/paint-bands-v1.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def boundaries(plan):
    return [plan['legacy_band_bottom_m'] + i *
            (plan['legacy_band_top_m'] - plan['legacy_band_bottom_m']) / plan['band_count']
            for i in range(1, plan['band_count'])]


def paint_index(z, original, plan):
    """Palette order is orange, white. Preserve lower stair/leg paint."""
    bottom, top = plan['legacy_band_bottom_m'], plan['legacy_band_top_m']
    if z < bottom:
        return original
    return min(plan['band_count'] - 1, int((z - bottom) / (top - bottom) * plan['band_count'])) % 2


def split_polygon(vertices, polygon, planes, edge_cache):
    """Partition a convex face with shared edge intersections and retained winding.

    Existing vertex coordinates/indices never change. Reusing each edge/plane
    intersection prevents a split from creating disconnected coincident seams.
    """
    pieces = [list(polygon)]
    for plane in planes:
        next_pieces = []
        for face in pieces:
            zs = [vertices[i][2] for i in face]
            if not min(zs) < plane < max(zs):
                next_pieces.append(face)
                continue
            below, above = [], []
            for i, j in zip(face, face[1:] + face[:1]):
                a, b = vertices[i], vertices[j]
                if a[2] <= plane:
                    below.append(i)
                if a[2] >= plane:
                    above.append(i)
                if (a[2] < plane < b[2]) or (b[2] < plane < a[2]):
                    key = (plane, min(i, j), max(i, j))
                    if key not in edge_cache:
                        # Always compute in the same direction, independent of face order.
                        p, q = vertices[key[1]], vertices[key[2]]
                        t = (plane - p[2]) / (q[2] - p[2])
                        edge_cache[key] = len(vertices)
                        vertices.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]), plane))
                    below.append(edge_cache[key])
                    above.append(edge_cache[key])
            for result in (below, above):
                if len(result) < 3 or len(set(result)) != len(result):
                    raise ValueError('Degenerate paint-boundary split')
                next_pieces.append(result)
        pieces = next_pieces
    return pieces


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def array(collection, field, width, dtype):
    import numpy as np
    value = np.empty(len(collection) * width, dtype=dtype)
    collection.foreach_get(field, value)
    return value


def mesh_state(mesh):
    """Hash coordinates, topology, all current attributes, shading and UVs."""
    import numpy as np
    digest = hashlib.sha256()
    properties = [(mesh.vertices, 'co', 3, np.float32), (mesh.edges, 'vertices', 2, np.int32),
                  (mesh.loops, 'vertex_index', 1, np.int32), (mesh.loops, 'edge_index', 1, np.int32),
                  (mesh.polygons, 'loop_start', 1, np.int32), (mesh.polygons, 'loop_total', 1, np.int32),
                  (mesh.polygons, 'material_index', 1, np.int32), (mesh.polygons, 'use_smooth', 1, np.bool_)]
    for col, field, width, dtype in properties:
        values = array(col, field, width, dtype)
        if not np.isfinite(values).all():
            raise ValueError('Non-finite mesh values')
        digest.update(values.tobytes())
    formats = {'FLOAT': ('value', 1, np.float32), 'INT': ('value', 1, np.int32),
               'BOOLEAN': ('value', 1, np.bool_), 'FLOAT_VECTOR': ('vector', 3, np.float32),
               'FLOAT2': ('vector', 2, np.float32), 'INT32_2D': ('value', 2, np.int32),
               'FLOAT_COLOR': ('color', 4, np.float32), 'BYTE_COLOR': ('color', 4, np.float32)}
    for attr in sorted(mesh.attributes, key=lambda a: a.name):
        digest.update(repr((attr.name, attr.domain, attr.data_type)).encode())
        if attr.data_type not in formats:
            raise ValueError('Unaccounted mesh attribute: ' + attr.data_type)
        field, width, dtype = formats[attr.data_type]
        digest.update(array(attr.data, field, width, dtype).tobytes())
    digest.update(array(mesh.corner_normals, 'vector', 3, np.float32).tobytes())
    return {'name': mesh.name, 'sha256': digest.hexdigest(), 'vertices': len(mesh.vertices), 'faces': len(mesh.polygons),
            'loops': len(mesh.loops), 'uv_layers': list(mesh.uv_layers.keys()),
            'custom_normals': mesh.has_custom_normals}


def rna_values(obj):
    """Scalar/array RNA values: include shader operations, not only socket values."""
    result = {}
    for p in obj.bl_rna.properties:
        if p.identifier == 'rna_type' or p.type in ('POINTER', 'COLLECTION') or p.is_readonly:
            continue
        v = getattr(obj, p.identifier)
        result[p.identifier] = list(v) if getattr(p, 'is_array', False) else sorted(v) if isinstance(v, set) else v
    return result


def tree_record(tree):
    nodes = []
    for n in tree.nodes:
        item = [n.name, n.bl_idname, rna_values(n),
                [(s.identifier, rna_values(s)) for s in n.inputs]]
        if getattr(n, 'node_tree', None):
            item.append(tree_record(n.node_tree))
        if hasattr(n, 'color_ramp'):
            item.append([rna_values(n.color_ramp), [rna_values(e) for e in n.color_ramp.elements]])
        nodes.append(item)
    return [nodes, sorted((l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier)
                          for l in tree.links)]


def object_record(ob):
    record = {'name': ob.name, 'type': ob.type, 'properties': dict(ob.items()),
              'matrix': [list(row) for row in ob.matrix_world], 'hide_render': ob.hide_render,
              'hide_viewport': ob.hide_viewport, 'hide_get': ob.hide_get(),
              'collections': sorted(c.name for c in ob.users_collection)}
    if ob.type == 'MESH':
        record['mesh'] = mesh_state(ob.data)
        record['materials'] = [m.name for m in ob.data.materials]
    else:
        record['data'] = rna_values(ob.data)
    return record


def scene_record():
    import bpy
    value = {'objects': {o.name: object_record(o) for o in bpy.context.scene.objects},
            'materials': {m.name: [rna_values(m), tree_record(m.node_tree)] for m in bpy.data.materials},
            'world': [rna_values(bpy.context.scene.world), tree_record(bpy.context.scene.world.node_tree)]}
    return json.loads(json.dumps(value))


def validate_scene(scope, exporter):
    import bpy
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    records = {o.name: {'part_id': o.get('otw_part_id'), 'source_object': o.get('source_object')} for o in objects}
    exporter.validate_part_identity(objects, records, scope)
    if len(bpy.data.scenes) != 1 or bpy.data.images or bpy.data.libraries or bpy.data.texts or bpy.data.sounds:
        raise ValueError('Unexpected scene or external dependency')
    for ob in bpy.context.scene.objects:
        if ob.modifiers or ob.constraints or ob.parent or ob.animation_data:
            raise ValueError('Unexpected object dependency')
    for m in bpy.data.materials:
        exporter.material_check(m)
    return {o['otw_part_id']: o for o in objects}


def edge_counts(mesh):
    import numpy as np
    counts = np.bincount(array(mesh.loops, 'edge_index', 1, np.int32), minlength=len(mesh.edges))
    return {'wire': int((counts == 0).sum()), 'boundary': int((counts == 1).sum()),
            'more_than_two_faces': int((counts > 2).sum())}


def build(source, out, plan, scope, exporter):
    import bpy
    import numpy as np
    bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
    by_id = validate_scene(scope, exporter)
    before = scene_record()
    write(out / 'before-state.json', before)
    palette = [by_id[pid].data.materials[0] for pid in plan['part_ids']]
    stats = {}
    for original_color, pid in enumerate(plan['part_ids']):
        ob = by_id[pid]
        old = ob.data
        if old.uv_layers or old.has_custom_normals or any(p.use_smooth for p in old.polygons):
            raise ValueError('Target shading/UV baseline differs')
        expected_attrs = {'position', '.edge_verts', 'sharp_face', '.corner_vert', '.corner_edge'}
        if {a.name for a in old.attributes} != expected_attrs or len(old.materials) != 1:
            raise ValueError('Target mesh attributes or slots differ')
        vertices = [tuple(v) for v in array(old.vertices, 'co', 3, np.float32).reshape(-1, 3)]
        faces, material_indices, origins, triangle_origins, cache = [], [], [], [], {}
        old.calc_loop_triangles()
        triangles_by_face = {}
        for triangle in old.loop_triangles:
            triangles_by_face.setdefault(triangle.polygon_index, []).append(triangle.index)
        changed, splits = 0, 0
        for f in old.polygons:
            zs = [vertices[i][2] for i in f.vertices]
            crosses = any(min(zs) < h < max(zs) for h in boundaries(plan))
            splits += crosses
            pieces = []
            if crosses:
                # Preserve Blender's actual tessellated surface, including slightly
                # twisted legacy bevel quads; do not introduce a new diagonal.
                for tri_idx in triangles_by_face[f.index]:
                    for piece in split_polygon(vertices, list(old.loop_triangles[tri_idx].vertices), boundaries(plan), cache):
                        pieces.append((piece, tri_idx))
            else:
                pieces.append((list(f.vertices), -1))
            for face, tri_idx in pieces:
                z = sum(vertices[i][2] for i in face) / len(face)
                color = paint_index(z, original_color, plan)
                faces.append(face)
                origins.append(f.index)
                triangle_origins.append(tri_idx)
                material_indices.append(0 if color == original_color else 1)
                changed += color != original_color
        mesh = bpy.data.meshes.new(old.name + ' / horizontal paint bands v1')
        mesh.from_pydata(vertices, [], faces)
        mesh.materials.append(palette[original_color])
        mesh.materials.append(palette[1 - original_color])
        mesh.polygons.foreach_set('material_index', np.asarray(material_indices, dtype=np.int32))
        mesh.update()
        if mesh.validate(verbose=False, clean_customdata=False):
            raise ValueError('Generated paint mesh required automatic repair')
        ob.data = mesh
        np.save(out / (pid + '-face-origins.npy'), np.asarray(origins, dtype=np.int32), allow_pickle=False)
        np.save(out / (pid + '-triangle-origins.npy'), np.asarray(triangle_origins, dtype=np.int32), allow_pickle=False)
        stats[pid] = {'before': mesh_state(old), 'after': mesh_state(mesh), 'split_source_faces': splits,
                      'faces_with_other_paint': changed, 'new_vertices': len(vertices) - len(old.vertices),
                      'before_edge_counts': edge_counts(old), 'after_edge_counts': edge_counts(mesh)}
    write(out / 'build.json', {'ok': True, 'plan_sha256': sha(PLAN), 'source_sha256': sha(source),
                              'boundaries_m': boundaries(plan), 'parts': stats})
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'after.blend'), compress=True)


def geometry_check(old, current, origins, triangle_origins, original_color, plan):
    """Independent conservation check against original faces, not clipping code."""
    import numpy as np
    a = array(old.vertices, 'co', 3, np.float32).reshape(-1, 3).astype(float)
    b = array(current.vertices, 'co', 3, np.float32).reshape(-1, 3).astype(float)
    if not np.isfinite(b).all() or not np.array_equal(a, b[:len(a)]):
        raise ValueError('An original vertex moved')
    if len(origins) != len(current.polygons) or len(triangle_origins) != len(origins) or set(origins) != set(range(len(old.polygons))):
        raise ValueError('Incomplete source face coverage')
    old.calc_loop_triangles()
    triangles_by_face = {}
    for tri in old.loop_triangles:
        triangles_by_face.setdefault(tri.polygon_index, set()).add(tri.index)
    face_groups = {}
    for idx, origin in enumerate(origins):
        face_groups.setdefault(int(origin), []).append(idx)
    max_area_error, max_plane_error, checked_split_faces = 0., 0., 0
    for source_idx, dests in face_groups.items():
        src = old.polygons[source_idx]
        src_ids = list(src.vertices)
        p = a[src_ids]
        if len(dests) == 1:
            if list(current.polygons[dests[0]].vertices) != src_ids:
                raise ValueError('Unsplit face topology changed')
            if triangle_origins[dests[0]] != -1:
                raise ValueError('Unexpected unsplit triangle mapping')
        else:
            groups = {}
            for idx in dests:
                groups.setdefault(int(triangle_origins[idx]), []).append(idx)
            if set(groups) != triangles_by_face[source_idx]:
                raise ValueError('Original surface triangle coverage differs')
            for tri_idx, pieces in groups.items():
                p = a[list(old.loop_triangles[tri_idx].vertices)]
                normal = np.cross(p[1] - p[0], p[2] - p[0])
                original_area = np.linalg.norm(normal) / 2
                if original_area <= 0:
                    raise ValueError('Degenerate original triangle')
                normal /= 2 * original_area
                def area(points):
                    return sum(np.dot(np.cross(points[i] - points[0], points[i + 1] - points[0]), normal)
                               for i in range(1, len(points) - 1)) / 2
                total_area = 0.
                for idx in pieces:
                    q = b[list(current.polygons[idx].vertices)]
                    plane_error = float(np.max(np.abs((q - p[0]) @ normal)))
                    max_plane_error = max(max_plane_error, plane_error)
                    if plane_error > 4e-5:
                        raise ValueError('Split left its original surface triangle')
                    for start, end in zip(p, np.roll(p, -1, axis=0)):
                        edge = end - start
                        signed = np.cross(edge, q - start) @ normal
                        if np.min(signed) < -4e-5 * max(1., np.linalg.norm(edge)):
                            raise ValueError('Split escaped its original surface triangle')
                    piece_area = area(q)
                    if piece_area <= 0:
                        raise ValueError('Flipped or degenerate split face')
                    total_area += piece_area
                error = abs(total_area - original_area)
                max_area_error = max(max_area_error, error)
                if error > max(2e-5, original_area * 2e-5):
                    raise ValueError('Surface area was lost or duplicated')
            checked_split_faces += 1
        for idx in dests:
            f = current.polygons[idx]
            zs = b[list(f.vertices), 2]
            if any(min(zs) + 4e-5 < h < max(zs) - 4e-5 for h in boundaries(plan)):
                raise ValueError('Face still crosses a paint boundary')
            expected = paint_index(float(zs.mean()), original_color, plan)
            if f.material_index != (0 if expected == original_color else 1):
                raise ValueError('Wrong paint assignment')
            if f.use_smooth != src.use_smooth:
                raise ValueError('Face smoothing changed')
    if edge_counts(old) != edge_counts(current):
        raise ValueError('Edge incidence defect counts changed')
    return {'original_vertices_unchanged': len(a), 'original_faces_covered': len(old.polygons),
            'split_source_faces_checked': checked_split_faces, 'max_plane_error_m': max_plane_error,
            'max_face_area_error_m2': max_area_error, 'edge_counts': edge_counts(current),
            'paint_assignments_checked': len(current.polygons)}


def validate(source, out, plan, scope, exporter):
    import bpy
    import numpy as np
    bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
    before = scene_record()
    if before != load(out / 'before-state.json'):
        raise ValueError('Build baseline state differs')
    bpy.ops.wm.open_mainfile(filepath=str(out / 'after.blend'), use_scripts=False)
    by_id = validate_scene(scope, exporter)
    after = scene_record()
    if before['materials'] != after['materials'] or before['world'] != after['world']:
        raise ValueError('Material definitions or world changed')
    if set(before['objects']) != set(after['objects']):
        raise ValueError('Scene object membership changed')
    changed_names = {by_id[pid].name for pid in plan['part_ids']}
    for name, record in before['objects'].items():
        if name not in changed_names:
            if record != after['objects'][name]:
                raise ValueError('Out-of-scope object changed: ' + name)
        elif {k: v for k, v in record.items() if k not in ('mesh', 'materials')} != {
                k: v for k, v in after['objects'][name].items() if k not in ('mesh', 'materials')}:
            raise ValueError('Target identity, visibility or placement changed')
    # Load only the two original mesh datablocks, leaving saved candidate untouched.
    with bpy.data.libraries.load(str(source), link=False) as (available, requested):
        names = [before['objects'][by_id[pid].name]['mesh']['name'] for pid in plan['part_ids']]
        if not set(names).issubset(available.meshes):
            raise ValueError('Missing original target meshes')
        requested.meshes = names
    old_meshes = dict(zip(plan['part_ids'], requested.meshes))
    if len(old_meshes) != 2:
        raise ValueError('Original target mesh resolution failed')
    stats = {}
    palette_names = [before['objects'][by_id[pid].name]['materials'][0] for pid in plan['part_ids']]
    for color, pid in enumerate(plan['part_ids']):
        obj = by_id[pid]
        if [m.name for m in obj.data.materials] != [palette_names[color], palette_names[1 - color]]:
            raise ValueError('Paint palette changed')
        stats[pid] = geometry_check(old_meshes[pid], obj.data,
                                   np.load(out / (pid + '-face-origins.npy'), allow_pickle=False),
                                   np.load(out / (pid + '-triangle-origins.npy'), allow_pickle=False), color, plan)
    for m in old_meshes.values():
        bpy.data.meshes.remove(m)
    write(out / 'validation.json', {'ok': True, 'saved_reopened': True, 'part_ids_preserved': 77,
                                    'unchanged_mesh_objects': 75, 'unchanged_camera_light': 2,
                                    'all_material_definitions_unchanged': True, 'parts': stats,
                                    'candidate_sha256': sha(out / 'after.blend'),
                                    'limitations': plan['limits'] + ['No new full topology, self-intersection or engineering safety certification.']})


VIEWS = [
    ('full', (0, 0, 165), (430, -550, 130), 400, 720, 960),
    ('band-231', (0, 0, 230.714285714), (45, -65, 12), 29, 800, 640),
    ('band-205', (0, 0, 205.142857143), (-45, -65, 8), 33, 800, 640),
    ('lower-control', (0, 0, 72), (210, -280, 40), 180, 640, 640),
]


def render(out, label):
    import bpy
    from mathutils import Vector
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    s.cycles.device = 'CPU'
    s.cycles.samples = 16
    s.cycles.seed = 0
    s.cycles.use_denoising = False
    s.cycles.use_adaptive_sampling = False
    s.render.threads_mode = 'FIXED'
    s.render.threads = 4
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGBA'
    result = {}
    for name, target, offset, scale, width, height in VIEWS:
        cam = s.camera
        point = Vector(target)
        cam.location = point + Vector(offset)
        cam.rotation_euler = (point - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = scale
        s.render.resolution_x, s.render.resolution_y = width, height
        path = out / (label + '-' + name + '.png')
        s.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        result[name] = {'image_sha256': sha(path), 'camera': object_record(cam),
                        'light': object_record(bpy.data.objects['Tower review sun']),
                        'world': tree_record(s.world.node_tree), 'view_transform': rna_values(s.view_settings),
                        'engine': s.render.engine, 'device': s.cycles.device, 'samples': s.cycles.samples,
                        'seed': s.cycles.seed, 'denoise': False, 'adaptive_sampling': False,
                        'size': [width, height], 'threads': 4}
    write(out / (label + '-renders.json'), result)


def compare(out):
    import bpy
    import numpy as np
    before, after = load(out / 'before-renders.json'), load(out / 'after-renders.json')
    results, rows = {}, []
    for name, *_ in VIEWS:
        def config(record):
            return {k: v for k, v in record.items() if k != 'image_sha256'}
        if config(before[name]) != config(after[name]):
            raise ValueError('Mismatched comparison settings')
        pixels = []
        for label, record in [('before', before), ('after', after)]:
            path = out / (label + '-' + name + '.png')
            if sha(path) != record[name]['image_sha256']:
                raise ValueError('Render image changed')
            image = bpy.data.images.load(str(path), check_existing=False)
            values = np.empty(len(image.pixels), dtype=np.float32)
            image.pixels.foreach_get(values)
            if list(image.size) != record[name]['size'] or not np.isfinite(values).all():
                raise ValueError('Invalid image dimensions or pixels')
            pixels.append(values.reshape(-1, 4))
            bpy.data.images.remove(image)
        delta = np.abs(pixels[0] - pixels[1])
        results[name] = {'size': before[name]['size'], 'matching_settings': True,
                         'identical': bool(np.array_equal(*pixels)),
                         'changed_pixels': int(np.any(delta > 1e-6, axis=1).sum()),
                         'max_rgba_difference': float(delta.max()), 'mean_rgba_difference': float(delta.mean())}
        rows.append(f'<h2>{html.escape(name)}</h2><div class="pair"><figure><figcaption>Before</figcaption>'
                    f'<img src="before-{name}.png"></figure><figure><figcaption>After</figcaption>'
                    f'<img src="after-{name}.png"></figure></div>')
    write(out / 'comparison.json', results)
    (out / 'review.html').write_text('<!doctype html><meta charset="utf-8"><title>Tokyo Tower paint bands</title>'
        '<style>body{font:16px system-ui;max-width:1500px;margin:32px auto;background:#eee;color:#222}'
        '.pair{display:flex;gap:12px}figure{margin:0;flex:1;min-width:0}img{width:100%}h2{margin-top:32px}</style>'
        '<h1>東京タワー：上部塗装帯の面分割</h1><p>モデル原作 ark4ez / OurJapan, CC BY 4.0。'
        '改変：部品005・006の既存推定境界で面を分割し塗り分け。実測復元ではありません。</p>'
        '<p>77部品を保持。ローカルレビュー用の独立モデルであり、共通cityへは未適用。</p>' + ''.join(rows),
        encoding='utf-8')


def main():
    import bpy
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--phase', choices=['build', 'validate', 'render-before', 'render-after', 'compare'], required=True)
    ap.add_argument('--input', required=True, type=Path)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:])
    source, out = args.input.resolve(), args.output.resolve()
    plan = load(PLAN)
    if bpy.app.version != (4, 5, 1):
        raise ValueError('Blender 4.5.1 required')
    if source.stat().st_size != plan['input_bytes'] or sha(source) != plan['input_sha256']:
        raise ValueError('Wrong fixed-ID tower baseline')
    scope_path = ROOT / 'assets/tokyo-tower/provenance.json'
    if sha(scope_path) != plan['provenance_sha256']:
        raise ValueError('Tower provenance changed')
    if source == out / 'after.blend' or source.parent == out:
        raise ValueError('Output must be separate from source directory')
    scope = load(scope_path)
    exporter = module(ROOT / 'assets/tokyo-tower/export.py', 'tower_export')
    if args.phase == 'build':
        if out.exists():
            raise ValueError('Build output must be a new directory')
        out.mkdir(parents=True)
        build(source, out, plan, scope, exporter)
    elif args.phase == 'validate':
        validate(source, out, plan, scope, exporter)
    elif args.phase == 'compare':
        compare(out)
    else:
        label = args.phase.removeprefix('render-')
        path = source if label == 'before' else out / 'after.blend'
        bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
        validate_scene(scope, exporter)
        render(out, label)
    if sha(source) != plan['input_sha256']:
        raise ValueError('Source changed during run')


if __name__ == '__main__':
    main()
