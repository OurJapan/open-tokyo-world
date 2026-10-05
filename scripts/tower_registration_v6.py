# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Provisional OSM plinth registration; saved-scene audit and matched views."""
import argparse,json,sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import tower_footway_geometry_v5 as geo
import tower_registration_geometry_v6 as feet
ALL_TARGETS=geo.TARGETS|feet.TARGETS
from tower_site_v3 import open_scene,read,write,points
from review import require,digest,compare_reports,validate_cameras
CONFIG=ROOT/'areas/tokyo-tower/tower-registration-v6-input.json'
PLAN=ROOT/'areas/tokyo-tower/tower-registration-v6-plan.json'
CAMERAS=ROOT/'areas/tokyo-tower/tower-registration-v6-cameras.json'

def protected():
    import tower_foundation_v4 as previous
    old=previous.geo.TARGETS
    try:
        previous.geo.TARGETS=ALL_TARGETS
        return previous.protected_state()
    finally:previous.geo.TARGETS=old

def records(mesh):
    return [(tuple(p.vertices),p.material_index,p.use_smooth,p.hide,p.select) for p in mesh.polygons]

def build(source,out,config,plan):
    import bpy
    from blender_worker import mesh_fingerprint
    open_scene(source);audit={}
    for name in sorted(geo.TARGETS):
        obj=bpy.data.objects[name];m=obj.data
        require(mesh_fingerprint(m)==config['objects'][name]['hash'],'Pinned mesh differs')
        require(m.users==1 and not m.uv_layers and not m.shape_keys and not obj.modifiers and not obj.parent and not obj.constraints and not obj.animation_data,'Unsupported mesh')
        require(all(abs(obj.matrix_world[i][j]-(i==j))<1e-7 for i in range(4) for j in range(4)),'Nonidentity target')
        require(not any(e.use_seam or e.use_edge_sharp or e.hide for e in m.edges),'Unsupported edge attributes')
        require(set(a.name for a in m.attributes)<= {'position','.edge_verts','.corner_vert','.corner_edge','.select_vert','.select_edge','.select_poly','sharp_face','sharp_edge','material_index','.hide_vert','.hide_edge','.hide_poly'},'Unsupported custom attribute: '+str([(a.name,a.domain,a.data_type) for a in m.attributes]))
        vs=[tuple(v.co) for v in m.vertices];local=[geo.local(v) for v in vs];oldn=len(vs)
        vflags=[(v.hide,v.select) for v in m.vertices];eflags={tuple(sorted(e.vertices)):e.select for e in m.edges}
        fs=[];flags=[];cut_count=0;removed_area=0.
        for ids,mat,smooth,hide,select in records(m):
            poly=[local[i] for i in ids]
            if max(v[2] for v in poly)>.61:outside,removed=[poly],[]
            else:outside,removed=geo.subtract(poly,plan['scopes'])
            amount=sum(geo.area(p) for p in removed)
            if amount<1e-8:fs.append(ids);flags.append((mat,smooth,hide,select));continue
            cut_count+=1;removed_area+=amount
            for part in outside:
                n=len(vs);vs.extend(geo.world(p) for p in part);fs.append(tuple(range(n,len(vs))));flags.append((mat,smooth,hide,select))
        retained_face_count=len(fs);replacement=plan['replacement'][name];offset=len(vs)
        vs.extend(geo.world(p) for p in replacement['vertices'])
        fs.extend(tuple(offset+i for i in f) for f in replacement['faces']);flags.extend((0,False,False,False) for f in replacement['faces'])
        m.clear_geometry();m.from_pydata(vs,[],fs)
        for p,flag in zip(m.polygons,flags):p.material_index,p.use_smooth,p.hide,p.select=flag
        for v,flag in zip(m.vertices,vflags):v.hide,v.select=flag
        for e in m.edges:e.select=eflags.get(tuple(sorted(e.vertices)),False)
        m.update()
        audit[name]={'source_vertices':oldn,'cut_faces':cut_count,'removed_area_m2':removed_area,'retained_faces':retained_face_count,'replacement_vertex_start':offset,'replacement_faces':len(replacement['faces'])}
    for name in sorted(feet.TARGETS):
        obj=bpy.data.objects[name];m=obj.data
        require(mesh_fingerprint(m)==config['objects'][name]['hash'],'Pinned support mesh differs')
        require(m.users==1 and not m.uv_layers and not m.shape_keys and not obj.parent and not obj.constraints and not obj.animation_data,'Unsupported support mesh')
        for v in m.vertices:v.co=feet.point(v.co,plan['caps'],name==feet.STONE)
        m.update()
    for m in bpy.data.materials:
        if m.users==0:m.use_fake_user=True
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'after.blend'),check_existing=False)
    return {'ok':True,'audit':audit,'changed_objects':sorted(ALL_TARGETS),'added_objects':[]}

def validate(source,out,config,plan):
    import bpy
    from blender_worker import validate as scene_validate,material_fingerprint
    from validate_tower_structure import check_mesh
    features=read(ROOT/'areas/tokyo-tower/foottown-v2-features.json')
    open_scene(source);before=scene_validate({'features':features});state=protected()
    materials={m.name:material_fingerprint(m) for m in bpy.data.materials}
    old={n:(points(bpy.data.objects[n].data)[0],records(bpy.data.objects[n].data),[(v.hide,v.select) for v in bpy.data.objects[n].data.vertices]) for n in geo.TARGETS}
    supports={n:points(bpy.data.objects[n].data) for n in feet.TARGETS}
    from tower_south_handrail import mesh_flags
    support_flags={n:mesh_flags(bpy.data.objects[n].data) for n in feet.TARGETS}
    open_scene(out/'after.blend');after=scene_validate({'features':features});changed=compare_reports(before,after,ALL_TARGETS)
    require(state==protected(),'Protected scene metadata/counts changed')
    require(materials=={m.name:material_fingerprint(m) for m in bpy.data.materials},'Materials changed')
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
            shape,_=check_mesh([geo.local(p) for p in newvs],newfs,((-51.01,67.01),(-63.01,61.01),(.299,.461)))
        else:
            require(all(abs(p[2]-.3)<1e-5 for p in newvs),'Road level differs')
            require(all(geo.area([newvs[i] for i in f])>1e-8 for f in newfs),'Degenerate road triangle')
        checks[name]={'preserved_faces':preserved,'cut_faces':cut_count,'source_vertices_exact':True,'outside_area_error_m2':abs(source_outside-saved_outside),'remaining_old_inside_area_m2':inside_residual,'new_shape':shape}
    support_checks=inspect_supports(supports,support_flags,plan)
    surface_samples=inspect_surface(plan)
    return {'ok':True,'surface_samples':surface_samples,'changed_objects':changed,'support_checks':support_checks,'protected_objects':len(before['objects'])-6,'objects':len(after['objects']),'checks':checks,'warnings':after['warnings'],'limits':after['limits']+plan['limits']}

def inspect_supports(old,flags,plan):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from tower_south_handrail import mesh_flags
    from validate_tower_structure import check_mesh
    stats={};high=0;max_move=0.
    for name,(ov,of) in old.items():
        m=bpy.data.objects[name].data;nv,nf=points(m)
        require(of==nf and len(ov)==len(nv) and mesh_flags(m)==flags[name],'Support topology or attributes changed')
        for a,b in zip(ov,nv):
            require(a[2]==b[2],'Support height changed')
            if a[2]>=30:require(a==b,'Support above 30m changed');high+=1
            max_move=max(max_move,math.dist(a,b))
            require(math.dist(a,b)<12.,'Support displacement exceeds local budget')
        # A per-leg deformation must never pull opposite sides of a connected
        # member apart. Its active zone must remain separated into quadrants.
        for e in m.edges:
            a,b=(ov[i] for i in e.vertices)
            if min(a[2],b[2])<30 and name!=feet.STONE:
                require(a[0]*b[0]>0 and a[1]*b[1]>0,'Active deformation crosses leg partition')
        m.calc_loop_triangles()
        stats[name],parts=check_mesh(nv,[tuple(t.vertices) for t in m.loop_triangles],((-55,55),(-55,55),(-1,334)))
        if name==feet.STONE:
            require(len(parts)==4,'Expected four plinths')
            for part in parts:
                x,y,z=part['center'];cap=min(plan['caps'],key=lambda c:math.dist((x,y),c['center']))
                require(math.dist((x,y),cap['center'])<1e-4,'Saved cap centroid differs from mapped rectangle')
                require(abs(z-1)<1e-5 and abs(part['size'][2]-2)<1e-5,'Cap height changed')
                for q in part['vertices']:
                    require(min(math.dist(q[:2],r) for r in cap['rectangle'])<1e-4,'Saved cap corner differs from mapped rectangle')
        if name==feet.PLATES:plate_parts=parts
    require(len(plate_parts)==80,'Plate and bolt count differs')
    steel=bpy.data.objects[feet.STEEL].data
    bv=BVHTree.FromPolygons([v.co for v in steel.vertices],[p.vertices[:] for p in steel.polygons])
    stone=bpy.data.objects[feet.STONE];contacts=[]
    for part in plate_parts:
        if len(part['vertices'])!=8:continue
        x,y,z=part['center'];near=bv.find_nearest(Vector((x,y,2.11)))
        require(near is not None and near[3]<.16,'Plate no longer contacts steel')
        # Every plate corner, not just its centre, must be supported.
        for q in part['vertices']:
            v=Vector(q)
            hit,co,n,index=stone.ray_cast(Vector((v.x,v.y,3)),Vector((0,0,-1)))
            require(hit and abs(co.z-2)<1e-4,'Plate corner outside cap')
        contacts.append(float(near[3]))
    require(len(contacts)==16,'Expected 16 supported plates')
    return dict(meshes=stats,unchanged_vertices_at_or_above_30m=high,maximum_displacement_m=max_move,
        steel_contact_max_distance_m=max(contacts),all_plate_corners_supported=True)


def inspect_surface(plan):
    import bpy
    from mathutils import Vector
    dg=bpy.context.evaluated_depsgraph_get();samples=0;blockers=[]
    mesh=bpy.data.objects['pavement_0 unified road'].data
    # Actual saved replacement triangles, tested above the walking surface.
    for face in mesh.polygons:
        ps=[geo.local(mesh.vertices[i].co) for i in face.vertices]
        if len(ps)!=3 or not all(abs(p[2]-.46)<1e-5 for p in ps):continue
        q=tuple(sum(p[k] for p in ps)/3 for k in range(3))
        if not geo.inside(q,plan['scopes'],-.001):continue
        origin=Vector(geo.world((q[0],q[1],1.95)))
        hit,co,n,i,obj,m=bpy.context.scene.ray_cast(dg,origin,Vector((0,0,-1)),distance=2.5)
        if not hit or obj.name!='pavement_0 unified road' or abs(co.z-.46)>.005:
            blockers.append({'point':q,'object':obj.name if hit else None,'height':float(co.z) if hit else None})
        samples+=1
    require(samples>0 and not blockers,'Walking surface obstructed: '+str(blockers[:8]))
    return {'saved_top_triangle_centroids':samples,'maximum_probe_height_m':1.95,'blockers':blockers,'limits':'Centroid probes are not a full continuous clearance or accessibility certificate.'}


def render(source,out,phase,preview):
    from blender_worker import render as scene_render
    cameras=read(CAMERAS)
    if preview:cameras['views']=[v for v in cameras['views'] if v['id'] in ('foundation-close','foundation-north','site-overhead')]
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
    names=('tower_registration_v6.py','tower_registration_geometry_v6.py','prepare_tower_registration_v6.py','tower_footway_geometry_v5.py','prepare_tower_footway_v5.py','tower_foundation_v4.py','tower_foundation_geometry_v4.py','tower_structure_v1.py','blender_worker.py','review.py','validate_tower_structure.py','validate_tower_foottown.py','tower_site_v3.py','tower_south_handrail.py')
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
