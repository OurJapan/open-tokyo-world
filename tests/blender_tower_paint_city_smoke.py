"""Check that generic scene inspection does not create custom-property groups."""
import sys
from pathlib import Path
import bpy
import numpy as np
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import tokyo_tower_paint_city as city

before_props = city.plain({o.name: dict(o.items()) for o in bpy.context.scene.objects})
before = city.snapshot()
after = city.snapshot()
after_props = city.plain({o.name: dict(o.items()) for o in bpy.context.scene.objects})
assert before_props == after_props, 'Read-only inspection changed custom properties'
assert city.require_unchanged(before, after, {'targets': []}) == 3
print('Read-only city snapshot smoke passed (3 untouched factory objects)')

# Real shader execution: all swatches are at world z=0, while object-local z
# samples the tower bands. This catches accidental use of world/Generated coords.
source = Path(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv else None
if source is None:
    raise ValueError('Pass the fixed city blend after -- for the shader check')
lock = city.paint.load(city.LOCK)
if city.paint.sha(source) != lock['city_sha256']:
    raise ValueError('Unexpected shader-smoke material source')
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(source), link=False) as (available, data):
    data.materials = ['Rebuilt • orange', 'Rebuilt • white']
palette = data.materials
colors = [list(m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value) for m in palette]
plan = city.paint.load(city.paint.PLAN)
heights = [145., 167., 190., 217., 242., 267., 292., 320.]
scene = bpy.context.scene
for row in range(2):
    mat = city.paint_material(palette, row, {'paint_material': 'Shader smoke '+str(row)}, plan)
    tree = mat.node_tree
    emission = tree.nodes.new('ShaderNodeEmission')
    tree.links.new(tree.nodes['OTW original paint colors'].outputs[0], emission.inputs['Color'])
    tree.links.new(emission.outputs[0], tree.nodes['Material Output'].inputs['Surface'])
    for column, z in enumerate(heights):
        mesh = bpy.data.meshes.new('Height swatch')
        mesh.from_pydata([(-.45,-.45,z),(.45,-.45,z),(.45,.45,z),(-.45,.45,z)], [], [(0,1,2,3)])
        mesh.materials.append(mat)
        ob = bpy.data.objects.new('Height swatch', mesh)
        scene.collection.objects.link(ob)
        ob.location = (column - 3.5, row - .5, -z)
camera = bpy.data.cameras.new('Shader smoke camera')
ob = bpy.data.objects.new(camera.name, camera)
scene.collection.objects.link(ob)
ob.location = (0,0,10)
camera.type = 'ORTHO'; camera.ortho_scale = 8
scene.camera = ob
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'; scene.cycles.samples = 1
scene.cycles.use_denoising = False
scene.render.threads_mode = 'FIXED'; scene.render.threads = 2
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 256,64,100
scene.render.image_settings.file_format = 'OPEN_EXR'; scene.render.image_settings.color_depth = '32'
scene.world = bpy.data.worlds.new('Black shader-smoke world')
scene.world.color = (0,0,0)
with tempfile.TemporaryDirectory(prefix='otw-tower-shader-') as directory:
    scene.render.filepath = str(Path(directory)/'swatches.exr')
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(scene.render.filepath)
    pixels = np.asarray(image.pixels[:], dtype=np.float32).reshape(64,256,4)
    for row in range(2):
        for column,z in enumerate(heights):
            expected = colors[city.white_mask(z,row,plan)][:3]
            actual = pixels[row*32+16,column*32+16,:3]
            assert np.allclose(actual, expected, atol=1e-5), (row,z,actual,expected)
    bpy.data.images.remove(image)
print('Native shader smoke passed: 16 local-height samples match the retained palette')
