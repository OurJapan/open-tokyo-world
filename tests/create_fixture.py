"""Run with Blender --factory-startup --background --python ... -- OUTPUT_DIR."""
import hashlib
import argparse
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector

p=argparse.ArgumentParser();p.add_argument('output');p.add_argument('--missing-image',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
out=Path(a.output).resolve()
if out.exists():raise ValueError('Fixture output must be new')
out.mkdir(parents=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.world.color=(0.3,0.3,0.3)
collection=bpy.data.collections.new('Fixture landmark');s.collection.children.link(collection)
bpy.ops.mesh.primitive_cube_add(size=2,location=(0,0,1));cube=bpy.context.object;cube.name='Fixture building'
for c in list(cube.users_collection):c.objects.unlink(cube)
collection.objects.link(cube)
if a.missing_image:
    image=bpy.data.images.new('Deliberately missing fixture image',width=2,height=2)
    image.source='FILE';image.filepath='//deliberately-missing.png'
    mat=bpy.data.materials.new('Missing asset test');mat.use_nodes=True
    mat.node_tree.nodes.new('ShaderNodeTexImage').image=image
    cube.data.materials.append(mat)
bpy.ops.mesh.primitive_plane_add(size=20)
bpy.ops.object.light_add(type='AREA',location=(2,-3,8));bpy.context.object.data.energy=1500;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=5
bpy.ops.object.camera_add();camera=bpy.context.object
views=[]
for name,location in [('front',(7,-9,6)),('back',(-7,9,6)),('side',(9,7,5)),('context',(12,-14,12))]:
    camera.location=location;camera.rotation_euler=(Vector((0,0,1))-camera.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    views.append({'id':name,'matrix_world':[list(r) for r in camera.matrix_world],'lens_mm':45,'sensor_width_mm':36,'sensor_height_mm':24,'sensor_fit':'AUTO','shift_x':0,'shift_y':0,'clip_start':0.1,'clip_end':100,'frame':1})
s.camera=camera
s.timeline_markers.new('Legacy film camera at frame 1',frame=1).camera=camera
blend=out/'fixture.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
def write(name,data):(out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
write('lock.json',{'bytes':blend.stat().st_size,'sha256':hashlib.sha256(blend.read_bytes()).hexdigest(),'blender_version':bpy.app.version_string})
write('cameras.json',{'version':1,'views':views})
write('features.json',{'version':1,'features':[{'id':'otw:fixture:building','collections':['Fixture landmark']}]})
write('patch.json',{'version':1,'purpose':'fixture-test','reason':'Exercise a scoped visible change; not a real-world correction.','source_refs':[],'operations':[{'op':'translate_object','feature_id':'otw:fixture:building','object':'Fixture building','translation_m':[1,0,0]}]})
