# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Compare saved tree geometry with reviewed, hash-pinned legacy prototype code.

Run in Blender with --factory-startup --disable-autoexec --background CITY
--python-exit-code 1 --python scripts/verify_tree_prototypes.py -- --output FILE.
Only the listed geometry ranges execute. No legacy top-level pipeline, embedded
Text, source download, placement reconstruction or blend save is performed.
"""
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
APPROVED = {
    'work/street_detail/build.py': ('263764443a32bf0f8dc3282fc6ec1685a3e3abe162cff086a35ab12a4a48ef48', [(8, 9)]),
    'work/tokyo_traffic/build.py': ('cac0d9630e17930608fc2947e1fb26e6230cc7033ab5240d9322c670c5377bba', [(24, 27), (30, 31), (60, 79)]),
    'work/tower15_env/build_environment.py': ('18075ad06cd96fef2600ba13a321a22458a06b16538bc78d1dba42f585604344', [(62, 67)]),
}


def load_reviewed_nodes(base):
    trees = {}
    for name, (expected, ranges) in APPROVED.items():
        data = (Path(base) / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Unreviewed legacy source: ' + name)
        nodes = ast.parse(data.decode('utf8')).body
        selected = []
        for span in ranges:
            matches = [n for n in nodes if (n.lineno, n.end_lineno) == span]
            if len(matches) != 1 or not isinstance(matches[0], (ast.FunctionDef, ast.For)):
                raise ValueError('Reviewed code range differs: ' + name)
            selected.extend(matches)
        trees[name] = selected
    return trees


def main():
    import bpy
    import bmesh
    from mathutils import Vector
    sys.path.insert(0, str(ROOT / 'scripts'))
    from city_catalog import read, require, sha, write
    from blender_worker import mesh_fingerprint

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', type=Path, default=ROOT / 'data/local/sources/legacy-production-defac576')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    source = Path(bpy.data.filepath)
    config = read(ROOT / 'manifests/city-catalog-v1.json')
    require(source.stat().st_size == config['input']['bytes'] and sha(source) == config['input']['sha256'], 'Wrong city')
    require(bpy.app.version_string == config['input']['blender_version'], 'Wrong Blender version')
    require(not bpy.context.preferences.filepaths.use_scripts_auto_execute, 'Disable automatic script execution')
    require(not args.output.exists(), 'Use a new output file')
    # Validate all three complete source hashes before executing any selected node.
    trees = load_reviewed_nodes(args.sources)
    old, cache = {}, {}
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and (obj.name.startswith('Street tree ') or obj.name.startswith('Park shrub ')):
            key = obj.data.as_pointer()
            if key not in cache:
                cache[key] = mesh_fingerprint(obj.data)
            old[obj.name] = {'mesh_sha256': cache[key], 'mesh': obj.data.name}

    # These audited ranges contain only mesh/material construction. The source
    # pipelines' file reads, subprocesses, downloads and saves are not included.
    ns = {'__builtins__': {'range': range, 'len': len, 'tuple': tuple, 'str': str, 'list': list},
          'bpy': bpy, 'bmesh': bmesh, 'math': math, 'random': random, 'Vector': Vector,
          'transform': None, 'geo': {}, 'prototypes': {}}
    def run(nodes):
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<reviewed-prototype-geometry>', 'exec'), ns)
    run(trees['work/street_detail/build.py'])
    ns['materials'] = {'bark': ns['mat']('Street tree textured bark', (.074, .053, .033), 0, .95)}
    run(trees['work/tokyo_traffic/build.py'])
    street = [{'species': species, 'variant': variant, 'vertices': len(mesh.vertices), 'polygons': len(mesh.polygons),
               'mesh_sha256': mesh_fingerprint(mesh)}
              for (species, variant), meshes in ns['prototypes'].items() for mesh in meshes]
    ns.update(r=random.Random(1560), prototypes=[])
    run(trees['work/tower15_env/build_environment.py'])
    shrubs = [{'variant': i, 'vertices': len(mesh.vertices), 'polygons': len(mesh.polygons),
               'mesh_sha256': mesh_fingerprint(mesh)} for i, mesh in enumerate(ns['prototypes'])]
    groups = []
    for prefix, protos, expected_count in [('Street tree ', street, 1314), ('Park shrub ', shrubs, 1333)]:
        rows = {name: row for name, row in old.items() if name.startswith(prefix)}
        require(len(rows) == expected_count, 'Unexpected saved prototype coverage')
        hashes = {p['mesh_sha256'] for p in protos}
        mismatches = sorted(name for name, row in rows.items() if row['mesh_sha256'] not in hashes)
        groups.append({'prefix': prefix, 'objects': len(rows), 'geometry_matches': len(rows) - len(mismatches),
                       'mismatches': mismatches, 'unique_saved_geometry': len({r['mesh_sha256'] for r in rows.values()}),
                       'prototypes': protos})
    result = {'version': 1, 'input_sha256': config['input']['sha256'], 'blender_version': bpy.app.version_string,
              'code_sha256_lf': {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                                  for path in [Path(__file__), ROOT / 'scripts/blender_worker.py']},
              'approved_code_ranges': APPROVED, 'groups': groups,
              'input_unchanged': sha(source) == config['input']['sha256'],
              'scope': 'Local mesh coordinates, topology, polygon material indices and UVs only. No placement, material nodes, modifiers or rights confirmation.'}
    result['ok'] = result['input_unchanged'] and all(not g['mismatches'] for g in groups)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, result)
    require(result['ok'], 'Prototype verification failed; see output report')
    print(json.dumps({'matched_mesh_objects': sum(g['geometry_matches'] for g in groups), 'input_unchanged': True}))


if __name__ == '__main__':
    main()
