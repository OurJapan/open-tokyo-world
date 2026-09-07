"""Internal Blender worker. No source file is saved in place."""
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def packed_hash(image):
    if image.packed_file:
        return hashlib.sha256(image.packed_file.data).hexdigest()
    return None


def array_prop(collection, prop, width, dtype):
    values=np.empty(len(collection)*width,dtype=dtype)
    collection.foreach_get(prop,values)
    return values


def mesh_fingerprint(mesh):
    h=hashlib.sha256()
    coords=array_prop(mesh.vertices,'co',3,np.float32)
    if not np.isfinite(coords).all(): raise ValueError('Non-finite mesh: '+mesh.name)
    loops=array_prop(mesh.loops,'vertex_index',1,np.int32)
    if len(loops) and (loops.min()<0 or loops.max()>=len(mesh.vertices)): raise ValueError('Invalid mesh index: '+mesh.name)
    for values in [coords,loops,array_prop(mesh.polygons,'loop_start',1,np.int32),array_prop(mesh.polygons,'loop_total',1,np.int32),array_prop(mesh.polygons,'material_index',1,np.int32)]:
        h.update(values.tobytes())
    for uv in mesh.uv_layers:
        h.update(uv.name.encode()); h.update(array_prop(uv.data,'uv',2,np.float32).tobytes())
    return h.hexdigest()


def material_fingerprint(material):
    if material is None: return None
    nodes=[];links=[]
    if material.use_nodes:
        for n in material.node_tree.nodes:
            inputs=[]
            for socket in n.inputs:
                if hasattr(socket,'default_value'):
                    v=socket.default_value
                    if hasattr(v,'to_list'): v=v.to_list()
                    elif not isinstance(v,(str,int,float,bool,type(None))):
                        try: v=list(v)
                        except TypeError: v=getattr(v,'name',str(v))
                    inputs.append((socket.identifier,v))
            nodes.append((n.name,n.bl_idname,inputs,getattr(getattr(n,'image',None),'name',None)))
        links=[(l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier) for l in material.node_tree.links]
    payload=[material.name,list(material.diffuse_color),nodes,sorted(links)]
    return hashlib.sha256(json.dumps(payload,sort_keys=True,default=str).encode()).hexdigest()


def prepare(job):
    seen={}
    for feature in job['features']['features']:
        for name in feature['collections']:
            collection=bpy.data.collections.get(name)
            if collection is None: raise ValueError('Missing required collection: '+name)
            collection['otw_feature_id']=feature['id']
            for obj in collection.all_objects:
                if obj.name in seen and seen[obj.name]!=feature['id']: raise ValueError('Overlapping feature mapping: '+obj.name)
                seen[obj.name]=feature['id']
                obj['otw_feature_id']=feature['id']
                obj['otw_legacy_name']=obj.name
    out=Path(job['output'])
    if Path(bpy.data.filepath).resolve() in ((out/'before.blend').resolve(),(out/'after.blend').resolve()): raise ValueError('Output equals input')
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'before.blend'),compress=True)
    patch=job['patch']
    if patch:
        for op in patch['operations']:
            obj=bpy.data.objects.get(op['object'])
            if obj is None or obj.get('otw_feature_id')!=op['feature_id']: raise ValueError('Patch target not in specified feature')
            if obj.animation_data or obj.constraints or obj.parent: raise ValueError('Translation adapter requires unanimated, unparented object without constraints')
            if op['op']=='translate_object':
                for i,value in enumerate(op['translation_m']): obj.location[i]+=value
            elif op['op'] in ('mori_crown_material_v1','mori_facade_v2'):
                if obj.type!='MESH' or mesh_fingerprint(obj.data)!=op['expected_mesh_sha256']:
                    raise ValueError('Crown material baseline mesh differs')
                if len(obj.data.materials)!=1 or material_fingerprint(obj.data.materials[0])!=op['expected_material_sha256']:
                    raise ValueError('Crown material baseline shader differs')
                sys.path.insert(0,str(Path(__file__).resolve().parent))
                if op['op']=='mori_facade_v2':
                    import mori_facade_v2
                    mori_facade_v2.apply(obj)
                else:
                    import mori_crown_material
                    mori_crown_material.apply(obj)
            elif op['op'] in ('mori_entrance_v1','mori_terrace_v1'):
                if obj.type!='MESH' or mesh_fingerprint(obj.data)!=op['expected_mesh_sha256']:
                    raise ValueError('Entrance baseline mesh differs')
                sys.path.insert(0,str(Path(__file__).resolve().parent))
                if op['op']=='mori_terrace_v1':
                    import mori_terrace_v1 as detail
                else:
                    import mori_entrance_v1 as detail
                detail.apply(obj)
            elif op['op'] in ('mori_podium_v2','mori_podium_v3'):
                if obj.type!='MESH' or mesh_fingerprint(obj.data)!=op['expected_mesh_sha256']:
                    raise ValueError('Podium baseline mesh differs')
                sys.path.insert(0,str(Path(__file__).resolve().parent))
                if op['op']=='mori_podium_v3':
                    import mori_podium_v3 as podium
                else:
                    import mori_podium_v2 as podium
                podium.apply(obj,job['geometry_source'])
            elif op['op'] in ('mori_plaza_v1','mori_plaza_link_v1'):
                if obj.type!='MESH' or mesh_fingerprint(obj.data)!=op['expected_mesh_sha256']:raise ValueError('Plaza anchor differs')
                sys.path.insert(0,str(Path(__file__).resolve().parent))
                if op['op']=='mori_plaza_link_v1':
                    import mori_plaza_link_v1 as detail
                else:
                    import mori_plaza_v1 as detail
                detail.apply(op,mesh_fingerprint)
            elif op['op'] in ('mori_shape_v1','mori_crown_v2'):
                if obj.type!='MESH' or mesh_fingerprint(obj.data)!=op['expected_mesh_sha256']:
                    raise ValueError('Shape patch baseline mesh differs')
                sys.path.insert(0,str(Path(__file__).resolve().parent))
                if op['op']=='mori_crown_v2':
                    import mori_crown_v2
                    mori_crown_v2.apply(obj)
                else:
                    import mori_shape
                    mori_shape.apply(obj)
            else: raise ValueError('Unsupported patch')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'after.blend'),compress=True)
    return {'ok':True,'mapped_objects':len(seen),'patch_applied':bool(patch)}


def validate(job):
    errors=[];warnings=[];objects={};assets=[];meshes={};mats={}
    scene=bpy.context.scene
    scene.frame_set(1)
    for obj in scene.objects:
        transform=[float(x) for row in obj.matrix_world for x in row]
        if not all(math.isfinite(x) for x in transform): errors.append('Non-finite transform: '+obj.name)
        entry={'type':obj.type,'transform':transform,'feature_id':obj.get('otw_feature_id'),'hide_render':obj.hide_render}
        if obj.type=='MESH':
            key=obj.data.as_pointer()
            if key not in meshes:
                try: meshes[key]=mesh_fingerprint(obj.data)
                except ValueError as e: errors.append(str(e)); meshes[key]='invalid'
            entry['mesh']=meshes[key]
            entry['materials']=[]
            for slot in obj.material_slots:
                mat=slot.material
                key=mat.as_pointer() if mat else 0
                if key not in mats: mats[key]=material_fingerprint(mat)
                entry['materials'].append(mats[key])
            if obj.get('otw_feature_id') and not len(obj.data.vertices):
                targets={op['object'] for op in (job.get('patch') or {}).get('operations',[])}
                reason=job['features'].get('legacy_empty_objects',{}).get(obj.name)
                if reason and obj.name not in targets: warnings.append('Known empty legacy mesh: '+obj.name+'; '+reason)
                else: errors.append('Empty required mesh: '+obj.name)
            if obj.modifiers: warnings.append('Modifier stack not fingerprinted: '+obj.name)
        objects[obj.name]=entry
    for image in bpy.data.images:
        if image.source in ('VIEWER','GENERATED'): continue
        entry={'type':'image','name':image.name,'source':image.source,'packed_sha256':packed_hash(image)}
        if image.source!='FILE': errors.append('Unsupported image dependency: '+image.name)
        elif not image.packed_file and not Path(bpy.path.abspath(image.filepath)).is_file(): errors.append('Missing image: '+image.name)
        else:
            try:
                if min(image.size)<=0 or len(image.pixels)<4 or not all(math.isfinite(v) for v in image.pixels[:4]): raise ValueError('Invalid image pixels')
                entry['size']=list(image.size)
            except Exception: errors.append('Image decode probe failed: '+image.name)
        assets.append(entry)
    for group in ('libraries','fonts','volumes','movieclips','sounds','cache_files'):
        for item in getattr(bpy.data,group,[]):
            path=getattr(item,'filepath','')
            if group=='fonts' and path=='<builtin>': continue
            packed=bool(getattr(item,'packed_file',None))
            if not packed and (not path or not Path(bpy.path.abspath(path)).is_file()): errors.append('Missing dependency: '+group+'/'+item.name)
            assets.append({'type':group,'name':item.name,'packed':packed})
    expected={f['id'] for f in job['features']['features']}
    found={o.get('otw_feature_id') for o in scene.objects}
    if not expected<=found: errors.append('Missing feature IDs')
    return {'ok':not errors,'errors':errors,'warnings':warnings,'objects':objects,'assets':sorted(assets,key=lambda a:(a['type'],a['name'])),'counts':{'objects':len(objects),'vertices':sum(len(o.data.vertices) for o in scene.objects if o.type=='MESH'),'polygons':sum(len(o.data.polygons) for o in scene.objects if o.type=='MESH')},'limits':['No geographic accuracy certification','No complete modifier/animation/node-group fingerprint','Image decode checks dimensions and a pixel probe; not all image samples','No manifold/zero-area/normal checks','External asset content hashes not yet recorded']}


def render(job, phase):
    s=bpy.context.scene; settings=job['settings']; out=Path(job['output']); views=[]
    # Blender re-evaluates camera-bound timeline markers when rendering a still.
    # Clear only in this disposable render process; never save these changes.
    s.timeline_markers.clear()
    s.render.engine='CYCLES'; s.cycles.samples=settings['samples']; s.cycles.seed=settings['seed']
    s.cycles.use_animated_seed=False; s.cycles.use_adaptive_sampling=False
    s.cycles.use_denoising=True; s.render.use_motion_blur=False
    s.render.resolution_x=settings['width'];s.render.resolution_y=settings['height'];s.render.resolution_percentage=100
    s.render.pixel_aspect_x=1;s.render.pixel_aspect_y=1;s.render.use_border=False
    s.render.use_compositing=False;s.render.use_sequencer=False
    s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='8'
    s.render.film_transparent=False
    devices=[]
    if settings['device']=='OPTIX':
        prefs=bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type='OPTIX';prefs.get_devices()
        for d in prefs.devices: d.use=(d.type=='OPTIX')
        devices=[d.name for d in prefs.devices if d.use]
        if not devices: raise ValueError('No OptiX device; explicitly select CPU if required')
        s.cycles.device='GPU'
    else: s.cycles.device='CPU'
    data=bpy.data.cameras.new('OTW review camera'); camera=bpy.data.objects.new('OTW review camera',data); s.collection.objects.link(camera)
    for view in job['cameras']['views']:
        s.frame_set(view.get('frame',1)); s.camera=camera
        camera.matrix_world=Matrix(view['matrix_world'])
        data.type='PERSP';data.lens=view['lens_mm'];data.sensor_width=view['sensor_width_mm'];data.sensor_height=view['sensor_height_mm'];data.sensor_fit=view['sensor_fit'];data.shift_x=view['shift_x'];data.shift_y=view['shift_y'];data.clip_start=view['clip_start'];data.clip_end=view['clip_end'];data.dof.use_dof=False
        s.render.filepath=str(out/(phase.removeprefix('render-')+'-'+view['id']+'.png'))
        started=time.monotonic(); bpy.ops.render.render(write_still=True)
        if s.camera != camera: raise ValueError('Review camera was overridden during render')
        image=bpy.data.images.load(s.render.filepath,check_existing=False)
        try:
            pixels=np.asarray(image.pixels[:],dtype=np.float32).reshape(-1,4)
            if list(image.size)!=[settings['width'],settings['height']] or not np.isfinite(pixels).all(): raise ValueError('Invalid render dimensions/pixels')
            if pixels[:,:3].max()<=1/255 or pixels[:,3].max()==0: raise ValueError('Black/transparent render')
            views.append({'id':view['id'],'seconds':round(time.monotonic()-started,3),'sha256':hashlib.sha256(Path(s.render.filepath).read_bytes()).hexdigest(),'pixel_sha256':hashlib.sha256(pixels.tobytes()).hexdigest(),'rgb_min':float(pixels[:,:3].min()),'rgb_max':float(pixels[:,:3].max()),'active_camera':s.camera.name,'camera_matrix_world':[list(r) for r in s.camera.matrix_world]})
        finally: bpy.data.images.remove(image)
    return {'ok':True,'views':views,'devices':devices,'human_camera_acceptance':'pending'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--job',required=True);p.add_argument('--phase',required=True);p.add_argument('--report',required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);job=load(a.job)
    result={'ok':False}
    try:
        if bpy.app.version_string!=job['settings']['blender_version']: raise ValueError('Blender version differs from lock')
        if a.phase=='prepare': result=prepare(job)
        elif a.phase.startswith('validate-'): result=validate(job)
        elif a.phase.startswith('render-'): result=render(job,a.phase)
        else: raise ValueError('Unknown worker phase')
        if not result['ok']: raise ValueError('Validation failed')
    except Exception as e:
        result['error']=str(e); raise
    finally:
        Path(a.report).write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


if __name__=='__main__': main()
