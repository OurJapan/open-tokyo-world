# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Bounded shared south grade, inclined plinths and source-backed rail correction."""
import argparse,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import tower_site_geometry_v8 as geo
import tower_footway_geometry_v5 as xy
from tower_site_v3 import open_scene,read,write,points
from review import require,digest,compare_reports,validate_cameras
CONFIG=ROOT/'areas/tokyo-tower/tower-site-v8-input.json'
PLAN=ROOT/'areas/tokyo-tower/tower-site-v8-plan.json'
CAMERAS=ROOT/'areas/tokyo-tower/tower-ground-v7-cameras.json'


def metadata():
    import bpy,tower_foottown_v2 as old
    from validate_tower_foottown import protected_metadata,json_value
    saved=old.CHANGED,old.ADDED
    try:
        old.CHANGED=geo.TARGETS;old.ADDED=set();state=protected_metadata()
    finally:old.CHANGED,old.ADDED=saved
    state['targets']={n:{'props':{k:json_value(o[k]) for k in o.keys()},
        # Disabled objects are absent from the dependency graph after reopening;
        # their matrix_world can be identity despite unchanged saved transforms.
        'matrix':[list(r) for r in (o.matrix_basis if n==geo.RAILS else o.matrix_world)],
        'hidden':None if n==geo.RAILS else (o.hide_render,o.hide_viewport,o.hide_get()),
        'collections':sorted(c.name for c in o.users_collection),
        'modifiers':[(m.name,m.type) for m in o.modifiers],
        'materials':[m.name if m else None for m in o.data.materials]}
        for n in geo.TARGETS for o in [bpy.data.objects[n]]}
    return state


def rows(m):return [(tuple(p.vertices),p.material_index,p.use_smooth,p.hide,p.select) for p in m.polygons]


def replace(o,vs,fs,attributes=None):
    m=o.data;m.clear_geometry();m.from_pydata(vs,[],fs);m.update()
    if attributes:
        for p,r in zip(m.polygons,attributes):p.material_index,p.use_smooth,p.hide,p.select=r


def intersects(poly,box):
    return min(p[0] for p in poly)<box[2] and max(p[0] for p in poly)>box[0] and min(p[1] for p in poly)<box[3] and max(p[1] for p in poly)>box[1]


def surface(o,plan):
    """Retain outside faces exactly; clip/densify only the declared local scope."""
    from mathutils import Vector
    m=o.data;vs,fs=points(m);old_rows=rows(m);local=[xy.local(o.matrix_world@Vector(p)) for p in vs]
    vertex_flags=[(v.hide,v.select) for v in m.vertices]
    edge_flags={tuple(sorted(e.vertices)):(e.hide,e.select,e.use_seam,e.use_edge_sharp) for e in m.edges}
    inverse=o.matrix_world.inverted();kept=[];new=[];origins=[];ids={}
    masks=list(plan['masks'])
    if o.name=='parking mapped land use':
        masks.append([(-4.,-70.),(4.,-70.),(36.5,-55.),(36.5,-29.),(-36.5,-29.),(-36.5,-55.)])
    boxes=[(min(p[0] for p in r),min(p[1] for p in r),max(p[0] for p in r),max(p[1] for p in r)) for r in masks]
    m.calc_loop_triangles();triangles={}
    for t in m.loop_triangles:triangles.setdefault(t.polygon_index,[]).append(tuple(t.vertices))
    def emit(poly,attrs,warp):
        for tri in ((poly[0],poly[i],poly[i+1]) for i in range(1,len(poly)-1)):
            for tri in geo.subdivide(tri) if warp else [tri]:
                if xy.area(tri)<1e-8:continue
                face=[]
                for p in tri:
                    key=tuple(round(q,8) for q in p)
                    if key not in ids:
                        ids[key]=len(vs);origins.append(p)
                        q=(p[0],p[1],p[2]+geo.grade(*p[:2]));vs.append(tuple(inverse@Vector(xy.world(q))))
                    face.append(ids[key])
                new.append((tuple(face),*attrs))
    for i,row in enumerate(old_rows):
        poly=[local[j] for j in row[0]]
        if max(p[2] for p in poly)>1.5 or not (intersects(poly,geo.BOUNDS) or any(intersects(poly,b) for b in boxes)):
            kept.append((i,row));continue
        for tri in triangles[i]:
            poly=[local[j] for j in tri];outside,inside=xy.cut(poly,geo.BOUNDS) if intersects(poly,geo.BOUNDS) else ([poly],[])
            for part,warp in [(p,False) for p in outside]+([(inside,True)] if inside else []):
                parts=[part]
                for mask,box in zip(masks,boxes):
                    parts=[q for p in parts for q in (geo.clip_convex(p,mask) if intersects(p,box) else [p])]
                for p in parts:emit(p,row[1:],warp)
    result=[r for i,r in kept]+new
    replace(o,vs,[r[0] for r in result],[r[1:] for r in result])
    for v,flags in zip(m.vertices,vertex_flags):v.hide,v.select=flags
    for e in m.edges:
        key=tuple(sorted(e.vertices))
        if key in edge_flags:e.hide,e.select,e.use_seam,e.use_edge_sharp=edge_flags[key]
    return dict(original_vertices=len(local),retained_faces=len(kept),changed_source_faces=len(fs)-len(kept),new_faces=len(new),retained_indices=[i for i,r in kept],origins=origins)


def move_details(o):
    from mathutils import Vector
    vs,fs=points(o.data);local=[xy.local(o.matrix_world@Vector(p)) for p in vs];moved=0;excluded=[]
    for group in geo.components(vs,fs):
        ps=[local[i] for i in group]
        if not any(geo.grade(*p[:2])>1e-6 for p in ps):continue
        if min(p[2] for p in ps)>1.5 or max(p[2] for p in ps)>3:
            excluded.append(dict(vertices=len(group),bounds=[(min(p[k] for p in ps),max(p[k] for p in ps)) for k in range(3)]));continue
        for i in group:
            dz=geo.grade(*local[i][:2])
            if dz:
                # Ground furniture in this pinned source has an identity linear transform.
                o.data.vertices[i].co.z+=dz;moved+=1
    o.data.update();return dict(moved_vertices=moved,excluded_high_components=excluded)


def build(source,out,config,plan):
    import bpy
    from blender_worker import mesh_fingerprint
    open_scene(source)
    for n in geo.TARGETS:
        o=bpy.data.objects[n];m=o.data
        require(mesh_fingerprint(m)==config['objects'][n]['hash'],'Pinned mesh differs: '+n)
        require(m.users==1 and not m.uv_layers and not m.shape_keys and not o.parent and not o.constraints and not o.animation_data,'Unsupported target: '+n)
    audit={}
    for n in sorted(geo.SURFACES):
        print('Surface: '+n,flush=True);audit[n]=surface(bpy.data.objects[n],plan)
    for n in sorted(geo.DETAILS):audit[n]=move_details(bpy.data.objects[n])
    for n in (geo.STONE,geo.JOINTS):
        m=bpy.data.objects[n].data
        old=[tuple(v.co) for v in m.vertices]
        new=geo.cladding_vertices(old,plan['caps'],plan['slopes']) if n==geo.STONE else [geo.incline(p,plan['caps'],plan['slopes']) for p in old]
        for v,p in zip(m.vertices,new):v.co=p
        m.update()
    m=bpy.data.objects[geo.PAVING].data
    from tower_foundation_geometry_v4 import grid
    count=sum(len(row) for row in grid())
    for v in list(m.vertices)[:count]:v.co.z=.115+geo.grade(v.co.x,v.co.y)
    m.update()
    # The original eight box corners and five side/bottom faces survive.
    o=bpy.data.objects[geo.GROUND];vs,fs=points(o.data);vs=vs[:8];fs=fs[:5]
    lookup={tuple(round(x,6) for x in p):i for i,p in enumerate(vs)}
    for d in plan['ground_top'].values():
        ids=[]
        for p in d['vertices']:
            key=tuple(round(x,6) for x in p)
            if key not in lookup:lookup[key]=len(vs);vs.append(tuple(p))
            ids.append(lookup[key])
        fs.extend(tuple(ids[i] for i in f) for f in d['faces'])
    replace(o,vs,fs)
    bpy.data.objects[geo.RAILS].hide_render=True;bpy.data.objects[geo.RAILS].hide_viewport=True
    write(out/'surface-audit.json',audit)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'after.blend'),check_existing=False)
    return dict(ok=True,audit_sha256=digest(out/'surface-audit.json'),surfaces={n:{k:v for k,v in a.items() if k not in ('origins','retained_indices')} for n,a in audit.items()},allowed_objects=sorted(geo.TARGETS))


def validate(source,out,config,plan):
    import bpy
    from mathutils import Vector
    from blender_worker import validate as scene_validate,material_fingerprint
    from validate_tower_structure import check_mesh
    from tower_south_handrail import mesh_flags
    features=read(ROOT/'areas/tokyo-tower/foottown-v2-features.json')
    open_scene(source);before=scene_validate({'features':features});state=metadata()
    materials={m.name:material_fingerprint(m) for m in bpy.data.materials}
    counts={k:len(getattr(bpy.data,k)) for k in ('objects','meshes','materials','images','collections','actions')}
    originals={n:(points(bpy.data.objects[n].data),rows(bpy.data.objects[n].data),mesh_flags(bpy.data.objects[n].data)) for n in geo.TARGETS}
    audit=read(out/'surface-audit.json');require(digest(out/'surface-audit.json')==read(out/'build.json')['audit_sha256'],'Audit changed')
    open_scene(out/'after.blend');after=scene_validate({'features':features});changed=compare_reports(before,after,geo.TARGETS)
    require(state==metadata(),'Protected metadata changed')
    require(materials=={m.name:material_fingerprint(m) for m in bpy.data.materials},'Materials changed')
    require(counts=={k:len(getattr(bpy.data,k)) for k in counts},'Datablocks changed')
    checks={};surface_samples=[]
    for n in geo.SURFACES:
        print('Validate surface: '+n,flush=True)
        o=bpy.data.objects[n];m=o.data;nv,nf=points(m);(ov,of),old_rows,flags=originals[n];a=audit[n]
        require(nv[:len(ov)]==ov,'Original surface vertex changed: '+n)
        require(rows(m)[:a['retained_faces']]==[old_rows[i] for i in a['retained_indices']],'Outside face/attribute changed: '+n)
        require(len(nv)==len(ov)+len(a['origins']),'Surface origin count differs')
        for v,p in zip(nv[len(ov):],a['origins']):
            q=xy.local(o.matrix_world@Vector(v));require(math.dist(q,(p[0],p[1],p[2]+geo.grade(*p[:2])))<3e-5,'Unexpected surface displacement')
        # Every new top triangle must remain above the shared soil. Collect
        # deterministic representative samples for the scene-level obstruction pass.
        checked=0
        for i,p in enumerate(list(m.polygons)[a['retained_faces']:]):
            ps=[xy.local(o.matrix_world@m.vertices[j].co) for j in p.vertices]
            cross=(ps[1][0]-ps[0][0])*(ps[2][1]-ps[0][1])-(ps[1][1]-ps[0][1])*(ps[2][0]-ps[0][0])
            if abs(cross)<=1e-8:continue
            q=tuple(sum(p[k] for p in ps)/3 for k in range(3))
            if n=='pavement_0 unified road':
                origin=o.matrix_world.inverted()@Vector(xy.world((q[0],q[1],8)))
                hit,co,normal,index=o.ray_cast(origin,Vector((0,0,-1)))
                if not hit or abs((o.matrix_world@co).z-q[2])>.002:continue
            hit,co,normal,index=bpy.data.objects[geo.GROUND].ray_cast(Vector(xy.world((q[0],q[1],8))),Vector((0,0,-1)))
            require(hit and co.z<=q[2]+.002,'Surface below terrain: '+str((n,q,float(co.z) if hit else None)))
            checked+=1
            if i%31==0:surface_samples.append((n,q))
        checks[n]=dict(preserved_vertices=len(ov),preserved_faces=a['retained_faces'],top_centroids_checked=checked)
    for n in geo.DETAILS:
        o=bpy.data.objects[n];nv,nf=points(o.data);(ov,of),r,flags=originals[n]
        require(nf==of and mesh_flags(o.data)==flags,'Ground detail topology or flags changed')
        local=[xy.local(o.matrix_world@Vector(p)) for p in ov];eligible=set()
        for group in geo.components(ov,of):
            if min(local[i][2] for i in group)<=1.5 and max(local[i][2] for i in group)<=3:eligible.update(group)
        moved=0
        for i,(a,b) in enumerate(zip(ov,nv)):
            require(a[:2]==b[:2],'Ground detail XY changed')
            dz=geo.grade(*local[i][:2]) if i in eligible else 0.
            require(abs(b[2]-a[2]-dz)<3e-5,'Ground detail elevation differs')
            if abs(b[2]-a[2])>1e-5:moved+=1
        checks[n]=dict(moved_vertices=moved)
    for n in (geo.STONE,geo.JOINTS):
        m=bpy.data.objects[n].data;nv,nf=points(m);(ov,of),r,flags=originals[n]
        require(nf==of and mesh_flags(m)==flags,'Cladding topology/flags changed')
        expected=geo.cladding_vertices(ov,plan['caps'],plan['slopes']) if n==geo.STONE else [geo.incline(a,plan['caps'],plan['slopes']) for a in ov]
        require(all(math.dist(b,a)<1e-5 for a,b in zip(expected,nv)),'Cladding incline differs')
        m.calc_loop_triangles();checks[n],parts=check_mesh(nv,[tuple(t.vertices) for t in m.loop_triangles],((-55,55),(-50,55),(-2.11,7.01)))
        if n==geo.STONE:
            require(len(parts)==4,'Expected four closed plinths')
            for i,(x,y,z) in enumerate(nv):
                if i%16>=4:continue
                hit,co,normal,index=bpy.data.objects[geo.GROUND].ray_cast(Vector(xy.world((x,y,8))),Vector((0,0,-1)))
                require(hit and co.z>z+.02,'Plinth bottom is exposed above ground')
    g=bpy.data.objects[geo.GROUND].data;nv,nf=points(g);(ov,of),r,flags=originals[geo.GROUND]
    require(nv[:8]==ov[:8] and nf[:5]==of[:5],'Original ground shell changed')
    g.calc_loop_triangles();checks['ground'],parts=check_mesh(nv,[tuple(t.vertices) for t in g.loop_triangles],((-15001,15001),(-15001,15001),(-2.01,4.286)))
    require(len(parts)==1,'Ground disconnected')
    paving=bpy.data.objects[geo.PAVING];m=paving.data;nv,nf=points(m);(ov,of),r,flags=originals[geo.PAVING]
    from tower_foundation_geometry_v4 import grid
    count=sum(len(row) for row in grid());require(nf==of and nv[count:]==ov[count:],'Apron underside/threshold changed')
    require(all(a[:2]==b[:2] and abs(b[2]-.115-geo.grade(*a[:2]))<1e-5 for a,b in zip(ov[:count],nv[:count])),'Apron does not follow shared grade')
    checks['apron'],_=check_mesh(nv,nf,((-37,37),(-71,-28),(-.1,4.41)))
    for x in (-7,0,7):
        hit,co,normal,index=paving.ray_cast(Vector((x,-29.1,8)),Vector((0,0,-1)))
        require(hit and abs(co.z-4.4)<1e-4,'South threshold disconnected')
    rails=bpy.data.objects[geo.RAILS];require(rails.hide_render and rails.hide_viewport,'Unsupported handrails remain visible')
    require(points(rails.data)==originals[geo.RAILS][0],'Hidden rail mesh changed')
    for step in plan['steps']:
        x,y=[sum(p[k] for p in step['polygon'])/4 for k in (0,1)];z=step['height']
        hit,co,normal,i,obj,m=bpy.context.scene.ray_cast(bpy.context.evaluated_depsgraph_get(),Vector(xy.world((x,y,z+1))),Vector((0,0,-1)),distance=2)
        require(hit and obj.name==geo.PREFIX+'stairs' and abs(co.z-z)<1e-4,'North tread blocked')
    # Compare ray obstructions at matched source/candidate points, recording
    # inherited furniture explicitly rather than allowing entire object classes.
    dg=bpy.context.evaluated_depsgraph_get();pending=[];inherited=[];clear=0
    for n,q in surface_samples:
        hit,co,normal,i,obj,m=bpy.context.scene.ray_cast(dg,Vector(xy.world((q[0],q[1],q[2]+1.49))),Vector((0,0,-1)),distance=1.6)
        if hit and obj.name in geo.SURFACES|{geo.PAVING} and -.02<=co.z-q[2]<=.36:
            clear+=1;continue
        pending.append((n,q,obj.name if hit else None,float(co.z) if hit else None))
    open_scene(source);dg=bpy.context.evaluated_depsgraph_get();blockers=[]
    for n,q,current,height in pending:
        dz=geo.grade(*q[:2]);z=q[2]-dz
        hit,co,normal,i,obj,m=bpy.context.scene.ray_cast(dg,Vector(xy.world((q[0],q[1],z+1.49))),Vector((0,0,-1)),distance=1.6)
        if hit and obj.name==current and (current in geo.DETAILS or abs(height-co.z)<.001):
            inherited.append(dict(point=q,object=current,source_height=float(co.z),height=height,
                basis='same XY footprint and independently checked per-vertex grade' if current in geo.DETAILS else 'unchanged source obstruction'))
        else:blockers.append(dict(point=q,surface=n,current=current,height=height,source=obj.name if hit else None))
    write(out/'surface-clearance.json',dict(clear=clear,inherited=inherited,blockers=blockers))
    require(not blockers,'Introduced surface obstruction: '+str(blockers[:8]))
    return dict(ok=True,changed_objects=changed,objects=len(after['objects']),protected_objects=len(before['objects'])-len(changed),checks=checks,
        stair_tread_centroids=8,surface_point_count=len(surface_samples),clear_surface_points=clear,inherited_obstructions=inherited,introduced_obstructions=blockers,
        warnings=after['warnings'],limits=after['limits']+plan['limits'])


def render(source,out,phase,preview):
    from blender_worker import render as scene_render
    cameras=read(CAMERAS)
    if preview:cameras['views']=[v for v in cameras['views'] if v['id'] in ('site-overhead','south-grade','foundation-close','foundation-north','foundation-west','north-stairs')]
    validate_cameras(cameras);open_scene(source if phase=='render-before' else out/'after.blend')
    settings={'device':'OPTIX','width':960 if preview else 1280,'height':636 if preview else 848,'samples':12 if preview else 32,'seed':0}
    result=scene_render({'output':str(out),'cameras':cameras,'settings':settings},phase);result.update(settings=settings,cameras_sha256=digest(CAMERAS));return result


def main():
    import bpy
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',required=True,choices=('build','validate','render-before','render-after'));p.add_argument('--input',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--preview',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    source=a.input.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);config=read(CONFIG);plan=read(PLAN);report=out/(a.phase+'.json')
    require(not report.exists() and source!=out/'after.blend','Refusing overwrite')
    config_hash=digest(CONFIG)
    require(digest(source)==config['input_sha256'] and digest(PLAN)==config['plan_sha256'],'Pinned inputs differ')
    require(bpy.app.version_string=='4.5.1 LTS' and not bpy.context.preferences.filepaths.use_scripts_auto_execute,'Blender environment differs')
    names=('tower_site_v8.py','tower_site_geometry_v8.py','prepare_tower_site_v8.py','prepare_tower_footway_v5.py','tower_ground_geometry_v7.py','tower_registration_geometry_v6.py','tower_footway_geometry_v5.py','tower_foundation_geometry_v4.py','tower_structure_v1.py','blender_worker.py','review.py','validate_tower_structure.py','validate_tower_foottown.py','tower_site_v3.py','tower_south_handrail.py','tower_foottown_v2.py','tower_site_geometry_v3.py')
    code={n:digest(ROOT/'scripts'/n) for n in names};candidate_hash=digest(out/'after.blend') if a.phase!='build' else None
    if a.phase=='build':
        require(not (out/'after.blend').exists(),'Candidate exists');result=build(source,out,config,plan)
    elif a.phase=='validate':result=validate(source,out,config,plan)
    else:result=render(source,out,a.phase,a.preview)
    require(digest(source)==config['input_sha256'],'Original changed')
    require(digest(CONFIG)==config_hash and digest(PLAN)==config['plan_sha256'],'Configuration changed during phase')
    if candidate_hash:require(digest(out/'after.blend')==candidate_hash,'Candidate changed')
    require(all(digest(ROOT/'scripts'/n)==h for n,h in code.items()),'Code changed during phase')
    result.update(input_sha256=config['input_sha256'],candidate_sha256=digest(out/'after.blend'),source_and_candidate_protected=True,blender_version=bpy.app.version_string,code_sha256=code,configuration_sha256=digest(CONFIG),plan_sha256=digest(PLAN));write(report,result);print('OK: '+a.phase)
if __name__=='__main__':main()
