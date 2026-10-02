# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Read the saved tower candidate in a separate, read-only Blender process.

Checks use saved vertices and polygon connectivity, never generated reference
geometry. Dimensions below are acceptance constraints for this inferred model,
not a claim of measured engineering accuracy.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tower_structure_v1 as tower

EPS = 3e-5  # Saved float32 coordinates at the 246 m tower elevation.
BOUNDS = {
    'foottown-shell': ((-36.5, 36.5), (-29, 29), (.35, 16)),
    'foottown-glazing': ((-36.5, 36.5), (-29, 29), (.5, 15)),
    'foottown-metal': ((-36.5, 36.5), (-29, 29), (.5, 17.5)),
    'foottown-roof': ((-36.5, 36.5), (-29, 29), (16, 16.2)),
    'base-connections': ((-50.51, 50.51), (-50.51, 50.51), (1.92, 2.28)),
    'lower-shaft-frame': ((-2.28, 2.28), (-2.28, 2.28), (.45, 145.35)),
    'lower-shaft-glazing': ((-2.22, 2.22), (-2.22, 2.22), (.52, 145.28)),
    'stairs-frame': ((-4.06, 4.06), (2.8, 6), (16.0, 145.2)),
    'stairs-treads': ((-4.75, 3.95), (2.925, 5.875), (16.08, 145.1)),
    'stairs-guards': ((-4, 4), (2.885, 5.915), (16.2, 146.24)),
    'roof-access': ((-4.9, -2), (2.55, 6.25), (16.2, 19.06)),
    'upper-shaft-frame': ((-1.88, 1.88), (-1.88, 1.88), (153.95, 246.15)),
    'upper-guide-rails': ((-1.48, 1.48), (-.075, 1.46), (154, 246.1)),
    'upper-support-links': ((-8.6, 8.6), (-8.6, 8.6), (152.1, 243.92)),
    'upper-platforms': ((-2.835, 2.835), (-.735, 3.335), (183.87, 218.14)),
    'lift-cars': ((-1.325, 1.325), (-1.3, 1.3), (79.9, 203.94)),
    'lift-glazing': ((-1.272, 1.272), (-1.262, 1.2), (80.095, 203.745)),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def cross(a, b, c):
    u = [b[i]-a[i] for i in range(3)]
    v = [c[i]-a[i] for i in range(3)]
    return (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])


def bounds(vertices):
    return tuple((min(p[i] for p in vertices), max(p[i] for p in vertices)) for i in range(3))


def near(a, b):
    return abs(a-b) <= EPS


def overlaps(a, b):
    return all(min(x[1], y[1])-max(x[0], y[0]) > EPS for x, y in zip(a, b))


def check_mesh(vertices, faces, envelope):
    """Check each disconnected solid, including globally reversed components."""
    require(vertices and faces, 'Empty saved tower mesh')
    for point in vertices:
        require(len(point) == 3 and all(type(v) in (int, float) and math.isfinite(v) for v in point),
                'Non-finite saved tower vertex')
        require(all(lo-EPS <= v <= hi+EPS for v, (lo, hi) in zip(point, envelope)),
                'Saved tower vertex outside part bounds')
    parents = list(range(len(vertices)))

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    edges, directed, used = Counter(), Counter(), set()
    for face in faces:
        require(len(face) >= 3 and len(set(face)) == len(face) and
                all(type(i) is int and 0 <= i < len(vertices) for i in face), 'Invalid saved tower polygon')
        points = [vertices[i] for i in face]
        normal = cross(*points[:3])
        length = math.sqrt(sum(v*v for v in normal))
        require(length > 1e-9, 'Degenerate saved tower polygon')
        # The normal from three rounded corners amplifies float32 error on
        # narrow beam caps; allow 0.1 mm, still far below member dimensions.
        require(all(abs(sum(normal[k]*(p[k]-points[0][k]) for k in range(3)))/length <= 1e-4
                    for p in points[3:]), 'Nonplanar saved tower polygon')
        for i in range(1, len(points)-1):
            triangle = cross(points[0], points[i], points[i+1])
            require(sum(triangle[k]*normal[k] for k in range(3)) > 1e-18,
                    'Degenerate or folded saved tower polygon')
        for a, b in zip(face, face[1:]+face[:1]):
            edges[tuple(sorted((a, b)))] += 1
            directed[(a, b)] += 1
            parents[root(b)] = root(a)
        used.update(face)
    require(len(used) == len(vertices), 'Unused saved tower vertices')
    require(all(n == 2 for n in edges.values()), 'Saved tower solid is not closed: edge incidence differs from two')
    require(all(n == directed[(b, a)] for (a, b), n in directed.items()), 'Inconsistent saved tower winding')
    groups = defaultdict(lambda: {'indices': [], 'faces': []})
    for i in range(len(vertices)):
        groups[root(i)]['indices'].append(i)
    for face in faces:
        groups[root(face[0])]['faces'].append(face)
    components = []
    for group in groups.values():
        points = [vertices[i] for i in group['indices']]
        extent = bounds(points)
        center = tuple((lo+hi)/2 for lo, hi in extent)
        volume = 0.
        for face in group['faces']:
            for j in range(1, len(face)-1):
                a, b, c = [tuple(vertices[i][k]-center[k] for k in range(3)) for i in (face[0], face[j], face[j+1])]
                normal = cross((0, 0, 0), b, c)
                volume += sum(a[k]*normal[k] for k in range(3))/6
        require(volume > 1e-9, 'Inward or zero-volume saved tower component')
        cuboid = len(points) == 8 and len(group['faces']) == 6 and all(len(f) == 4 for f in group['faces'])
        cuboid = cuboid and all(all(near(v, lo) or near(v, hi) for v, (lo, hi) in zip(p, extent)) for p in points)
        components.append({'bounds': extent, 'size': tuple(hi-lo for lo, hi in extent),
                           'center': center, 'volume_m3': volume, 'cuboid': cuboid})
    stats = {'vertices': len(vertices), 'polygons': len(faces), 'components': len(components),
             'bounds_m': bounds(vertices), 'closed_edge_incidence_two': True,
             'consistent_outward_winding': True, 'volume_m3': sum(c['volume_m3'] for c in components)}
    return stats, components


def check_stairs(parts):
    require(len(parts) == 646 and all(p['cuboid'] for p in parts), 'Expected 598 treads, 47 landings and one threshold')
    treads = sorted((p for p in parts if near(p['size'][2], .09)), key=lambda p: p['bounds'][2][1])
    thresholds = [p for p in parts if near(p['size'][0], .8) and near(p['size'][1], 1.4)]
    landings = sorted((p for p in parts if p not in thresholds and (near(p['size'][2], .12) or near(p['size'][2], .13))),
                      key=lambda p: p['bounds'][2][1])
    require(len(treads) == 598 and len(landings) == 47 and len(thresholds) == 1, 'Saved tread, landing or threshold count differs')
    threshold = thresholds[0]
    require(near(threshold['bounds'][2][1], 16.2) and near(threshold['bounds'][0][1], landings[0]['bounds'][0][0]) and
            near(threshold['center'][1], 4.4), 'Roof threshold does not meet starting landing')
    riser, flight_rise = (145.1-16.2)/598, (145.1-16.2)/46
    for i, tread in enumerate(treads):
        require(near(tread['bounds'][2][1], 16.2+(i+1)*riser), 'Saved stair riser sequence differs')
        require(near(tread['size'][0], 5.7/13+.025) and near(tread['size'][1], 1.35), 'Saved tread size differs')
    for i, landing in enumerate(landings):
        require(near(landing['bounds'][2][1], 16.2+i*flight_rise), 'Saved landing elevation differs')
        require(near(landing['size'][0], 1.1) and near(landing['size'][1], 2.95) and
                near(landing['center'][1], 4.4), 'Saved landing span differs')
    for i in range(46):
        flight = treads[i*13:(i+1)*13]
        direction = 1 if i % 2 == 0 else -1
        require(all(near(p['center'][1], 3.6 if direction == 1 else 5.2) for p in flight), 'Stair lane differs')
        for first, second in zip(flight, flight[1:]):
            require(direction*(second['center'][0]-first['center'][0]) > 0 and
                    overlaps(first['bounds'][:2], second['bounds'][:2]), 'Gap or reversal in saved stair flight')
        require(overlaps(landings[i]['bounds'][:2], flight[0]['bounds'][:2]) and
                overlaps(landings[i+1]['bounds'][:2], flight[-1]['bounds'][:2]), 'Saved flight does not meet its landings')
    return {'treads': 598, 'landings': 47, 'thresholds': 1, 'flights': 46, 'bottom_m': 16.2, 'top_m': 145.1,
            'riser_m': riser, 'landing_connections_checked': 92}


def check_open_upper(vertices, faces, components):
    pillars = [p for p in components if p['size'][2] > 90]
    require(len(pillars) == 4, 'Upper frame must have four continuous posts')
    for part in pillars:
        require(part['cuboid'] and near(part['size'][0], .16) and near(part['size'][1], .16) and
                near(part['bounds'][2][0], 154) and near(part['bounds'][2][1], 246.1), 'Upper post span or section differs')
    require({(round(p['center'][0], 2), round(p['center'][1], 2)) for p in pillars} ==
            {(-1.8, -1.8), (-1.8, 1.8), (1.8, -1.8), (1.8, 1.8)}, 'Upper post corners differ')
    require(all(p in pillars or p['size'][2] <= 4.1 for p in components), 'Upper frame contains a tall wall or unbounded member')
    check_no_upper_walls(vertices, faces)
    return {'continuous_posts': 4, 'wide_vertical_walls': 0}


def check_no_upper_walls(vertices, faces):
    # A diagonal beam may have a large bounding rectangle, but its projected
    # surface is narrow. Wide vertical sheets would enclose the open lift.
    for face in faces:
        points = [vertices[i] for i in face]
        extent = bounds(points)
        height = extent[2][1]-extent[2][0]
        if height <= 1:
            continue
        area = [0., 0., 0.]
        for i in range(1, len(points)-1):
            normal = cross(points[0], points[i], points[i+1])
            for k in range(3):
                area[k] += abs(normal[k])/2
        require(max(area[:2])/height <= .3, 'Wide vertical wall closes the upper lift')


def check_guides(parts):
    rails = [p for p in parts if p['cuboid']]
    require(len(rails) == 4 and len(parts) == 11, 'Expected four guide rails and seven ropes')
    locations = set()
    for rail in rails:
        x, y, _ = rail['center']
        require(near(abs(x), 1.43) and (near(y, 0) or near(y, 1.4)) and
                near(rail['bounds'][2][0], 154) and near(rail['bounds'][2][1], 246.1), 'Guide rail location or endpoint differs')
        require(near(rail['size'][0], .1 if near(y, 0) else .08) and
                near(rail['size'][1], .15 if near(y, 0) else .12), 'Guide rail section differs')
        locations.add((round(x, 2), round(y, 2)))
    require(len(locations) == 4, 'Duplicate or missing guide rail')
    ropes = [p for p in parts if not p['cuboid']]
    require(all(near(p['bounds'][2][0], 203.94) and near(p['bounds'][2][1], 246) for p in ropes),
            'Suspension rope passes through the upper cabin or misses its roof')
    return {'guide_rails': 4, 'ropes': 7, 'bottom_m': 154, 'top_m': 246.1}


def check_foottown(parts):
    roof = parts['foottown-roof']
    require(len(roof) == 4 and all(p['cuboid'] and near(p['bounds'][2][0], 16) and near(p['bounds'][2][1], 16.2) for p in roof),
            'FootTown roof panels or 16.2 m access level differ')
    area = sum(p['size'][0]*p['size'][1] for p in roof)
    require(abs(area-(73*58-4.7**2)) < .003, 'FootTown roof coverage differs')
    for i, panel in enumerate(roof):
        require(not overlaps(panel['bounds'][:2], ((-2.35, 2.35), (-2.35, 2.35))), 'Roof closes the lower lift opening')
        require(not any(overlaps(panel['bounds'][:2], other['bounds'][:2]) for other in roof[i+1:]), 'Overlapping roof panels')
    shell, glazing = parts['foottown-shell'], parts['foottown-glazing']
    require(glazing and all(p['cuboid'] for p in shell+glazing), 'Unsupported FootTown wall or pane geometry')
    for pane in glazing:
        require(not any(overlaps(pane['bounds'], wall['bounds']) for wall in shell), 'Opaque FootTown wall behind saved glazing')
    for group in ('foottown-shell', 'foottown-metal', 'foottown-glazing'):
        for part in parts[group]:
            require(not overlaps(part['bounds'], ((-6, 6), (-8, 8), (16.2, 100))), 'FootTown roof access is obstructed')
    doorway = ((-4.8, -4.64), (3.7, 5.1), (16.2, 18.3))
    require(not any(overlaps(p['bounds'], doorway) for p in parts['roof-access']), 'Roof access doorway is blocked')
    return {'roof_top_m': 16.2, 'roof_area_m2': area, 'shaft_opening_area_m2': 4.7**2,
            'glazed_components': len(glazing), 'opaque_backed_panes': 0, 'doorway_open': True}


def check_plates(parts):
    plates, bolts = [p for p in parts if p['cuboid']], [p for p in parts if not p['cuboid']]
    require(len(plates) == 16 and len(bolts) == 64, 'Expected sixteen foot plates and sixty-four bolts')
    require(len({tuple(round(v, 4) for v in p['center'][:2]) for p in plates}) == 16, 'Duplicate tower foot plate')
    quadrants = Counter()
    for plate in plates:
        x, y, _ = plate['center']
        require(all(near(a, b) for a, b in zip(plate['size'], (1.06, 1.06, .19))) and
                near(plate['bounds'][2][0], 1.92) and near(plate['bounds'][2][1], 2.11), 'Foot plate size or contact level differs')
        require(all(min(abs(abs(v)-target) for target in (43.2406666667, 49.9726666667)) <= EPS for v in (x, y)),
                'Foot plate outside pinned leg joints')
        quadrants[(x > 0, y > 0)] += 1
        attached = [b for b in bolts if all(abs(b['center'][i]-plate['center'][i]) <= .5 for i in (0, 1))]
        require(len(attached) == 4 and all(near(b['bounds'][2][0], 2.1) and near(b['bounds'][2][1], 2.28) for b in attached),
                'Missing or floating plate bolts')
    require(len(quadrants) == 4 and set(quadrants.values()) == {4}, 'Foot plates missing at a tower leg')
    return {'plates': 16, 'bolts': 64, 'legs': 4, 'plate_bottom_m': 1.92}


def check_geometry(meshes):
    require(set(meshes) == set(BOUNDS), 'Saved tower part scope differs')
    result, parts = {}, {}
    for name, (vertices, faces) in meshes.items():
        try:
            result[name], parts[name] = check_mesh(vertices, faces, BOUNDS[name])
        except ValueError as error:
            raise ValueError(name+': '+str(error)) from error
    for name in ('upper-guide-rails', 'upper-support-links', 'upper-platforms'):
        check_no_upper_walls(*meshes[name])
    return {'objects': result, 'stairs': check_stairs(parts['stairs-treads']),
            'upper_open_frame': check_open_upper(*meshes['upper-shaft-frame'], parts['upper-shaft-frame']),
            'upper_guides': check_guides(parts['upper-guide-rails']),
            'foottown': check_foottown(parts), 'base_connections': check_plates(parts['base-connections'])}


def retained_snapshot(name, snapshot):
    """Independently select only the pinned legacy core/stair primitives."""
    vertices = snapshot['vertices']
    if name == tower.ORANGE:
        require(len(vertices) == 75064, 'Unexpected original orange vertex count')
        removed = set(range(70464, 72584))
        require(all(abs(vertices[i][0]) < 3.1 and -2.21 <= vertices[i][1] <= 4.91 and
                    15.9 <= vertices[i][2] <= 144 for i in removed), 'Original orange trim envelope differs')
    elif name == tower.WHITE:
        removed = {i for i, p in enumerate(vertices) if abs(p[0]) < 3.1 and 3.3 < p[1] < 4.9 and 16.9 < p[2] < 144}
        require(len(removed) == 4576, 'Original white trim count differs')
    else:
        raise ValueError('Unsupported retained mesh target')
    kept = [i for i in range(len(vertices)) if i not in removed]
    indices = {old: new for new, old in enumerate(kept)}
    faces, flags = [], []
    for face, flag in zip(snapshot['faces'], snapshot['polygon_flags']):
        hits = sum(i in removed for i in face)
        require(hits in (0, len(face)), 'Original trim intersects retained structural member')
        if not hits:
            faces.append([indices[i] for i in face])
            flags.append(flag)
    return {**snapshot, 'vertices': [vertices[i] for i in kept], 'faces': faces, 'polygon_flags': flags}


def compare_retained(expected, saved):
    for key in ('vertices', 'faces', 'polygon_flags', 'matrix_world', 'materials', 'modifiers'):
        require(expected[key] == saved[key], 'Retained tower '+key+' differ')
    payload = json.dumps(saved, separators=(',', ':'), allow_nan=False).encode()
    return {'vertices': len(saved['vertices']), 'polygons': len(saved['faces']),
            'coordinates_faces_material_indices_smooth_flags_exact': True,
            'modifier_settings_exact': True, 'modifiers': saved['modifiers'],
            'retained_data_sha256': hashlib.sha256(payload).hexdigest()}


def snapshot_modifier_rna(value):
    """Serialize the pinned bevel stack, including its embedded curve profile.

    Only its measured execution time is excluded: it is a runtime measurement,
    not a saved setting. Unknown structs/properties fail instead of being skipped.
    """
    kind = value.bl_rna.identifier
    require(kind in ('BevelModifier', 'CurveProfile', 'CurveProfilePoint'),
            'Unsupported retained modifier RNA: '+kind)
    state = {'rna_type': kind}
    for prop in value.bl_rna.properties:
        key = prop.identifier
        if key == 'rna_type' or (kind == 'BevelModifier' and key == 'execution_time'):
            continue
        item = getattr(value, key)
        if prop.type in ('BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'):
            items = list(item) if getattr(prop, 'is_array', False) else [item]
            require(all(type(v) in (str, int, float, bool) and
                        (not isinstance(v, float) or math.isfinite(v)) for v in items),
                    'Unsupported or non-finite retained modifier property: '+key)
            state[key] = items if getattr(prop, 'is_array', False) else item
        elif prop.type == 'POINTER':
            state[key] = None if item is None else snapshot_modifier_rna(item)
        elif prop.type == 'COLLECTION':
            state[key] = [snapshot_modifier_rna(element) for element in item]
        else:
            raise ValueError('Unsupported retained modifier property: '+key)
    return state


def snapshot_object(obj):
    require(obj is not None and obj.type == 'MESH' and not obj.parent and
            not obj.constraints and not obj.animation_data, 'Unsupported retained tower state')
    return {'vertices': [tuple(v.co) for v in obj.data.vertices],
            'faces': [list(p.vertices) for p in obj.data.polygons],
            'polygon_flags': [(p.material_index, p.use_smooth) for p in obj.data.polygons],
            'matrix_world': [list(row) for row in obj.matrix_world],
            'materials': [m.name if m else None for m in obj.data.materials],
            'modifiers': [snapshot_modifier_rna(modifier) for modifier in obj.modifiers]}


def inspect(args):
    import bpy
    from blender_worker import mesh_fingerprint
    require(bpy.app.version_string == '4.5.1 LTS', 'Use Blender 4.5.1 LTS')
    require(not bpy.context.preferences.filepaths.use_scripts_auto_execute, 'Disable Blender auto-execution')
    require(Path(bpy.data.filepath).resolve() == args.input.resolve(), 'Opened scene differs from requested input')
    bpy.context.scene.frame_set(1)
    collection = bpy.data.collections.get(tower.COLLECTION)
    require(collection is not None and collection.get('otw_feature_id') == tower.FEATURE, 'Missing tower feature collection')
    require(not collection.hide_render and not collection.hide_viewport, 'Hidden tower collection')
    require({obj.name for obj in collection.all_objects} == tower.ADDED, 'Tower collection object scope differs')
    require({obj.name for obj in bpy.data.objects if obj.name.startswith(tower.PREFIX)} == tower.ADDED,
            'Unexpected or missing tower structure objects')
    materials = {'foottown-shell': 'brown', 'foottown-glazing': 'glass', 'foottown-metal': 'light',
                 'foottown-roof': 'roof', 'lower-shaft-frame': 'steel', 'lower-shaft-glazing': 'glass',
                 'roof-access': 'light', 'upper-guide-rails': 'steel', 'upper-platforms': 'steel',
                 'lift-cars': 'light', 'lift-glazing': 'glass'}
    meshes, hashes = {}, {}
    for part in BOUNDS:
        obj = bpy.data.objects[tower.PREFIX+part]
        require(obj.type == 'MESH' and not obj.hide_render and not obj.hide_viewport and not obj.hide_get() and obj.visible_get(),
                'Tower object must be a visible mesh: '+part)
        require(obj.get('otw_feature_id') == tower.FEATURE and obj.get('otw_part_id') == 'tokyo-tower-structure-v1-'+part and
                obj.get('otw_structure_revision') == 'v1', 'Tower feature, part or revision differs: '+part)
        require({c.name for c in obj.users_collection} == {tower.COLLECTION}, 'Unexpected tower collection membership')
        require(not obj.modifiers and not obj.parent and not obj.constraints and not obj.animation_data, 'Unsupported saved tower state')
        require(all(abs(obj.matrix_world[r][c]-(r == c)) < 1e-7 for r in range(4) for c in range(4)), 'Unexpected tower transform')
        require(len(obj.data.materials) == 1 and obj.data.materials[0] is not None and
                all(p.material_index == 0 for p in obj.data.polygons), 'Missing or invalid tower material slot')
        material = obj.data.materials[0]
        require(material.name == 'OTW Tower structure v1 / '+materials.get(part, 'orange') and material.use_nodes,
                'Wrong tower material assignment: '+part)
        shader = material.node_tree.nodes.get('Principled BSDF')
        require(shader is not None and near(shader.inputs['Alpha'].default_value, 1), 'Invisible tower shader')
        require(all(math.isfinite(v) for v in material.diffuse_color), 'Non-finite tower material')
        require(not any(v.hide for v in obj.data.vertices) and not any(p.hide for p in obj.data.polygons), 'Hidden tower mesh elements')
        meshes[part] = ([tuple(v.co) for v in obj.data.vertices], [list(p.vertices) for p in obj.data.polygons])
        hashes[obj.name] = mesh_fingerprint(obj.data)
    result = check_geometry(meshes)
    result.update(ok=True, blender_version=bpy.app.version_string, frame=1, autoexec_enabled=False,
                  scene_saved=False, saved_mesh_sha256=hashes, inspected_added_meshes=len(meshes),
                  limitations=['Existing-object preservation is checked separately by review.py fingerprints.',
                               'Closed disconnected solids may intersect at structural joints; this is not a structural or navigation certification.',
                               'Dimensions and layout are inferred exterior geometry, not measured engineering drawings.'])
    # Take plain Python snapshots before opening the original; no candidate is
    # saved and no Blender data references survive the file switch.
    saved = {name: snapshot_object(bpy.data.objects.get(name)) for name in (tower.ORANGE, tower.WHITE)}
    require(digest(args.original) == tower.INPUT_SHA256, 'Original is not the registered city input')
    bpy.ops.wm.open_mainfile(filepath=str(args.original), use_scripts=False)
    require(Path(bpy.data.filepath).resolve() == args.original.resolve(), 'Opened original differs from requested input')
    require(not bpy.context.preferences.filepaths.use_scripts_auto_execute, 'Original enabled Blender auto-execution')
    bpy.context.scene.frame_set(1)
    result['retained_original_meshes'] = {}
    for name in (tower.ORANGE, tower.WHITE):
        obj = bpy.data.objects.get(name)
        require(obj is not None and mesh_fingerprint(obj.data) == tower.BASELINE_HASHES[name], 'Original baseline mesh differs: '+name)
        expected = retained_snapshot(name, snapshot_object(obj))
        result['retained_original_meshes'][name] = compare_retained(expected, saved[name])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', type=Path)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--original', type=Path, required=True, help='Immutable registered city input for retained-member comparison')
    parser.add_argument('--output', type=Path, required=True, help='New JSON report path')
    parser.add_argument('--timeout', type=int, default=900)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    require(not args.output.exists(), 'Refusing to overwrite validation report')
    if args.worker:
        report = {'ok': False}
        try:
            report = inspect(args)
        except Exception as error:
            report['error'] = str(error)
            raise
        finally:
            write(args.output, report)
        return
    require(args.blender is not None and args.timeout > 0, 'Specify Blender and a positive timeout')
    args.input, args.original, args.output = args.input.resolve(), args.original.resolve(), args.output.resolve()
    log = args.output.with_suffix('.log')
    require(not log.exists(), 'Refusing to overwrite validation log')
    input_hash = digest(args.input)
    original_hash = digest(args.original)
    require(original_hash == tower.INPUT_SHA256, 'Original is not the registered city input')
    dependencies = tuple(Path(__file__).with_name(name) for name in
                         ('validate_tower_structure.py', 'tower_structure_v1.py', 'tower_foottown_v1.py', 'blender_worker.py'))
    code_hashes = {path.name: digest(path) for path in dependencies}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {'ok': False}
    try:
        command = [str(args.blender), '--factory-startup', '--disable-autoexec', '--background', str(args.input),
                   '--python-exit-code', '1', '--python', str(Path(__file__).resolve()), '--', '--worker',
                   '--input', str(args.input), '--original', str(args.original), '--output', str(args.output)]
        with log.open('x', encoding='utf-8') as stream:
            process = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=args.timeout, check=False)
        if args.output.exists():
            report = json.loads(args.output.read_text(encoding='utf-8'))
        require(process.returncode == 0 and report.get('ok') is True, report.get('error', 'Saved tower validation failed; inspect local log'))
        require(digest(args.input) == input_hash, 'Saved input scene changed during validation')
        require(digest(args.original) == original_hash, 'Original scene changed during validation')
        require(all(digest(path) == code_hashes[path.name] for path in dependencies), 'Validation code changed during inspection')
        report.update(input_unchanged=True, original_unchanged=True, code_unchanged=True)
    except Exception as error:
        report.update(ok=False, error=str(error))
        raise
    finally:
        report.update(input_sha256=input_hash, original_sha256=original_hash,
                      platform=platform.platform(), python_version=platform.python_version(),
                      code_sha256=code_hashes)
        write(args.output, report)
    print('Saved tower validation complete: '+str(args.output))


if __name__ == '__main__':
    main()
