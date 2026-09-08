# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Blender 4.5.1 worker for the pinned single-tile trial."""
import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import tile
spec=importlib.util.spec_from_file_location('plaza_source',HERE.parent/'plaza/scene.py')
plaza=importlib.util.module_from_spec(spec);spec.loader.exec_module(plaza)


def digest(obj):
    h=hashlib.sha256(plaza.mesh_digest(obj.data).encode())
    for uv in obj.data.uv_layers:
        for loop in uv.data:h.update(np.asarray(loop.uv,dtype='<f4').tobytes())
    return h.hexdigest()


def build(folder):
    doc,buf,ids=tile.parse(tile.verify('data221.b3dm',(folder/'inputs/data221.b3dm').read_bytes()))
    region=tile.parent(tile.verify('tileset.json',(folder/'inputs/tileset.json').read_bytes()))
    primitives,decoder_hash=tile.decode(doc,buf)
    # Only create the independently licensed six-part starter in a new scene.
    plaza.build(folder,.9)
    scene=bpy.context.scene
    for key in list(scene.keys()):del scene[key]
    scene.name='PLATEAU one-tile trial'
    view=doc['bufferViews'][0]
    webp=tile.section(buf,view.get('byteOffset',0),view['byteLength'])
    (folder/'source-texture.webp').write_bytes(webp)
    image=bpy.data.images.load(str(folder/'source-texture.webp'),check_existing=False)
    if min(image.size)<=0:raise ValueError('WebP decode failed')
    image.pack()
    materials=[]
    for i,source in enumerate(doc['materials']):
        m=bpy.data.materials.new('PLATEAU source material '+str(i));m.use_nodes=True
        bs=m.node_tree.nodes.get('Principled BSDF');pbr=source['pbrMetallicRoughness']
        bs.inputs['Base Color'].default_value=tuple(pbr.get('baseColorFactor',[1,1,1,1]))
        bs.inputs['Metallic'].default_value=pbr.get('metallicFactor',1)
        bs.inputs['Roughness'].default_value=pbr.get('roughnessFactor',1)
        if 'baseColorTexture' in pbr:
            texture=m.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image;texture.extension='EXTEND'
            m.node_tree.links.new(texture.outputs['Color'],bs.inputs['Base Color'])
        materials.append(m)
    positions=[tile.enu(a['POSITION'],doc['extensions']['CESIUM_RTC']['center']) for a,_,_ in primitives]
    features=[]
    for batch_id,gid in enumerate(ids):
        chunks=[xyz[a['_BATCHID']==batch_id] for xyz,(a,_,_) in zip(positions,primitives)]
        original=np.concatenate(chunks)
        if not len(original):raise ValueError('Empty feature')
        dz=.32-float(original[:,2].min())
        vertices=[];faces=[];uvs=[];mat_ids=[]
        for xyz,(arrays,ix,mat) in zip(positions,primitives):
            selected=ix[arrays['_BATCHID'][ix[:,0]]==batch_id]
            # Explicit per-triangle vertices keep UV/batch identity through save/reopen.
            for face in selected:
                start=len(vertices)
                pts=xyz[face].copy();pts[:,2]+=dz
                vertices.extend(pts.tolist());faces.append((start,start+1,start+2));mat_ids.append(mat)
                uv=arrays.get('TEXCOORD_0')
                uvs.extend([(float(u),1-float(v)) for u,v in uv[face]] if uv is not None else [(0.,0.)]*3)
        mesh=bpy.data.meshes.new(gid);mesh.from_pydata(vertices,[],faces);mesh.update()
        obj=bpy.data.objects.new(gid,mesh);scene.collection.objects.link(obj)
        obj['gml_id']=gid;obj['batch_id']=batch_id;obj['legacy_z_shift_m']=dz
        obj['source_sha256']=tile.FILES['data221.b3dm'][2]
        obj['source_license']='PLATEAU site policy; see NOTICE.md'
        for m in materials:mesh.materials.append(m)
        uv_layer=mesh.uv_layers.new(name='Source UV')
        for face,mat in zip(mesh.polygons,mat_ids):face.material_index=mat
        for loop,uv in zip(uv_layer.data,uvs):loop.uv=uv
        features.append({'gml_id':gid,'batch_id':batch_id,'triangles':len(faces),'source_enu_min':original.min(axis=0).tolist(),'source_enu_max':original.max(axis=0).tolist(),'legacy_z_shift_m':dz})
    scene.camera.data.type='ORTHO';scene.camera.data.ortho_scale=750;scene.camera.data.clip_end=3000
    target=Vector((-500,340,140));scene.camera.location=target+Vector((650,-900,700))
    scene.camera.rotation_euler=(target-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.resolution_x=960;scene.render.resolution_y=720;scene.cycles.samples=16
    scene['coordinate_mode']='legacy-compatible-per-feature-ground-0.32'
    meshes={o.name:o for o in scene.objects if o.type=='MESH'}
    manifest={'features':features,'mesh_hashes':{k:digest(v) for k,v in meshes.items()},'image_sha256':hashlib.sha256(webp).hexdigest(),'image_size':list(image.size),'decoder_sha256':decoder_hash,'source_region_radians_ellipsoid_height':region,'origin':{'longitude':139.74543,'latitude':35.65858,'ellipsoid_height':0},'transform':'glTF (x,-z,y) + RTC -> ECEF -> ENU; then per-feature z shift','limitations':['Legacy display height, not surveyed ground','Source PLATEAU building, not previously refined Mori model','No road or terrain input','24 source features plus six inferred plaza parts']}
    (folder/'georeference.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'scene.blend'),compress=True)


def validate(folder):
    bpy.ops.wm.open_mainfile(filepath=str(folder/'scene.blend'))
    ref=json.loads((folder/'georeference.json').read_text(encoding='utf8'))
    scene=bpy.context.scene
    meshes={o.name:o for o in scene.objects if o.type=='MESH'}
    expected=plaza.EXPECTED | {f['gml_id'] for f in ref['features']}
    if len(ref['features'])!=24 or set(meshes)!=expected or len(bpy.data.scenes)!=1 or len(bpy.data.objects)!=32:
        raise ValueError('Unexpected scene/object count')
    if bpy.data.libraries or bpy.data.texts or bpy.data.sounds:raise ValueError('Unexpected dependency')
    images=[im for im in bpy.data.images if im.type!='RENDER_RESULT']
    if len(images)!=1 or not images[0].packed_file or hashlib.sha256(images[0].packed_file.data).hexdigest()!=ref['image_sha256']:
        raise ValueError('Missing/changed packed source texture')
    if list(images[0].size)!=ref['image_size'] or min(images[0].size)<=0:raise ValueError('Invalid texture pixels')
    # Check that the packed image is actually connected to the rendered source material.
    for i,roughness,metallic in [(0,0.,0.),(1,.3,.5)]:
        mat=bpy.data.materials.get('PLATEAU source material '+str(i))
        if not mat or not mat.use_nodes:raise ValueError('Missing source material')
        bs=mat.node_tree.nodes.get('Principled BSDF')
        if not bs or abs(bs.inputs['Roughness'].default_value-roughness)>1e-6 or abs(bs.inputs['Metallic'].default_value-metallic)>1e-6:
            raise ValueError('Changed source material factors')
        links=list(bs.inputs['Base Color'].links)
        if i==1 and (len(links)!=1 or links[0].from_node.type!='TEX_IMAGE' or links[0].from_node.image!=images[0]):
            raise ValueError('Missing source texture link')
        if i==0 and links:raise ValueError('Unexpected texture link')
    total=0
    for name,obj in meshes.items():
        if digest(obj)!=ref['mesh_hashes'][name]:raise ValueError('Mesh/UV mismatch '+name)
        if obj.modifiers or obj.constraints or obj.parent:raise ValueError('Unexpected geometry dependency')
        if any(abs(obj.matrix_world[i][j]-float(i==j))>1e-6 for i in range(4) for j in range(4)):raise ValueError('Unexpected transform')
        if not all(math.isfinite(c) for v in obj.data.vertices for c in v.co):raise ValueError('Nonfinite vertex')
        obj.data.calc_loop_triangles()
        if any(t.area<=1e-10 for t in obj.data.loop_triangles):raise ValueError('Degenerate triangle '+name)
        if name not in plaza.EXPECTED:total+=len(obj.data.loop_triangles)
    for f in ref['features']:
        o=meshes[f['gml_id']]
        if o.get('gml_id')!=f['gml_id'] or o.get('batch_id')!=f['batch_id'] or abs(o.get('legacy_z_shift_m',0)-f['legacy_z_shift_m'])>1e-8:raise ValueError('Changed feature identity')
        if [m.name for m in o.data.materials]!=['PLATEAU source material 0','PLATEAU source material 1']:raise ValueError('Changed material slots')
    if total!=4804:raise ValueError('Triangle count changed')
    pictures={}
    for name,center,offset,scale in [('overview',(-500,340,140),(650,-900,700),750),('entrance',(-409,312,1),(45,9,42),60)]:
        target=Vector(center);scene.camera.location=target+Vector(offset)
        scene.camera.rotation_euler=(target-scene.camera.location).to_track_quat('-Z','Y').to_euler()
        scene.camera.data.ortho_scale=scale
        bpy.context.view_layer.update()
        if name=='overview':
            from bpy_extras.object_utils import world_to_camera_view
            for obj in meshes.values():
                for vertex in obj.data.vertices:
                    q=world_to_camera_view(scene,scene.camera,vertex.co)
                    if not (.01<q.x<.99 and .01<q.y<.99 and .1<q.z<3000):raise ValueError('Object outside overview camera')
        scene.render.filepath=str(folder/(name+'.png'));bpy.ops.render.render(write_still=True)
        im=bpy.data.images.load(scene.render.filepath,check_existing=False)
        px=np.empty(len(im.pixels),dtype=np.float32);im.pixels.foreach_get(px);rgb=px.reshape(-1,4)[:,:3]
        if list(im.size)!=[960,720] or not np.isfinite(px).all() or float(rgb.std())<.01:raise ValueError('Invalid render')
        pictures[name]={'sha256':hashlib.sha256((folder/(name+'.png')).read_bytes()).hexdigest(),'width':960,'height':720,'rgb_std':float(rgb.std())}
        bpy.data.images.remove(im)
    (folder/'validation.json').write_text(json.dumps({'ok':True,'blender':bpy.app.version_string,'mesh_count':len(meshes),'source_feature_count':24,'source_triangles':total,'packed_texture_verified':True,'source_material_links_verified':True,'overview_framing_verified':True,'feature_ids_verified':True,'mesh_uv_hashes_verified':True,'renders':pictures},indent=2)+'\n')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--folder',required=True,type=Path);ap.add_argument('--phase',choices=['build','validate'],required=True)
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
    if bpy.app.version!=(4,5,1):raise ValueError('This profile requires Blender 4.5.1')
    (build if args.phase=='build' else validate)(args.folder.resolve())
