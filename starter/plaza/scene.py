# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Build or independently reopen the six-part plaza starter with Blender."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import mori_plaza_v1 as plaza
import mori_plaza_link_v1 as link

GROUPS = [(plaza, 'OTW Mori entry plaza / '), (link, 'OTW Mori plaza link / ')]
COLORS = {
    'paving': [(.22,.23,.22),(.32,.33,.31),(.35,.35,.33),(.29,.30,.29)],
    'planters': [(.075,.055,.027),(.29,.30,.28)],
    'planting': [(.035,.095,.015),(.075,.16,.026),(.11,.20,.035),(.055,.125,.022),(.13,.085,.045)],
}
EXPECTED = {prefix + part for _, prefix in GROUPS for part in COLORS}


def mesh_digest(mesh):
    import struct
    h = hashlib.sha256()
    for v in mesh.vertices:
        h.update(struct.pack('<3f', *v.co))
    for f in mesh.polygons:
        h.update(struct.pack('<I', len(f.vertices)))
        h.update(struct.pack('<' + 'I' * len(f.vertices), *f.vertices))
        h.update(struct.pack('<I?', f.material_index, f.use_smooth))
    return h.hexdigest()


def build(folder, brightness):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = 'OurJapan six-part starter'
    fingerprints = {}
    for module, prefix in GROUPS:
        for part in COLORS:
            geom = module.geometry(part)
            mesh = bpy.data.meshes.new(prefix + part)
            mesh.from_pydata(geom.vertices, [], geom.faces)
            mesh.update()
            obj = bpy.data.objects.new(prefix + part, mesh)
            scene.collection.objects.link(obj)
            obj['license'] = 'CC-BY-4.0'
            obj['attribution'] = 'ark4ez / OurJapan; see ASSET-LICENSE.md and provenance.json'
            obj['accuracy'] = 'inferred layout; legacy registration, not surveyed'
            for i, color in enumerate(COLORS[part]):
                material = bpy.data.materials.new(f'{prefix}{part} / {i}')
                material.use_nodes = True
                color = tuple(c * brightness for c in color) if part == 'paving' else color
                material.diffuse_color = (*color, 1)
                node = material.node_tree.nodes.get('Principled BSDF')
                node.inputs['Base Color'].default_value = (*color, 1)
                node.inputs['Roughness'].default_value = .85
                node.inputs['Emission Strength'].default_value = 0
                mesh.materials.append(material)
            for face, material, smooth in zip(mesh.polygons, geom.materials, geom.smooth):
                face.material_index = material
                face.use_smooth = smooth
            fingerprints[obj.name] = mesh_digest(mesh)
    center = Vector((-410.8, 308.8, 1.2))
    camera_data = bpy.data.cameras.new('Starter camera')
    camera = bpy.data.objects.new('Starter camera', camera_data)
    scene.collection.objects.link(camera)
    camera.location = center + Vector((32, -42, 42))
    camera.rotation_euler = (center-camera.location).to_track_quat('-Z','Y').to_euler()
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = 39
    camera_data.clip_start = .1
    camera_data.clip_end = 250
    scene.camera = camera
    sun_data = bpy.data.lights.new('Starter sun','SUN')
    sun_data.energy = 3
    sun_data.angle = .12
    sun = bpy.data.objects.new('Starter sun',sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (.4,-.5,-.4)
    scene.world = bpy.data.worlds.new('Starter world')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.22,.27,.34,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .7
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 12
    scene.cycles.seed = 13
    scene.render.resolution_x = 800
    scene.render.resolution_y = 600
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene['asset_license'] = 'CC-BY-4.0; see accompanying provenance and ASSET-LICENSE.md'
    scene['starter_paving_brightness'] = brightness
    scene['starter_meshes'] = json.dumps(fingerprints,sort_keys=True)
    scene['scope'] = 'Six procedural parts only; no city baseline or third-party textures'
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'scene.blend'),compress=True)


def validate_and_render(folder):
    bpy.ops.wm.open_mainfile(filepath=str(folder/'scene.blend'))
    scene = bpy.context.scene
    meshes = {o.name:o for o in scene.objects if o.type == 'MESH'}
    if set(meshes) != EXPECTED:
        raise ValueError('Wrong six-part object set')
    if len(bpy.data.scenes)!=1 or len(bpy.data.objects)!=8:
        raise ValueError('Unexpected scene objects')
    if bpy.data.libraries or bpy.data.images or bpy.data.texts or bpy.data.sounds:
        raise ValueError('Unexpected external, image, script or audio data')
    hashes = json.loads(scene['starter_meshes'])
    brightness = float(scene['starter_paving_brightness'])
    if not .5 <= brightness <= 1.5:
        raise ValueError('Brightness outside supported starter range')
    for name,obj in meshes.items():
        mesh = obj.data
        if obj.parent or obj.modifiers or obj.constraints or obj.animation_data or mesh.shape_keys:
            raise ValueError('Unexpected mesh dependency')
        if any(abs(obj.matrix_world[i][j] - float(i == j)) > 1e-6 for i in range(4) for j in range(4)):
            raise ValueError('Unexpected mesh transform')
        if mesh_digest(mesh)!=hashes[name]:
            raise ValueError('Saved mesh fingerprint mismatch: '+name)
        if not all(math.isfinite(c) for v in mesh.vertices for c in v.co):
            raise ValueError('Nonfinite coordinates')
        mesh.calc_loop_triangles()
        if not mesh.loop_triangles or any(t.area<=1e-10 for t in mesh.loop_triangles):
            raise ValueError('Empty or degenerate geometry')
        part=name.rsplit(' / ',1)[1]
        if len(mesh.materials)!=len(COLORS[part]):
            raise ValueError('Unexpected materials')
        for m, color in zip(mesh.materials,COLORS[part]):
            if not m or not m.use_nodes or m.animation_data:
                raise ValueError('Missing or unexpected material')
            if {n.bl_idname for n in m.node_tree.nodes}!={'ShaderNodeBsdfPrincipled','ShaderNodeOutputMaterial'}:
                raise ValueError('Unexpected material nodes')
            p=m.node_tree.nodes.get('Principled BSDF')
            expected=[c*brightness for c in color] if part=='paving' else color
            if any(abs(a-b)>1e-6 for a,b in zip(p.inputs['Base Color'].default_value,(*expected,1))):
                raise ValueError('Material mismatch')
            if p.inputs['Emission Strength'].default_value!=0:
                raise ValueError('Unexpected emission')
    if not scene.camera or scene.camera.data.type!='ORTHO' or abs(scene.camera.data.ortho_scale-39)>1e-6:
        raise ValueError('Unexpected camera')
    from bpy_extras.object_utils import world_to_camera_view
    for obj in meshes.values():
        for vertex in obj.data.vertices:
            projected = world_to_camera_view(scene, scene.camera, obj.matrix_world @ vertex.co)
            if not (.02 < projected.x < .98 and .02 < projected.y < .98 and .1 < projected.z < 250):
                raise ValueError('Mesh outside camera margin')
    scene.render.filepath=str(folder/'preview.png')
    bpy.ops.render.render(write_still=True)
    image=bpy.data.images.load(str(folder/'preview.png'),check_existing=False)
    import numpy as np
    pixels=np.empty(len(image.pixels),dtype=np.float32)
    image.pixels.foreach_get(pixels)
    rgb=pixels.reshape(-1,4)[:,:3]
    if tuple(image.size)!=(800,600) or not np.isfinite(rgb).all() or rgb.max()-rgb.min()<.01:
        raise ValueError('Invalid or flat preview')
    report={'ok':True,'separate_process_open':True,'mesh_count':6,'mesh_fingerprints':hashes,
            'paving_brightness':brightness,'render_pixels':[800,600],
            'blender_version':bpy.app.version_string,'triangles':sum(len(o.data.loop_triangles) for o in meshes.values()),
            'scope':'geometry/material/render checks; not real-world accuracy or legal assurance'}
    (folder/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['build','validate'],required=True)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--brightness',type=float,default=1)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    folder=args.output.resolve()
    if args.mode=='build':
        if not math.isfinite(args.brightness) or not .5<=args.brightness<=1.5:
            parser.error('Brightness must be between 0.5 and 1.5')
        folder.mkdir(parents=True,exist_ok=False)
        build(folder,args.brightness)
    else:
        validate_and_render(folder)
