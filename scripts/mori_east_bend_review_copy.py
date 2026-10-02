# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Prepare separate review copies that open with the local context camera."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from tower_approach import read, write, digest


def geometry_signature():
    import bpy
    from blender_worker import mesh_fingerprint, material_fingerprint, packed_hash
    objects = {o.name:{'mesh':mesh_fingerprint(o.data), 'matrix':[list(r) for r in o.matrix_world],
                       'materials':[material_fingerprint(m) for m in o.data.materials],
                       'hide_render':o.hide_render, 'collections':sorted(c.name for c in o.users_collection)}
               for o in bpy.context.scene.objects if o.type=='MESH'}
    images = {i.name:packed_hash(i) for i in bpy.data.images if i.source=='FILE'}
    return hashlib.sha256(json.dumps({'objects':objects,'images':images},sort_keys=True).encode()).hexdigest()


def worker(args):
    import bpy
    from mathutils import Matrix
    out=args.output.resolve(); camera=read(out/'cameras.json')['views'][0]
    if bpy.app.version_string!='4.5.1 LTS' or bpy.context.preferences.filepaths.use_scripts_auto_execute:
        raise ValueError('Use pinned Blender without automatic scripts')
    if args.worker=='prepare':
        rows={}
        for stage in ('before','after'):
            source=out/(stage+'-neighborhood.blend'); target=out/(stage+'-review.blend')
            if target.exists():raise ValueError('Keep existing review copies')
            before_hash=digest(source)
            bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
            signature=geometry_signature(); scene=bpy.context.scene
            scene.timeline_markers.clear(); scene.frame_set(1)
            data=bpy.data.cameras.new('OTW local review camera')
            obj=bpy.data.objects.new('OTW local review camera',data);scene.collection.objects.link(obj)
            obj.matrix_world=Matrix(camera['matrix_world']);scene.camera=obj
            for field,key in [('lens','lens_mm'),('sensor_width','sensor_width_mm'),('sensor_height','sensor_height_mm'),
                              ('sensor_fit','sensor_fit'),('shift_x','shift_x'),('shift_y','shift_y'),
                              ('clip_start','clip_start'),('clip_end','clip_end')]:
                setattr(data,field,camera[key])
            scene.render.resolution_x=960;scene.render.resolution_y=540;scene.render.resolution_percentage=100
            for screen in bpy.data.screens:
                for area in screen.areas:
                    for space in area.spaces:
                        if space.type=='VIEW_3D':
                            space.region_3d.view_perspective='CAMERA'
                            space.region_3d.view_camera_zoom=0
                            space.clip_end=600
            bpy.ops.wm.save_as_mainfile(filepath=str(target),check_existing=False)
            if digest(source)!=before_hash or geometry_signature()!=signature:
                raise ValueError('Review-copy source or geometry changed')
            rows[stage]={'source_sha256':before_hash,'saved_sha256':digest(target),'geometry_assets_signature':signature,
                         'camera':obj.name,'saved':target.name}
        write(out/'review-copy-prepare.json',{'ok':True,'rows':rows})
    else:
        previous=read(out/'review-copy-prepare.json')
        for stage,row in previous['rows'].items():
            target=out/row['saved']
            bpy.ops.wm.open_mainfile(filepath=str(target),use_scripts=False)
            if digest(target)!=row['saved_sha256'] or geometry_signature()!=row['geometry_assets_signature']:
                raise ValueError('Saved review-copy geometry differs')
            actual=bpy.context.scene.camera
            if actual.name!=row['camera'] or max(abs(actual.matrix_world[r][c]-camera['matrix_world'][r][c]) for r in range(4) for c in range(4))>1e-6:
                raise ValueError('Local camera differs')
        write(out/'review-copy-check.json',{'ok':True,'fresh_process_reopen':True,'rows':previous['rows'],
                                           'script_sha256':digest(Path(__file__))})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--blender',type=Path)
    p.add_argument('--worker',choices=('prepare','check'))
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    if a.worker:return worker(a)
    if not a.blender:p.error('--blender required')
    for phase in ('prepare','check'):
        cmd=[str(a.blender),'--factory-startup','--disable-autoexec','--background','--threads','2',
             '--python-exit-code','1','--python',str(Path(__file__).resolve()),'--',
             '--output',str(a.output.resolve()),'--worker',phase]
        with (a.output/('review-copy-'+phase+'.log')).open('w',encoding='utf-8') as log:
            subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    print(json.dumps({'ok':True,'report':str(a.output/'review-copy-check.json')}))


if __name__=='__main__':main()
