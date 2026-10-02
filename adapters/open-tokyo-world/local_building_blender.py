"""Small, isolated GLB conversion. Never opens or saves the shared city."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import bpy
import bmesh
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'starter/plateau'))
import tile

FEATURE='bldg_af7335da-7542-44dd-964d-8cccd2b046ff'
TEXTURE_SHA='85bcc1658f6899c6cd8ae3de43bc31048db4694af428e33e6aca11bd31b9523f'


def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def source(job):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(job['input'],link=False) as (src,dst):dst.objects=list(src.objects)
    for obj in dst.objects:bpy.context.scene.collection.objects.link(obj)
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    if len(objects)!=1 or objects[0].get('gml_id')!=FEATURE:raise ValueError('Expected the single isolated source feature')
    obj=objects[0]
    if len(obj.data.vertices)!=235 or len(obj.data.polygons)!=466 or obj.modifiers or obj.animation_data:
        raise ValueError('Unexpected source geometry or modifiers')
    tile.parent(tile.verify('tileset.json',(Path(job['inputs'])/'tileset.json').read_bytes()))
    doc,buffer,ids=tile.parse(tile.verify('data221.b3dm',(Path(job['inputs'])/'data221.b3dm').read_bytes()))
    if ids[15]!=FEATURE:raise ValueError('Source identity mismatch')
    official=[]
    for image in doc['images']:
        view=doc['bufferViews'][image['bufferView']];start=view.get('byteOffset',0)
        official.append(hashlib.sha256(buffer[start:start+view['byteLength']]).hexdigest())
    packed=[image for image in bpy.data.images if image.packed_file]
    if len(packed)!=1 or hashlib.sha256(packed[0].packed_file.data).hexdigest()!=TEXTURE_SHA or TEXTURE_SHA not in official:
        raise ValueError('Only the pinned official embedded texture is allowed')
    return obj,packed[0]


def geometry(obj):
    points=[tuple(obj.matrix_world@v.co) for v in obj.data.vertices]
    triangles=[[points[i] for i in p.vertices] for p in obj.data.polygons]
    bounds=[min(p[i] for p in points) for i in range(3)]+[max(p[i] for p in points) for i in range(3)]
    return triangles,bounds


def principled(material):
    shaders=[n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED']
    if len(shaders)!=1:raise ValueError('Expected one Principled material')
    shader=shaders[0]
    for name in ('Metallic','Roughness','Alpha','Normal','Transmission Weight','Coat Weight'):
        if shader.inputs[name].is_linked:raise ValueError('Unsupported linked non-colour material input: '+name)
    return shader


def bake_facade(obj,out):
    # Only the source material using Geometry.Position/Normal needs a colour bake.
    procedural=[i for i,m in enumerate(obj.data.materials) if any(n.type=='TEX_BRICK' for n in m.node_tree.nodes)]
    if len(procedural)!=1:raise ValueError('Expected the retained single procedural facade')
    slot=procedural[0];material=obj.data.materials[slot];shader=principled(material)
    selected=[p for p in obj.data.polygons if p.material_index==slot]
    original_loops=[list(p.loop_indices) for p in selected]
    if len(selected)!=66:raise ValueError('Unexpected procedural facade face count')
    mesh=bpy.data.meshes.new('Local colour-bake mesh')
    vertices=[tuple(obj.data.vertices[i].co) for p in selected for i in p.vertices]
    mesh.from_pydata(vertices,[],[(3*i,3*i+1,3*i+2) for i in range(len(selected))]);mesh.materials.append(material)
    temporary=bpy.data.objects.new('Local colour-bake source',mesh);temporary.matrix_world=obj.matrix_world.copy()
    bpy.context.scene.collection.objects.link(temporary)
    for o in bpy.context.scene.objects:o.select_set(False)
    temporary.select_set(True);bpy.context.view_layer.objects.active=temporary
    mesh.uv_layers.new(name='WebFacadeUV')
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh.update();bpy.context.view_layer.update()
    # Edit mode replaces RNA layer storage. Reacquire it and retain plain values before baking.
    uv=temporary.data.uv_layers['WebFacadeUV']
    baked_coordinates=[[tuple(uv.data[i].uv) for i in p.loop_indices] for p in temporary.data.polygons]
    image=bpy.data.images.new('Local procedural facade colour',width=1024,height=1024,alpha=False)
    image.colorspace_settings.name='sRGB'
    target=material.node_tree.nodes.new('ShaderNodeTexImage');target.image=image;material.node_tree.nodes.active=target
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1
    scene.render.bake.use_pass_direct=False;scene.render.bake.use_pass_indirect=False;scene.render.bake.use_pass_color=True
    # Bake only the 66-face temporary mesh; the original packed atlas remains outside this render scene.
    bpy.context.scene.collection.objects.unlink(obj)
    bpy.context.view_layer.update()
    bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'},margin=8)
    bpy.context.scene.collection.objects.link(obj)
    image.filepath_raw=str(out/'facade-basecolor.png');image.file_format='PNG';image.save()
    destination=obj.data.uv_layers.new(name='WebFacadeUV')
    for loops,coordinates in zip(original_loops,baked_coordinates):
        for old_loop,coordinate in zip(loops,coordinates):destination.data[old_loop].uv=coordinate
    replacement=material.copy();replacement.name=material.name+' - local colour bake'
    new_shader=principled(replacement)
    for node in list(replacement.node_tree.nodes):
        if node.type not in ('BSDF_PRINCIPLED','OUTPUT_MATERIAL'):replacement.node_tree.nodes.remove(node)
    texture=replacement.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image
    uv_node=replacement.node_tree.nodes.new('ShaderNodeUVMap');uv_node.uv_map=destination.name
    replacement.node_tree.links.new(uv_node.outputs['UV'],texture.inputs['Vector'])
    replacement.node_tree.links.new(texture.outputs['Color'],new_shader.inputs['Base Color'])
    obj.data.materials[slot]=replacement
    material.node_tree.nodes.remove(target)
    bpy.data.objects.remove(temporary,do_unlink=True);bpy.data.meshes.remove(mesh)
    # Explicitly retain the original atlas UV for the other source material.
    original_uv=obj.data.uv_layers[0];original_uv.active_render=True;obj.data.uv_layers.active_index=0
    for index,mat in enumerate(obj.data.materials):
        if index==slot:continue
        principled(mat)
        for node in mat.node_tree.nodes:
            if node.type=='TEX_IMAGE' and not node.inputs['Vector'].is_linked:
                uv_source=mat.node_tree.nodes.new('ShaderNodeUVMap');uv_source.uv_map=original_uv.name
                mat.node_tree.links.new(uv_source.outputs['UV'],node.inputs['Vector'])
    return {'faces':len(selected),'resolution':[1024,1024],'pass':'diffuse colour only','samples':1,
            'original_uv_retained':True,'roughness_metallic_alpha_and_other_principled_constants_retained':True}


def export(job,out):
    obj,image=source(job);before,bounds=geometry(obj)
    material_state=[{'name':m.name,'faces':sum(p.material_index==i for p in obj.data.polygons),
                    'roughness':float(principled(m).inputs['Roughness'].default_value),
                    'metallic':float(principled(m).inputs['Metallic'].default_value)} for i,m in enumerate(obj.data.materials)]
    bake=bake_facade(obj,out)
    after,_=geometry(obj)
    if before!=after:raise ValueError('Colour conversion changed metre geometry')
    for key in list(obj.keys()):del obj[key]
    obj['gml_id']=FEATURE;obj['source_batch_id']=15;obj['local_review_only']=True;obj['units']='meters'
    for other in bpy.context.scene.objects:other.select_set(False)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.gltf(filepath=str(out/'model.glb'),export_format='GLB',use_selection=True,
        export_yup=True,export_extras=True,export_attributes=False,export_normals=True,export_texcoords=True,
        export_materials='EXPORT',export_image_format='AUTO',export_apply=False,export_animations=False)
    write(out/'geometry-export.json',{'ok':True,'source_vertices':235,'source_triangles':466,
        'bounds_source_xyz_m':bounds,'bounds_render_m':[bounds[0],bounds[2],-bounds[4],bounds[3],bounds[5],-bounds[1]],
        'geometry_unchanged_in_export_scene':True,'official_texture_sha256':TEXTURE_SHA,
        'source_materials':material_state,'colour_bake':bake,'units':'meters','render_axes':'east-up-south'})


def canonical(triangles):
    return np.asarray(sorted(tuple(sorted(tuple(p) for p in t)) for t in triangles))


def verify(job,out):
    obj,original_image=source(job);expected,_=geometry(obj)
    original_pixels=np.asarray(original_image.pixels[:],dtype=np.float32)
    source_roughness=[float(principled(m).inputs['Roughness'].default_value) for m in obj.data.materials]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(out/'model.glb'))
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    if len(objects)!=1 or objects[0].get('gml_id')!=FEATURE:raise ValueError('Reimported feature identity differs')
    actual,bounds=geometry(objects[0])
    if len(actual)!=466:raise ValueError('Reimported triangle count differs')
    error=float(np.max(np.abs(canonical(expected)-canonical(actual))))
    if error>5e-5:raise ValueError('GLB metre geometry or coordinate conversion differs')
    materials=objects[0].data.materials
    roughness=[float(principled(m).inputs['Roughness'].default_value) for m in materials]
    if len(materials)!=2 or max(abs(a-b) for a,b in zip(source_roughness,roughness))>1e-6:
        raise ValueError('Material roughness mapping differs')
    textures=[n.image for m in materials for n in m.node_tree.nodes if n.type=='TEX_IMAGE']
    matching=[image for image in textures if tuple(image.size)==(2048,2048)]
    if len(matching)!=1:raise ValueError('Original atlas missing')
    pixel_error=float(np.max(np.abs(original_pixels-np.asarray(matching[0].pixels[:],dtype=np.float32))))
    if pixel_error>1e-6:raise ValueError('Original atlas pixels changed')
    write(out/'verification.json',{'ok':True,'blender':bpy.app.version_string,'feature_id':FEATURE,
        'reimported_meshes':1,'triangles':len(actual),'maximum_geometry_error_m':error,
        'bounds_reimported_xyz_m':bounds,'source_atlas_maximum_pixel_error':pixel_error,
        'materials':len(materials),'roughness':roughness,'source_roughness':source_roughness,
        'texture_sizes':[list(i.size) for i in textures],
        'limits':['Texture baking approximates the original procedural base-colour shader at 1024px.',
                  'This checks conversion, not surveyed terrain, building identity or exact cross-renderer lighting.']})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--job',type=Path,required=True)
    parser.add_argument('--phase',choices=['export','verify'],required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if bpy.app.version!=(4,5,1):raise ValueError('Blender 4.5.1 required')
    job=json.loads(args.job.read_text(encoding='utf8'));out=Path(job['output'])
    if args.phase=='export':export(job,out)
    else:verify(job,out)
