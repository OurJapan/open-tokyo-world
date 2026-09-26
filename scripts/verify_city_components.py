# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Replay the remaining 29 components and compare 2,676 procedural material assignments.

Run in Blender 4.5.1 with --factory-startup --disable-autoexec --background CITY
--python-exit-code 1 --python scripts/verify_city_components.py -- --output NEW.json.
Pinned inputs are immutable. No source pipeline, embedded Text, render or save runs.
"""
import argparse
import ast
import builtins
import json
import math
from pathlib import Path
import random
import sys
from types import SimpleNamespace
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from component_contracts import material_snapshot, mesh_object_snapshot, reviewed_nodes, signature
from workspace import digest, inside, read_json, verify_file, write_json

CITY = '98a3932e6dc972d4ae702d264c1e894d77765a9a3a5e57c8a75591eafd42e926'
CINEMATIC = 'outputs/Tokyo_Cinematic_Final/tower.blend'
ENVIRONMENT = 'outputs/Tokyo_Tower_15s_Preparation/Tokyo_Tower_Environment_Updated.blend'
STREET = 'outputs/Tokyo_Tower_Street_Detail/Tokyo_Tower_Street_Detail.blend'
LEAVES = ['leaf' + str(i) for i in range(4)]
PINS = {
    'work/tokyo60/build_city.py': '7ad68498792753110a455649f80e02c195a827af61b7add24652fc70861986aa',
    'work/tower15_env/build_environment.py': '18075ad06cd96fef2600ba13a321a22458a06b16538bc78d1dba42f585604344',
    'work/tower15_env/refine_canopies.py': '03e2f78af4f164c3af08e1a1dc7da528d1dc79fef255295a2dcab0ab1ef22bd9',
    'work/street_detail/closeup_finish.py': '0e714ab334764ce919e307ae6aeab2dd53c5bf461f28c44d00250b730f5879a9',
    'work/street_detail/build.py': '263764443a32bf0f8dc3282fc6ec1685a3e3abe162cff086a35ab12a4a48ef48',
    'work/tokyo_traffic/build.py': 'cac0d9630e17930608fc2947e1fb26e6230cc7033ab5240d9322c670c5377bba',
    'work/detail_upgrade/finish_detail.py': 'b8f3bcc5a920e754664b393e69bd49348924e7d4cb87e32dba9cdf6f072a965e',
    'work/camera_options/render.py': '0770a3922a4c9ca9f7e465f7eba6e3c408f91119ea255be670398bcda9893f82',
}
# Only these complete top-level statements may execute. File reads in the light
# and equipment stages are constrained to already verified input paths below.
RANGES = {
    'work/tokyo60/build_city.py': [(20, 25), (32, 34)],
    'work/tower15_env/build_environment.py': [(14, 15), (21, 22), (46, 55)],
    'work/tower15_env/refine_canopies.py': [(5, 22)],
    'work/street_detail/build.py': [(8, 17), (18, 34), (48, 62), (66, 79), (81, 84)],
    'work/tokyo_traffic/build.py': [(11, 13), (15, 18), (21, 57), (59, 79)],
    'work/detail_upgrade/finish_detail.py': [(13, 40)],
    'work/camera_options/render.py': [(14, 17)],
}
INPUTS = [CINEMATIC, ENVIRONMENT, STREET, 'work/osm.xml', 'work/detail_upgrade/imported_features.json',
          'work/tokyo_traffic/layout.json', 'work/tokyo_traffic/tree_centers.json', 'work/tokyo_traffic/tree_keep.json',
          'work/street_detail/placements.json', 'work/street_detail/facade_input.json', 'work/street_detail/facade_layouts.json']


def is_aggregate(name):
    return name in LEAVES or name.startswith(('Tokyo traffic ', 'Close detail ', 'Street lights '))


def is_candidate(name):
    return is_aggregate(name) or name.startswith(('Street tree ', 'Park shrub '))


def run(args):
    import bpy
    import bmesh
    import numpy as np
    from mathutils import Vector

    city = Path(bpy.data.filepath)
    if args.output.exists():
        raise ValueError('Use a new output file')
    if digest(city) != CITY or bpy.app.version_string != '4.5.1 LTS' or bpy.context.preferences.filepaths.use_scripts_auto_execute:
        raise ValueError('Use the pinned city, Blender 4.5.1 and disabled auto-execution')
    manifest = read_json(ROOT / 'manifests/legacy-production-inputs.json')
    inputs = {name: verify_file(inside(args.inputs, name), manifest['files'][name]) for name in INPUTS}
    source_nodes = {}
    for name, pin in PINS.items():
        path = inside(args.sources, name)
        if digest(path) != pin:
            raise ValueError('Unreviewed source: ' + name)
        source_nodes[name] = reviewed_nodes(path, pin, RANGES.get(name, []))

    bpy.context.scene.frame_set(1)
    current = {o.name: o for o in bpy.context.scene.objects if o.type == 'MESH' and is_candidate(o.name)}
    if len(current) != 2676 or sum(is_aggregate(name) for name in current) != 29:
        raise ValueError('Unexpected candidate coverage')
    if any(slot.link != 'DATA' for o in current.values() for slot in o.material_slots):
        raise ValueError('Unexpected object material override')
    baseline = {name: mesh_object_snapshot(o) for name, o in current.items() if is_aggregate(name)}
    assignments = {name: [m.name if m else None for m in o.data.materials] for name, o in current.items()}
    baseline_materials = {name: material_snapshot(bpy.data.materials[name])
                          for name in {n for names in assignments.values() for n in names}}
    print('BASELINE_CAPTURED', len(baseline), len(baseline_materials), flush=True)
    del current
    report = {'version': 1, 'ok': False, 'city_sha256': CITY, 'blender_version': bpy.app.version_string,
              'numpy': np.__version__, 'source_pins': PINS, 'executed_ranges': RANGES,
              'adapted_formula': {'source': 'work/street_detail/closeup_finish.py', 'range': [40, 56],
                  'description': 'Replay only float32 in-place cluster shrink; discarded individual leaves and their random draws are not generated.'},
              'input_pins': {n: manifest['files'][n] for n in INPUTS}, 'intermediate_checks': {},
              'render_preset': {'source': 'work/camera_options/render.py', 'range': [14, 17],
                  'interpretation': 'This later recorded rule reproduces the stored BEVEL render flags. It does not prove which historical script was run.',
                  'changes': []},
              'baseline_objects': baseline, 'baseline_materials': baseline_materials,
              'code_sha256_lf': {p: __import__('hashlib').sha256((ROOT / p).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                  for p in ['scripts/verify_city_components.py', 'scripts/component_contracts.py', 'scripts/blender_worker.py']}}
    rebuilt, rebuilt_materials, expected_assignments = {}, {}, {}
    allowed_reads = set(inputs.values())

    def read_only(path, mode='r', **kwargs):
        path = Path(path).resolve()
        if path not in allowed_reads or mode not in {'r', 'rb'}:
            raise ValueError('Unapproved legacy file access')
        if mode == 'r':
            kwargs.setdefault('encoding', 'utf8')
        return builtins.open(path, mode, **kwargs)

    def namespace():
        names = ['range', 'len', 'tuple', 'str', 'list', 'dict', 'set', 'enumerate', 'zip', 'max', 'min',
                 'sum', 'map', 'ord', 'abs', 'any', 'all', 'int', 'float', 'round', 'print']
        # NumPy's array operations need the normal import hook internally. The
        # security boundary here is the reviewed source hash/ranges, not exec.
        return {'__builtins__': {**{n: getattr(builtins, n) for n in names},
                                 '__import__': builtins.__import__, 'open': read_only},
                'bpy': bpy, 'bmesh': bmesh, 'np': np, 'math': math, 'random': random, 'Vector': Vector,
                'json': json, 'ET': ET, 's': bpy.context.scene}

    def execute(name, first, last, ns):
        nodes = [n for n in source_nodes[name] if first <= n.lineno and n.end_lineno <= last]
        if not nodes:
            raise ValueError('No approved statements')
        exec(compile(ast.Module(body=nodes, type_ignores=[]), name, 'exec'), ns)

    def collect(objects):
        objects = list(objects)
        before = {o.name: mesh_object_snapshot(o) for o in objects}
        # Apply only the original BEVEL render rule to generated candidates in
        # memory. Never replay the file's loading, hiding, saving or rendering.
        preset_ns = namespace()
        preset_ns['s'] = SimpleNamespace(objects=objects)
        execute('work/camera_options/render.py', 14, 17, preset_ns)
        bpy.context.view_layer.update()
        for o in objects:
            rebuilt[o.name] = mesh_object_snapshot(o)
            for old, new in zip(before[o.name]['modifiers'], rebuilt[o.name]['modifiers']):
                if old['settings']['show_render'] != new['settings']['show_render']:
                    report['render_preset']['changes'].append({'object': o.name, 'modifier': new['name'],
                        'property': 'show_render', 'before': old['settings']['show_render'],
                        'after': new['settings']['show_render']})
            expected_assignments[o.name] = [m.name for m in o.data.materials]
            for m in o.data.materials:
                rebuilt_materials[m.name] = material_snapshot(m)

    def load_leaf_only(path):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        with bpy.data.libraries.load(str(path), link=False) as (source, dest):
            if not set(LEAVES) <= set(source.objects):
                raise ValueError('Missing precursor canopies')
            dest.objects = list(LEAVES)
        for o in dest.objects:
            bpy.context.scene.collection.objects.link(o)

    def verify_canopy_stage(key, snapshots):
        from blender_worker import mesh_fingerprint
        report['intermediate_checks'][key] = {
            name: mesh_fingerprint(bpy.data.objects[name].data) == snapshots[name] for name in LEAVES}
        if not all(report['intermediate_checks'][key].values()):
            raise ValueError('Canopy intermediate differs: ' + key)

    try:
        # Read the two intermediate canopy fingerprints before building anything.
        from blender_worker import mesh_fingerprint
        stages = {}
        for name in (ENVIRONMENT, STREET):
            load_leaf_only(inputs[name])
            stages[name] = {n: mesh_fingerprint(bpy.data.objects[n].data) for n in LEAVES}
        load_leaf_only(inputs[CINEMATIC])
        # Replace precursor leaf materials only in this temporary Blender process.
        precursor_materials = {n: material_snapshot(bpy.data.materials[n]) for n in LEAVES}
        for name in LEAVES:
            bpy.data.materials.remove(bpy.data.materials[name], do_unlink=True)
        ns = namespace(); ns['M'] = {}
        execute('work/tokyo60/build_city.py', 20, 34, ns)
        initial = {n: material_snapshot(bpy.data.materials[n]) for n in LEAVES}
        report['intermediate_checks']['initial_leaf_materials'] = initial == precursor_materials
        if initial != precursor_materials:
            raise ValueError('Initial canopy material recipe differs from precursor')
        for name in LEAVES:
            obj = bpy.data.objects[name]; obj.data.materials.clear(); obj.data.materials.append(bpy.data.materials[name])
        execute('work/tower15_env/build_environment.py', 14, 55, ns)
        execute('work/tower15_env/refine_canopies.py', 5, 22, ns)
        verify_canopy_stage('environment_canopies', stages[ENVIRONMENT])
        print('ENVIRONMENT_CANOPIES_MATCHED', flush=True)
        shrunk = 0
        for name in LEAVES:
            obj = bpy.data.objects[name]
            array = np.array([tuple(v.co) for v in obj.data.vertices], dtype=np.float32)
            if len(array) % 420:
                raise ValueError('Unexpected canopy cluster layout')
            for start in range(0, len(array), 420):
                tree = array[start:start + 420]; center = tree.mean(axis=0)
                if math.hypot(center[0] - 110, center[1] + 60) > 220:
                    continue
                shrunk += 1
                for cluster in range(10):
                    part = tree[cluster * 42:(cluster + 1) * 42]; center = part.mean(axis=0)
                    part[:] = center + (part - center) * .60
            obj.data.vertices.foreach_set('co', array.reshape(-1)); obj.data.update()
        report['near_canopies_shrunk'] = shrunk
        verify_canopy_stage('street_canopies', stages[STREET])
        print('STREET_CANOPIES_MATCHED', flush=True)
        ns.update(keep=read_json(inputs['work/tokyo_traffic/tree_keep.json']), park_centers=[])
        execute('work/tokyo_traffic/build.py', 11, 13, ns)
        report['intermediate_checks']['tree_centers'] = ns['tree_centers'] == read_json(inputs['work/tokyo_traffic/tree_centers.json'])
        if not report['intermediate_checks']['tree_centers']:
            raise ValueError('Exported tree centers differ')
        execute('work/tokyo_traffic/build.py', 15, 18, ns)
        execute('work/street_detail/build.py', 8, 17, ns)
        ns.update(layout=read_json(inputs['work/tokyo_traffic/layout.json']), col=bpy.context.scene.collection)
        execute('work/tokyo_traffic/build.py', 21, 57, ns)
        collect([o for o in bpy.context.scene.objects if is_aggregate(o.name)])
        print('TRAFFIC_AND_RETAINED_CANOPIES_BUILT', flush=True)
        report['retained_park_trees'] = len(ns['park_centers'])
        report['cars'] = len(ns['layout']['cars'])
        execute('work/tokyo_traffic/build.py', 59, 79, ns)
        for i, tree in enumerate(ns['layout']['trees']):
            for j, mesh in enumerate(ns['prototypes'][tree['species'], tree['variant']]):
                name = f"Street tree {tree['species']} {i}" + ('.001' if j else '')
                expected_assignments[name] = [m.name for m in mesh.materials]
                for m in mesh.materials:
                    rebuilt_materials[m.name] = material_snapshot(m)
        for i in range(1333):
            expected_assignments[f'Park shrub {i}'] = ['leaf' + str(i % 4)]
        del ns

        # Window geometry needs the predecessor's polygon groups. Their exported
        # facade_input must equal the recovered record. Palette sampling and wall
        # recoloring are outside the eight Close detail objects and are not replayed.
        bpy.ops.wm.open_mainfile(filepath=str(inputs[ENVIRONMENT]), use_scripts=False)
        ns = namespace(); ns.update(P=args.inputs / 'work/street_detail', col=bpy.context.scene.collection)
        execute('work/street_detail/build.py', 8, 34, ns)
        execute('work/street_detail/build.py', 48, 62, ns)
        facade_input = [{'polygons': g['poly'], 'step': 2.7 + (sum(map(ord, g['obj'].name)) % 6) * .12}
                        for g in ns['groups'].values()]
        # Exported JSON arrays deserialize as lists; in-memory coordinates are
        # tuples. Compare exact serialized values without changing point order.
        report['intermediate_checks']['facade_input'] = signature(facade_input) == signature(read_json(inputs['work/street_detail/facade_input.json']))
        if not report['intermediate_checks']['facade_input']:
            raise ValueError('Predecessor facade groups differ')
        report['facade_groups'] = len(facade_input)
        ns.update(layouts=read_json(inputs['work/street_detail/facade_layouts.json']),
                  walls=[bpy.data.materials.new('Unverified wall palette placeholder ' + str(i)) for i in range(6)])
        execute('work/street_detail/build.py', 66, 84, ns)
        collect([o for o in bpy.context.scene.objects if o.name.startswith('Close detail ')])
        print('EQUIPMENT_BUILT', flush=True)
        report['windows'] = ns['windows']
        del ns

        bpy.ops.wm.read_factory_settings(use_empty=True)
        ns = namespace(); ns.update(ROOT=args.inputs, P=args.inputs / 'work/detail_upgrade')
        execute('work/detail_upgrade/finish_detail.py', 13, 40, ns)
        collect([ns['lamp']]); report['lights'] = len(ns['placed'])
        if set(rebuilt) != set(baseline) or set(expected_assignments) != set(assignments):
            raise ValueError('Rebuilt object/material coverage differs')
        report['rebuilt_objects'] = rebuilt
        report['rebuilt_materials'] = rebuilt_materials
        report['object_mismatches'] = {n: [k for k in baseline[n] if baseline[n][k] != rebuilt[n][k]]
                                       for n in baseline if baseline[n] != rebuilt[n]}
        report['material_mismatches'] = sorted(n for n in baseline_materials
                                              if baseline_materials[n] != rebuilt_materials.get(n))
        report['assignment_mismatches'] = sorted(n for n in assignments if assignments[n] != expected_assignments[n])
        report['matched_objects'] = len(baseline) - len(report['object_mismatches'])
        report['matched_materials'] = len(baseline_materials) - len(report['material_mismatches'])
        report['matched_assignments'] = len(assignments) - len(report['assignment_mismatches'])
        report['material_signatures'] = {n: {'baseline': signature(baseline_materials[n]),
                                             'rebuilt': signature(rebuilt_materials[n])} for n in baseline_materials}
        report['ok'] = not (report['object_mismatches'] or report['material_mismatches'] or report['assignment_mismatches'])
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        report['city_unchanged'] = digest(city) == CITY
        report['inputs_unchanged'] = all(digest(p) == manifest['files'][n]['sha256'] for n, p in inputs.items())
        report['sources_unchanged'] = all(digest(inside(args.sources, n)) == h for n, h in PINS.items())
        report['ok'] = report['ok'] and report['city_unchanged'] and report['inputs_unchanged'] and report['sources_unchanged']
        write_json(args.output, report)
    if not report['ok']:
        raise ValueError('Component comparison failed; see report')
    print(json.dumps({k: report[k] for k in ['ok', 'matched_objects', 'matched_materials', 'matched_assignments']}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', type=Path, default=ROOT / 'data/local/sources/legacy-production-defac576')
    parser.add_argument('--inputs', type=Path, default=ROOT / 'data/local/sources/legacy-production-inputs-v1')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    args.sources, args.inputs, args.output = args.sources.resolve(), args.inputs.resolve(), args.output.resolve()
    run(args)


if __name__ == '__main__':
    main()
