# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Read-only saved FootTown validation against the immutable PR59 candidate.

Saved geometry is inspected independently; the geometry producer is never run.
Bounds and clearances are model acceptance constraints, not surveyed dimensions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tower_foottown_v2 as detail
from validate_tower_structure import (BOUNDS as TOWER_BOUNDS, check_mesh,
    convex_intersects_box, digest, near, require, write)

ENVELOPE = ((-37, 37), (-37, 34), (0, 26))
CLEARANCES = {
    'roof lift shaft': ((-2.35, 2.35), (-2.35, 2.35), (16.0, 26)),
    'roof stair approach': ((-12, -4.8), (3.1, 5.7), (16.21, 18.5)),
    'roof stair doorway': ((-4.8, -3.96), (3.71, 5.09), (16.21, 18.29)),
}
FEATURES = Path(__file__).resolve().parents[1]/'areas/tokyo-tower/foottown-v2-features.json'


def check_clearances(parts, volumes):
    for label, box in volumes.items():
        for group, solids in parts.items():
            require(not any(convex_intersects_box(solid, box) for solid in solids),
                    'FootTown blocks '+label+': '+group)


def check_entries(parts):
    """Six framed door pairs, plus open approaches through the exterior walls.

    The 1.55 m pair is represented closed in this exterior model; glass and
    the centre seam are allowed inside its opening, opaque wall/fascia is not.
    """
    opaque = {group: solids for group, solids in parts.items()
              if group not in ('foottown-glazing', 'foottown-joints')}
    entries = [(x, 26.97, .02, 3.385, 'main') for x in (-16, -5.5, 5.5, 16)]
    entries += [(x, -28.885, 4.465, 7.015, 'south') for x in (-5, 5)]
    for x, y, low, high, label in entries:
        check_clearances(opaque, {label+' door opening': ((x-.77,x+.77), (y-.25,y+.25), (low+.01,high-.01))})
        for lo, hi in ((x-.775,x-.012), (x+.012,x+.775)):
            matches = [part for part in parts['foottown-glazing'] if part['cuboid'] and
                       all(near(a, b) for a, b in zip(part['bounds'][0], (lo,hi))) and
                       all(near(a, b) for a, b in zip(part['bounds'][2], (low,high))) and
                       near(part['center'][1], y) and near(part['size'][1], .025)]
            require(len(matches) == 1, 'Missing or duplicate FootTown '+label+' door leaf')
        if label == 'main':
            approach = ((x-.75,x+.75), (27.3,33.1), (.035,2.6))
        else:
            approach = ((x-.75,x+.75), (-31.2,-29.2), (4.5,6.5))
        check_clearances(parts, {label+' entrance approach': approach})
    return {'main_door_pairs': 4, 'south_door_pairs': 2, 'door_pair_width_m': 1.55,
            'door_state': 'closed static exterior geometry'}


def check_ground_connections(parts):
    """Check contacts with the measured local z=0 ground, without inferring terrain."""
    for group, rectangle, label in (
            ('foottown-shell', ((-36.5,36.5),(-29,29)), 'body floor'),
            ('foottown-roof', ((-28,28),(26.8,33.3)), 'main apron')):
        require(any(p['cuboid'] and near(p['bounds'][2][0], 0) and near(p['bounds'][2][1], .02) and
                    all(a <= c+3e-5 and b >= d-3e-5 for (a,b),(c,d) in zip(p['bounds'][:2],rectangle))
                    for p in parts[group]), 'FootTown '+label+' is not grounded at z=0 with floor top .02')
    for x in (-24,-8,8,24):
        columns = [p for p in parts['foottown-metal'] if p['cuboid'] and
                   near(p['center'][0],x) and near(p['center'][1],32.70) and
                   near(p['size'][0],.64) and near(p['size'][1],.66)]
        require(len(columns) == 1 and near(columns[0]['bounds'][2][0],0) and
                near(columns[0]['bounds'][2][1],7.25), 'FootTown main canopy column is not grounded')
    for x in (-7.3,0,7.3):
        for y, width, top in ((-31.6,.20,7.43),(-30.15,.22,4.30)):
            columns = [p for p in parts['foottown-metal'] if p['cuboid'] and
                       near(p['center'][0],x) and near(p['center'][1],y) and
                       near(p['size'][0],width) and near(p['size'][1],width)]
            require(len(columns) == 1 and near(columns[0]['bounds'][2][0],0) and
                    near(columns[0]['bounds'][2][1],top), 'FootTown south support column is not grounded')
    # Door leaves finish at the floor top. Their thin lower frames are recessed
    # into the floor and cannot become another step across the opening.
    for x in (-16,-5.5,5.5,16):
        frames = [p for p in parts['foottown-metal'] if p['cuboid'] and
                  near(p['center'][0],x) and near(p['center'][1],27.045) and
                  near(p['size'][0],4.27) and near(p['size'][1],.22) and p['bounds'][2][1] < 1]
        require(len(frames) == 1 and frames[0]['size'][2] <= .015+3e-5 and
                frames[0]['bounds'][2][0] >= -3e-5 and near(frames[0]['bounds'][2][1],.02),
                'FootTown main door threshold is raised above the grounded floor')
    # The south entry remains at 2F; these are open treads, not riser walls.
    for y in (-29.67,-31.13):
        bases = [p for p in parts['foottown-metal'] if p['cuboid'] and
                 near(p['center'][0],-14.2) and near(p['center'][1],y) and
                 near(p['size'][0],.22) and near(p['size'][1],.22)]
        require(len(bases) == 1 and near(bases[0]['bounds'][2][0],0) and
                near(bases[0]['bounds'][2][1],.06), 'FootTown south stair support base is not grounded')
    treads = sorted((p for p in parts['foottown-roof'] if p['cuboid'] and
                     near(p['center'][1],-30.4) and near(p['size'][1],1.4) and near(p['size'][2],.09)),
                    key=lambda p:p['bounds'][2][1])
    require(len(treads) == 25, 'FootTown south stair must have 25 treads')
    rise = (4.4-.02)/25
    for i,p in enumerate(treads):
        require(near(p['bounds'][2][1],.02+(i+1)*rise) and
                near(p['center'][0],-14.2+(i+.5)*6.2/25) and near(p['size'][0],6.2/25+.018),
                'FootTown south stair starts above ground or has a broken riser sequence')
    landings = [p for p in parts['foottown-roof'] if p['cuboid'] and
                near(p['center'][0],0) and near(p['center'][1],-30.2) and
                near(p['size'][0],16) and near(p['size'][1],2.4)]
    require(len(landings) == 1 and near(landings[0]['bounds'][2][1],4.4) and
            treads[-1]['bounds'][0][1] >= landings[0]['bounds'][0][0],
            'FootTown south stair does not meet its 2F landing')
    return {'ground_z_m':0, 'main_floor_top_m':.02, 'grounded_main_columns':4, 'grounded_south_columns':6,
            'main_door_threshold_max_m':.015, 'south_stair_treads':25,
            'grounded_south_stair_bases':2,
            'south_stair_start_floor_m':.02, 'south_first_tread_top_m':treads[0]['bounds'][2][1],
            'south_stair_riser_m':rise, 'south_landing_top_m':4.4}


def check_geometry(meshes, stairs=None):
    require(set(meshes) == set(detail.GROUPS), 'Saved FootTown mesh scope differs')
    stats, parts = {}, {}
    for group, mesh in meshes.items():
        stats[group], parts[group] = check_mesh(*mesh, ENVELOPE)
    check_clearances(parts, CLEARANCES)
    ground = check_ground_connections(parts)
    entries = check_entries(parts)
    roof = parts['foottown-roof']
    # Existing roof elevation and four quadrants around the shaft must survive.
    for x, y in ((-18, -14), (18, -14), (-18, 14), (18, 14)):
        require(any(p['bounds'][0][0] <= x <= p['bounds'][0][1] and
                    p['bounds'][1][0] <= y <= p['bounds'][1][1] and near(p['bounds'][2][1], 16.2)
                    for p in roof), 'FootTown roof is missing or at a different elevation')
    checked_stairs = 0
    if stairs is not None:
        _, treads = check_mesh(*stairs, TOWER_BOUNDS['stairs-treads'])
        volumes = {}
        for index, tread in enumerate(treads):
            floor = tread['bounds'][2][1]
            if floor > ENVELOPE[2][1]:
                continue
            # Exclude the walking surface itself. All FootTown solids must stay
            # outside the first roof flights and landing headroom.
            volumes['existing stair headroom '+str(index)] = (
                *tread['bounds'][:2], (floor+.10, floor+1.8))
        require(volumes, 'Missing existing roof stair walking surfaces')
        check_clearances(parts, volumes)
        checked_stairs = len(volumes)
    return {'meshes': stats, 'clearances': list(CLEARANCES),
            'existing_stair_headroom_surfaces': checked_stairs,
            'roof_elevation_m': 16.2, 'entries': entries, 'ground_connections': ground}


def json_value(value):
    if hasattr(value, 'to_dict'):
        value = value.to_dict()
    if hasattr(value, 'to_list'):
        value = value.to_list()
    if isinstance(value, dict):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(v) for v in value]
    if value is None or type(value) in (str, int, float, bool):
        return value
    # Blender ID custom properties are represented by stable type/name pairs.
    require(hasattr(value, 'name') and hasattr(value, 'bl_rna'), 'Unsupported saved custom property')
    return {'id_type': value.bl_rna.identifier, 'id_name': value.name}


def protected_metadata():
    import bpy
    from blender_worker import array_prop
    import numpy as np
    data, mesh_flags = {}, {}
    for obj in bpy.context.scene.objects:
        if obj.name in detail.CHANGED | detail.ADDED:
            continue
        entry = {'properties': {key: json_value(obj[key]) for key in obj.keys()},
                 'collections': sorted(c.name for c in obj.users_collection),
                 'hide_viewport': obj.hide_viewport, 'hide_local': obj.hide_get(),
                 'parent': obj.parent.name if obj.parent else None,
                 'modifiers': [(m.name, m.type) for m in obj.modifiers],
                 'constraints': [(c.name, c.type) for c in obj.constraints]}
        if obj.type == 'MESH':
            key = obj.data.as_pointer()
            if key not in mesh_flags:
                flags = hashlib.sha256()
                for collection, attribute in ((obj.data.polygons, 'use_smooth'), (obj.data.polygons, 'hide'),
                                               (obj.data.vertices, 'hide'), (obj.data.edges, 'hide')):
                    flags.update(array_prop(collection, attribute, 1, np.bool_).tobytes())
                mesh_flags[key] = flags.hexdigest()
            entry['mesh_flags_sha256'] = mesh_flags[key]
        data[obj.name] = entry
    collections = {c.name: {'properties': {key: json_value(c[key]) for key in c.keys()},
                           'children': sorted(child.name for child in c.children),
                           'hide_render': c.hide_render, 'hide_viewport': c.hide_viewport}
                   for c in bpy.data.collections if c.name != detail.COLLECTION}
    return {'objects': data, 'collections': collections}


def inspect(args):
    import bpy
    from blender_worker import mesh_fingerprint, material_fingerprint, validate
    from review import compare_reports
    require(bpy.app.version_string == '4.5.1 LTS', 'Use Blender 4.5.1 LTS')
    require(not bpy.context.preferences.filepaths.use_scripts_auto_execute, 'Disable Blender auto-execution')
    require(Path(bpy.data.filepath).resolve() == args.input.resolve(), 'Opened candidate differs')
    bpy.context.scene.frame_set(1)
    require(len(bpy.context.scene.objects) == detail.INPUT_OBJECTS+len(detail.ADDED), 'Candidate object count differs')
    collection = bpy.data.collections.get(detail.COLLECTION)
    require(collection is not None and collection.get('otw_feature_id') == detail.FEATURE and
            collection.get('otw_foottown_revision') == 'v2', 'Missing FootTown collection identity')
    require(not collection.hide_render and not collection.hide_viewport and
            {obj.name for obj in collection.all_objects} == detail.ADDED, 'FootTown collection scope or visibility differs')
    require({obj.name for obj in bpy.data.objects if obj.name.startswith(detail.PREFIX)} == detail.ADDED,
            'Unexpected FootTown additions')
    meshes, hashes, materials = {}, {}, {}
    for group in detail.GROUPS:
        name = detail.object_name(group)
        obj = bpy.data.objects.get(name)
        require(obj is not None and obj.type == 'MESH' and not obj.hide_render and not obj.hide_viewport and
                not obj.hide_get() and obj.visible_get(), 'FootTown object must be a visible mesh: '+name)
        old = group in detail.OLD_GROUPS
        require(obj.get('otw_feature_id') == detail.FEATURE and obj.get('otw_foottown_revision') == 'v2' and
                obj.get('otw_part_id') == ('tokyo-tower-structure-v1-' if old else 'tokyo-tower-foottown-v2-')+group,
                'FootTown object identity differs: '+name)
        require({c.name for c in obj.users_collection} == {detail.OLD_COLLECTION if old else detail.COLLECTION},
                'FootTown collection membership differs')
        require(not obj.modifiers and not obj.parent and not obj.constraints and not obj.animation_data,
                'Unsupported FootTown saved object state')
        require(all(abs(obj.matrix_world[r][c]-(r == c)) < 1e-7 for r in range(4) for c in range(4)),
                'Unexpected FootTown transform')
        require(obj.data.users == 1 and len(obj.data.materials) == 1 and obj.data.materials[0] is not None and
                all(p.material_index == 0 for p in obj.data.polygons), 'FootTown mesh or material must be single user')
        material = obj.data.materials[0]
        require(material.name == detail.MATERIAL_PREFIX+group and material.users == 1 and material.use_nodes,
                'FootTown must own its finish material')
        shader = material.node_tree.nodes.get('Principled BSDF')
        require(shader is not None and not shader.inputs['Alpha'].is_linked and near(shader.inputs['Alpha'].default_value, 1),
                'Invisible FootTown shader')
        if group == 'foottown-glazing':
            require(shader.inputs['Transmission Weight'].default_value >= .5, 'FootTown glazing is not transmissive')
        require(not any(v.hide for v in obj.data.vertices) and not any(p.hide for p in obj.data.polygons), 'Hidden FootTown mesh elements')
        meshes[group] = ([tuple(v.co) for v in obj.data.vertices], [list(p.vertices) for p in obj.data.polygons])
        hashes[name] = mesh_fingerprint(obj.data)
        materials[name] = material_fingerprint(material)
    stairs = bpy.data.objects[detail.OLD_PREFIX+'stairs-treads'].data
    result = check_geometry(meshes, ([tuple(v.co) for v in stairs.vertices], [list(p.vertices) for p in stairs.polygons]))
    features = json.loads(FEATURES.read_text(encoding='utf-8'))
    require(features['features'] == [] and features['waiver_input_sha256'] == detail.INPUT_SHA256,
            'FootTown features must preserve already-tagged input objects')
    candidate = validate({'features': features})
    metadata = protected_metadata()
    require(digest(args.original) == detail.INPUT_SHA256, 'Original is not the pinned PR59 input')
    bpy.ops.wm.open_mainfile(filepath=str(args.original), use_scripts=False)
    require(Path(bpy.data.filepath).resolve() == args.original.resolve() and
            not bpy.context.preferences.filepaths.use_scripts_auto_execute, 'Original read-only scene state differs')
    bpy.context.scene.frame_set(1)
    require(len(bpy.context.scene.objects) == detail.INPUT_OBJECTS, 'Original object count differs')
    for name, expected in detail.BASELINE_HASHES.items():
        obj = bpy.data.objects.get(name)
        require(obj is not None and mesh_fingerprint(obj.data) == expected, 'Original FootTown baseline differs')
    original = validate({'features': features})
    changed = compare_reports(original, candidate, detail.CHANGED, detail.ADDED)
    require(metadata == protected_metadata(), 'Protected object flags, metadata or collection state changed')
    result.update(ok=True, blender_version=bpy.app.version_string, frame=1, scene_saved=False,
                  autoexec_enabled=False, inspected_meshes=len(meshes), saved_mesh_sha256=hashes,
                  saved_material_sha256=materials, changed_objects=changed,
                  protected_existing_objects=detail.INPUT_OBJECTS-len(detail.CHANGED),
                  protected_metadata_and_flags_unchanged=True, original_assets_unchanged=True,
                  limitations=['Photo-guided model constraints do not certify real-world dimensions or engineering correctness.',
                               'Closed disconnected solids may meet or intersect at construction joints.',
                               'Existing mesh/material/assets use the review harness fingerprints; arbitrary animation and complete modifier state are not fingerprinted.'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', type=Path)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--original', type=Path, required=True, help='Immutable pinned PR59 candidate')
    parser.add_argument('--output', type=Path, required=True, help='New JSON report path')
    parser.add_argument('--timeout', type=int, default=900)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    require(not args.output.exists(), 'Refusing to overwrite validation report')
    if args.worker:
        report = {'ok': False}
        try:
            report = inspect(args)
        except Exception as error:
            report['error'] = str(error)
            raise
        finally:
            write(args.output, report)
        return
    require(args.blender is not None and args.timeout > 0, 'Specify Blender and a positive timeout')
    args.input, args.original, args.output = args.input.resolve(), args.original.resolve(), args.output.resolve()
    require(args.input != args.original, 'Candidate and original must differ')
    log = args.output.with_suffix('.log')
    require(not log.exists(), 'Refusing to overwrite validation log')
    input_hash, original_hash = digest(args.input), digest(args.original)
    require(original_hash == detail.INPUT_SHA256, 'Original is not the pinned PR59 input')
    dependencies = tuple(Path(__file__).with_name(name) for name in (
        'validate_tower_foottown.py', 'tower_foottown_v2.py', 'tower_foottown_geometry_v2.py',
        'tower_structure_v1.py', 'validate_tower_structure.py', 'blender_worker.py', 'review.py'))+(FEATURES,)
    code_hashes = {path.name: digest(path) for path in dependencies}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {'ok': False}
    try:
        command = [str(args.blender), '--factory-startup', '--disable-autoexec', '--background', str(args.input),
                   '--python-exit-code', '1', '--python', str(Path(__file__).resolve()), '--', '--worker',
                   '--input', str(args.input), '--original', str(args.original), '--output', str(args.output)]
        with log.open('x', encoding='utf-8') as stream:
            process = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=args.timeout, check=False)
        if args.output.exists():
            report = json.loads(args.output.read_text(encoding='utf-8'))
        require(process.returncode == 0 and report.get('ok') is True, report.get('error', 'Saved FootTown validation failed; inspect log'))
        require(digest(args.input) == input_hash and digest(args.original) == original_hash, 'Scene changed during validation')
        require(all(digest(path) == code_hashes[path.name] for path in dependencies), 'Validation code changed during inspection')
        report.update(input_unchanged=True, original_unchanged=True, code_unchanged=True)
    except Exception as error:
        report.update(ok=False, error=str(error))
        raise
    finally:
        report.update(input_sha256=input_hash, original_sha256=original_hash,
                      platform=platform.platform(), python_version=platform.python_version(), code_sha256=code_hashes)
        write(args.output, report)
    print('Saved FootTown validation complete: '+str(args.output))


if __name__ == '__main__':
    main()
