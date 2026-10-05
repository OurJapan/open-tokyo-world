# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Parking clearance, stepped terrain and photo-guided lower support details."""
import argparse,json,sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import tower_footway_geometry_v5 as geo
import tower_ground_geometry_v7 as detail
ALL_TARGETS=detail.TARGETS
from tower_site_v3 import open_scene,read,write,points
from review import require,digest,compare_reports,validate_cameras
CONFIG=ROOT/'areas/tokyo-tower/tower-ground-v7-input.json'
PLAN=ROOT/'areas/tokyo-tower/tower-ground-v7-plan.json'
CAMERAS=ROOT/'areas/tokyo-tower/tower-ground-v7-cameras.json'

def protected():
    import bpy
    import tower_foottown_v2 as old
    from validate_tower_foottown import protected_metadata,json_value
    saved=old.CHANGED,old.ADDED,old.COLLECTION
    try:
        old.CHANGED=ALL_TARGETS;old.ADDED=detail.ADDED;old.COLLECTION='OTW Tokyo Tower ground v7'
        state=protected_metadata()
    finally:old.CHANGED,old.ADDED,old.COLLECTION=saved
    state['targets']={n:{'props':{k:json_value(o[k]) for k in o.keys()},'matrix':[list(r) for r in o.matrix_world],
        'hide_render':o.hide_render,'hide_viewport':o.hide_viewport,'hide_local':o.hide_get(),
        'collections':sorted(c.name for c in o.users_collection),
        'modifiers':[{k:getattr(m,k) for k in ('name','type','width','segments','limit_method','angle_limit','show_viewport','show_render') if hasattr(m,k)} for m in o.modifiers]}
        for n in ALL_TARGETS for o in [bpy.data.objects[n]]}
    return state


def records(mesh):
    return [(tuple(p.vertices),p.material_index,p.use_smooth,p.hide,p.select) for p in mesh.polygons]

def build(source,out,config,plan):
    import bpy
    import tower_footway_v5 as road_worker
    from blender_worker import mesh_fingerprint
    from tower_foundation_geometry_v4 import paving_mesh
    import tower_foundation_geometry_v4 as apron
    from tower_site_v3 import rotation
    open_scene(source)
    for name in ALL_TARGETS:
        o=bpy.data.objects[name];m=o.data
        require(mesh_fingerprint(m)==config['objects'][name]['hash'],'Pinned mesh differs: '+name)
        require(m.users==1 and not m.uv_layers and not m.shape_keys and not o.parent and not o.constraints and not o.animation_data,'Unsupported target')
    result=road_worker.build(source,out,config,plan)
    for name in (detail.STEEL,detail.PLATES):
        for v in bpy.data.objects[name].data.vertices:v.co=detail.lift(v.co)
        bpy.data.objects[name].data.update()
    def replace(name,data):
        m=bpy.data.objects[name].data;m.clear_geometry();m.from_pydata(data['vertices'],[],data['faces']);m.update()
    replace(detail.STONE,detail.cap_mesh(plan['caps'],plan))
    # Only the complete three-stroke bays selected in the source audit disappear.
    m=bpy.data.objects[detail.MARKS].data;ov,of=points(m);vs=[];fs=[]
    for i in range(15):
        if i in config['remove_parking_bays']:continue
        offset=len(vs);vs.extend(ov[i*24:i*24+24]);fs.extend(tuple(offset+j-i*24 for j in f) for f in of[i*18:i*18+18])
    replace(detail.MARKS,dict(vertices=vs,faces=fs))
    # Insert a shared-boundary ground top into the retained original box.
    m=bpy.data.objects[detail.GROUND].data;vs,of=points(m);fs=[f for i,f in enumerate(of) if i!=1]
    lookup={tuple(round(x,6) for x in p):i for i,p in enumerate(vs)}
    for group in ('grid','outside'):
        d=plan['ground_top'][group];ids=[]
        for p in d['vertices']:
            key=tuple(round(x,6) for x in p)
            if key not in lookup:lookup[key]=len(vs);vs.append(tuple(p))
            ids.append(lookup[key])
        fs.extend(tuple(ids[i] for i in f) for f in d['faces'])
    replace(detail.GROUND,dict(vertices=vs,faces=fs))
    old_height=apron.surface_height
    try:
        apron.surface_height=detail.apron_height
        paving=paving_mesh(config['apron_ground'])
    finally:apron.surface_height=old_height
    replace(detail.PAVING,paving)
    mats={}
    for key,(color,metal,rough) in detail.MATERIALS.items():
        name=detail.PREFIX+key;require(name not in bpy.data.materials,'New material already exists')
        m=bpy.data.materials.new(name);m.diffuse_color=color;m.use_nodes=True
        bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=color;bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough;mats[key]=m
    bpy.data.objects[detail.STONE].data.materials[0]=mats['plinth']
    c=bpy.data.collections.new('OTW Tokyo Tower ground v7');bpy.context.scene.collection.children.link(c)
    for key,data in detail.details(plan['caps'],plan).items():
        name=detail.PREFIX+key;require(name not in bpy.data.objects,'Detail already exists')
        m=bpy.data.meshes.new(name);m.from_pydata(data['vertices'],[],data['faces']);m.materials.append(mats[key]);m.update()
        o=bpy.data.objects.new(name,m);c.objects.link(o);o.matrix_world=rotation();o['feature_id']='otw:jp:tokyo:minato:tokyo-tower'
    for m in bpy.data.materials:
        if m.users==0:m.use_fake_user=True
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'after.blend'),check_existing=False)
    result.update(changed_objects=sorted(ALL_TARGETS),added_objects=sorted(detail.ADDED),removed_parking_bays=config['remove_parking_bays'])
    return result


def validate(source,out,config,plan):
    import bpy
    from blender_worker import validate as scene_validate,material_fingerprint
    from validate_tower_structure import check_mesh
    features=read(ROOT/'areas/tokyo-tower/foottown-v2-features.json')
    open_scene(source);before=scene_validate({'features':features});state=protected()
    materials={m.name:material_fingerprint(m) for m in bpy.data.materials}
    old={n:(points(bpy.data.objects[n].data)[0],records(bpy.data.objects[n].data),[(v.hide,v.select) for v in bpy.data.objects[n].data.vertices]) for n in geo.TARGETS}
    supports={n:points(bpy.data.objects[n].data) for n in ALL_TARGETS-geo.TARGETS}
    counts={k:len(getattr(bpy.data,k)) for k in ('objects','meshes','materials','images','collections','actions')}
    from tower_south_handrail import mesh_flags
    support_flags={n:mesh_flags(bpy.data.objects[n].data) for n in (detail.STEEL,detail.PLATES)}
    baseline_surface=surface_baseline(plan)
    open_scene(out/'after.blend');after=scene_validate({'features':features});changed=compare_reports(before,after,ALL_TARGETS|detail.ADDED,detail.ADDED)
    require(state==protected(),'Protected scene metadata/counts changed')
    require(materials=={n:material_fingerprint(bpy.data.materials[n]) for n in materials},'Original materials changed')
    require(set(m.name for m in bpy.data.materials)-set(materials)=={detail.PREFIX+k for k in detail.MATERIALS},'Unexpected material')
    for k,v in counts.items():require(len(getattr(bpy.data,k))==v+dict(objects=4,meshes=4,materials=5,collections=1).get(k,0),'Unexpected datablock count: '+k)
    audit=read(out/'build.json')['audit'];checks={}
    for name,(vs,fs,vflags) in old.items():
        m=bpy.data.objects[name].data;nv,nf=points(m);rows=records(m);a=audit[name]
        require(vs==nv[:len(vs)],'Original vertex moved')
        require(vflags==[(v.hide,v.select) for v in m.vertices[:len(vs)]],'Original vertex flags changed')
        # Saved face records outside the clipping area remain exactly identical.
        from collections import Counter
        retained=Counter(rows[:a['retained_faces']]);local=[geo.local(v) for v in vs]
        source_outside=0.;preserved=0;cut_count=0
        for row in fs:
            poly=[local[i] for i in row[0]]
            if max(v[2] for v in poly)>.61:parts,removed=[poly],[]
            else:parts,removed=geo.subtract(poly,plan['scopes'])
            if sum(geo.area(p) for p in removed)<1e-8:
                require(retained[row]>0,'Outside face or attributes changed');retained[row]-=1;preserved+=1
            else:cut_count+=1
            source_outside+=sum(geo.area(p) for p in parts)
        saved_outside=0.;inside_residual=0.;residual_faces=[]
        for row in rows[:a['retained_faces']]:
            poly=[geo.local(nv[i]) for i in row[0]];saved_outside+=geo.area(poly)
            if max(v[2] for v in poly)<=.61001:
                residual=sum(geo.area(p) for p in geo.subtract(poly,plan['scopes'])[1]);inside_residual+=residual
                if residual>1e-5:residual_faces.append((residual,poly))
        require(abs(source_outside-saved_outside)<.06,'Outside surface area changed')
        require(inside_residual<.015,'Old fragments retained inside scope: '+str((name,inside_residual,sorted(residual_faces,reverse=True)[:8])))
        replacement=plan['replacement'][name];offset=a['replacement_vertex_start'];newvs=nv[offset:];newfs=[[i-offset for i in r[0]] for r in rows[a['retained_faces']:]]
        require(newfs==replacement['faces'],'Replacement topology differs from pinned plan')
        require(len(newvs)==len(replacement['vertices']),'New vertex count differs')
        for p,q in zip(newvs,replacement['vertices']):require(math.dist(geo.local(p),q)<2e-5,'Replacement coordinates differ')
        for q in replacement['vertices']:require(geo.inside(q,plan['scopes']),'Replacement outside declared scope')
        require(all(r[1:]==(0,False,False,False) for r in rows[a['retained_faces']:]),'Replacement flags differ')
        shape={}
        if name.startswith('pavement'):
            shape,_=check_mesh([geo.local(p) for p in newvs],newfs,((33.49,63.01),(19.99,60.51),(-1.61,.761)))
        else:
            require(all(abs(geo.local(p)[2]-.3-detail.profile(*geo.local(p)[:2],plan))<.0001 for p in newvs),'Road profile differs')
            require(all(geo.area([newvs[i] for i in f])>1e-8 for f in newfs),'Degenerate road triangle')
        checks[name]={'preserved_faces':preserved,'cut_faces':cut_count,'source_vertices_exact':True,'outside_area_error_m2':abs(source_outside-saved_outside),'remaining_old_inside_area_m2':inside_residual,'new_shape':shape}
    support_checks=inspect_supports(supports,support_flags,plan,config)
    surface_samples=inspect_surface(plan,audit,baseline_surface)
    return {'ok':True,'surface_samples':surface_samples,'changed_objects':changed,'support_checks':support_checks,'protected_objects':len(before['objects'])-9,'objects':len(after['objects']),'checks':checks,'warnings':after['warnings'],'limits':after['limits']+plan['limits']}

def inspect_supports(old,flags,plan,config):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from tower_south_handrail import mesh_flags
    from validate_tower_structure import check_mesh
    stats={};high=0
    for name in (detail.STEEL,detail.PLATES):
        m=bpy.data.objects[name].data;nv,nf=points(m);ov,of=old[name]
        require(of==nf and len(ov)==len(nv) and mesh_flags(m)==flags[name],'Support topology or attributes changed')
        for a,b in zip(ov,nv):
            require(a[:2]==b[:2],'Support horizontal position changed')
            if a[2]>=30:require(a==b,'Support above 30m changed');high+=1
            else:
                t=max(0.,min(1.,(a[2]-2.)/28.));dz=5*(1-t*t*(3-2*t))
                require(abs(b[2]-a[2]-dz)<1e-4,'Unexpected support height change')
        m.calc_loop_triangles();stats[name],parts=check_mesh(nv,[tuple(t.vertices) for t in m.loop_triangles],((-55,55),(-55,55),(1,334)))
        if name==detail.PLATES:plate_parts=parts
    stone=bpy.data.objects[detail.STONE];stats['caps'],caps=check_mesh(*points(stone.data),((-50,50),(-45,50),(-2,7.01)))
    require(len(caps)==4,'Expected four plinths')
    require(all(abs(c['bounds'][2][1]-7)<1e-4 for c in caps),'Plinth top differs')
    steel=bpy.data.objects[detail.STEEL].data;bv=BVHTree.FromPolygons([v.co for v in steel.vertices],[p.vertices[:] for p in steel.polygons]);contacts=[]
    require(len(plate_parts)==80,'Plate/bolt count changed')
    for part in plate_parts:
        if len(part['vertices'])!=8:continue
        x,y,z=part['center'];near=bv.find_nearest(Vector((x,y,7.11)))
        require(near is not None and near[3]<.16,'Plate disconnected from steel')
        for x,y,z in part['vertices']:
            hit,co,n,i=stone.ray_cast(Vector((x,y,8)),Vector((0,0,-1)))
            require(hit and abs(co.z-7)<1e-4,'Plate corner lacks support')
        contacts.append(float(near[3]))
    require(len(contacts)==16,'Expected sixteen supported plates')
    # Check complete parking groups against original saved coordinates.
    ov,of=old[detail.MARKS];nv,nf=points(bpy.data.objects[detail.MARKS].data);expected=[];expected_faces=[]
    for i in range(15):
        if i in config['remove_parking_bays']:continue
        offset=len(expected);expected.extend(ov[i*24:i*24+24]);expected_faces.extend(tuple(offset+j-i*24 for j in f) for f in of[i*18:i*18+18])
    require(nv==expected and nf==expected_faces,'Parking removal exceeds declared whole bays')
    stats['parking'],marks=check_mesh(nv,nf,((-200,200),(-200,200),(-1,5)))
    require(len(marks)==3*(15-len(config['remove_parking_bays'])),'Parking bay stroke count differs')
    ground=bpy.data.objects[detail.GROUND].data;nv,nf=points(ground);ov,of=old[detail.GROUND]
    require(nv[:8]==ov and nf[:5]==[f for i,f in enumerate(of) if i!=1],'Ground sides/bottom or original corners changed')
    for p in nv[8:]:
        if not geo.inside(geo.local(p),plan['scopes'],.0001):require(p[2]==0,'Ground outside scope changed height')
    # Triangles avoid nonplanarity assumptions; the complete original ground
    # box, including its replacement top, must be a single closed volume.
    ground.calc_loop_triangles();stats['ground'],gs=check_mesh(nv,[tuple(t.vertices) for t in ground.loop_triangles],((-15001,15001),(-15001,15001),(-2.01,.31)))
    require(len(gs)==1,'Ground shell disconnected')
    paving=bpy.data.objects[detail.PAVING];stats['apron'],_=check_mesh(*points(paving.data),((-37,37),(-71,-28),(-.1,4.41)))
    from tower_foundation_geometry_v4 import width
    ov,of=old[detail.PAVING];nv,nf=points(paving.data)
    require(of==nf and len(ov)==len(nv),'Apron topology changed')
    boundary_count=0
    for a,b in zip(ov,nv):
        require(a[:2]==b[:2],'Apron footprint changed')
        if abs(abs(a[0])-width(a[1]))<1e-5 or a[1]<=-70 or a[1]>-29 or a[2]<0:
            require(a==b,'Apron outer edge, threshold or underside changed');boundary_count+=1
    for x in (-7,0,7):
        hit,co,n,i=paving.ray_cast(Vector((x,-29.1,8)),Vector((0,0,-1)))
        require(hit and abs(co.z-4.4)<1e-4,'South entrance threshold disconnected')
    hit,co,n,i=paving.ray_cast(Vector((0,-55,8)),Vector((0,0,-1)))
    require(hit and abs(co.z-3.2)<1e-4,'South lot relative height differs')
    from tower_site_v3 import rotation
    for name in sorted(detail.ADDED):
        o=bpy.data.objects[name];m=o.data
        require(not o.modifiers and not o.parent and not o.constraints and not o.animation_data and len(m.materials)==1,'Unsupported added detail')
        require(all(abs(o.matrix_world[i][j]-rotation()[i][j])<1e-7 for i in range(4) for j in range(4)),'Detail transform differs')
        m.calc_loop_triangles();stats[name],parts=check_mesh(*([tuple(v.co) for v in m.vertices],[tuple(t.vertices) for t in m.loop_triangles]),((-55,55),(-45,52),(-2.01,30)))
        if name.endswith('/ stairs'):
            tops=sorted(p['bounds'][2][1] for p in parts)
            require(len(tops)==8 and all(abs(z-(-1.44+(i+1)*.275))<1e-4 for i,z in enumerate(tops)),'Saved stair riser sequence differs')
    return dict(meshes=stats,unchanged_vertices_at_or_above_30m=high,steel_contact_max_distance_m=max(contacts),
        plates=16,all_plate_corners_supported=True,removed_parking_bays=config['remove_parking_bays'],south_threshold_m=4.4,south_lot_model_height_m=3.2,unchanged_apron_boundary_and_bottom_vertices=boundary_count)


def surface_baseline(plan):
    """Record inherited tactile tiles / furniture, without exempting new overlaps."""
    import bpy
    from mathutils import Vector
    d=plan['replacement']['pavement_0 unified road'];dg=bpy.context.evaluated_depsgraph_get();hits={}
    for fi,f in enumerate(d['faces']):
        ps=[d['vertices'][i] for i in f]
        if len(ps)!=3 or not all(abs(p[2]-.46)<.0001 for p in ps):continue
        x,y=[sum(p[k] for p in ps)/3 for k in (0,1)]
        hit,co,n,i,obj,m=bpy.context.scene.ray_cast(dg,Vector(geo.world((x,y,1.95))),Vector((0,0,-1)),distance=2.5)
        if hit and obj.name not in ALL_TARGETS|detail.ADDED:hits[fi]=(obj.name,float(co.z))
    return hits

def inspect_surface(plan,audit,baseline):
    import bpy
    from mathutils import Vector
    dg=bpy.context.evaluated_depsgraph_get();samples=0;blockers=[];inherited=[]
    name='pavement_0 unified road';mesh=bpy.data.objects[name].data
    for fi,face in enumerate(list(mesh.polygons)[audit[name]['retained_faces']:]):
        ps=[geo.local(mesh.vertices[i].co) for i in face.vertices]
        if len(ps)!=3 or not all(abs(p[2]-.46-detail.profile(*p[:2],plan))<.0001 for p in ps):continue
        q=tuple(sum(p[k] for p in ps)/3 for k in range(3));origin=Vector(geo.world((q[0],q[1],q[2]+1.49)))
        hit,co,n,i,obj,m=bpy.context.scene.ray_cast(dg,origin,Vector((0,0,-1)),distance=2.5)
        if not hit or obj.name!=name or abs(co.z-q[2])>.005:
            previous=baseline.get(fi)
            if hit and previous and abs(q[2]-.46)<.0001 and obj.name==previous[0] and abs(co.z-previous[1])<.0001:
                inherited.append({'point':q,'object':obj.name,'height':float(co.z)})
            else:blockers.append((q,obj.name if hit else None,float(co.z) if hit else None))
        samples+=1
    stair_samples=0
    for step in plan['steps']:
        x=sum(p[0] for p in step['polygon'])/4;y=sum(p[1] for p in step['polygon'])/4;z=step['height']
        hit,co,n,i,obj,m=bpy.context.scene.ray_cast(dg,Vector(geo.world((x,y,z+1))),Vector((0,0,-1)),distance=2)
        require(hit and obj.name==detail.PREFIX+'stairs' and abs(co.z-z)<1e-4,'Stair tread obstructed or underground')
        stair_samples+=1
    require(samples and not blockers,'Walking surface obstructed: '+str(blockers[:10]))
    return dict(saved_top_triangle_centroids=samples,stair_tread_centroids=stair_samples,blockers=blockers,inherited_surface_details=inherited,
        limits='Point samples detect introduced obstruction. Unchanged tactile tiles and street furniture are recorded against baseline; not a continuous clearance or accessibility certificate.')

def render(source,out,phase,preview):
    from blender_worker import render as scene_render
    cameras=read(CAMERAS)
    if preview:cameras['views']=[v for v in cameras['views'] if v['id'] in ('foundation-close','foundation-north','site-overhead','north-stairs','base-joints')]
    validate_cameras(cameras);open_scene(source if phase=='render-before' else out/'after.blend')
    settings={'device':'OPTIX','width':960 if preview else 1280,'height':636 if preview else 848,'samples':12 if preview else 32,'seed':0}
    result=scene_render({'output':str(out),'cameras':cameras,'settings':settings},phase);result.update(settings=settings,cameras_sha256=digest(CAMERAS));return result

def main():
    import bpy
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',required=True,choices=('build','validate','render-before','render-after'));p.add_argument('--input',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--preview',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    source=a.input.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);config=read(CONFIG);plan=read(PLAN);report=out/(a.phase+'.json')
    require(not report.exists() and source!=out/'after.blend','Refusing to overwrite')
    require(digest(source)==config['input_sha256'] and digest(PLAN)==config['plan_sha256'],'Pinned input differs')
    require(bpy.app.version_string=='4.5.1 LTS' and not bpy.context.preferences.filepaths.use_scripts_auto_execute,'Blender environment differs')
    names=('tower_ground_v7.py','tower_ground_geometry_v7.py','prepare_tower_ground_v7.py','tower_registration_geometry_v6.py','tower_footway_v5.py','tower_footway_geometry_v5.py','prepare_tower_footway_v5.py','tower_foundation_v4.py','tower_foundation_geometry_v4.py','tower_structure_v1.py','blender_worker.py','review.py','validate_tower_structure.py','validate_tower_foottown.py','tower_site_v3.py','tower_south_handrail.py','tower_foottown_v2.py','tower_site_geometry_v3.py')
    code={n:digest(ROOT/'scripts'/n) for n in names};candidate_hash=digest(out/'after.blend') if a.phase!='build' else None
    if a.phase=='build':
        require(not (out/'after.blend').exists(),'Candidate already exists');result=build(source,out,config,plan)
    elif a.phase=='validate':result=validate(source,out,config,plan)
    else:result=render(source,out,a.phase,a.preview)
    require(digest(source)==config['input_sha256'],'Original changed')
    if candidate_hash:require(digest(out/'after.blend')==candidate_hash,'Candidate changed')
    require(all(digest(ROOT/'scripts'/n)==h for n,h in code.items()),'Code changed during phase')
    result.update(input_sha256=config['input_sha256'],candidate_sha256=digest(out/'after.blend'),source_and_candidate_protected=True,blender_version=bpy.app.version_string,code_sha256=code,configuration_sha256=digest(CONFIG),plan_sha256=digest(PLAN));write(report,result);print('OK: '+a.phase)
if __name__=='__main__':main()
