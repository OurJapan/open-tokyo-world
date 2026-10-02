# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Read-only saved-scene checks for the separate northeast footway bend."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import audit_mori_plaza_levels as levels
import mori_plaza_east_bend_v1 as path
from validate_mori_plaza_outline import digest, read, write


def worker(args):
    import bpy
    import numpy as np
    from mathutils import Vector
    if bpy.app.version_string != '4.5.1 LTS' or bpy.context.preferences.filepaths.use_scripts_auto_execute:
        raise ValueError('Use Blender 4.5.1 LTS without automatic scripts')
    probes = []
    for stage, scene in [('before', args.before), ('after', args.after)]:
        bpy.ops.wm.open_mainfile(filepath=str(scene), use_scripts=False)
        bpy.context.scene.frame_set(1)
        for index, name in enumerate(sorted(path.ROADS)):
            mesh = bpy.data.objects[name].data
            arrays = {}
            for key, collection, prop, width, dtype in [
                ('vertices', mesh.vertices, 'co', 3, np.float32),
                ('indices', mesh.loops, 'vertex_index', 1, np.int32),
                ('starts', mesh.polygons, 'loop_start', 1, np.int32),
                ('counts', mesh.polygons, 'loop_total', 1, np.int32),
                ('material', mesh.polygons, 'material_index', 1, np.int32),
                ('smooth', mesh.polygons, 'use_smooth', 1, np.bool_),
                ('normal', mesh.polygons, 'normal', 3, np.float32)]:
                data = np.empty(len(collection) * width, dtype=dtype)
                collection.foreach_get(prop, data)
                arrays[key] = data.reshape(-1, 3) if width == 3 else data
            np.savez_compressed(args.output / f'{stage}-{index}.npz', **arrays)
        if stage == 'before':
            paving = bpy.data.objects[levels.PAVING]
            vertices = [tuple(paving.matrix_world @ v.co) for v in paving.data.vertices]
            _, edges = levels.top_boundary(vertices, [list(f.vertices) for f in paving.data.polygons])
            boundary = list(levels.boundary_samples(vertices, edges))
            selected = [p for p in boundary if -11.95 <= levels.local_uv(*p['xy'])[0] <= -4.05
                        and 81.05 <= levels.local_uv(*p['xy'])[1] <= 88.95]
            for index, sample in enumerate(selected):
                for offset in [i * .002 for i in range(-15, 16)]:
                    xy = [sample['xy'][k] + offset * sample['normal_xy'][k] for k in (0, 1)]
                    probes.append({'kind': 'target-boundary', 'pair': index, 'offset': offset, 'xy': xy})
            priorities = [(-21.864186737978322, 50.2447274376262), (-22.75472606452176, 49.80043092724036)]
            for index, uv in enumerate(priorities):
                sample = min(boundary, key=lambda p: math.dist(levels.local_uv(*p['xy']), uv))
                for offset in [i * .002 for i in range(-15, 16)]:
                    xy = [sample['xy'][k] + offset * sample['normal_xy'][k] for k in (0, 1)]
                    probes.append({'kind': 'old-junction', 'pair': index, 'offset': offset, 'xy': xy})
            for u in (-3.25, .25, 3.25):
                for v in (21.99, 22.01, 31.99, 32.01):
                    probes.append({'kind': 'entry', 'xy': path.world(u, v)[:2]})
            for i in range(37):
                for j in range(37):
                    probes.append({'kind': 'grid', 'xy': path.world(-17 + i * .5, 76 + j * .5)[:2]})
            for i in range(17):
                for j in range(29):
                    probes.append({'kind': 'protected-west', 'xy': path.world(-30+i,47+j)[:2]})
            write(args.output / 'boundary-selection.json', {'samples': len(selected), 'offset_step_m': .002})
        depsgraph = bpy.context.evaluated_depsgraph_get()
        def cast(xy):
            origin = Vector((*xy, 2))
            for _ in range(24):
                hit, location, normal, index, obj, matrix = bpy.context.scene.ray_cast(
                    depsgraph, origin, Vector((0, 0, -1)), distance=origin.z + 2)
                if not hit:
                    return {'object': None, 'z': None}
                if not obj.hide_render:
                    return {'object': obj.name, 'z': float(location.z)}
                origin = location - Vector((0, 0, .0005))
            raise ValueError('Too many hidden surfaces')
        rows = [{**probe, 'uv': levels.local_uv(*probe['xy']), **cast(probe['xy'])} for probe in probes]
        write(args.output / f'{stage}-rays.json', rows)
        if stage == 'after':
            write(args.output / 'saved-patch-audit.json', json.loads(bpy.context.scene[path.AUDIT_KEY]))
            seam = bpy.data.objects[path.SEAM]
            write(args.output / 'seam-mesh.json', {'vertices': [list(v.co) for v in seam.data.vertices],
                                                 'faces': [list(face.vertices) for face in seam.data.polygons],
                                                 'matrix_world': [list(row) for row in seam.matrix_world]})
    write(args.output / 'export.json', {'ok': True, 'scene_saved': False, 'blender_version': bpy.app.version_string})


def geometry_audit(args):
    import numpy as np
    import shapely as sh
    if sys.version_info[:2] != (3, 12) or np.__version__ != '2.3.5' or sh.__version__ != '2.1.2' or sh.geos_version_string != '3.13.1':
        raise ValueError('Use the existing pinned production Python 3.12 / NumPy 2.3.5 / Shapely 2.1.2 / GEOS 3.13.1')
    extent = path.scope_bounds()
    def data(stage, index):
        with np.load(args.output / f'{stage}-{index}.npz', allow_pickle=False) as saved:
            return {k: saved[k] for k in saved.files}
    def faces(mesh):
        for index, (start, count) in enumerate(zip(mesh['starts'], mesh['counts'])):
            ids = mesh['indices'][start:start + count]
            yield index, ids, (tuple(int(v) for v in ids), int(mesh['material'][index]), bool(mesh['smooth'][index]))
    def local_faces(mesh):
        xy = mesh['vertices'][mesh['indices'], :2]
        lower = np.minimum.reduceat(xy, mesh['starts'], axis=0)
        upper = np.maximum.reduceat(xy, mesh['starts'], axis=0)
        return ((lower[:, 0] <= extent[2]) & (lower[:, 1] <= extent[3]) &
                (upper[:, 0] >= extent[0]) & (upper[:, 1] >= extent[1]))
    results = {}
    for index, name in enumerate(sorted(path.ROADS)):
        before, after = data('before', index), data('after', index)
        if not np.array_equal(before['vertices'], after['vertices'][:len(before['vertices'])]):
            raise ValueError('Original vertices changed: ' + name)
        old_faces = Counter(key for _, _, key in faces(before))
        new_faces = Counter(key for _, _, key in faces(after))
        outside = Counter()
        footprints = {}
        inverted = 0
        for stage, mesh in [('before', before), ('after', after)]:
            polygons = []
            selected = local_faces(mesh)
            for face_index, ids, key in faces(mesh):
                added_vertices = stage == 'after' and bool(np.any(ids >= len(before['vertices'])))
                if not selected[face_index] and not added_vertices:
                    if stage == 'before':
                        outside[key] += 1
                    continue
                poly = mesh['vertices'][ids].astype(np.float64)
                polygon = sh.Polygon(poly[:, :2])
                # A valid vertical side can project to only two distinct XY points.
                if polygon.area <= 1e-8:
                    continue
                if not polygon.is_valid:
                    raise ValueError('Invalid saved XY face: ' + name)
                polygons.append(polygon)
                if stage == 'after' and key not in old_faces:
                    center = poly[:, :2].mean(axis=0)
                    if path.factor(*center) < 1 - 1e-6 and mesh['normal'][face_index, 2] <= 0:
                        inverted += 1
            footprints[stage] = sh.union_all(polygons)
        if outside - new_faces:
            raise ValueError('Exterior face, material or smooth flag changed: ' + name)
        xy_error = footprints['before'].symmetric_difference(footprints['after']).area
        if xy_error > .003 or inverted:
            raise ValueError(f'Footprint or walking surface orientation differs: {name}, {xy_error}, {inverted}')
        max_height_error = 0.
        for x, y, z in after['vertices'][len(before['vertices']):].astype(np.float64):
            u, v = path.local(x, y)
            # Independent formula for the isolated rectangle; prior grading is disjoint.
            scale = min(1., max(0., (abs(u + 8) - 4) / 4, (abs(v - 85) - 4) / 4))
            error = min(abs(z - (.11 + (level - .11) * scale)) for level in (.30, .46))
            max_height_error = max(max_height_error, error)
        if max_height_error > .0001:
            raise ValueError('Saved transition height differs: ' + name)
        results[name] = {'original_vertices_retained': len(before['vertices']),
                         'outside_faces_preserved': sum(outside.values()),
                         'xy_symmetric_difference_m2': xy_error,
                         'maximum_vertex_height_error_m': max_height_error,
                         'inverted_new_walking_faces': inverted}
    saved = read(args.output / 'saved-patch-audit.json')
    plan = path.load_plan(args.seam_plan, saved['seam_fill']['plan_sha256'])
    seam = read(args.output / 'seam-mesh.json')
    expected_matrix = np.eye(4)
    expected_matrix[:3, 3] = path.SEAM_ORIGIN
    if not np.array_equal(np.array(seam['matrix_world']), expected_matrix):
        raise ValueError('Unexpected infill object transform')
    # Forward the exact integer translation in float64 for the XY audit; a
    # float32 world-coordinate export would lose the small stored edge detail.
    seam_vertices = [[p[i] + path.SEAM_ORIGIN[i] for i in range(3)] for p in seam['vertices']]
    directed_edges = Counter()
    tops = []
    for face in seam['faces']:
        points = [seam_vertices[index] for index in face]
        if path.outline.area(points) <= 1e-10:
            raise ValueError('Degenerate new seam face')
        for a, b in zip(face, face[1:] + face[:1]):
            directed_edges[a, b] += 1
        if all(abs(p[2] - .11) < 1e-6 for p in points):
            if path.outline.signed_area(points) <= 0:
                raise ValueError('Inverted seam top')
            tops.append(sh.Polygon([p[:2] for p in points]))
    if any(count != 1 or directed_edges[b, a] != count for (a, b), count in directed_edges.items()):
        raise ValueError('Seam infill is not closed and consistently oriented')
    fill = sh.union_all(tops)
    planned = sh.union_all([sh.Polygon(p) for p in plan['paving_triangles']])
    if not fill.is_valid or fill.symmetric_difference(planned).area > 1e-7:
        raise ValueError('Saved infill differs from pinned plan')
    surfaces = read(args.seam_plan.parent / 'surfaces.json')
    paving = sh.union_all([sh.Polygon(p) for p in surfaces[levels.PAVING]])
    roads = sh.union_all([sh.Polygon(p) for name in path.ROADS for p in surfaces[name]])
    prior_fill = sh.union_all([sh.Polygon(p) for p in surfaces[path.previous.SEAM]])
    overlap = fill.intersection(paving.union(roads).union(prior_fill)).area
    if overlap > .0001 or fill.intersection(prior_fill).area > .000001:
        raise ValueError('New seam overlaps existing surfaces beyond float32 edge precision')
    permitted = paving.union(prior_fill).buffer(.0101, join_style=2).intersection(roads.buffer(.0101, join_style=2))
    if fill.difference(permitted).area > 1e-7:
        raise ValueError('Seam expands outside nearby existing surfaces')
    before, after = read(args.output / 'before-rays.json'), read(args.output / 'after-rays.json')
    prior_pairs = {}
    for row in before:
        if row['kind'] == 'target-boundary' and row['offset'] in (-.02, .02):
            prior_pairs.setdefault(row['pair'], []).append(row)
    eligible = {index for index, pair in prior_pairs.items() if len(pair) == 2
                and levels.road_pair(pair[0], pair[1]) is not None}
    if not eligible:
        raise ValueError('No mapped road/paving boundary selected')
    boundary_rises, gaps, retained, grid_checked = [], [], 0, 0
    pairs = {}
    for old, new in zip(before, after, strict=True):
        if old['xy'] != new['xy']:
            raise ValueError('Probe coordinates differ')
        if old['kind'] in ('old-junction', 'entry', 'protected-west'):
            if old['object'] != new['object'] or old['z'] is None or new['z'] is None or abs(old['z'] - new['z']) > .000001:
                raise ValueError('Adopted junction or entrance changed')
            retained += 1
        elif old['kind'] == 'target-boundary' and old['pair'] in eligible:
            if new['z'] is None or abs(new['z'] - .11) > .002:
                gaps.append({'pair': old['pair'], 'offset': old['offset'], 'before': old['z'], 'after': new['z'], 'object': new['object']})
            if old['offset'] in (-.02, .02):
                pairs.setdefault(old['pair'], []).append(new['z'])
        elif old['object'] in path.ROADS and path.factor(*old['xy']) == 0:
            if new['z'] is None or abs(new['z'] - .11) > .0001:
                raise ValueError('Flat path grid differs')
            grid_checked += 1
    for pair in pairs.values():
        if len(pair) == 2 and all(value is not None for value in pair):
            boundary_rises.append(abs(pair[0] - pair[1]))
    result = {'ok': not gaps and max(boundary_rises, default=0) <= .002,
              'objects': results, 'boundary_samples': len(eligible),
              'selected_boundary_samples': read(args.output / 'boundary-selection.json')['samples'],
              'seam_fill': {'closed_consistent_mesh': True, 'area_m2': fill.area,
                            'overlap_existing_m2': overlap, 'overlap_adopted_seam_m2': fill.intersection(prior_fill).area},
              'boundary_maximum_rise_m': max(boundary_rises, default=0), 'unresolved_boundary_probes': gaps,
              'prior_junction_and_entrance_probes_preserved': retained, 'flat_road_grid_probes': grid_checked,
              'limits': ['Fixed model-space probes; no surveyed elevations, continuous collision or accessibility certification.',
                         'Only three road meshes inside the declared rectangle may change.']}
    write(args.output / 'geometry-audit.json', result)
    if not result['ok']:
        raise ValueError('Boundary probes found an unresolved height or gap; see geometry-audit.json')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', type=Path)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seam-plan', type=Path, required=True)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    if args.worker:
        worker(args)
        return
    if not args.blender:
        parser.error('--blender is required')
    args.output.mkdir(parents=True, exist_ok=False)
    hashes = {name: digest(scene) for name, scene in [('before', args.before), ('after', args.after)]}
    command = [str(args.blender), '--factory-startup', '--background', '--disable-autoexec', '--python-exit-code', '1',
               '--python', str(Path(__file__).resolve()), '--', '--worker', '--before', str(args.before.resolve()),
               '--after', str(args.after.resolve()), '--output', str(args.output.resolve()),
               '--seam-plan', str(args.seam_plan.resolve())]
    with (args.output / 'blender.log').open('w', encoding='utf-8') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=600, check=True)
    result = geometry_audit(args)
    if hashes != {name: digest(scene) for name, scene in [('before', args.before), ('after', args.after)]}:
        raise ValueError('Saved scene changed during read-only validation')
    write(args.output / 'run.json', {'ok': result['ok'], 'scenes_unchanged': True, 'scene_sha256': hashes,
                                    'validator_sha256': digest(Path(__file__)), 'result': result})
    print(json.dumps({'ok': result['ok'], 'boundary_samples': result['boundary_samples'],
                      'maximum_rise_m': result['boundary_maximum_rise_m'], 'report': str(args.output / 'run.json')}))


if __name__ == '__main__':
    main()
