# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Independent saved-scene checks for the bounded entrance junction repair.

Use the pinned production Python for planar geometry checks. All exports and
coordinates remain local. Neither saved scene is modified.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_mori_plaza_levels as levels
import mori_plaza_connection_v1 as connection
from validate_mori_plaza_outline import digest, read, write

PRIORITY = [(-21.864186737978322,50.2447274376262),(-22.75472606452176,49.80043092724036)]


def expected_height(u,v,z):
    scale=min(1.,max(0.,(max(abs(u+22),abs(v-50))-4)/4))
    return .11+(z-.11)*scale


def worker(args):
    import bpy
    import numpy as np
    from mathutils import Vector
    if bpy.app.version_string != '4.5.1 LTS' or bpy.context.preferences.filepaths.use_scripts_auto_execute:
        raise ValueError('Use Blender 4.5.1 LTS without auto-execution')
    samples=[]
    for stage,path in [('before',args.before),('after',args.after)]:
        bpy.ops.wm.open_mainfile(filepath=str(path),use_scripts=False)
        bpy.context.scene.frame_set(1)
        for i,name in enumerate(sorted(connection.ROADS)):
            mesh=bpy.data.objects[name].data
            arrays={}
            for key, collection, prop, width, dtype in [
                ('vertices',mesh.vertices,'co',3,np.float32),('indices',mesh.loops,'vertex_index',1,np.int32),
                ('starts',mesh.polygons,'loop_start',1,np.int32),('counts',mesh.polygons,'loop_total',1,np.int32),
                ('material',mesh.polygons,'material_index',1,np.int32),('smooth',mesh.polygons,'use_smooth',1,np.bool_),
                ('areas',mesh.polygons,'area',1,np.float64)]:
                values=np.empty(len(collection)*width,dtype=dtype);collection.foreach_get(prop,values)
                arrays[key]=values.reshape(-1,3) if key=='vertices' else values
            np.savez_compressed(args.output/f'{stage}-{i}.npz',**arrays)
        if stage=='before':
            obj=bpy.data.objects[levels.PAVING]
            vertices=[tuple(obj.matrix_world@v.co) for v in obj.data.vertices]
            _,edges=levels.top_boundary(vertices,[list(f.vertices) for f in obj.data.polygons])
            boundary=list(levels.boundary_samples(vertices,edges))
            paving_tops=[[vertices[i][:2] for i in f.vertices] for f in obj.data.polygons
                         if all(abs(vertices[i][2]-.11)<1e-6 for i in f.vertices)]
            write(args.output/'before-paving-tops.json',paving_tops)
            for index,sample in enumerate(boundary):
                for side in (-1,1):
                    xy=[sample['xy'][k]+side*.02*sample['normal_xy'][k] for k in (0,1)]
                    samples.append({'kind':'boundary','pair':index,'side':side,'xy':xy})
            for index,uv in enumerate(PRIORITY):
                sample=min(boundary,key=lambda s:math.dist(levels.local_uv(*s['xy']),uv))
                if math.dist(levels.local_uv(*sample['xy']),uv)>1e-6:raise ValueError('Priority probe moved')
                for offset in [i*.002 for i in range(-15,16)]:
                    xy=[sample['xy'][k]+offset*sample['normal_xy'][k] for k in (0,1)]
                    samples.append({'kind':'priority-seam','pair':index,'offset':offset,'xy':xy})
            for i in range(37):
                for j in range(37):
                    uv=(-31+i*.5,41+j*.5)
                    samples.append({'kind':'grid','xy':connection.world(*uv)[:2]})
            for u in (-3.25,.25,3.25):
                for v in (21.99,22.01,31.99,32.01):
                    samples.append({'kind':'entry','xy':connection.world(u,v)[:2]})
        dg=bpy.context.evaluated_depsgraph_get()
        def cast(xy,height=2):
            origin=Vector((*xy,height))
            for _ in range(24):
                hit,point,normal,index,obj,matrix=bpy.context.scene.ray_cast(dg,origin,Vector((0,0,-1)),distance=origin.z+2)
                if not hit:return {'object':None,'z':None}
                if not obj.hide_render:return {'object':obj.name,'z':float(point.z)}
                origin=point-Vector((0,0,.0005))
            raise ValueError('Too many hidden ray hits')
        rays=[]
        for sample in samples:
            row={**sample,'uv':levels.local_uv(*sample['xy']),**cast(sample['xy'])}
            if sample['kind']=='grid' and max(abs(row['uv'][0]+22),abs(row['uv'][1]-50))<4:
                row['overhead']=cast(sample['xy'],70)
            rays.append(row)
        write(args.output/f'{stage}-rays.json',rays)
        if stage=='after':
            write(args.output/'saved-patch-audit.json',json.loads(bpy.context.scene['otw_plaza_connection_audit']))
            mesh=bpy.data.objects[connection.SEAM].data
            write(args.output/'seam-mesh.json',{'vertices':[list(v.co) for v in mesh.vertices],
                                               'faces':[list(f.vertices) for f in mesh.polygons]})
    write(args.output/'export.json',{'ok':True,'scene_saved':False,'blender_version':bpy.app.version_string})


def geometry_audit(args):
    import numpy as np
    import shapely as sh
    if (sys.version_info[:2]!=(3,12) or np.__version__!='2.3.5' or sh.__version__!='2.1.2' or sh.geos_version_string!='3.13.1'):
        raise ValueError('Use pinned Python 3.12 / NumPy 2.3.5 / Shapely 2.1.2 / GEOS 3.13.1')
    mask=sh.Polygon([connection.world(u,v)[:2] for u,v in [(-30,42),(-14,42),(-14,58),(-30,58)]])
    extent=mask.bounds
    def load(stage,i):
        with np.load(args.output/f'{stage}-{i}.npz',allow_pickle=False) as f:return {k:f[k] for k in f.files}
    def faces(data):
        for i,(start,count) in enumerate(zip(data['starts'],data['counts'])):
            ids=data['indices'][start:start+count]
            yield i,ids,(tuple(int(x) for x in ids),int(data['material'][i]),bool(data['smooth'][i]))
    checks={};before_road_tops=[]
    for idx,name in enumerate(sorted(connection.ROADS)):
        before,after=load('before',idx),load('after',idx)
        if not np.array_equal(before['vertices'],after['vertices'][:len(before['vertices'])]):
            raise ValueError('Original road vertices moved')
        old_faces=Counter(key for _,_,key in faces(before))
        new_faces=Counter(key for _,_,key in faces(after))
        required=Counter();tops={};max_error=0.;new_top_count=0
        for stage,data in [('before',before),('after',after)]:
            polygons=[]
            for i,ids,key in faces(data):
                poly=data['vertices'][ids].astype(np.float64)
                b=(*poly[:,:2].min(axis=0),*poly[:,:2].max(axis=0))
                if not connection.outline.overlaps(b,extent):
                    if stage=='before':required[key]+=1
                    elif key not in old_faces:raise ValueError('New face outside correction extent')
                    continue
                xy=sh.Polygon(poly[:,:2]);horizontal=float(np.ptp(poly[:,2]))<1e-6
                if stage=='before':
                    geom=xy if xy.area>1e-9 else sh.MultiPoint(poly[:,:2]).convex_hull
                    if geom.intersection(mask).is_empty or geom.intersection(mask).area<1e-9 and xy.area>1e-9:
                        required[key]+=1
                    if horizontal and xy.area>1e-9:polygons.append(xy)
                else:
                    if key not in old_faces and (not math.isfinite(data['areas'][i]) or data['areas'][i]<=1e-9):
                        raise ValueError('New degenerate face')
                    if xy.area<=1e-9:continue
                    top=.46 if name=='pavement_0 unified road' else .3
                    expect=[expected_height(*levels.local_uv(*p[:2]),top) for p in poly]
                    error=max(abs(p[2]-z) for p,z in zip(poly,expect))
                    if error>1e-5:raise ValueError(f'Unexpected surface height: {name}, {error}')
                    max_error=max(max_error,error)
                    if key not in old_faces:
                        new_top_count+=1
                        # Clipped exterior fragments inherit their original winding.
                        # Require upward normals only on the newly lowered surfaces.
                        if max(abs(p[2]-top) for p in poly)>1e-6 and connection.outline.signed_area(poly.tolist())<=0:
                            raise ValueError('New downward walking face')
                    if not xy.is_valid:raise ValueError('Invalid new footprint')
                    polygons.append(xy)
            tops[stage]=sh.union_all(polygons)
        if required-new_faces:raise ValueError('Outside face or attributes changed')
        difference=tops['before'].symmetric_difference(tops['after']).area
        if difference>.003:raise ValueError(f'XY footprint changed: {name}: {difference}')
        before_road_tops.append(tops['before'])
        checks[name]={'original_vertices_exact':True,'outside_faces_and_attributes_exact':sum(required.values()),
                      'xy_symmetric_difference_m2':difference,'new_top_faces':new_top_count,
                      'maximum_height_error_m':max_error,'new_degenerate_faces':0}
    seam=read(args.output/'seam-mesh.json');vertices=seam['vertices'];edges=Counter();directed=Counter();seam_tops=[]
    for face in seam['faces']:
        poly=[vertices[i] for i in face]
        if connection.outline.area(poly)<=1e-10:raise ValueError('Degenerate seam face')
        for a,b in zip(face,face[1:]+face[:1]):edges[tuple(sorted((a,b)))]+=1;directed[(a,b)]+=1
        if all(abs(p[2]-.11)<1e-6 for p in poly):
            if connection.outline.signed_area(poly)<=0:raise ValueError('Inverted seam top')
            seam_tops.append(sh.Polygon([p[:2] for p in poly]))
        elif all(abs(p[2]+.01)<1e-6 for p in poly):
            if connection.outline.signed_area(poly)>=0:raise ValueError('Inverted seam bottom')
        elif any(min(abs(p[2]-.11),abs(p[2]+.01))>1e-6 for p in poly):raise ValueError('Unexpected seam height')
    if any(n!=2 for n in edges.values()) or any(n!=directed[(b,a)] for (a,b),n in directed.items()):
        raise ValueError('Seam fill is not a closed consistently oriented slab')
    actual=sh.union_all(seam_tops)
    paving=sh.union_all([sh.Polygon(p) for p in read(args.output/'before-paving-tops.json')])
    roads=sh.union_all(before_road_tops)
    core=sh.Polygon([connection.world(u,v)[:2] for u,v in [(-26,46),(-18,46),(-18,54),(-26,54)]]).buffer(-.02,join_style=2)
    expected=paving.buffer(.01,join_style=2).intersection(roads.buffer(.01,join_style=2)).difference(paving.union(roads)).intersection(core)
    seam_error=actual.symmetric_difference(expected).area
    overlap=actual.intersection(paving.union(roads)).area
    if not actual.is_valid or actual.is_empty or actual.area>.5 or seam_error>.0003 or overlap>.0003:
        raise ValueError('Seam footprint outside expected millimetric gap')
    before,after=read(args.output/'before-rays.json'),read(args.output/'after-rays.json')
    counts=Counter();priority={};seam_gaps=Counter();max_error=0.
    for a,b in zip(before,after):
        if a['xy']!=b['xy']:raise ValueError('Probe coordinates differ')
        radius=max(abs(a['uv'][0]+22),abs(a['uv'][1]-50))
        if a['object'] in connection.ROADS:
            expected=expected_height(*a['uv'],a['z'])
            if b['object']!=a['object'] or abs(b['z']-expected)>2e-5:
                raise ValueError('Saved road ray disagrees with independent expected height: '+str((a,b,expected)))
            counts['road_samples']+=1
            if radius<4:counts['flat_core_road_samples']+=1
            if radius>=8:counts['unchanged_outside_road_samples']+=1
            max_error=max(max_error,abs(b['z']-expected))
        elif b['object']==connection.SEAM:
            if a['object'] not in ('ground',None) or abs(b['z']-.11)>1e-5:raise ValueError('Seam covered an existing surface')
            counts['filled_gap_samples']+=1
        else:
            if a['object']!=b['object'] or a['z']!=b['z']:
                if a['object']!=b['object'] or a['z'] is None or abs(a['z']-b['z'])>1e-5:
                    raise ValueError('Unrelated surface changed')
            if a['kind']=='entry':counts['entry_samples']+=1
        if a['kind']=='priority-seam':
            if abs(abs(a['offset'])-.02)<1e-8:
                priority.setdefault(str(a['pair']),[]).append({'before_object':a['object'],'before_z_m':a['z'],'after_z_m':b['z']})
            if b['z'] is None or abs(b['z']-.11)>1e-5:seam_gaps[str(a['pair'])]+=1
        if 'overhead' in b and a['object'] in connection.ROADS|{levels.PAVING}:
            if b['overhead']['object']!=b['object'] or abs(b['overhead']['z']-b['z'])>2e-5:
                raise ValueError('Core overhead obstruction')
            counts['core_clearance_samples']+=1
    for pair in priority.values():
        if len(pair)!=2 or max(abs(p['after_z_m']-.11) for p in pair)>1e-5:
            raise ValueError('Priority rise was not removed')
    if seam_gaps:raise ValueError('Unfilled priority seam: '+str(seam_gaps))
    if counts['entry_samples']!=12 or counts['flat_core_road_samples']<10 or counts['unchanged_outside_road_samples']<100:
        raise ValueError('Insufficient retained or repaired surface coverage')
    return {'ok':True,'road_checks':checks,'ray_checks':dict(counts),'priority_pairs':priority,
            'seam_fill':{'closed_oriented_slab':True,'area_m2':actual.area,'xy_symmetric_difference_m2':seam_error,
                         'overlap_existing_m2':overlap},
            'maximum_ray_height_error_m':max_error,'priority_seam_nonflush_samples_2mm_spacing':dict(seam_gaps),
            'runtime':{'python':sys.version.split()[0],'numpy':np.__version__,'shapely':sh.__version__,'geos':sh.geos_version_string}}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('before','after','output'):p.add_argument('--'+arg,type=Path,required=True)
    p.add_argument('--blender',type=Path);p.add_argument('--worker',action='store_true')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    if args.worker:worker(args);return
    if not args.blender:raise ValueError('Supply Blender')
    args.output.mkdir(parents=True,exist_ok=False)
    hashes={key:digest(getattr(args,key)) for key in ('before','after')};result={'ok':False}
    try:
        command=[str(args.blender.resolve()),'--factory-startup','--disable-autoexec','--background',
                 '--python-exit-code','1','--python',str(Path(__file__).resolve()),'--','--worker']
        for key in ('before','after','output'):command+=['--'+key,str(getattr(args,key).resolve())]
        with (args.output/'export.log').open('w',encoding='utf-8') as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200)
        result=geometry_audit(args)
    except Exception as error:
        result.update(ok=False,error=str(error));raise
    finally:
        result['saved_blends_unchanged']=hashes=={key:digest(getattr(args,key)) for key in hashes}
        result['ok']=result['ok'] and result['saved_blends_unchanged']
        result['input_blend_sha256']=hashes
        result['code_sha256']={p.name:digest(p) for p in [Path(__file__),Path(connection.__file__),Path(levels.__file__)]}
        write(args.output/'validation.json',result)
    if not result['ok']:raise ValueError('Read-only verification changed saved scene')
    print(json.dumps({'ok':True,'ray_checks':result['ray_checks'],'priority_pairs':result['priority_pairs'],
                      'seam_gaps':result['priority_seam_nonflush_samples_2mm_spacing']},indent=2))


if __name__=='__main__':main()
