# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Prepare or verify a local, unlicensed review candidate of 16 prototypes and 31 materials.

Use Blender --factory-startup --disable-autoexec --background FILE --python-exit-code 1
--python scripts/prepare_procedural_candidate.py -- build --report REPORT --output NEW_DIR
or -- verify --output DIR [--render]. Build reads the pinned city; verify reads kit.blend.
This does not publish a package or grant redistribution rights.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from blender_worker import mesh_fingerprint
from component_contracts import material_snapshot, signature
from workspace import digest, read_json, write_json
from verify_city_components import CITY


def requirements():
    groups = read_json(ROOT / 'sources/city-pr12-production-audit.json')['prototype_verification']['groups']
    result = []
    for group in groups:
        for p in group['prototypes']:
            if group['prefix'] == 'Street tree ':
                part = 'bark' if p['vertices'] == 592 else 'foliage'
                key = f"{p['species']}-{p['variant']}-{part}"
                location = ((p['variant'] - 1) * 10, 12 if p['species'] == 'zelkova' else 0, 0)
            else:
                key = f"shrub-{p['variant']}"
                location = ((p['variant'] - 1.5) * 5, -9, 1.25)
            result.append({'id': key, 'mesh_sha256': p['mesh_sha256'], 'location': list(location)})
    if len(result) != 16 or len({r['mesh_sha256'] for r in result}) != 16:
        raise ValueError('Unexpected prototype evidence')
    return result


def build(args):
    import bpy
    from mathutils import Vector
    source = Path(bpy.data.filepath)
    if args.output.exists() or digest(source) != CITY:
        raise ValueError('Use the pinned city and a new output directory')
    evidence = read_json(args.report)
    if not (evidence['ok'] and evidence['city_sha256'] == CITY and evidence['matched_objects'] == 29
            and evidence['matched_materials'] == 31 and evidence['matched_assignments'] == 2676):
        raise ValueError('Successful component verification is required')
    for name, pin in evidence['code_sha256_lf'].items():
        if hashlib.sha256((ROOT / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != pin:
            raise ValueError('Component verification code changed')
    plan = requirements()
    wanted = {r['mesh_sha256'] for r in plan}
    found, checked = {}, set()
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not obj.name.startswith(('Street tree ', 'Park shrub ')):
            continue
        if obj.data.as_pointer() in checked:
            continue
        checked.add(obj.data.as_pointer())
        pin = mesh_fingerprint(obj.data)
        if pin in wanted:
            found[pin] = obj.data.name
    if set(found) != wanted:
        raise ValueError('Missing verified prototype')
    material_names = sorted(evidence['material_signatures'])
    for name in material_names:
        if signature(material_snapshot(bpy.data.materials[name])) != evidence['material_signatures'][name]['baseline']:
            raise ValueError('Material differs: ' + name)
    for row in plan:
        row['source_mesh_name'] = found[row['mesh_sha256']]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(source), link=False) as (data_from, data_to):
        data_to.meshes = [r['source_mesh_name'] for r in plan]
        data_to.materials = list(material_names)
    scene = bpy.context.scene
    for row in plan:
        mesh = bpy.data.meshes[row['source_mesh_name']]
        if mesh_fingerprint(mesh) != row['mesh_sha256'] or mesh.shape_keys or mesh.has_custom_normals:
            raise ValueError('Appended geometry changed')
        obj = bpy.data.objects.new(row['id'], mesh); scene.collection.objects.link(obj)
        obj.location = row['location']; obj['candidate_scope'] = 'prototype-only; license decision pending'
        row['materials'] = [m.name for m in mesh.materials]
    if set(m.name for m in bpy.data.materials) != set(material_names):
        raise ValueError('Unexpected material data in isolated candidate')
    for m in bpy.data.materials:
        m.use_fake_user = True
    # Append may retain a source-library bookkeeping entry even though the
    # meshes and shaders are local. Reject linked data before removing it.
    for collection in (bpy.data.meshes, bpy.data.materials, bpy.data.node_groups, bpy.data.objects):
        if any(item.library for item in collection):
            raise ValueError('Candidate still contains linked data')
    source_library_entries_removed = len(bpy.data.libraries)
    for library in list(bpy.data.libraries):
        bpy.data.libraries.remove(library)
    if bpy.data.images or bpy.data.texts or bpy.data.libraries:
        raise ValueError('Unexpected dependency: ' + json.dumps({
            'images': [(i.name, i.type, i.source, i.users) for i in bpy.data.images],
            'texts': list(bpy.data.texts.keys()),
            'libraries': [(lib.name, lib.users) for lib in bpy.data.libraries]}))

    world = bpy.data.worlds.new('Candidate studio'); world.use_nodes = True
    world.node_tree.nodes.get('Background').inputs['Color'].default_value = (.62, .69, .8, 1)
    world.node_tree.nodes.get('Background').inputs['Strength'].default_value = .65
    scene.world = world
    for name, location, energy, size in [('Key', (1, -8, 25), 3200, 20), ('Fill', (-20, -3, 16), 2200, 18),
                                          ('Rim', (3, 22, 25), 3000, 18)]:
        light = bpy.data.lights.new(name, 'AREA'); light.energy = energy; light.shape = 'DISK'; light.size = size
        obj = bpy.data.objects.new(name, light); scene.collection.objects.link(obj); obj.location = location
        obj.rotation_euler = (Vector((0, 5, 4)) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    camera = bpy.data.cameras.new('Preview camera'); camera.type = 'ORTHO'; camera.ortho_scale = 40
    obj = bpy.data.objects.new('Preview camera', camera); scene.collection.objects.link(obj)
    obj.location = (22, -38, 26); obj.rotation_euler = (Vector((0, 4, 3)) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = obj; scene.render.engine = 'CYCLES'; scene.cycles.samples = 24
    scene.cycles.use_denoising = True; scene.cycles.device = 'CPU'; scene.cycles.seed = 0
    scene.render.resolution_x = 1200; scene.render.resolution_y = 850; scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'; scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = True
    scene['distribution_status'] = 'local-review-only; license decision pending'
    scene['scope'] = '16 local-coordinate prototypes and 31 procedural materials; new preview layout, no city coordinates'
    args.output.mkdir(parents=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output / 'kit.blend'), compress=True)
    record = {'version': 1, 'status': 'local-review-license-decision-pending', 'new_license_grant': None,
              'source_city_sha256': CITY, 'source_unchanged': digest(source) == CITY,
              'component_report_sha256': digest(args.report), 'blender_version': bpy.app.version_string,
              'source_library_entries_removed': source_library_entries_removed,
              'prototype_meshes': plan, 'material_signatures': {n: evidence['material_signatures'][n]['baseline'] for n in material_names},
              'preview_only_objects': ['Preview camera', 'Key', 'Fill', 'Rim'],
              'excluded': ['city layout/coordinates', 'OSM and PLATEAU data', 'aggregated mapped geometry',
                           'building imagery', 'legacy source code', 'legacy embedded scripts'],
              'file': {'path': 'kit.blend', 'bytes': (args.output / 'kit.blend').stat().st_size,
                       'sha256': digest(args.output / 'kit.blend')},
              'builder_sha256_lf': hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()}
    write_json(args.output / 'candidate.json', record)
    (args.output / 'README.txt').write_text(
        'Local review candidate. No redistribution license has been granted for these assets yet.\n'
        'Contains 16 verified tree/shrub prototype meshes and 31 procedural materials.\n'
        'The demonstration layout is new; original city placement and legacy source code are excluded.\n', encoding='utf8')
    print(json.dumps({'candidate': str(args.output / 'kit.blend'), 'bytes': record['file']['bytes']}), flush=True)


def verify(args):
    import bpy
    if (args.output / 'verification.json').exists():
        raise ValueError('Verification output already exists')
    record = read_json(args.output / 'candidate.json')
    scene_file = Path(bpy.data.filepath)
    if digest(scene_file) != record['file']['sha256'] or scene_file.resolve() != (args.output / 'kit.blend').resolve():
        raise ValueError('Unexpected candidate file')
    actual = {o.name: o for o in bpy.context.scene.objects if o.type == 'MESH'}
    if set(actual) != {r['id'] for r in record['prototype_meshes']} or len(bpy.data.meshes) != 16:
        raise ValueError('Unexpected candidate mesh coverage')
    if set(bpy.data.objects.keys()) != set(actual) | set(record['preview_only_objects']):
        raise ValueError('Unexpected object outside the preview/prototype scope')
    for row in record['prototype_meshes']:
        o = actual[row['id']]
        if (mesh_fingerprint(o.data) != row['mesh_sha256'] or list(o.location) != row['location']
                or [m.name for m in o.data.materials] != row['materials'] or o.modifiers or o.parent or o.constraints
                or o.animation_data or o.data.shape_keys or o.data.has_custom_normals):
            raise ValueError('Prototype changed: ' + row['id'])
    if set(m.name for m in bpy.data.materials) != set(record['material_signatures']):
        raise ValueError('Unexpected material coverage')
    for name, pin in record['material_signatures'].items():
        if signature(material_snapshot(bpy.data.materials[name])) != pin:
            raise ValueError('Saved material differs: ' + name)
    if bpy.data.images or bpy.data.libraries or bpy.data.texts:
        raise ValueError('Unexpected dependency or embedded content')
    result = {'ok': True, 'mesh_prototypes': 16, 'procedural_materials': 31,
              'images': 0, 'libraries': 0, 'embedded_texts': 0, 'candidate_sha256': record['file']['sha256']}
    if args.render:
        import numpy as np
        preview = args.output / 'preview.png'
        if preview.exists():
            raise ValueError('Preview already exists')
        bpy.context.scene.render.filepath = str(preview)
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(str(preview), check_existing=False)
        pixels = np.empty(len(image.pixels), dtype=np.float32); image.pixels.foreach_get(pixels)
        if tuple(image.size) != (1200, 850) or not np.isfinite(pixels).all() or np.max(pixels.reshape(-1, 4)[:, 3]) == 0:
            raise ValueError('Invalid preview')
        result['preview'] = {'path': 'preview.png', 'bytes': preview.stat().st_size, 'sha256': digest(preview)}
    result['file_unchanged'] = digest(scene_file) == record['file']['sha256']
    if not result['file_unchanged']:
        raise ValueError('Candidate file changed during verification')
    write_json(args.output / 'verification.json', result)
    print(json.dumps(result), flush=True)


def main():
    import bpy
    if bpy.app.version_string != '4.5.1 LTS' or bpy.context.preferences.filepaths.use_scripts_auto_execute:
        raise ValueError('Use Blender 4.5.1 with auto-execution disabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['build', 'verify'])
    parser.add_argument('--report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--render', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    args.output = args.output.resolve()
    if args.mode == 'build':
        if not args.report: parser.error('build requires --report')
        build(args)
    else:
        verify(args)


if __name__ == '__main__':
    main()
