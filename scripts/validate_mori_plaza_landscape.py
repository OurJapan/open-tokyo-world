# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Reopen the saved landscape candidate and check mesh scope, slab and joins."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import mori_plaza_landscape_v1 as landscape


def write(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def worker(args):
    import bpy
    import numpy as np
    from mathutils import Vector
    if bpy.app.version_string!='4.5.1 LTS':raise ValueError('Use Blender 4.5.1 LTS')
    edge=landscape.connector_edges()
    centers=[((edge[i][0]+edge[-1-i][0])/2,(edge[i][1]+edge[-1-i][1])/2) for i in range(1,25)]
    samples=[{'kind':'connector','uv':list(p)} for p in centers]
    samples += [{'kind':'connector-width','uv':[edge[i][k]*t+edge[-1-i][k]*(1-t) for k in (0,1)]}
                for i in range(1,25) for t in (.1,.3,.7,.9)]
    samples += [{'kind':'entry','uv':[u,v]} for u in (-3.25,.25,3.25) for v in (21.99,22.01,31.99)]
    samples += [{'kind':'seam','uv':[0,v]} for v in (31.99,32.01,63.4,63.5,65,70)]
    def cast(dg,uv,height):
        origin=Vector(landscape.world(*uv,height))
        for _ in range(16):
            hit,point,normal,index,obj,matrix=bpy.context.scene.ray_cast(dg,origin,Vector((0,0,-1)),distance=origin.z+2)
            if not hit or not obj.hide_render:break
            origin=point-Vector((0,0,.0005))
        return {'hit':hit,'object':obj.name if hit else None,'z':float(point.z) if hit else None}
    for stage,path in [('before',args.before),('after',args.after)]:
        bpy.ops.wm.open_mainfile(filepath=str(path),use_scripts=False)
        bpy.context.scene.frame_set(1)
        for name,key in [(landscape.PARK,'park'),(landscape.PAVING,'paving')]:
            obj=bpy.data.objects.get(name)
            if obj is None:continue
            mesh=obj.data
            vertices=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',vertices)
            indices=np.empty(len(mesh.loops),np.int32);mesh.loops.foreach_get('vertex_index',indices)
            arrays={'vertices':vertices.reshape(-1,3),'indices':indices}
            for key_name,prop,dtype in [('starts','loop_start',np.int32),('counts','loop_total',np.int32),
                                        ('material','material_index',np.int32),('smooth','use_smooth',np.bool_),('areas','area',np.float64)]:
                values=np.empty(len(mesh.polygons),dtype);mesh.polygons.foreach_get(prop,values);arrays[key_name]=values
            np.savez_compressed(args.output/f'{stage}-{key}.npz',**arrays)
        dg=bpy.context.evaluated_depsgraph_get();rays=[]
        for sample in samples:
            record={**sample,**cast(dg,sample['uv'],2)}
            if sample['kind'].startswith('connector'):
                # Check roofs from above, but measure joins near ground to avoid
                # subtracting a 70m float32 ray length for micrometre heights.
                record['clearance']=cast(dg,sample['uv'],70)
            rays.append(record)
        write(args.output/f'{stage}-rays.json',rays)
        if stage=='after':write(args.output/'saved-patch-audit.json',json.loads(bpy.context.scene['otw_plaza_landscape_audit']))


def audit(args,plan):
    import numpy as np
    import shapely as sh
    if (sys.version_info[:2]!=(3,12) or np.__version__!='2.3.5' or sh.__version__!='2.1.2' or sh.geos_version_string!='3.13.1'):
        raise ValueError('Use the pinned production environment')
    def load(name):
        with np.load(args.output/name,allow_pickle=False) as data:return {k:data[k] for k in data.files}
    def faces(data):
        for i,(start,count) in enumerate(zip(data['starts'],data['counts'])):
            ids=data['indices'][start:start+count]
            yield i,ids,(tuple(int(v) for v in ids),int(data['material'][i]),bool(data['smooth'][i]))
    def tops(data, inherited_invalid=None):
        parts=[];invalid=Counter()
        for i,ids,key in faces(data):
            poly=data['vertices'][ids]
            if np.max(np.abs(poly[:,2]-.11))<1e-6:
                shape=sh.Polygon(poly[:,:2])
                if not shape.is_valid or shape.area<=1e-9:
                    invalid[key]+=1
                    continue
                parts.append(shape)
        if inherited_invalid is not None and invalid != inherited_invalid:
            raise ValueError('Invalid saved top faces differ from the pinned inherited faces')
        return sh.union_all(parts),invalid
    before,after,paved=load('before-park.npz'),load('after-park.npz'),load('after-paving.npz')
    with np.load(args.inputs/'work/tower15_env/landuse.npz',allow_pickle=False) as source:
        if not np.array_equal(before['vertices'],source['park']):raise ValueError('Park is not the pinned source vertex array')
    if (not np.all(before['counts']==3) or not np.array_equal(before['indices'],np.arange(len(before['vertices'])))):
        raise ValueError('Park source triangle ordering differs')
    if not np.array_equal(before['vertices'],after['vertices'][:len(before['vertices'])]):raise ValueError('Original lawn vertices moved')
    connector=sh.union_all([sh.Polygon(p) for p in plan['connector_triangles']])
    restoration=sh.union_all([sh.Polygon(p) for p in plan['lawn_triangles']])
    expected_paving=sh.union_all([sh.Polygon(p) for p in plan['paving_triangles']])
    # The source array and original vertices were verified above. Only exactly
    # inherited face indices/material/smooth flags may be omitted from unions;
    # their multiplicities must remain unchanged. New invalid faces fail.
    actual_before,inherited_invalid=tops(before)
    actual_after,_=tops(after,inherited_invalid)
    actual_paving,_=tops(paved,Counter())
    expected=actual_before.difference(connector).union(restoration)
    difference=actual_after.symmetric_difference(expected).area
    paving_difference=actual_paving.symmetric_difference(expected_paving).area
    overlap=actual_after.intersection(actual_paving).area
    if difference>.03 or paving_difference>.03 or overlap>.03:
        raise ValueError(f'Surface union mismatch: {difference}, {paving_difference}, overlap {overlap}')
    required=Counter()
    for i,ids,key in faces(before):
        if sh.Polygon(before['vertices'][ids,:2]).intersection(connector).area<=1e-8:required[key]+=1
    after_faces=Counter(key for _,_,key in faces(after))
    if required-after_faces:raise ValueError('A lawn face outside the connector changed')
    old_faces=Counter(key for _,_,key in faces(before))
    for i,ids,key in faces(after):
        if key not in old_faces and (not math.isfinite(after['areas'][i]) or after['areas'][i]<=1e-9):
            raise ValueError('New degenerate lawn face')
    edges=Counter();directed=Counter();volume=0.
    for i,ids,key in faces(paved):
        if not math.isfinite(paved['areas'][i]) or paved['areas'][i]<=1e-9:raise ValueError('Degenerate paving face')
        ids=[int(v) for v in ids]
        for a,b in zip(ids,ids[1:]+ids[:1]):edges[tuple(sorted((a,b)))]+=1;directed[(a,b)]+=1
        xyz=paved['vertices'][ids].astype(np.float64)
        # Translate for stable volume evaluation, without changing orientation.
        xyz-=np.array([-400,350,0])
        for b,c in zip(xyz[1:-1],xyz[2:]):volume+=float(np.dot(xyz[0],np.cross(b,c)))/6
    if set(edges.values())!={2} or any(directed[(b,a)]!=n for (a,b),n in directed.items()):
        raise ValueError('Paving slab is not closed and consistently oriented')
    expected_volume=actual_paving.area*(landscape.outline.f32(.11)-landscape.outline.f32(-.01))
    if abs(volume-expected_volume)>.001:raise ValueError('Paving slab volume differs')
    scope=landscape.outline.build_scope(args.inputs)
    protected=sh.union_all([sh.Polygon(p) for p,_ in scope['protect']])
    protected_overlap=restoration.union(actual_paving).intersection(protected).area
    if protected_overlap>.01:raise ValueError('New surface crosses protected roads')
    rays_before,rays_after=read(args.output/'before-rays.json'),read(args.output/'after-rays.json')
    entry=0;connections=0;width_samples=0;seams=[]
    for a,b in zip(rays_before,rays_after):
        if not b['hit']:raise ValueError('Missing ground at '+str(b))
        if a['kind']=='entry':
            if a['object']!=b['object'] or abs(a['z']-b['z'])>1e-5:raise ValueError('Adopted entrance changed')
            entry+=1
        elif a['kind'].startswith('connector'):
            if b['object']!=landscape.PAVING or abs(b['z']-.11)>1e-5:raise ValueError('Connector has a gap or step: '+str(b))
            if b['clearance']['object']!=landscape.PAVING:raise ValueError('Connector is obstructed: '+str(b))
            if a['kind']=='connector':connections+=1
            else:width_samples+=1
        else:seams.append({'uv':a['uv'],'before_object':a['object'],'before_z':a['z'],'after_object':b['object'],'after_z':b['z']})
    if abs(seams[2]['after_z']-seams[3]['after_z'])>1e-5:raise ValueError('Former grass edge still has a height discontinuity')
    return {'ok':True,'park_matches_pinned_source_vertices_and_triangles':True,'original_park_vertices_unchanged':True,
            'outside_park_faces_and_attributes_exact':sum(required.values()),
            'park_symmetric_difference_m2':difference,'paving_symmetric_difference_m2':paving_difference,
            'park_paving_overlap_m2':overlap,'new_surface_protected_overlap_m2':protected_overlap,
            'paving_closed_consistently_oriented':True,'paving_volume_m3':volume,'new_degenerate_faces':0,
            'inherited_degenerate_park_faces_exact':sum(inherited_invalid.values()),
            'retained_entry_samples':entry,'continuous_connector_samples':connections,
            'connector_width_clearance_samples':width_samples,'seam_samples':seams,
            'limitations':['Source footprints are mapped approximations, not a survey.',
                           'Connector geometry and flat 0.11m elevation are inferred; real stairs and grades remain unresolved.',
                           'Existing higher road interfaces outside the entrance-to-west-path connection remain unchanged.',
                           'Garden areas retain the inherited grass representation; individual landscape planting is not reconstructed.',
                           'Exactly inherited zero-area lawn faces remain; they are excluded only from area unions.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('before','after','inputs','plan','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--blender',type=Path)
    parser.add_argument('--worker',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--worker' in sys.argv else None)
    if args.worker:worker(args);return
    if not args.blender or args.output.exists():raise ValueError('Supply Blender and a new output directory')
    landscape.verify_sources(args.inputs)
    plan=read(args.plan);landscape.validate_plan(plan)
    hashes={name:landscape.digest(getattr(args,name)) for name in ('before','after','plan')}
    args.output.mkdir(parents=True)
    result={'ok':False}
    try:
        command=[str(args.blender.resolve()),'--factory-startup','--disable-autoexec','--background','--python-exit-code','1',
                 '--python',str(Path(__file__).resolve()),'--','--worker']
        for name in ('before','after','inputs','plan','output'):command+=['--'+name,str(getattr(args,name).resolve())]
        with (args.output/'export.log').open('w',encoding='utf-8') as stream:
            subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=1200)
        result=audit(args,plan)
        result['inputs_unchanged']=hashes=={name:landscape.digest(getattr(args,name)) for name in hashes}
        if not result['inputs_unchanged']:raise ValueError('Verification modified an input')
        landscape.verify_sources(args.inputs)
        result['input_sha256']=hashes
        result['validator_sha256']=landscape.digest(__file__)
    except Exception as error:
        result.update(ok=False,error=str(error));raise
    finally:write(args.output/'validation.json',result)
    print('Saved landscape verification passed: '+str(args.output/'validation.json'))


if __name__=='__main__':main()
