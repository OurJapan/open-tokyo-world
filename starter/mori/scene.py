"""Build, independently reopen and compare one landmark replacement."""
import sys, json, hashlib, math, argparse, importlib.util
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path[:0]=[str(HERE),str(ROOT/'scripts'),str(HERE.parent/'plateau')]
import tile, profile, facade
import mori_entrance_v1, mori_terrace_v1
spec=importlib.util.spec_from_file_location('plateau_scene',HERE.parent/'plateau/scene.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
VIEWS=[('full',(-430,253,165),(450,600,230),520),('crown',(-430,253,307),(180,260,120),120),('podium',(-440,278,20),(85,140,105),175),('entrance',(-409,312,1),(45,9,42),60)]
ID='otw:jp:tokyo:minato:azabudai-mori-jp'

def material_state(m):
    def val(v):
        if isinstance(v,(str,int,float,bool)):return v
        try:return list(v)
        except TypeError:return str(v)
    return {'name':m.name,'nodes':[{ 'name':n.name,'type':n.bl_idname,'operation':getattr(n,'operation',None),'blend_type':getattr(n,'blend_type',None),'uv_map':getattr(n,'uv_map',None),'image':getattr(getattr(n,'image',None),'name',None),'inputs':[(s.identifier,val(s.default_value)) for s in n.inputs if hasattr(s,'default_value')]} for n in m.node_tree.nodes], 'links':sorted((l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier) for l in m.node_tree.links)}

def state(o):
    data={'mesh':base.digest(o),'matrix':[list(r) for r in o.matrix_world],'hidden':o.hide_render,'materials':[material_state(m) for m in o.data.materials],'properties':{k:o[k] for k in ['gml_id','batch_id','legacy_z_shift_m','otw_feature_id','otw_part_id'] if k in o}}
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()

def objects():return {o.name:o for o in bpy.context.scene.objects if o.type=='MESH'}

def new_object(name):
    if bpy.data.objects.get(name):raise ValueError('Duplicate part '+name)
    mesh=bpy.data.meshes.new(name);o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);return o

def podium(tri):
    o=new_object('Mori JP podium / stone');mesh=o.data
    mesh.from_pydata(tri.reshape(-1,3).tolist(),[],np.arange(len(tri)*3).reshape(-1,3).tolist());mesh.update()
    for name,color,metal,rough in [('glazing',(.16,.25,.30),.45,.16),('terrace',(.34,.37,.34),0,.7),('paving',(.42,.43,.41),0,.75)]:
        m=bpy.data.materials.new('Mori podium / '+name);m.use_nodes=True
        p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
        mesh.materials.append(m)
    glass=mesh.materials[0];n=glass.node_tree.nodes;l=glass.node_tree.links
    geo=n.new('ShaderNodeNewGeometry');xyz=n.new('ShaderNodeSeparateXYZ');l.new(geo.outputs['Position'],xyz.inputs[0])
    mod=n.new('ShaderNodeMath');mod.operation='MODULO';mod.inputs[1].default_value=5.2;l.new(xyz.outputs['Z'],mod.inputs[0])
    band=n.new('ShaderNodeMath');band.operation='LESS_THAN';band.inputs[1].default_value=.27;l.new(mod.outputs[0],band.inputs[0])
    color=n.new('ShaderNodeMixRGB');color.inputs[1].default_value=(.16,.25,.30,1);color.inputs[2].default_value=(.52,.54,.53,1)
    l.new(band.outputs[0],color.inputs[0]);l.new(color.outputs[0],n.get('Principled BSDF').inputs['Base Color'])
    for f in mesh.polygons:
        if abs(f.normal.z)>.7:f.material_index=2 if f.center.z<1 else 1
    return o

def floors_and_roof(radii):
    # Retain the legacy inferred floor/ceiling and roof elevations. No furnishings.
    o=new_object('Mori independent / floors and roof')
    theta=np.arange(160)*math.tau/160;directions=np.column_stack((np.cos(theta),np.sin(theta)))
    vertices=[];faces=[];slots=[]
    def slab(z,thickness,inset,contour_z,slot):
        pts=np.array(profile.CENTER)+directions*(np.asarray(radii)*(1-.014*((contour_z-165)/165)**2)-inset)[:,None]
        start=len(vertices);n=len(pts)
        vertices.extend((float(x),float(y),zz) for zz in [z,z+thickness] for x,y in pts)
        local=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        faces.extend(tuple(start+i for i in f) for f in local);slots.extend([slot]*len(local))
    levels=np.r_[np.linspace(.32,24.32,5),np.linspace(29.22,318.32,60)]
    for z0,z1 in zip(levels,levels[1:]):
        slab(z0+.02,.2,.24,z0,0)
        slab(min(z1-.48,z0+3.30),.14,.24,z0,1)
    slab(318.6,.35,1,319,2)
    o.data.from_pydata(vertices,[],faces);o.data.update()
    for color in [(.30,.27,.235),(.38,.4,.39),(.43,.415,.375)]:
        m=bpy.data.materials.new('Mori inferred slab');m.use_nodes=True
        p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=.7
        o.data.materials.append(m)
    for f,slot in zip(o.data.polygons,slots):f.material_index=slot
    return o

def build(out):
    base.build(out)
    scene=bpy.context.scene
    # Shared daylight rig: illuminate the inspected northeast facade in both states.
    bpy.data.objects['Starter sun'].rotation_euler=(-.5,.5,0)
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.6,.68,.78,1)
    before={n:state(o) for n,o in objects().items()}
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'before.blend'),compress=True)
    matches=[o for o in objects().values() if o.get('gml_id')==profile.FEATURE]
    profile.target_index([o.get('gml_id') for o in objects().values()])
    target=matches[0]
    vertices=np.array([tuple(v.co) for v in target.data.vertices]);faces=np.array([tuple(f.vertices) for f in target.data.polygons])
    triangles=vertices[faces]
    radii=profile.cross_section(triangles)
    low=profile.lowrise(triangles)
    created=facade.build(radii)+[podium(low),floors_and_roof(radii)]
    for module in [mori_entrance_v1,mori_terrace_v1]:
        for name in sorted(module.TARGETS):
            o=new_object(name);o.hide_render=True;module.apply(o);created.append(o)
    for o in created:
        o['otw_feature_id']=ID;o['otw_part_id']=o.name;o['source_gml_id']=profile.FEATURE
        o['source_sha256']=tile.FILES['data221.b3dm'][2]
        o['accuracy']='photo-guided estimates; legacy display height'
    bpy.data.objects.remove(target,do_unlink=True)
    scene['replacement_gml_id']=profile.FEATURE
    after={n:state(o) for n,o in objects().items()}
    unchanged=set(before)-{profile.FEATURE}
    if any(before[n]!=after[n] for n in unchanged):raise ValueError('Changed unrelated object')
    ref={'before':before,'after':after,'unchanged':sorted(unchanged),'parts':sorted(o.name for o in created),'profile_radii':radii,'feature_id':ID,'source_gml_id':profile.FEATURE,'podium_triangles':len(low),'legacy_input_used':False,'interior_scope':'inferred floor/ceiling slabs and roof only; no furniture','road_input_included':False}
    (out/'replacement.json').write_text(json.dumps(ref,indent=2)+'\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'after.blend'),compress=True)

def validate(out,which):
    bpy.ops.wm.open_mainfile(filepath=str(out/(which+'.blend')),use_scripts=False)
    ref=json.loads((out/'replacement.json').read_text());geo=json.loads((out/'georeference.json').read_text())
    meshes=objects();scene=bpy.context.scene
    if set(meshes)!=set(ref[which]):raise ValueError('Object set mismatch')
    if bpy.data.libraries or bpy.data.texts or bpy.data.sounds:raise ValueError('Unexpected dependencies')
    images=[i for i in bpy.data.images if i.type!='RENDER_RESULT']
    if len(images)!=1 or not images[0].packed_file or hashlib.sha256(images[0].packed_file.data).hexdigest()!=geo['image_sha256']:raise ValueError('Missing source image')
    triangles=0
    for name,o in meshes.items():
        if state(o)!=ref[which][name]:raise ValueError('Object/material fingerprint mismatch: '+name)
        if o.parent or o.modifiers or o.constraints:raise ValueError('Unexpected mesh dependency')
        if not all(math.isfinite(c) for v in o.data.vertices for c in v.co):raise ValueError('Nonfinite coordinate')
        o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
        if any(t.area<=1e-10 for t in o.data.loop_triangles):raise ValueError('Degenerate geometry: '+name)
    if which=='after':
        if any(o.get('gml_id')==profile.FEATURE for o in meshes.values()):raise ValueError('Duplicate source tower')
        if len([o for o in meshes.values() if o.get('otw_feature_id')==ID])!=13:raise ValueError('Incorrect detailed part count')
        roof=meshes['Mori independent / floors and roof']
        if len(roof.data.polygons)!=129*162 or abs(max(v.co.z for v in roof.data.vertices)-318.95)>.001:raise ValueError('Missing floor or roof slabs')
        if len(meshes['Mori JP podium / stone'].data.polygons)!=1070:raise ValueError('Podium face loss')
        for name in ref['unchanged']:
            if state(meshes[name])!=ref['before'][name]:raise ValueError('Unrelated object changed')
        glass=meshes['Mori continuous pearl glass / pearl grey coated glass']
        for m in glass.data.materials:
            bs=m.node_tree.nodes.get('Principled BSDF')
            if bs.inputs['Emission Strength'].default_value!=0:raise ValueError('Daytime emission')
            if abs(bs.inputs['Transmission Weight'].default_value-.12)>1e-6:raise ValueError('Glass transmission changed')
        pts=np.array([tuple(v.co) for v in glass.data.vertices]);angles=np.degrees(np.arctan2(pts[:,1]-253.4,pts[:,0]+430.39))%360
        for angle in [18.28125,109.6875,198.28125,286.875]:
            nearby=pts[np.abs((angles-angle+180)%360-180)<1]
            if abs(nearby[:,2].max()-331.1)>.1:raise ValueError('Crown peak misplaced')
    if triangles>2000000 or (out/(which+'.blend')).stat().st_size>100000000:raise ValueError('Trial geometry/storage budget exceeded')
    pictures={}
    for name,center,offset,scale in VIEWS:
        target=Vector(center);cam=scene.camera;cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=scale;cam.data.clip_end=3000
        scene.timeline_markers.clear();scene.cycles.device='CPU';scene.cycles.seed=0;scene.cycles.samples=16
        scene.render.resolution_x=960;scene.render.resolution_y=720;scene.render.resolution_percentage=100
        bpy.context.view_layer.update()
        if name=='full':
            from bpy_extras.object_utils import world_to_camera_view
            targets=[o for o in meshes.values() if o.get('gml_id')==profile.FEATURE or o.get('otw_feature_id')==ID]
            for o in targets:
                for corner in o.bound_box:
                    q=world_to_camera_view(scene,cam,o.matrix_world@Vector(corner))
                    if not (0<q.x<1 and 0<q.y<1 and .1<q.z<3000):raise ValueError('Landmark outside full camera')
        path=out/(which+'-'+name+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
        im=bpy.data.images.load(str(path),check_existing=False);px=np.array(im.pixels[:]).reshape(-1,4)
        if tuple(im.size)!=(960,720) or not np.isfinite(px).all() or px[:,:3].std()<.01:raise ValueError('Bad image')
        bpy.data.images.remove(im);pictures[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    (out/(which+'-validation.json')).write_text(json.dumps({'ok':True,'blender':bpy.app.version_string,'meshes':len(meshes),'triangles':triangles,'blend_bytes':(out/(which+'.blend')).stat().st_size,'saved_reopened':True,'renders':pictures,'cameras':VIEWS,'render_settings':{'engine':'CYCLES','device':'CPU','samples':16,'seed':0,'resolution':[960,720]},'full_camera_bounds_checked':True},indent=2)+'\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--folder',type=Path,required=True);ap.add_argument('--phase',choices=['build','before','after'],required=True)
    a=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
    if bpy.app.version!=(4,5,1):raise ValueError('Requires Blender 4.5.1')
    if a.phase=='build':build(a.folder)
    else:validate(a.folder,a.phase)
