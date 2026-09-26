# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Check recovered tree/shrub layouts against the immutable city's shapes and transforms.

Run in Blender with --factory-startup --disable-autoexec --background CITY
--python-exit-code 1 --python scripts/verify_city_tree_placements.py -- --output FILE.
This reads JSON and scene geometry; it does not execute legacy code or save a blend.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def expected_records(layout, shrubs, prototypes):
    street = next(g for g in prototypes['groups'] if g['prefix'] == 'Street tree ')['prototypes']
    bush = next(g for g in prototypes['groups'] if g['prefix'] == 'Park shrub ')['prototypes']
    shapes = {(p['species'], p['variant'], 'bark' if p['vertices'] == 592 else 'foliage'): p['mesh_sha256'] for p in street}
    bushes = {p['variant']: p for p in bush}
    if len(shapes) != 12 or set(bushes) != {0, 1, 2, 3}:
        raise ValueError('Unexpected reviewed prototype set')
    records = []
    for i, tree in enumerate(layout['trees']):
        scale = .9 + (i % 7) * .035
        for suffix, part in [('', 'bark'), ('.001', 'foliage')]:
            records.append({'name': f"Street tree {tree['species']} {i}{suffix}", 'group': 'street-trees',
                            'mesh_sha256': shapes[tree['species'], tree['variant'], part],
                            'location': [*tree['xy'], .2], 'rotation_euler': [0, 0, tree['yaw']], 'scale': [scale] * 3})
    rng = random.Random(1560)
    # build_environment.py consumes one draw per prototype vertex before yaw.
    for i in range(4):
        for _ in range(bushes[i]['vertices']):
            rng.uniform(.88, 1.12)
    for i, (x, y, radius) in enumerate(shrubs):
        records.append({'name': f'Park shrub {i}', 'group': 'shrubs', 'mesh_sha256': bushes[i % 4]['mesh_sha256'],
                        'location': [x, y, .11 + radius * .5], 'rotation_euler': [0, 0, rng.random() * math.tau],
                        'scale': [radius, radius * .85, radius * .65]})
    for record in records:
        for key in ('location', 'rotation_euler', 'scale'):
            record[key] = [f32(v) for v in record[key]]
    return records


def main():
    import bpy
    sys.path.insert(0, str(ROOT / 'scripts'))
    from city_catalog import read, require, sha, write
    from workspace import inside, verify_file
    from blender_worker import mesh_fingerprint

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=ROOT / 'data/local/sources/legacy-production-inputs-v1')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    source = Path(bpy.data.filepath)
    catalog = read(ROOT / 'manifests/city-catalog-v1.json')
    input_manifest = read(ROOT / 'manifests/legacy-production-inputs.json')
    evidence = read(ROOT / 'sources/city-pr12-production-audit.json')
    require(sha(source) == catalog['input']['sha256'] == input_manifest['city_sha256'] == evidence['baseline']['sha256'], 'Wrong city')
    require(bpy.app.version_string == catalog['input']['blender_version'], 'Wrong Blender version')
    require(not bpy.context.preferences.filepaths.use_scripts_auto_execute, 'Disable automatic script execution')
    require(not args.output.exists(), 'Use a new output file')
    input_names = ('work/tokyo_traffic/layout.json', 'work/tower15_env/shrubs.json')
    inputs = {name: verify_file(inside(args.inputs, name), input_manifest['files'][name]) for name in input_names}
    records = expected_records(read(inputs[input_names[0]]), read(inputs[input_names[1]]), evidence['prototype_verification'])
    expected = {r['name']: r for r in records}
    actual = {o.name: o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.startswith(('Street tree ', 'Park shrub '))}
    require(len(expected) == 2647 and set(actual) == set(expected), 'Tree/shrub coverage differs')
    cache, mismatches, matches = {}, [], {'street-trees': 0, 'shrubs': 0}
    for name, obj in actual.items():
        row = expected[name]; errors = []
        for key in ('location', 'rotation_euler', 'scale'):
            if list(getattr(obj, key)) != row[key]:
                errors.append(key)
        if (obj.parent is not None or obj.constraints or obj.animation_data or obj.rotation_mode != 'XYZ'
                or tuple(obj.delta_location) != (0, 0, 0) or tuple(obj.delta_rotation_euler) != (0, 0, 0)
                or tuple(obj.delta_scale) != (1, 1, 1)):
            errors.append('additional-transform-dependency')
        key = obj.data.as_pointer()
        if key not in cache:
            cache[key] = mesh_fingerprint(obj.data)
        if cache[key] != row['mesh_sha256']:
            errors.append('prototype-geometry-or-variant')
        if errors:
            mismatches.append({'object': name, 'fields': errors})
        else:
            matches[row['group']] += 1
    result = {'version': 1, 'input_sha256': catalog['input']['sha256'], 'blender_version': bpy.app.version_string,
              'code_sha256_lf': hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
              'layout_inputs': {name: input_manifest['files'][name] for name in input_names},
              'matched_objects': matches, 'mismatches': mismatches,
              'comparison': 'Exact Blender float32 location/Euler/scale plus expected prototype geometry hash; no extra transform dependencies.',
              'limitations': ['Material node graphs, visibility and the remaining 29 objects are not verified here.',
                              'Matching inferred placement does not establish surveyed positions or a distribution license.'],
              'input_unchanged': sha(source) == catalog['input']['sha256'],
              'layouts_unchanged': all(sha(path) == input_manifest['files'][name]['sha256'] for name, path in inputs.items())}
    result['ok'] = not mismatches and result['input_unchanged'] and result['layouts_unchanged']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, result)
    require(result['ok'], 'Tree placement verification failed; see output')
    print(json.dumps({'matched_objects': matches, 'input_unchanged': True}))


if __name__ == '__main__':
    main()
