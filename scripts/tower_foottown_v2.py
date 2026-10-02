# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Replace only four pinned FootTown meshes and add three finish groups."""
import math

INPUT_SHA256 = '7a5cd95d2223092a1a2931131eeadd3978605d8e7293b5908aada3b13f301350'
INPUT_BYTES = 631833930
INPUT_OBJECTS = 3358
FEATURE = 'otw:jp:tokyo:minato:tokyo-tower'
OLD_COLLECTION = 'OTW Tokyo Tower structure v1'
COLLECTION = 'OTW Tokyo Tower FootTown v2'
OLD_PREFIX = 'OTW Tokyo Tower structure / '
PREFIX = 'OTW Tokyo Tower FootTown v2 / '
MATERIAL_PREFIX = 'OTW FootTown v2 / '
OLD_GROUPS = ('foottown-shell', 'foottown-glazing', 'foottown-metal', 'foottown-roof')
NEW_GROUPS = ('foottown-cladding', 'foottown-joints', 'foottown-screen')
GROUPS = OLD_GROUPS + NEW_GROUPS
BASELINE_HASHES = {
    OLD_PREFIX+'foottown-shell': 'e9ca32a95250f2ca6291569dc2c3892ab7297199f6695da046da5945dc356f12',
    OLD_PREFIX+'foottown-glazing': 'ace2ac1401e5f93b319cca219bf34febbd5d9149ff4127cf23c4cbccdfba4d34',
    OLD_PREFIX+'foottown-metal': '6c637c0e92534112f3a714bd036d84ed80d56bc0e30df7860524855b9438207c',
    OLD_PREFIX+'foottown-roof': '28ac51cb1f987fd3c1da1eee131495114060724ba7f56ac0bb1bc4545a3ed7c7',
}
ANCHOR = OLD_PREFIX+'foottown-shell'
CHANGED = set(BASELINE_HASHES)
ADDED = {PREFIX+group for group in NEW_GROUPS}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def object_name(group):
    require(group in GROUPS, 'Unknown FootTown group')
    return (OLD_PREFIX if group in OLD_GROUPS else PREFIX)+group


def validate_operation(op):
    require(set(op) == {'op', 'feature_id', 'object', 'expected_mesh_sha256', 'target_mesh_sha256', 'added_objects'},
            'Unexpected FootTown patch keys')
    require(op['op'] == 'tower_foottown_v2' and op['object'] == ANCHOR and op['feature_id'] == FEATURE, 'Wrong FootTown anchor or feature')
    require(op['expected_mesh_sha256'] == BASELINE_HASHES[ANCHOR], 'FootTown anchor hash differs')
    require(isinstance(op['target_mesh_sha256'], dict) and op['target_mesh_sha256'] == BASELINE_HASHES, 'FootTown baseline targets or hashes differ')
    names = op['added_objects']
    require(isinstance(names, list) and all(isinstance(name, str) for name in names) and
            len(names) == len(ADDED) and set(names) == ADDED, 'FootTown additions differ')


def apply(op, fingerprint):
    import bpy
    from tower_structure_v1 import MeshBuilder
    import tower_foottown_geometry_v2 as geometry
    validate_operation(op)
    require(len(bpy.context.scene.objects) == INPUT_OBJECTS, 'FootTown input object count differs')
    require(not bpy.data.collections.get(COLLECTION) and not any(bpy.data.objects.get(name) for name in ADDED), 'FootTown increment already exists')
    require(set(geometry.GROUPS) == set(GROUPS) and set(geometry.MATERIALS) == set(GROUPS), 'FootTown geometry or material groups differ')
    for group in GROUPS:
        require(bpy.data.materials.get(MATERIAL_PREFIX+group) is None, 'FootTown material name collision')
        spec = geometry.MATERIALS[group]
        require(set(spec) == {'base_color', 'metallic', 'roughness', 'transmission'}, 'FootTown material keys differ')
        require(len(spec['base_color']) == 4 and all(type(v) in (float, int) and math.isfinite(v) and 0 <= v <= 1
                for v in (*spec['base_color'], spec['metallic'], spec['roughness'], spec['transmission'])),
                'Invalid FootTown material values')
        require(spec['base_color'][3] == 1, 'FootTown material alpha must be opaque')
    for name, expected in BASELINE_HASHES.items():
        obj = bpy.data.objects.get(name)
        require(obj is not None and obj.type == 'MESH' and fingerprint(obj.data) == expected, 'FootTown baseline differs: '+name)
        require(obj.get('otw_feature_id') == FEATURE and {c.name for c in obj.users_collection} == {OLD_COLLECTION}, 'FootTown target identity differs: '+name)
        require(not obj.modifiers and not obj.parent and not obj.constraints and not obj.animation_data, 'Unsupported FootTown target state')
        require(all(abs(obj.matrix_world[r][c]-(r == c)) < 1e-7 for r in range(4) for c in range(4)), 'Unexpected FootTown target transform')
        require(obj.get('otw_foottown_revision') is None, 'FootTown target already revised')
    builder = MeshBuilder()
    geometry.geometry(builder)
    require(set(builder.groups) == set(GROUPS), 'FootTown generated scope differs')
    for group, mesh in builder.groups.items():
        require(mesh['vertices'] and mesh['faces'], 'Empty FootTown group: '+group)
        require(all(len(p) == 3 and all(math.isfinite(v) for v in p) for p in mesh['vertices']), 'Non-finite FootTown geometry')
        require(all(len(f) >= 3 and len(set(f)) == len(f) and all(type(i) is int and 0 <= i < len(mesh['vertices']) for i in f)
                    for f in mesh['faces']), 'Invalid FootTown polygon indices')
    collection = bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(collection)
    collection['otw_feature_id'] = FEATURE
    collection['otw_foottown_revision'] = 'v2'
    for group in GROUPS:
        data = builder.groups[group]
        mesh = bpy.data.meshes.new(object_name(group)+' / v2')
        mesh.from_pydata(data['vertices'], [], data['faces']); mesh.update()
        # Each finish owns a new material datablock. Existing shared shaders
        # (including lower lift glass and metal) are never modified or reused.
        spec = geometry.MATERIALS[group]
        material = bpy.data.materials.new(MATERIAL_PREFIX+group)
        material.use_nodes = True
        material.diffuse_color = spec['base_color']
        shader = material.node_tree.nodes.get('Principled BSDF')
        for name, value in [('Base Color', spec['base_color']), ('Metallic', spec['metallic']),
                            ('Roughness', spec['roughness']), ('Transmission Weight', spec['transmission'])]:
            shader.inputs[name].default_value = value
        mesh.materials.append(material)
        if group in OLD_GROUPS:
            obj = bpy.data.objects[object_name(group)]
            obj.data = mesh
        else:
            obj = bpy.data.objects.new(object_name(group), mesh)
            collection.objects.link(obj)
            obj['otw_feature_id'] = FEATURE
            obj['otw_part_id'] = 'tokyo-tower-foottown-v2-'+group
        obj['otw_foottown_revision'] = 'v2'
        obj['otw_accuracy'] = 'photo-guided; exterior layout and dimensions inferred'
