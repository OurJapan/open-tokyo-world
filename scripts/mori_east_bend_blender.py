# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Isolated full-city increment and disposable bounded neighborhood review."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from blender_worker import array_prop, mesh_fingerprint, render
from tower_approach_blender import extended_validate
from city_catalog_blender import enabled_meshes
import mori_plaza_east_bend_v1 as bend


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def snapshot(job):
    result = extended_validate(job, False)
    result['scene_properties'] = {k: bpy.context.scene[k] for k in bpy.context.scene.keys()
                                  if isinstance(bpy.context.scene[k], (str, int, float, bool))}
    result['text_hashes'] = {t.name: hashlib.sha256(t.as_string().encode()).hexdigest() for t in bpy.data.texts}
    return result


def build(job):
    if bend.digest(job['input']) != bend.INPUT_SHA256:
        raise ValueError('Pinned city differs')
    if bend.digest(job['plan']) != job['patch']['plan_sha256']:
        raise ValueError('Pinned infill plan differs')
    if bend.AUDIT_KEY in bpy.context.scene:
        raise ValueError('Already applied')
    before = snapshot(job)
    if not before['ok']:
        raise ValueError('Invalid input: '+str(before['errors']))
    out = Path(job['output'])
    write(out/'validate-before.json', before)
    audit = bend.apply(job['patch'], mesh_fingerprint, job['road_inputs'], job['plan'])
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'after.blend'), check_existing=False)
    return {'ok': True, 'audit': audit, 'saved': str(out/'after.blend')}


def camera(ident, eye, target, lens=42):
    e = Vector(bend.world(*eye)); t = Vector(bend.world(*target))
    matrix = (t-e).to_track_quat('-Z', 'Y').to_matrix().to_4x4()
    matrix.translation = e
    return {'id': ident, 'frame': 1, 'matrix_world': [list(r) for r in matrix],
            'lens_mm': lens, 'sensor_width_mm': 36, 'sensor_height_mm': 24,
            'sensor_fit': 'HORIZONTAL', 'shift_x': 0, 'shift_y': 0,
            'clip_start': .03, 'clip_end': 600}


def neighborhood(job, stage):
    """Temporary review extraction; never saved over the complete candidate."""
    center = bend.world(*bend.CENTER)[:2]
    radius = 95.
    extent = (center[0]-radius, center[1]-radius, center[0]+radius, center[1]+radius)
    visible = enabled_meshes()
    removed, cropped = [], {}
    for obj in list(bpy.context.scene.objects):
        if obj.type in ('CAMERA', 'LIGHT'):
            continue
        if obj.type != 'MESH' or obj.name not in visible:
            removed.append(obj.name); bpy.data.objects.remove(obj, do_unlink=True); continue
        box = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
        bounds = (min(p.x for p in box), min(p.y for p in box), max(p.x for p in box), max(p.y for p in box))
        if not bend.outline.overlaps(bounds, extent):
            removed.append(obj.name); bpy.data.objects.remove(obj, do_unlink=True); continue
        if bounds[0] >= extent[0] and bounds[1] >= extent[1] and bounds[2] <= extent[2] and bounds[3] <= extent[3]:
            continue
        mesh = obj.data
        if not len(mesh.polygons):
            continue
        local = array_prop(mesh.vertices, 'co', 3, np.float64).reshape(-1, 3)
        matrix = np.array(obj.matrix_world, dtype=np.float64)
        xy = (local @ matrix[:3, :3].T + matrix[:3, 3])[:, :2]
        ids = array_prop(mesh.loops, 'vertex_index', 1, np.int32)
        starts = array_prop(mesh.polygons, 'loop_start', 1, np.int32)
        lower, upper = np.minimum.reduceat(xy[ids], starts), np.maximum.reduceat(xy[ids], starts)
        keep = ((lower[:, 0] <= extent[2]) & (lower[:, 1] <= extent[3]) &
                (upper[:, 0] >= extent[0]) & (upper[:, 1] >= extent[1]))
        if keep.all():
            continue
        if not keep.any():
            removed.append(obj.name); bpy.data.objects.remove(obj, do_unlink=True); continue
        obj.data = mesh.copy()
        bm = bmesh.new(); bm.from_mesh(obj.data); bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.faces[int(i)] for i in np.flatnonzero(~keep)], context='FACES')
        bm.to_mesh(obj.data); bm.free(); obj.data.update()
        cropped[obj.name] = {'before_faces': len(mesh.polygons), 'after_faces': len(obj.data.polygons)}
    job['cameras'] = {'views': [
        camera('context', (9, 69, 18), (-8, 85, 0), 42),
        camera('walk', (-8, 77, 1.7), (-8, 87, .30), 34),
        camera('edge', (-2, 85, 1.20), (-6.5, 85, .12), 48),
        camera('reverse', (-10, 94, 2.7), (-8, 85, .12), 40)]}
    bpy.context.scene['otw_review_extraction'] = '190m XY neighborhood; source objects outside excluded; full candidate is after.blend'
    out = Path(job['output'])
    write(out/'cameras.json', job['cameras'])
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(stage+'-neighborhood.blend')), check_existing=False)
    result = render(job, 'render-'+stage)
    result['extraction'] = {'bounds_xy_m': extent, 'excluded_objects': len(removed), 'cropped': cropped,
                            'retained_objects': len(bpy.context.scene.objects), 'scope': 'Neighborhood review, not full-city render'}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--phase', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    job = read(args.job)
    if bpy.app.version_string != '4.5.1 LTS' or bpy.context.preferences.filepaths.use_scripts_auto_execute:
        raise ValueError('Use pinned Blender 4.5.1 LTS without auto-execution')
    bpy.context.scene.frame_set(1)
    if args.phase == 'build':
        result = build(job)
    elif args.phase == 'validate-after':
        result = snapshot(job)
    elif args.phase in ('render-before', 'render-after'):
        result = neighborhood(job, args.phase.removeprefix('render-'))
    elif args.phase == 'duplicate':
        try:
            bend.apply(job['patch'], mesh_fingerprint, job['road_inputs'], job['plan'])
        except ValueError as exc:
            result = {'ok': 'already applied' in str(exc), 'refused': str(exc), 'saved': False}
        else:
            raise ValueError('Duplicate increment accepted')
    else:
        raise ValueError('Unknown phase')
    write(args.report, result)
    if not result['ok']:
        raise ValueError('Phase failed: '+str(result.get('errors')))


if __name__ == '__main__':
    main()
