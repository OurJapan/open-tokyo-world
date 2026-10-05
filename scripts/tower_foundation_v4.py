# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Isolated PR62 increment: foundation axes and bounded apron transition."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import tower_foundation_geometry_v4 as geo
from tower_site_v3 import open_scene,read,write,points,rotation,components,bounds
from review import require,digest,compare_reports,validate_cameras

CONFIG=ROOT/'areas/tokyo-tower/tower-foundation-v4-input.json'
CAMERAS=ROOT/'areas/tokyo-tower/tower-foundation-v4-cameras.json'


def protected_state():
    import bpy
    import tower_foottown_v2 as detail
    from validate_tower_foottown import protected_metadata,json_value
    old=detail.CHANGED,detail.ADDED,detail.COLLECTION
    try:
        detail.CHANGED=geo.TARGETS;detail.ADDED=set();detail.COLLECTION='no excluded collection'
        state=protected_metadata()
    finally:
        detail.CHANGED,detail.ADDED,detail.COLLECTION=old
    state['targets']={n:{'props':{k:json_value(o[k]) for k in o.keys()},
        'matrix':[list(r) for r in o.matrix_world],'hide_render':o.hide_render,
        'hide_viewport':o.hide_viewport,'hide_local':o.hide_get(),
        'collections':sorted(c.name for c in o.users_collection),
        'modifiers':[{k:getattr(m,k) for k in ('name','type','width','segments','limit_method','angle_limit','show_viewport','show_render') if hasattr(m,k)} for m in o.modifiers]}
        for n in geo.TARGETS for o in [bpy.data.objects[n]]}
    state['counts']={k:len(getattr(bpy.data,k)) for k in ('objects','meshes','materials','images','collections','actions')}
    return state


def build(source,out,config):
    import bpy
    from blender_worker import mesh_fingerprint
    open_scene(source)
    for name,spec in config['objects'].items():
        obj=bpy.data.objects[name];mesh=obj.data
        require(mesh_fingerprint(mesh)==spec['mesh_sha256'],'Pinned target differs: '+name)
        require(mesh.users==1 and not mesh.uv_layers and not mesh.shape_keys and not obj.parent and not obj.constraints and not obj.animation_data,'Unsupported target')
        require(all(abs(obj.matrix_world[i][j]-spec['matrix_world'][i][j])<1e-7 for i in range(4) for j in range(4)),'Target transform differs')
        if name==geo.PAVING:
            data=geo.paving_mesh(config['ground'])
            mesh.clear_geometry();mesh.from_pydata(data['vertices'],[],data['faces'])
            for face in mesh.polygons:
                face.use_smooth=len(face.vertices)==3 and all(mesh.vertices[i].co.z>-.05 for i in face.vertices)
        else:
            transform=geo.foundation_point if name==geo.STONE else geo.lower_point
            for vertex in mesh.vertices:vertex.co=transform(vertex.co)
        mesh.update()
    retained=[m.name for m in bpy.data.materials if m.users==0]
    for name in retained:bpy.data.materials[name].use_fake_user=True
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'after.blend'),check_existing=False)
    return {'ok':True,'changed_objects':sorted(geo.TARGETS),'added_objects':[],
            'foundation_axis_span_m':88.,'upper_geometry_preserved_from_z_m':52.,'retained_unused_materials':retained}


def inspect_geometry():
    """Measure saved geometry independently of the production deformation."""
    import bpy
    from mathutils import Vector
    from validate_tower_structure import check_mesh
    stone=bpy.data.objects[geo.STONE]
    stats,solids=check_mesh(*points(stone.data),((-50,50),(-50,50),(-.01,2.01)))
    require(len(solids)==4,'Expected four foundations')
    for p in solids:
        require(all(abs(abs(p['center'][i])-44.)<1e-4 for i in (0,1)),'Foundation axis is not 88m')
        require(all(abs(a-b)<1e-4 for a,b in zip(p['size'],(10.5,10.5,2.))),'Foundation dimensions changed')
    plate=bpy.data.objects[geo.PLATES]
    pv,pf=points(plate.data)
    plate.data.calc_loop_triangles()
    ps,parts=check_mesh(pv,[tuple(t.vertices) for t in plate.data.loop_triangles],((-49,49),(-49,49),(1.9,2.3)))
    require(len(parts)==80,'Plate/bolt component count changed')
    steel=bpy.data.objects[geo.STEEL]
    # Measure the sixteen lower chord joints, where inherited beam caps are
    # near Z=2; retained contact plates must still reach those chord surfaces.
    from mathutils.bvhtree import BVHTree
    bv=BVHTree.FromPolygons([v.co for v in steel.data.vertices],[p.vertices[:] for p in steel.data.polygons],all_triangles=False)
    contacts=[]
    for part in parts:
        if len(part['vertices'])!=8:continue
        x,y,z=part['center'];near=bv.find_nearest(Vector((x,y,2.11)))
        require(near is not None and near[3]<.16,'Foot plate disconnected from steel')
        support=stone.ray_cast(Vector((x,y,3)),Vector((0,0,-1)))
        require(support[0] and abs(support[1].z-2.)<1e-4,'Foot plate outside foundation')
        contacts.append(float(near[3]))
    require(len(contacts)==16,'Expected sixteen steel contacts')
    paving=bpy.data.objects[geo.PAVING]
    terrain_stats,_=check_mesh(*points(paving.data),((-36.51,36.51),(-70.01,-28.53),(-.061,4.401)))
    for x in (-7,0,7):
        hit,co,n,i=paving.ray_cast(Vector((x,-29.1,8)),Vector((0,0,-1)))
        require(hit and abs(co.z-4.4)<1e-4,'South threshold lost')
    # Evaluate lateral/far boundary against the protected city at <=0.5m.
    # The north edge meets the building; it is not a city-ground seam.
    vs,fs=points(paving.data);surface_edges={}
    for f in fs:
        if len(f)!=3 or not all(vs[i][2]>-.05 for i in f):continue
        if not all(vs[i][1]<=-29 for i in f):continue
        for a,b in zip(f,f[1:]+f[:1]):
            key=tuple(sorted((a,b)));surface_edges[key]=surface_edges.get(key,0)+1
    tower_names=set(read(ROOT/'areas/tokyo-tower/tower-site-v3-input.json')['tower_objects'])|{o.name for o in bpy.context.scene.objects if o.name.startswith('OTW Tokyo Tower site v3 / ')}
    dg=bpy.context.evaluated_depsgraph_get()
    import math
    differences=[];edge_failures=[]
    for (a,b),count in surface_edges.items():
        if count!=1:continue
        A,B=Vector(vs[a]),Vector(vs[b])
        if A.y>-29.01 and B.y>-29.01:continue
        length=(A-B).length;steps=max(1,math.ceil(length/.5))
        for k in range(steps+1):
            q=A.lerp(B,k/steps);origin=rotation()@Vector((q.x,q.y,80));ground=None
            for _ in range(96):
                hit,co,n,i,obj,m=bpy.context.scene.ray_cast(dg,origin,Vector((0,0,-1)),distance=90)
                require(hit,'Missing city surface at apron edge')
                if obj.name not in tower_names and not obj.hide_render:
                    ground=co.z;break
                origin=co+Vector((0,0,-.005))
            require(ground is not None and -.01<=ground<=.61,'Building or void intersects apron edge: '+str((tuple(q),ground,obj.name)))
            differences.append(float(q.z-ground))
            if abs(q.z-ground)>=.21:edge_failures.append((tuple(q),ground,obj.name))
    require(differences and not edge_failures,'Unresolved high apron side face: '+str(edge_failures[:12]))
    # Every top triangle is checked at its centroid against surrounding objects.
    triangle_count=0;curb_overlaps=[]
    for f in fs:
        if len(f)!=3 or not all(vs[i][2]>-.05 for i in f):continue
        q=sum((Vector(vs[i]) for i in f),Vector())/3
        origin=rotation()@Vector((q.x,q.y,80));reached=False
        for _ in range(96):
            hit,co,n,i,obj,m=bpy.context.scene.ray_cast(dg,origin,Vector((0,0,-1)),distance=90)
            if not hit:break
            if obj.name==geo.PAVING:reached=True;break
            if obj.name not in tower_names and not obj.hide_render:
                # Protected low city paving/curbs remain visible where a step
                # crosses a sloping triangle. Never accept a roof or building.
                if -.01<=co.z<=.61:
                    curb_overlaps.append(float(co.z-q.z));reached=True
                break
            origin=co+Vector((0,0,-.005))
        require(reached,'Existing city obstructs terrain triangle: '+str((tuple(q),obj.name,tuple(co))))
        triangle_count+=1
    return {'foundation':stats,'plates_and_bolts':ps,'steel_contact_max_distance_m':max(contacts),
        'paving':terrain_stats,'edge_samples':len(differences),'maximum_edge_step_m':max(abs(v) for v in differences),
        'terrain_triangle_clearance_samples':triangle_count,'retained_city_curb_overlap_samples':len(curb_overlaps),'maximum_retained_curb_overlap_m':max(curb_overlaps,default=0.),'door_threshold_m':4.4,
        'foundation_size_is_retained_estimate':True,'surface_is_legacy_city_transition_not_full_dem':True}


def validate(source,out,config):
    import bpy
    from blender_worker import validate as scene_validate,material_fingerprint
    from tower_south_handrail import mesh_flags
    from validate_tower_structure import check_mesh
    features=read(ROOT/'areas/tokyo-tower/foottown-v2-features.json')
    open_scene(source)
    before=scene_validate({'features':features});state=protected_state()
    shaders={m.name:material_fingerprint(m) for m in bpy.data.materials}
    old={n:points(bpy.data.objects[n].data) for n in geo.TARGETS if n!=geo.PAVING}
    flags={n:mesh_flags(bpy.data.objects[n].data) for n in old}
    open_scene(out/'after.blend')
    after=scene_validate({'features':features});changed=compare_reports(before,after,geo.TARGETS)
    require(protected_state()==state,'Protected metadata, transforms or counts changed')
    require(shaders=={m.name:material_fingerprint(m) for m in bpy.data.materials},'Material datablock changed')
    retained_high=0
    for name,(ov,of) in old.items():
        mesh=bpy.data.objects[name].data;nv,nf=points(mesh)
        require(of==nf and len(ov)==len(nv) and mesh_flags(mesh)==flags[name],'Topology or flags changed')
        for a,b in zip(ov,nv):
            require(a[2]==b[2],'Vertical position changed')
            if name==geo.STONE:
                require(all(abs(b[i]-(a[i]-(3.5 if a[i]>0 else -3.5)))<1e-4 for i in (0,1)),'Unexpected foundation shift')
            elif a[2]>=52:
                require(a==b,'Upper geometry changed');retained_high+=1
            else:
                # Independent bounded analytic check, not a generator call.
                t=max(0.,min(1.,(a[2]-2.)/50.));s=44./46.6066666667
                s+=(1.-s)*t*t*(3.-2.*t)
                require(all(abs(b[i]-a[i]*s)<1e-4 for i in (0,1)),'Unexpected lower-frame displacement')
        mesh.calc_loop_triangles()
        check_mesh(nv,[tuple(t.vertices) for t in mesh.loop_triangles],((-55,55),(-55,55),(-1,334)))
    geometry=inspect_geometry()
    return {'ok':True,'changed_objects':changed,'protected_objects':len(before['objects'])-4,
        'objects':len(after['objects']),'retained_vertices_at_or_above_52m':retained_high,
        'original_topology_and_flags_retained_except_paving':True,'protected_metadata_and_original_shaders_unchanged':True,
        'geometry':geometry,'warnings':after['warnings'],'limits':after['limits']+[
        '88m axis spacing is interpreted from historical foundation Fig.12, not a current survey.',
        'Foundation cap dimensions and lower-frame interpolation remain model estimates.',
        'Apron transition matches legacy city surfaces; full parking terrain and underground foundations are not reconstructed.',
        'Boundary and triangle samples do not prove continuous clearance or accessibility.']}


def render(source,out,phase,preview):
    from blender_worker import render as scene_render
    cameras=read(CAMERAS)
    if preview:cameras['views']=[v for v in cameras['views'] if v['id'] in ('south-grade','foundation-close','site-overhead')]
    validate_cameras(cameras)
    open_scene(source if phase=='render-before' else out/'after.blend')
    settings={'device':'OPTIX','width':960 if preview else 1280,'height':636 if preview else 848,'samples':12 if preview else 32,'seed':0}
    result=scene_render({'output':str(out),'cameras':cameras,'settings':settings},phase)
    result.update(settings=settings,cameras_sha256=digest(CAMERAS))
    return result


def main():
    import bpy
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase',required=True,choices=('build','validate','render-before','render-after'))
    p.add_argument('--input',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--preview',action='store_true')
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);source=a.input.resolve();out=a.output.resolve()
    out.mkdir(parents=True,exist_ok=True);report=out/(a.phase+'.json');config=read(CONFIG)
    require(not report.exists(),'Refusing to overwrite report')
    require(source!=out/'after.blend' and digest(source)==config['input_sha256'],'Pinned input differs')
    require(bpy.app.version_string=='4.5.1 LTS' and not bpy.context.preferences.filepaths.use_scripts_auto_execute,'Blender environment differs')
    code={name:digest(ROOT/'scripts'/name) for name in ('tower_foundation_v4.py','tower_foundation_geometry_v4.py','tower_structure_v1.py','blender_worker.py','review.py','validate_tower_structure.py','validate_tower_foottown.py','tower_south_handrail.py','tower_site_v3.py')}
    candidate_hash=digest(out/'after.blend') if a.phase!='build' else None
    if a.phase=='build':
        require(not (out/'after.blend').exists(),'Refusing to overwrite candidate')
        result=build(source,out,config)
    elif a.phase=='validate':result=validate(source,out,config)
    else:result=render(source,out,a.phase,a.preview)
    require(digest(source)==config['input_sha256'],'Original changed')
    if candidate_hash:require(digest(out/'after.blend')==candidate_hash,'Read-only phase changed candidate')
    require(all(digest(ROOT/'scripts'/n)==h for n,h in code.items()),'Code changed during phase')
    result.update(input_sha256=config['input_sha256'],candidate_sha256=digest(out/'after.blend'),
        source_and_candidate_protected=True,blender_version=bpy.app.version_string,code_sha256=code,configuration_sha256=digest(CONFIG))
    write(report,result);print('OK: '+a.phase)


if __name__=='__main__':main()
