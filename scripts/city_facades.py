# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Image-free, illustrative facade materials. Blender-only worker implementation."""
import hashlib
import json

PALETTE = (
    (.46, .43, .38), (.66, .65, .60), (.29, .32, .33), (.48, .50, .48),
    (.28, .24, .21), (.23, .30, .34), (.55, .47, .39), (.43, .43, .41),
)


def build_material(material, index):
    """Original repeating window recipe; no sampled image, geometry or measured facade."""
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    wall = (*PALETTE[index], 1)
    material.diffuse_color = wall

    def node(kind, name):
        result = tree.nodes.new(kind)
        result.name = name
        result.label = name
        return result

    def connect(value, socket):
        if isinstance(value, (int, float, tuple)):
            socket.default_value = value
        else:
            tree.links.new(value, socket)

    def math(operation, a, b=0):
        n = node('ShaderNodeMath', operation)
        n.operation = operation
        connect(a, n.inputs[0]); connect(b, n.inputs[1])
        return n.outputs[0]

    def band(value, low, high):
        return math('MULTIPLY', math('GREATER_THAN', value, low), math('LESS_THAN', value, high))

    def separate(value, name):
        n = node('ShaderNodeSeparateXYZ', name)
        connect(value, n.inputs[0])
        return n.outputs

    def mix(factor, a, b, name):
        n = node('ShaderNodeMixRGB', name)
        n.blend_type = 'MIX'
        connect(factor, n.inputs[0]); connect(a, n.inputs[1]); connect(b, n.inputs[2])
        return n.outputs[0]

    uv = node('ShaderNodeTexCoord', 'Existing UV coordinates')
    geometry = node('ShaderNodeNewGeometry', 'World position and normal')
    u = separate(uv.outputs['UV'], 'Facade horizontal coordinate')['X']
    z = separate(geometry.outputs['Position'], 'Height in metres')['Z']
    normal_z = separate(geometry.outputs['True Normal'], 'Roof exclusion')['Z']
    # Legacy horizontal UV repeats once per approximately 20 metres. Eight bays
    # per repeat and 3.2 m floors are visual assumptions, not source measurements.
    column = math('FRACT', math('MULTIPLY', u, 8))
    floor = math('FRACT', math('MULTIPLY', z, 1 / 3.2))
    vertical = math('LESS_THAN', math('ABSOLUTE', normal_z), .25)
    facade = math('MULTIPLY', vertical, math('GREATER_THAN', z, 1))
    frame = math('MULTIPLY', facade, math('MULTIPLY', band(column, .13, .87), band(floor, .20, .83)))
    glass = math('MULTIPLY', facade, math('MULTIPLY', band(column, .17, .83), band(floor, .24, .79)))
    # An opaque centre mullion. The windows are shading only, never openings.
    glass = math('MULTIPLY', glass, math('GREATER_THAN', math('ABSOLUTE', math('SUBTRACT', column, .5)), .012))
    framed = mix(frame, wall, (.18, .19, .19, 1), 'Neutral frames')
    color = mix(glass, framed, (.065, .105, .135, 1), 'Opaque blue grey glazing')
    roughness = math('SUBTRACT', .72, math('MULTIPLY', glass, .35))
    shader = node('ShaderNodeBsdfPrincipled', 'Procedural facade v1')
    connect(color, shader.inputs['Base Color'])
    connect(roughness, shader.inputs['Roughness'])
    shader.inputs['Metallic'].default_value = 0
    bump = node('ShaderNodeBump', 'Shallow window recess')
    bump.invert = True
    bump.inputs['Strength'].default_value = .15
    bump.inputs['Distance'].default_value = .025
    connect(glass, bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    output = node('ShaderNodeOutputMaterial', 'Material output')
    tree.links.new(shader.outputs['BSDF'], output.inputs['Surface'])
    # Lay out deterministic columns so the generated material can be edited.
    for i, n in enumerate(tree.nodes):
        n.location = ((i // 8) * 240, -(i % 8) * 180)


def graph_hash(material):
    from blender_worker import material_fingerprint
    extra = [(n.name, {p: getattr(n, p) for p in ('operation', 'blend_type', 'invert', 'use_clamp') if hasattr(n, p)})
             for n in material.node_tree.nodes]
    return hashlib.sha256(json.dumps([material_fingerprint(material), extra], sort_keys=True).encode()).hexdigest()


def preflight(config):
    import bpy
    from blender_worker import mesh_fingerprint, material_fingerprint, packed_hash
    atlas = bpy.data.images.get(config['removed_image']['name'])
    if atlas is None or packed_hash(atlas) != config['removed_image']['packed_sha256']:
        raise ValueError('Pinned legacy atlas differs')
    targets = []
    for name, expected in config['targets'].items():
        obj = bpy.data.objects.get(name)
        if (obj is None or obj.type != 'MESH' or obj.data.users != 1 or obj.library
                or obj.animation_data or obj.constraints or obj.modifiers or obj.parent):
            raise ValueError('Unexpected facade object state: ' + name)
        if mesh_fingerprint(obj.data) != expected['mesh']:
            raise ValueError('Facade mesh differs: ' + name)
        if len(obj.material_slots) != 1 or not obj.material_slots[0].material:
            raise ValueError('Expected one facade material: ' + name)
        mat = obj.material_slots[0].material
        if mat.users != 1 or mat.library or mat.animation_data or material_fingerprint(mat) != expected['material']:
            raise ValueError('Facade material differs or is shared: ' + name)
        if not obj.data.uv_layers.active:
            raise ValueError('Missing facade UV: ' + name)
        targets.append((obj, mat))
    return atlas, targets


def prepare(job):
    import bpy
    from pathlib import Path
    from review import digest, require
    require(digest(bpy.data.filepath) == job['config']['input']['sha256'], 'Input changed before Blender loaded it')
    atlas, targets = preflight(job['config'])
    for obj, material in targets:
        build_material(material, int(obj.name.removeprefix('wall')))
    # Never force-unlink an unexpected world, compositor, group or other user.
    require(atlas.users == 0, 'Unexpected remaining atlas user; refusing removal')
    bpy.data.images.remove(atlas)
    output = Path(job['output']) / 'after.blend'
    require(not output.exists(), 'Refusing to overwrite a candidate')
    bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
    return {'ok': True, 'material_graph_hashes': {o.name: graph_hash(m) for o, m in targets}}


def validate(job, phase):
    import bpy
    from blender_worker import validate as validate_scene
    from review import require
    result = validate_scene(job)
    if phase == 'validate-before':
        preflight(job['config'])
    else:
        require(bpy.data.images.get(job['config']['removed_image']['name']) is None, 'Atlas remains in saved candidate')
        hashes = {}
        for name in job['config']['targets']:
            obj = bpy.data.objects.get(name)
            require(obj is not None and len(obj.material_slots) == 1, 'Target material missing')
            mat = obj.material_slots[0].material
            require(mat is not None and mat.use_nodes, 'Missing generated shader')
            require(not any(n.bl_idname in ('ShaderNodeTexImage', 'ShaderNodeTexEnvironment', 'ShaderNodeGroup') for n in mat.node_tree.nodes),
                    'Generated shader has an external or nested image dependency')
            hashes[name] = graph_hash(mat)
        result['material_graph_hashes'] = hashes
    return result
