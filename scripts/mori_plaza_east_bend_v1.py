# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Repair one mapped footway bend outside the protected west correction.

Only the three inherited road meshes inside a 16m by 16m rectangle change.
The 8m by 8m core meets the adopted 0.11m paving; four 4m strips return
to the existing heights. Dimensions and heights are model-space choices,
not surveyed terrain. The existing entrance and seam-fill object stay intact.
"""
import json
from functools import cache
import math
from pathlib import Path

import mori_plaza_connection_v1 as previous

outline = previous.outline
FEATURE, ANCHOR, ROADS = previous.FEATURE, previous.ANCHOR, previous.ROADS
INPUT_SHA256 = '966a81151beaf851a796bae8f91cad4d4106e82a40ccc69bad92aec48f1f6d9b'
CENTER = (-8., 85.)
CORE = (4., 4.)
OUTER = (8., 8.)
TOP_Z = .11
AUDIT_KEY = 'otw_plaza_east_bend_audit'
SEAM = 'OTW Mori east bend / seam fill'
ADDED = {SEAM}
world, local, digest = previous.world, previous.local, previous.digest
SEAM_ORIGIN = tuple(float(round(v)) for v in world(*CENTER)[:2]) + (0.,)


def factor(x, y):
    uv = local(x, y)
    scale = max((abs(uv[i] - CENTER[i]) - CORE[i]) / (OUTER[i] - CORE[i]) for i in (0, 1))
    return min(1., max(0., scale))


@cache
def cells():
    def rectangle(half_size):
        return [world(CENTER[0] + u * half_size[0], CENTER[1] + v * half_size[1])[:2]
                for u, v in [(-1, -1), (1, -1), (1, 1), (-1, 1)]]
    inner, outer = rectangle(CORE), rectangle(OUTER)
    return [inner] + [outline.normalize_ring([inner[i], outer[i], outer[(i+1) % 4], inner[(i+1) % 4]])
                      for i in range(4)]


@cache
def scope_bounds():
    return outline.bounds([p for ring in cells() for p in ring])


def partition(poly):
    if not outline.overlaps(outline.bounds(poly), scope_bounds()):
        return [poly], []
    outside, selected = [poly], []
    for cell in cells():
        remainder = []
        for part in outside:
            rest, inside = outline.subtract_convex(part, cell)
            remainder.extend(rest)
            if inside:
                selected.append(inside)
        outside = remainder
    return outside, selected


def height(x, y, z):
    scale = factor(x, y)
    return z if scale >= 1. else TOP_Z + (z - TOP_Z) * scale


def lowered(poly):
    result = outline.clean([tuple(outline.f32(value) for value in
                            (x, y, height(x, y, z))) for x, y, z in poly])
    if outline.area(result) <= outline.AREA_EPS:
        return []
    if abs(max(p[2] for p in poly) - min(p[2] for p in poly)) < 1e-6:
        if outline.signed_area(result) < 0:
            result.reverse()
    return result


def validate_plan(plan):
    if set(plan) != {'version', 'input_sha256', 'paving_triangles', 'paving_rings', 'audit'} or plan['version'] != 1 or plan['input_sha256'] != INPUT_SHA256:
        raise ValueError('Wrong east bend seam plan or input')
    for key in ('paving_triangles', 'paving_rings'):
        if not isinstance(plan[key], list) or not 1 <= len(plan[key]) <= 10000:
            raise ValueError('Invalid east bend seam polygon count')
        for ring in plan[key]:
            if len(ring) < 3 or key == 'paving_triangles' and len(ring) != 3:
                raise ValueError('Invalid east bend seam polygon')
            for point in ring:
                if len(point) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in point):
                    raise ValueError('Invalid east bend seam coordinate')
                uv = local(*point)
                if any(abs(uv[i] - CENTER[i]) > CORE[i] + .0001 for i in (0, 1)):
                    raise ValueError('East bend seam outside flat core')
            area = outline.signed_area(ring)
            if abs(area) <= 1e-10 or key == 'paving_triangles' and area < 0:
                raise ValueError('Degenerate or inverted east bend seam polygon')
    if sum(outline.signed_area(p) for p in plan['paving_triangles']) > .5:
        raise ValueError('East bend seam exceeds bounded area')


def load_plan(file, expected_hash):
    if previous.digest(file) != expected_hash:
        raise ValueError('East bend seam plan hash differs')
    plan = json.loads(Path(file).read_text(encoding='utf-8'))
    validate_plan(plan)
    return plan


def seam_mesh(plan):
    vertices, faces = previous.paving_mesh(plan)
    # Store the small infill near an exact integer origin. World-coordinate
    # float32 storage around (-412,355) can reopen micrometre boundary gaps.
    return [tuple(outline.f32(p[i] - SEAM_ORIGIN[i]) for i in range(3)) for p in vertices], faces


def apply(op, mesh_fingerprint, folder, plan_file):
    import bpy
    attribution = previous.source_attribution(folder)
    plan = load_plan(plan_file, op['plan_sha256'])
    if AUDIT_KEY in bpy.context.scene or bpy.data.objects.get(SEAM):
        raise ValueError('East bend correction already applied')
    for name in sorted(ROADS):
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != 'MESH' or mesh_fingerprint(obj.data) != op['road_mesh_sha256'][name]:
            raise ValueError('East bend baseline differs: ' + name)
        if obj.data.users != 1 or obj.data.uv_layers or obj.modifiers or obj.parent or obj.constraints or obj.animation_data:
            raise ValueError('Unsupported east bend road state: ' + name)
        if any(abs(obj.matrix_world[r][c] - (r == c)) > 1e-6 for r in range(4) for c in range(4)):
            raise ValueError('Unexpected east bend road transform')
    audit = {'source_attribution': attribution, 'center_uv_m': CENTER,
             'flat_half_size_m': CORE, 'outer_half_size_m': OUTER,
             'flat_height_m': TOP_Z, 'objects': {},
             'basis': 'Mapped footway XY; provisional model-space height, not surveyed terrain.'}
    for name in sorted(ROADS):
        obj = bpy.data.objects[name]
        original = obj.data
        coords = [tuple(v.co) for v in original.vertices]
        faces, materials, smooth = [], [], []
        changed = collapsed = 0
        for face in original.polygons:
            ids = list(face.vertices)
            poly = [coords[i] for i in ids]
            kept, selected = partition(poly)
            if not selected or all(abs(height(*p) - p[2]) < 1e-6 for part in selected for p in part):
                faces.append(ids); materials.append(face.material_index); smooth.append(face.use_smooth)
                continue
            if any(not .10999 <= p[2] <= .46001 for p in poly):
                raise ValueError('Unexpected east bend elevation: ' + name)
            # Keep faces already flat at the adopted height, including the old junction.
            if all(abs(p[2] - TOP_Z) < 1e-6 for p in poly):
                faces.append(ids); materials.append(face.material_index); smooth.append(face.use_smooth)
                continue
            changed += 1
            pieces = [outline.clean([tuple(outline.f32(v) for v in p) for p in part]) for part in kept]
            for part in selected:
                mapped = lowered(part)
                if mapped:
                    pieces.append(mapped)
                else:
                    collapsed += 1
            for part in pieces:
                if outline.area(part) <= outline.AREA_EPS:
                    raise ValueError('Degenerate cut outside flattened east bend riser')
                start = len(coords)
                coords.extend(part)
                faces.append(list(range(start, len(coords))))
                materials.append(face.material_index)
                smooth.append(face.use_smooth)
        if not changed:
            raise ValueError('Missing east bend correction: ' + name)
        mesh = bpy.data.meshes.new('OTW east bend height / ' + name)
        mesh.from_pydata(coords, [], faces)
        mesh.update()
        for material in original.materials:
            mesh.materials.append(material)
        for face, material, flag in zip(mesh.polygons, materials, smooth):
            face.material_index = material
            face.use_smooth = flag
        obj.data = mesh
        audit['objects'][name] = {'changed_original_faces': changed, 'collapsed_riser_fragments': collapsed,
                                  'original_vertices_retained': len(original.vertices),
                                  'new_vertices': len(coords) - len(original.vertices)}
    vertices, faces = seam_mesh(plan)
    mesh = bpy.data.meshes.new(SEAM)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(bpy.data.materials['pavement'])
    obj = bpy.data.objects.new(SEAM, mesh)
    obj.location = SEAM_ORIGIN
    bpy.data.collections['Mori JP podium'].objects.link(obj)
    obj['otw_feature_id'] = FEATURE
    obj['otw_part'] = 'Thin infill of existing calculation gaps along the provisional northeast footway bend'
    audit['seam_fill'] = {'plan_sha256': op['plan_sha256'], **plan['audit']}
    bpy.context.scene[AUDIT_KEY] = json.dumps(audit, sort_keys=True)
    return audit
