# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Prepare bounded thin infill from the adopted northeast footway bend surfaces."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_mori_plaza_levels as levels
import mori_plaza_east_bend_v1 as path
from prepare_mori_plaza_connection import gap_geometry


def verify_input(file):
    if levels.digest(file) != path.INPUT_SHA256:
        raise ValueError('Expected the preserved PR51 + PR47 city')


def worker(args):
    import bpy
    verify_input(args.input)
    if bpy.app.version_string != '4.5.1 LTS' or bpy.context.preferences.filepaths.use_scripts_auto_execute:
        raise ValueError('Use Blender 4.5.1 LTS without automatic scripts')
    bpy.ops.wm.open_mainfile(filepath=str(args.input), use_scripts=False)
    bpy.context.scene.frame_set(1)
    surfaces = {}
    for name in sorted(path.ROADS | {levels.PAVING, path.previous.SEAM}):
        obj = bpy.data.objects[name]
        surfaces[name] = []
        for face in obj.data.polygons:
            if abs(face.normal.z) < 1e-4:
                continue
            points = [tuple(obj.matrix_world @ obj.data.vertices[index].co) for index in face.vertices]
            if min(p[2] for p in points) < .10 or abs(path.outline.signed_area(points)) <= 1e-8:
                continue
            if path.outline.overlaps(path.outline.bounds(points), path.scope_bounds()):
                surfaces[name].append([p[:2] for p in points])
    levels.write_new(args.output / 'surfaces.json', surfaces)


def make_plan(surfaces):
    import numpy as np
    import shapely as sh
    if sys.version_info[:2] != (3, 12) or np.__version__ != '2.3.5' or sh.__version__ != '2.1.2' or sh.geos_version_string != '3.13.1':
        raise ValueError('Use the existing pinned production environment')
    paving = sh.union_all([sh.Polygon(p) for p in surfaces[levels.PAVING]])
    roads = sh.union_all([sh.Polygon(p) for name in path.ROADS for p in surfaces[name]])
    old_fill = sh.union_all([sh.Polygon(p) for p in surfaces[path.previous.SEAM]])
    # Include the adopted seam as existing paving; it must never be duplicated.
    existing = paving.union(old_fill)
    core = sh.Polygon(path.cells()[0]).buffer(-.001, join_style=2)
    gap = gap_geometry(existing, roads, core)
    # Preserve the adopted seam and meet the road boundary without a clearance
    # strip. Round in the added object's small local coordinates, not world XY.
    gap = gap.difference(old_fill.buffer(.0001, join_style=2))
    origin = np.array(path.SEAM_ORIGIN[:2], dtype=np.float64)
    rounded = sh.make_valid(sh.transform(gap, lambda xy: (xy - origin).astype(np.float32).astype(np.float64) + origin))
    def polygons(geometry):
        if geometry.geom_type == 'Polygon':
            if geometry.area > 1e-8:
                yield geometry
        elif hasattr(geometry, 'geoms'):
            for part in geometry.geoms:
                yield from polygons(part)
    gap = sh.orient_polygons(sh.union_all(list(polygons(rounded))))
    if gap.is_empty or not gap.is_valid or gap.area > .5:
        raise ValueError('Unexpected east bend seam area')
    rings = [list(ring.coords)[:-1] for poly in sh.get_parts(gap) for ring in [poly.exterior, *poly.interiors]]
    triangles = []
    for triangle in sh.get_parts(sh.constrained_delaunay_triangles(gap)):
        points = list(triangle.exterior.coords)[:3]
        if path.outline.signed_area(points) < 0:
            points.reverse()
        triangles.append(points)
    plan = {'version': 1, 'input_sha256': path.INPUT_SHA256, 'paving_triangles': triangles, 'paving_rings': rings,
            'audit': {'fill_area_m2': gap.area, 'maximum_distance_to_either_surface_m': .01,
                      'core_inset_m': .001, 'overlap_existing_m2': gap.intersection(existing.union(roads)).area,
                      'road_edge_clearance_m': 0., 'adopted_seam_clearance_m': .0001,
                      'mesh_origin_m': path.SEAM_ORIGIN,
                      'overlap_adopted_seam_m2': gap.intersection(old_fill).area, 'height_m': .11,
                      'basis': 'Inherited millimetric calculation gaps inside the new flat core only; no surveyed geometry.'}}
    path.validate_plan(plan)
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--blender', type=Path)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    if args.worker:
        worker(args)
        return
    verify_input(args.input)
    if not args.blender:
        parser.error('--blender is required')
    args.output.mkdir(parents=True, exist_ok=False)
    result = {'ok': False, 'scene_saved': False, 'input_sha256': path.INPUT_SHA256}
    try:
        command = [str(args.blender), '--factory-startup', '--background', '--disable-autoexec', '--python-exit-code', '1',
                   '--python', str(Path(__file__).resolve()), '--', '--worker', '--input', str(args.input.resolve()),
                   '--output', str(args.output.resolve())]
        with (args.output / 'blender.log').open('w', encoding='utf-8') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=600, check=True)
        plan = make_plan(levels.read(args.output / 'surfaces.json'))
        levels.write_new(args.output / 'plan.json', plan)
        result.update(ok=True, plan_sha256=levels.digest(args.output / 'plan.json'),
                      surfaces_sha256=levels.digest(args.output / 'surfaces.json'), audit=plan['audit'])
    finally:
        result['input_unchanged'] = levels.digest(args.input) == path.INPUT_SHA256
        result['ok'] = result['ok'] and result['input_unchanged']
        result['code_sha256'] = {p.name: levels.digest(p) for p in [Path(__file__), Path(path.__file__)]}
        levels.write_new(args.output / 'run.json', result)
    if not result['ok']:
        raise ValueError('Seam preparation failed or changed source')
    print(json.dumps({'ok': result['ok'], 'plan_sha256': result['plan_sha256'], 'audit': result['audit']}))


if __name__ == '__main__':
    main()
