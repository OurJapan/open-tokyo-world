# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Independently verify saved road removal with Shapely and Blender ground rays.

Run with the pinned Python 3.12 production environment. Exports and full audit
stay in a new local directory; no scene is saved by this validator.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

# Blender's --python runner does not add the script directory to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import mori_plaza_outline_v1 as outline


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def world(u, v, z):
    return (-419.8+(2*u+v)/math.sqrt(5), 290.82+(-u+2*v)/math.sqrt(5), z)


def export_scenes(before, after, sources, output):
    import bpy
    import numpy as np
    from mathutils import Vector
    if bpy.app.version_string != '4.5.1 LTS':
        raise ValueError('Use Blender 4.5.1 LTS')
    scope = outline.build_scope(sources)
    samples = []
    for u, v in [(0, v) for v in (32.01, 63.4, 63.5, 65, 68, 70, 80, 90)]:
        samples.append({'kind': 'removal', 'u': u, 'v': v, 'xy': world(u, v, 0)[:2]})
    for u in (-3.25, .25, 3.25):
        for v in (21.99, 22.01, 31.99, 32.01):
            samples.append({'kind': 'entry', 'u': u, 'v': v, 'xy': world(u, v, 0)[:2]})
    for i, (poly, _) in enumerate(scope['protect']):
        samples.append({'kind': 'protected', 'seed_index': i,
                        'xy': [sum(p[k] for p in poly)/len(poly) for k in (0, 1)]})
    for stage, path in [('before', before), ('after', after)]:
        bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
        bpy.context.scene.frame_set(1)
        for i, name in enumerate(sorted(outline.ROADS)):
            obj = bpy.data.objects[name]
            mesh = obj.data
            vertices = np.empty(len(mesh.vertices)*3, dtype=np.float32)
            mesh.vertices.foreach_get('co', vertices)
            indices = np.empty(len(mesh.loops), dtype=np.int32)
            mesh.loops.foreach_get('vertex_index', indices)
            arrays = {'vertices': vertices.reshape(-1, 3), 'indices': indices}
            for key, prop, dtype in [('starts', 'loop_start', np.int32), ('counts', 'loop_total', np.int32),
                                     ('material', 'material_index', np.int32), ('smooth', 'use_smooth', np.bool_),
                                     ('areas', 'area', np.float64)]:
                values = np.empty(len(mesh.polygons), dtype=dtype)
                mesh.polygons.foreach_get(prop, values)
                arrays[key] = values
            np.savez_compressed(output / f'{stage}-{i}.npz', **arrays)
        dg = bpy.context.evaluated_depsgraph_get()
        rays = []
        for sample in samples:
            start = Vector((*sample['xy'], 2.0))
            hit = False
            for _ in range(16):
                hit, point, normal, index, obj, matrix = bpy.context.scene.ray_cast(dg, start, Vector((0, 0, -1)), distance=start.z+2)
                if not hit or not obj.hide_render:
                    break
                start = point-Vector((0, 0, .0005))
            rays.append({**sample, 'hit': hit, 'object': obj.name if hit else None,
                         'z': float(point.z) if hit else None})
        write(output / f'{stage}-rays.json', rays)
        if stage == 'after':
            write(output / 'saved-patch-audit.json', json.loads(bpy.context.scene['otw_plaza_outline_audit']))
    write(output / 'export.json', {'ok': True, 'scene_saved': False, 'blender_version': bpy.app.version_string})


def geometry_audit(folder, sources):
    import numpy as np
    import shapely as sh
    if (sys.version_info[:2] != (3, 12) or np.__version__ != '2.3.5' or
            sh.__version__ != '2.1.2' or sh.geos_version_string != '3.13.1'):
        raise ValueError('Use Python 3.12, NumPy 2.3.5, Shapely 2.1.2 and GEOS 3.13.1')
    scope = outline.build_scope(sources)
    target = sh.union_all([sh.Polygon(p) for p, _ in scope['remove']])
    protected = sh.union_all([sh.Polygon(p) for p, _ in scope['protect']])
    mask = target.difference(protected)
    if not mask.is_valid or mask.is_empty:
        raise ValueError('Invalid independent removal mask')

    def faces(data):
        for i, (start, count) in enumerate(zip(data['starts'], data['counts'])):
            ids = data['indices'][start:start+count]
            key = (tuple(int(v) for v in ids), int(data['material'][i]), bool(data['smooth'][i]))
            yield i, ids, key

    checks = {}
    for index, name in enumerate(sorted(outline.ROADS)):
        with np.load(folder / f'before-{index}.npz', allow_pickle=False) as data:
            before = {k: data[k] for k in data.files}
        with np.load(folder / f'after-{index}.npz', allow_pickle=False) as data:
            after = {k: data[k] for k in data.files}
        if not np.array_equal(before['vertices'], after['vertices'][:len(before['vertices'])]):
            raise ValueError('Original road vertices moved: ' + name)
        old_faces = Counter(key for _, _, key in faces(before))
        new_faces = Counter(key for _, _, key in faces(after))
        top = {}
        exact_required = Counter()
        for stage, data in [('before', before), ('after', after)]:
            polygons = []
            for i, ids, key in faces(data):
                poly = data['vertices'][ids].astype(np.float64)
                b = (float(poly[:, 0].min()), float(poly[:, 1].min()), float(poly[:, 0].max()), float(poly[:, 1].max()))
                if stage == 'after' and key not in old_faces:
                    if not math.isfinite(data['areas'][i]) or data['areas'][i] <= 1e-9:
                        raise ValueError('New degenerate road face: ' + name)
                if not outline.overlaps(b, scope['bounds']) or poly[:, 2].max() > 1 or poly[:, 2].min() < -.01:
                    if stage == 'before':
                        exact_required[key] += 1
                    continue
                xy = sh.Polygon(poly[:, :2])
                horizontal = float(np.ptp(poly[:, 2])) < 1e-6
                if horizontal and xy.area > 1e-9:
                    if not xy.is_valid:
                        raise ValueError('Invalid saved horizontal face: ' + name)
                    polygons.append(xy)
                    affected = xy.intersection(mask).area > 1e-8
                else:
                    # A vertical curb projects to a line; check it independently
                    # of the production 3D polygon clipping algorithm.
                    points = sorted(set(tuple(p) for p in poly[:, :2]))
                    if len(points) >= 2:
                        a, b = max(((a, b) for a in points for b in points), key=lambda ab:math.dist(*ab))
                        affected = sh.LineString([a, b]).intersection(mask).length > 1e-7
                    else:
                        affected = False
                if stage == 'before' and not affected:
                    exact_required[key] += 1
            top[stage] = sh.union_all(polygons)
        if exact_required - new_faces:
            raise ValueError('An out-of-scope road face or its attributes changed: ' + name)
        expected = top['before'].difference(mask)
        difference = expected.symmetric_difference(top['after']).area
        remaining = top['after'].intersection(mask).area
        protection_error = top['before'].intersection(protected).symmetric_difference(top['after'].intersection(protected)).area
        if difference > .1 or remaining > .02 or protection_error > .02:
            raise ValueError(f'Independent surface comparison failed: {name}: {difference}, {remaining}, {protection_error}')
        checks[name] = {'original_vertices_exact': True,
                        'outside_faces_and_attributes_exact': sum(exact_required.values()),
                        'expected_removed_top_area_m2': top['before'].intersection(mask).area,
                        'saved_xy_symmetric_difference_m2': difference,
                        'remaining_inside_mask_m2': remaining,
                        'protected_xy_symmetric_difference_m2': protection_error,
                        'new_degenerate_faces': 0}
    before, after = read(folder / 'before-rays.json'), read(folder / 'after-rays.json')
    removal, entry, protected_checks = [], [], []
    for a, b in zip(before, after):
        if a['kind'] == 'removal':
            if not b['hit'] or b['object'] in outline.ROADS or not -.01 <= b['z'] < 1:
                raise ValueError('Removal point has no exposed ground: ' + str(b))
            removal.append({'u': a['u'], 'v': a['v'], 'before_object': a['object'], 'before_z': a['z'],
                            'after_object': b['object'], 'after_z': b['z']})
        elif a['kind'] == 'entry' or a['object'] in outline.ROADS:
            if a['hit'] != b['hit'] or a['object'] != b['object'] or abs(a['z'] - b['z']) > 1e-5:
                raise ValueError('Retained surface sample changed: ' + str(a))
            (entry if a['kind'] == 'entry' else protected_checks).append(a)
    if len(entry) != 12 or len(protected_checks) < 3:
        raise ValueError('Insufficient retained-surface samples')
    return {'ok': True, 'source_attribution': scope['audit'], 'road_checks': checks,
            'independent_mask_area_m2': mask.area, 'saved_ground_rays': removal,
            'retained_entry_samples': len(entry), 'retained_other_road_samples': len(protected_checks),
            'verification_method': 'Independent Shapely planar boolean comparison; exact vertex/face/attribute checks; Blender ray casts after reopening both saved scenes.',
            'runtime': {'python': sys.version.split()[0], 'numpy': np.__version__, 'shapely': sh.__version__, 'geos': sh.geos_version_string},
            'limitations': ['Existing ground and overlapping legitimate road surfaces are inherited.',
                            'No survey, navigation, accessibility or real-world grade certification.',
                            'Road shells are inherited thin surfaces, not watertight solids.',
                            'Only the exclusively attributed area-outline contribution is removed.']}


def main():
    worker = '--worker' in sys.argv
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', required=True, type=Path)
    parser.add_argument('--after', required=True, type=Path)
    parser.add_argument('--road-inputs', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--blender', type=Path)
    parser.add_argument('--worker', action='store_true')
    argv = sys.argv[sys.argv.index('--')+1:] if worker else None
    args = parser.parse_args(argv)
    if worker:
        export_scenes(args.before, args.after, args.road_inputs, args.output)
        return
    if not args.blender or args.output.exists():
        raise ValueError('Supply Blender and a new audit output directory')
    outline.verify_sources(args.road_inputs)
    args.output.mkdir(parents=True)
    hashes = {'before': digest(args.before), 'after': digest(args.after)}
    result = {'ok': False}
    try:
        command = [str(args.blender.resolve()), '--factory-startup', '--disable-autoexec', '--background',
                   '--python-exit-code', '1', '--python', str(Path(__file__).resolve()), '--', '--worker',
                   '--before', str(args.before.resolve()), '--after', str(args.after.resolve()),
                   '--road-inputs', str(args.road_inputs.resolve()), '--output', str(args.output.resolve())]
        with (args.output / 'export.log').open('w', encoding='utf-8') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1200)
        result = geometry_audit(args.output, args.road_inputs)
        result['saved_blends_unchanged'] = hashes == {'before': digest(args.before), 'after': digest(args.after)}
        if not result['saved_blends_unchanged']:
            raise ValueError('Saved scene changed during read-only verification')
        result['input_blend_sha256'] = hashes
        result['validator_sha256'] = digest(__file__)
    except Exception as error:
        result.update(ok=False, error=str(error))
        raise
    finally:
        write(args.output / 'validation.json', result)
    print('Saved outline verification passed: ' + str(args.output / 'validation.json'))


if __name__ == '__main__':
    main()
