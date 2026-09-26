# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Read-only boundary-height diagnosis for the accepted PR 40 plaza paving.

Reports model-space differences, not surveyed elevations or accessibility.
The city file and detailed boundary coordinates stay in a local directory.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import mori_plaza_landscape_v1 as landscape

PAVING = landscape.PAVING
ROADS = landscape.outline.ROADS | {'paint_0 unified road'}
LOCK = ROOT / 'manifests/mori-plaza-landscape-accepted.json'
SPACING = .5
OFFSET = .02


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def verify_input(path):
    lock = read(LOCK)
    if path.stat().st_size != lock['bytes'] or digest(path) != lock['sha256']:
        raise ValueError('Expected the pinned PR 40 accepted city')
    return lock


def top_boundary(vertices, faces):
    """Boundary edges of horizontal paving tops, excluding bottom and walls."""
    counts = Counter()
    tops = 0
    for face in faces:
        if len(face) < 3:
            raise ValueError('Invalid paving face')
        if not all(abs(vertices[i][2] - landscape.TOP_Z) < 1e-5 for i in face):
            continue
        tops += 1
        for a, b in zip(face, face[1:] + face[:1]):
            counts[tuple(sorted((a, b)))] += 1
    if not tops or any(value > 2 for value in counts.values()):
        raise ValueError('Missing or overlapping paving top topology')
    return tops, sorted(edge for edge, count in counts.items() if count == 1)


def boundary_samples(vertices, edges):
    """Midpoint samples cover each edge with intervals no longer than 0.5m."""
    for edge_id, (ia, ib) in enumerate(edges):
        a, b = vertices[ia], vertices[ib]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length < .001:
            continue
        count = max(1, math.ceil(length / SPACING))
        for index in range(count):
            t = (index + .5) / count
            yield {'edge': edge_id, 'xy': [a[0] + t * dx, a[1] + t * dy],
                   'normal_xy': [-dy / length, dx / length], 'interval_m': length / count}


def road_pair(negative, positive):
    """Always report road minus paving, regardless of boundary orientation."""
    for road, paving in ((negative, positive), (positive, negative)):
        if paving['object'] == PAVING and road['object'] in ROADS:
            heights = (road['z'], paving['z'])
            if not all(isinstance(value, (float, int)) and math.isfinite(value) for value in heights):
                raise ValueError('Invalid sampled height')
            return {'road': road, 'paving': paving, 'rise_m': road['z'] - paving['z']}
    return None


def local_uv(x, y):
    x, y = x + 419.8, y - 290.82
    return [(2 * x - y) / math.sqrt(5), (x + 2 * y) / math.sqrt(5)]


def worker(args):
    import bpy
    from mathutils import Vector
    verify_input(args.input)
    if bpy.app.version_string != '4.5.1 LTS' or bpy.context.preferences.filepaths.use_scripts_auto_execute:
        raise ValueError('Use Blender 4.5.1 LTS with automatic scripts disabled')
    bpy.ops.wm.open_mainfile(filepath=str(args.input), use_scripts=False)
    bpy.context.scene.frame_set(1)
    obj = bpy.data.objects[PAVING]
    if obj.type != 'MESH' or obj.hide_render or obj.modifiers:
        raise ValueError('Unexpected paving state')
    vertices = [tuple(obj.matrix_world @ v.co) for v in obj.data.vertices]
    top_faces, edges = top_boundary(vertices, [list(face.vertices) for face in obj.data.polygons])
    dg = bpy.context.evaluated_depsgraph_get()

    def cast(x, y):
        origin = Vector((x, y, 2))
        for _ in range(24):
            hit, point, normal, index, obj, matrix = bpy.context.scene.ray_cast(
                dg, origin, Vector((0, 0, -1)), distance=max(0, origin.z + 2))
            if not hit:
                return {'object': None, 'z': None, 'normal_z': None}
            if not obj.hide_render:
                return {'object': obj.name, 'z': float(point.z), 'normal_z': float(normal.z)}
            origin = point - Vector((0, 0, .0005))
        raise ValueError('Too many hidden surfaces along a probe')

    samples, contacts = [], []
    neighbors = Counter()
    for sample in boundary_samples(vertices, edges):
        x, y = sample['xy']
        nx, ny = sample['normal_xy']
        negative = cast(x - OFFSET * nx, y - OFFSET * ny)
        positive = cast(x + OFFSET * nx, y + OFFSET * ny)
        sample.update(uv=local_uv(x, y), negative=negative, positive=positive)
        samples.append(sample)
        for a, b in ((negative, positive), (positive, negative)):
            if a['object'] == PAVING and b['object'] != PAVING:
                neighbors[b['object'] or 'no-hit'] += 1
        pair = road_pair(negative, positive)
        if pair:
            contacts.append({**sample, **pair})
    groups = Counter((row['road']['object'], round(row['road']['z'], 3),
                      round(row['rise_m'], 3)) for row in contacts)
    result = {
        'version': 1, 'ok': True, 'saved_scene': False, 'frame': 1,
        'blender_version': bpy.app.version_string, 'input_sha256': digest(args.input),
        'settings': {'spacing_m': SPACING, 'side_offset_m': OFFSET, 'ray_start_z_m': 2,
                     'ray_end_z_m': -2, 'maximum_hidden_hits': 24},
        'paving_top_faces': top_faces, 'boundary_edges': len(edges),
        'boundary_samples': len(samples), 'road_pairs': len(contacts),
        'neighbor_counts': dict(sorted(neighbors.items())),
        'height_groups': [{'object': key[0], 'road_z_m': key[1], 'rise_m': key[2], 'samples': count}
                          for key, count in sorted(groups.items())],
        'limits': ['Model-space diagnostic, not surveyed terrain or an accessibility assessment.',
                   'Samples are not unique joins, continuous coverage, or an edge-length estimate.',
                   'Rays start at z=2m; overhead obstructions and hidden geometry are outside the diagnosis.',
                   'Only the fixed accepted paving boundary is sampled; other streets and grass boundaries are not covered.',
                   'No geometry, materials, registration or source file are saved.'],
    }
    write_new(args.output / 'samples.json', samples)
    write_new(args.output / 'contacts.json', contacts)
    write_new(args.output / 'summary.json', result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New local directory; never overwritten')
    parser.add_argument('--blender', type=Path)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    args.input, args.output = args.input.resolve(), args.output.resolve()
    if args.worker:
        worker(args)
        return 0
    if not args.blender:
        parser.error('--blender is required')
    lock = verify_input(args.input)
    args.output.mkdir(parents=True, exist_ok=False)
    command = [str(args.blender), '--factory-startup', '--disable-autoexec', '--background',
               '--python-exit-code', '1', '--python', str(Path(__file__).resolve()), '--',
               '--worker', '--input', str(args.input), '--output', str(args.output)]
    result = {'version': 1, 'ok': False, 'input_sha256': lock['sha256']}
    try:
        with (args.output / 'blender.log').open('w', encoding='utf-8') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=600, check=True)
        result['summary'] = read(args.output / 'summary.json')
        result['ok'] = result['summary']['ok']
    finally:
        result['input_unchanged'] = digest(args.input) == lock['sha256']
        result['ok'] = result['ok'] and result['input_unchanged']
        paths = [Path(__file__), ROOT / 'scripts/mori_plaza_landscape_v1.py',
                 ROOT / 'scripts/mori_plaza_outline_v1.py', LOCK]
        result['code_and_lock_sha256_lf'] = {
            p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
            for p in paths}
        write_new(args.output / 'run.json', result)
    print(json.dumps({'ok': result['ok'], 'input_unchanged': result['input_unchanged'],
                      'boundary_samples': result['summary']['boundary_samples'],
                      'road_pairs': result['summary']['road_pairs'], 'report': str(args.output / 'run.json')}, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    arguments = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None
    try:
        raise SystemExit(main(arguments))
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        print('Plaza level audit failed: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
