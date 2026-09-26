# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Small real-Blender regression checks for the component/shader comparison contract."""
import bpy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from component_contracts import material_snapshot, mesh_object_snapshot, signature

material = bpy.data.materials.new('Contract fixture'); material.use_nodes = True
nodes, links = material.node_tree.nodes, material.node_tree.links
noise = nodes.new('ShaderNodeTexNoise'); ramp = nodes.new('ShaderNodeValToRGB')
links.new(noise.outputs['Fac'], ramp.inputs[0])
links.new(ramp.outputs['Color'], nodes.get('Principled BSDF').inputs['Base Color'])
initial = material_snapshot(material)
reference = signature(initial)
noise.location.x += 100; noise.select = not noise.select
after_ui = material_snapshot(material)
if signature(after_ui) != reference:
    for a, b in zip(initial['nodes'], after_ui['nodes']):
        if a != b:
            print(json.dumps({'node': a['name'], 'before': a, 'after': b}))
assert signature(after_ui) == reference, 'Editor layout must not change material comparison'
noise.noise_dimensions = '4D'
assert signature(material_snapshot(material)) != reference, 'Noise mode must be captured'
noise.noise_dimensions = '3D'
assert signature(material_snapshot(material)) == reference
ramp.color_ramp.elements[0].color[0] = .25
assert signature(material_snapshot(material)) != reference, 'Ramp colors must be captured'
ramp.color_ramp.elements[0].color[0] = 0
assert signature(material_snapshot(material)) == reference
noise.inputs['Scale'].default_value += 1
assert signature(material_snapshot(material)) != reference, 'Socket defaults must be captured'
nodes.new('ShaderNodeTexImage')
try:
    material_snapshot(material)
except ValueError as error:
    assert 'Unsupported shader node' in str(error)
else:
    raise AssertionError('Image nodes must fail closed')

bpy.ops.mesh.primitive_cube_add()
obj = bpy.context.object; mod = obj.modifiers.new('Edges', 'BEVEL'); mod.width = .1
before = mesh_object_snapshot(obj)
mod.width = .2
assert mesh_object_snapshot(obj)['modifiers'] != before['modifiers']
mod.width = .1; mod.show_render = False
assert mesh_object_snapshot(obj)['modifiers'] != before['modifiers'], 'Render toggle must be captured'
obj.data.polygons[0].use_smooth = True
assert mesh_object_snapshot(obj)['smooth_sha256'] != before['smooth_sha256']
obj.location.x = 1; bpy.context.view_layer.update()
assert mesh_object_snapshot(obj)['matrix_world'] != before['matrix_world']
print(json.dumps({'ok': True, 'shader_changes_detected': ['noise-mode', 'ramp-color', 'socket-default'],
                  'unsupported_image_node_rejected': True, 'editor_layout_ignored': True,
                  'object_changes_detected': ['bevel-width', 'bevel-render-toggle', 'smooth-face', 'world-transform']}))
