# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Contracts for limited legacy component replay and procedural shader comparison."""
import ast
import hashlib
import json
import math
from pathlib import Path


def signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                    allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def reviewed_nodes(path, expected_sha256, ranges):
    """Validate the whole source before selecting complete top-level statements."""
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError('Unreviewed legacy source: ' + str(path))
    body = ast.parse(data.decode('utf8')).body
    selected = []
    for start, end in ranges:
        nodes = [n for n in body if start <= n.lineno and n.end_lineno <= end]
        overlapping = [n for n in body if n.lineno <= end and n.end_lineno >= start]
        if not nodes or nodes != overlapping or min(n.lineno for n in nodes) != start or max(n.end_lineno for n in nodes) != end:
            raise ValueError('Range must cover complete reviewed statements')
        if any(n in selected for n in nodes):
            raise ValueError('Overlapping reviewed ranges')
        selected.extend(nodes)
    return selected


def primitive(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('Non-finite property')
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, set):
        return sorted(value)
    return [primitive(v) for v in value]


def scalar_properties(value, exclude=()):
    result = {}
    for prop in value.bl_rna.properties:
        if (prop.identifier in exclude or prop.identifier.startswith('bl_') or prop.is_readonly
                or prop.type not in {'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'}):
            continue
        result[prop.identifier] = primitive(getattr(value, prop.identifier))
    return result


NODE_TYPES = {
    'ShaderNodeBsdfPrincipled', 'ShaderNodeOutputMaterial', 'ShaderNodeNewGeometry',
    'ShaderNodeTexNoise', 'ShaderNodeValToRGB', 'ShaderNodeBump',
    'ShaderNodeBsdfTranslucent', 'ShaderNodeMixShader',
}
NODE_UI = {'name', 'label', 'location', 'location_absolute', 'width', 'height', 'color', 'use_custom_color',
           'select', 'show_options', 'show_preview', 'show_texture', 'hide', 'warning_propagation'}
MATERIAL_ID = {'name', 'use_fake_user', 'use_extra_user', 'is_embedded_data', 'tag',
               'is_evaluated', 'is_missing', 'is_runtime_data', 'paint_active_slot', 'paint_clone_slot'}


def ramp_snapshot(ramp):
    return {'settings': scalar_properties(ramp),
            'elements': [{'position': e.position, 'color': list(e.color)} for e in ramp.elements]}


def material_snapshot(material):
    """Compare the observed procedural node families; reject external/animated graphs.

    This includes Noise mode/mapping, ColorRamp elements, all socket defaults,
    links, mute flags and writable material settings. Layout/selection is omitted.
    Images and node groups are outside this contract, not silently ignored.
    """
    if not material or not material.use_nodes or material.animation_data or material.node_tree.animation_data:
        raise ValueError('Expected an unanimated procedural node material')
    nodes = []
    for node in material.node_tree.nodes:
        if node.bl_idname not in NODE_TYPES or getattr(node, 'image', None) or getattr(node, 'node_tree', None):
            raise ValueError('Unsupported shader node: ' + node.bl_idname)
        row = {'name': node.name, 'type': node.bl_idname,
               'settings': scalar_properties(node, NODE_UI), 'sockets': {}}
        for direction in ('inputs', 'outputs'):
            row['sockets'][direction] = [{'identifier': s.identifier, 'type': s.bl_idname,
                'default': primitive(s.default_value) if hasattr(s, 'default_value') else None}
                for s in getattr(node, direction)]
        if hasattr(node, 'color_ramp'):
            row['color_ramp'] = ramp_snapshot(node.color_ramp)
        if hasattr(node, 'texture_mapping'):
            row['texture_mapping'] = scalar_properties(node.texture_mapping)
        if hasattr(node, 'color_mapping'):
            row['color_mapping'] = scalar_properties(node.color_mapping)
            row['color_mapping']['color_ramp'] = ramp_snapshot(node.color_mapping.color_ramp)
        nodes.append(row)
    links = sorted((l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier)
                   for l in material.node_tree.links)
    return {'settings': scalar_properties(material, MATERIAL_ID),
            'cycles': scalar_properties(material.cycles) if hasattr(material, 'cycles') else None,
            'nodes': sorted(nodes, key=lambda n: n['name']), 'links': links}


def mesh_object_snapshot(obj):
    import numpy as np
    from blender_worker import array_prop, mesh_fingerprint
    if (obj.type != 'MESH' or obj.parent or obj.constraints or obj.animation_data
            or obj.data.shape_keys or obj.data.has_custom_normals):
        raise ValueError('Unsupported object dependency: ' + obj.name)
    if any(slot.link != 'DATA' for slot in obj.material_slots):
        raise ValueError('Object material override: ' + obj.name)
    modifiers = []
    for mod in obj.modifiers:
        if mod.type != 'BEVEL' or mod.profile_type == 'CUSTOM' or mod.vertex_group:
            raise ValueError('Unsupported modifier: ' + mod.name)
        modifiers.append({'name': mod.name, 'type': mod.type, 'settings': scalar_properties(mod)})
    return {'mesh_sha256': mesh_fingerprint(obj.data), 'vertices': len(obj.data.vertices),
            'polygons': len(obj.data.polygons),
            'smooth_sha256': hashlib.sha256(array_prop(obj.data.polygons, 'use_smooth', 1, np.bool_).tobytes()).hexdigest(),
            'matrix_world': [float(v) for row in obj.matrix_world for v in row],
            'modifiers': modifiers, 'materials': [m.name if m else None for m in obj.data.materials]}
