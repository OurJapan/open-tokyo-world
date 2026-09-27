# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Prepare a pinned local plan closing millimetric gaps at the flat junction.

The input is the accepted PR 40 scene. Geometry stays in a new ignored local
directory. This does not expand the inherited paving beyond nearby road edges.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_mori_plaza_levels as levels
import mori_plaza_connection_v1 as connection
import mori_plaza_landscape_v1 as landscape


def gap_geometry(paving, roads, core):
    """Only the empty space within 1cm of both existing paved surfaces."""
    return paving.buffer(.01,join_style=2).intersection(roads.buffer(.01,join_style=2)).difference(
        paving.union(roads)).intersection(core)


def worker(args):
    import bpy
    levels.verify_input(args.input)
    if bpy.app.version_string!='4.5.1 LTS' or bpy.context.preferences.filepaths.use_scripts_auto_execute:
        raise ValueError('Use Blender 4.5.1 LTS without auto-execution')
    bpy.ops.wm.open_mainfile(filepath=str(args.input),use_scripts=False)
    bpy.context.scene.frame_set(1)
    shapes={}
    for name in sorted(connection.ROADS|{levels.PAVING}):
        obj=bpy.data.objects[name]
        shapes[name]=[]
        for face in obj.data.polygons:
            pts=[tuple(obj.matrix_world@obj.data.vertices[i].co) for i in face.vertices]
            if max(p[2] for p in pts)-min(p[2] for p in pts)>1e-6 or min(p[2] for p in pts)<.10:continue
            if connection.outline.overlaps(connection.outline.bounds(pts),connection.scope_bounds()):
                shapes[name].append([p[:2] for p in pts])
    levels.write_new(args.output/'surfaces.json',shapes)


def make_plan(shapes):
    import numpy as np
    import shapely as sh
    if (sys.version_info[:2]!=(3,12) or np.__version__!='2.3.5' or sh.__version__!='2.1.2' or sh.geos_version_string!='3.13.1'):
        raise ValueError('Use the pinned production environment')
    paving=sh.union_all([sh.Polygon(p) for p in shapes[levels.PAVING]])
    roads=sh.union_all([sh.Polygon(p) for name in connection.ROADS for p in shapes[name]])
    core=sh.Polygon(connection.cells()[0]).buffer(-.02,join_style=2)
    gap=gap_geometry(paving,roads,core)
    rounded=sh.make_valid(sh.transform(gap,lambda xy:xy.astype(np.float32).astype(np.float64)))
    def polygons(geometry):
        if geometry.geom_type=='Polygon':
            if geometry.area>1e-8:yield geometry
        elif hasattr(geometry,'geoms'):
            for part in geometry.geoms:yield from polygons(part)
    gap=sh.orient_polygons(sh.union_all(list(polygons(rounded))))
    if gap.is_empty or not gap.is_valid or gap.area>.5:raise ValueError('Unexpected seam fill area')
    rings=[]
    for polygon in sh.get_parts(gap):
        rings.extend([list(r.coords)[:-1] for r in [polygon.exterior,*polygon.interiors]])
    triangles=[]
    for triangle in sh.get_parts(sh.constrained_delaunay_triangles(gap)):
        points=list(triangle.exterior.coords)[:3]
        if connection.outline.signed_area(points)<0:points.reverse()
        triangles.append(points)
    plan={'version':1,'input_sha256':connection.INPUT_SHA256,'paving_triangles':triangles,'paving_rings':rings,
          'audit':{'fill_area_m2':gap.area,'maximum_distance_to_either_surface_m':.01,
                   'core_inset_m':.02,'overlap_existing_m2':gap.intersection(paving.union(roads)).area,
                   'height_m':.11,'basis':'Close inherited calculation gaps only; no surveyed geometry claimed.'}}
    connection.validate_plan(plan)
    return plan


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--blender',type=Path);p.add_argument('--worker',action='store_true')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    if args.worker:worker(args);return
    levels.verify_input(args.input)
    if not args.blender:raise ValueError('Supply Blender')
    args.output.mkdir(parents=True,exist_ok=False)
    result={'ok':False,'scene_saved':False,'input_sha256':connection.INPUT_SHA256}
    try:
        command=[str(args.blender.resolve()),'--factory-startup','--disable-autoexec','--background','--python-exit-code','1',
                 '--python',str(Path(__file__).resolve()),'--','--worker','--input',str(args.input.resolve()),'--output',str(args.output.resolve())]
        with (args.output/'export.log').open('w',encoding='utf-8') as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
        plan=make_plan(levels.read(args.output/'surfaces.json'))
        levels.write_new(args.output/'plan.json',plan)
        result.update(ok=True,plan_sha256=levels.digest(args.output/'plan.json'),audit=plan['audit'])
    finally:
        result['input_unchanged']=levels.digest(args.input)==connection.INPUT_SHA256
        result['ok']=result['ok'] and result['input_unchanged']
        result['code_sha256']={p.name:levels.digest(p) for p in [Path(__file__),Path(connection.__file__),Path(levels.__file__)]}
        levels.write_new(args.output/'run.json',result)
    if not result['ok']:raise ValueError('Preparation failed or changed source')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
