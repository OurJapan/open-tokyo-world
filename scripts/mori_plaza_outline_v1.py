# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Remove the exclusive contribution of one misread pedestrian-area outline.

The pinned OSM and exported road seed stay external. Match the old generator's
float32 rectangles exactly, then protect every other seed surface. This does
not fill, redesign, or assert the surveyed shape of Central Green.
"""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

FEATURE = 'otw:jp:tokyo:minato:azabudai-mori-jp'
ANCHOR = 'Mori JP podium / stone'
ROADS = {'asphalt 15s road detail', 'gutter 15s road detail', 'pavement_0 unified road'}
ADDED = set()
WAY_ID = '1443867470'
REMOVE_PADDING_M = .003
PROTECT_PADDING_M = .005
AREA_EPS = 1e-8
SOURCE_FILES = {
    'work/osm.xml': (10528704, 'f04e8e70ab24a61ca749375d1ef37401feb0fdc840cc506b670ef71454a6a8ab'),
    'work/twin_towers/tower_surfaces.json': (4429925, '184875e48426ba84b0dddb169f2dc2a414798ac42ee3b7c0047b572991013531'),
}


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def verify_sources(folder):
    folder = Path(folder)
    for name, (size, expected) in SOURCE_FILES.items():
        path = folder / name
        if path.stat().st_size != size:
            raise ValueError('Road source size differs: ' + name)
        with path.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != expected:
            raise ValueError('Road source hash differs: ' + name)


def bounds(poly):
    return (min(p[0] for p in poly), min(p[1] for p in poly),
            max(p[0] for p in poly), max(p[1] for p in poly))


def overlaps(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def cross(a, b):
    return a[0]*b[1] - a[1]*b[0]


def signed_area(poly):
    return sum(cross(a, b) for a, b in zip(poly, poly[1:] + poly[:1])) / 2


def normalize_ring(poly):
    points = []
    for p in poly:
        q = tuple(float(v) for v in p[:2])
        if not all(math.isfinite(v) for v in q):
            raise ValueError('Non-finite source ring')
        if not points or math.dist(q, points[-1]) > 1e-9:
            points.append(q)
    if len(points) > 1 and math.dist(points[0], points[-1]) < 1e-9:
        points.pop()
    if len(points) < 3 or abs(signed_area(points)) < AREA_EPS:
        raise ValueError('Degenerate source ring')
    if signed_area(points) < 0:
        points.reverse()
    # Exported road-box tops are convex; do not reinterpret an unknown shape.
    for i, p in enumerate(points):
        q, r = points[(i+1) % len(points)], points[(i+2) % len(points)]
        if cross((q[0]-p[0], q[1]-p[1]), (r[0]-q[0], r[1]-q[1])) <= 1e-10:
            raise ValueError('Source ring must be strictly convex')
    return points


def ring_key(ring):
    p = [tuple(f32(x) for x in v[:2]) for v in ring]
    if p[-1] == p[0]:
        p.pop()
    return min(tuple(q[i:] + q[:i]) for q in (p, list(reversed(p))) for i in range(len(q)))


def legacy_rectangles(points, width):
    """Reproduce build_city.py box() top XY, including float32 storage."""
    rectangles = []
    for a, b in zip(points, points[1:]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        if length < .1:
            continue
        angle = math.atan2(dy, dx)
        c, s = math.cos(angle), math.sin(angle)
        x, y = (a[0]+b[0])/2, (a[1]+b[1])/2
        rectangles.append([(f32(x+c*i*length/2-s*j*width/2),
                            f32(y+s*i*length/2+c*j*width/2))
                           for i, j in [(-1, -1), (1, -1), (1, 1), (-1, 1)]])
    return rectangles


def match_seed(seed, rectangles, expected_z):
    wanted = Counter(ring_key(p) for p in rectangles)
    matched, remaining = [], []
    for index, row in enumerate(seed):
        key = ring_key(row['ring'])
        if wanted[key] and abs(row['z'] - expected_z) < 1e-6:
            wanted[key] -= 1
            matched.append(index)
        else:
            remaining.append(index)
    if any(wanted.values()):
        raise ValueError('The area outline does not exactly match the road seed')
    return matched, remaining


def padded_ring(poly, amount):
    p = normalize_ring(poly)
    lines = []
    for a, b in zip(p, p[1:] + p[:1]):
        d = (b[0]-a[0], b[1]-a[1])
        length = math.hypot(*d)
        lines.append(((a[0]+amount*d[1]/length, a[1]-amount*d[0]/length), d))
    result = []
    for i, (q, e) in enumerate(lines):
        a, d = lines[i-1]
        denominator = cross(d, e)
        if abs(denominator) < 1e-10:
            raise ValueError('Parallel source-ring sides')
        t = cross((q[0]-a[0], q[1]-a[1]), e) / denominator
        result.append((a[0]+t*d[0], a[1]+t*d[1]))
    return normalize_ring(result)


def build_scope(folder):
    verify_sources(folder)
    folder = Path(folder)
    root = ET.parse(folder / 'work/osm.xml').getroot()
    target = next(w for w in root.findall('way') if w.get('id') == WAY_ID)
    tags = {t.get('k'): t.get('v') for t in target.findall('tag')}
    if tags.get('area') != 'yes' or tags.get('highway') != 'pedestrian' or tags.get('width'):
        raise ValueError('Unexpected pedestrian-area semantics')
    refs = [n.get('ref') for n in target.findall('nd')]
    if refs[0] != refs[-1]:
        raise ValueError('Expected a closed pedestrian area')
    nodes = {n.get('id'): n for n in root.findall('node') if n.get('id') in set(refs)}
    points = [((float(nodes[r].get('lon'))-139.74543)*111320*math.cos(math.radians(35.65858)),
               (float(nodes[r].get('lat'))-35.65858)*110950) for r in refs]
    seed = json.loads((folder / 'work/twin_towers/tower_surfaces.json').read_text(encoding='utf-8'))
    matching = {}
    matched_rows = []
    other_rows = []
    targets = []
    for material, width, z in [('asphalt', 9, .30), ('pavement', 11.1, .23)]:
        rectangles = legacy_rectangles(points, width)
        matched, remaining = match_seed(seed[material], rectangles, z)
        if len(matched) != 111:
            raise ValueError('Unexpected fixed-source match count')
        matching[material] = len(matched)
        matched_rows.extend((material, i, seed[material][i]) for i in matched)
        other_rows.extend(seed[material][i] for i in remaining if round(seed[material][i]['z']) == 0)
        if material == 'pavement':
            targets = [padded_ring(seed[material][i]['ring'], REMOVE_PADDING_M) for i in matched]
    other_rows.extend(row for row in seed['paint'] if round(row['z']) == 0)
    extent = bounds([p for ring in targets for p in ring])
    protected = []
    for row in other_rows:
        b = bounds(row['ring'])
        expanded = (b[0]-PROTECT_PADDING_M*2, b[1]-PROTECT_PADDING_M*2,
                    b[2]+PROTECT_PADDING_M*2, b[3]+PROTECT_PADDING_M*2)
        if overlaps(expanded, extent):
            protected.append(padded_ring(row['ring'], PROTECT_PADDING_M))
    # Only the selected seed records are removed; identical records belonging
    # to other inputs remain in the protection set.
    audit = {'way_id': WAY_ID, 'way_version': target.get('version'),
             'way_timestamp': target.get('timestamp'), 'tags': tags,
             'source_sha256': {k: v[1] for k, v in SOURCE_FILES.items()},
             'matched_seed_faces': matching,
             'matched_records_sha256': hashlib.sha256(json.dumps(matched_rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
             'protected_seed_faces': len(protected),
             'remove_padding_m': REMOVE_PADDING_M, 'protect_padding_m': PROTECT_PADDING_M,
             'attribution': 'Exact float32 XY ring and top-Z match to 222 exported legacy road-box tops; not merely distance to the OSM outline.',
             'scope': 'Exclusive target contribution; overlapping non-target seed surfaces remain protected.'}
    return {'remove': [(p, bounds(p)) for p in targets],
            'protect': [(p, bounds(p)) for p in protected], 'bounds': extent, 'audit': audit}


def clean(poly):
    result = []
    for p in poly:
        if not result or math.dist(p, result[-1]) > 1e-9:
            result.append(tuple(p))
    if len(result) > 1 and math.dist(result[0], result[-1]) < 1e-9:
        result.pop()
    return result


def area(poly):
    if len(poly) < 3:
        return 0.0
    a = poly[0]
    total = 0.0
    for b, c in zip(poly[1:-1], poly[2:]):
        x, y = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
        total += math.sqrt(sum(v*v for v in (x[1]*y[2]-x[2]*y[1],
                                           x[2]*y[0]-x[0]*y[2],
                                           x[0]*y[1]-x[1]*y[0]))) / 2
    return total


def subtract_convex(poly, footprint):
    remaining, outside = poly, []
    for a, b in zip(footprint, footprint[1:] + footprint[:1]):
        if len(remaining) < 3:
            break
        dx, dy = b[0]-a[0], b[1]-a[1]
        values = [dx*(p[1]-a[1])-dy*(p[0]-a[0]) for p in remaining]
        if min(values) >= -1e-10:
            continue
        if max(values) <= 1e-10:
            outside.append(remaining)
            return outside, []
        inside_part, outside_part = [], []
        for i, (p, q) in enumerate(zip(remaining, remaining[1:] + remaining[:1])):
            dp, dq = values[i], values[(i+1) % len(values)]
            (inside_part if dp >= 0 else outside_part).append(p)
            if (dp < 0) != (dq < 0):
                t = dp / (dp-dq)
                point = tuple(p[k]+t*(q[k]-p[k]) for k in range(3))
                inside_part.append(point)
                outside_part.append(point)
        part = clean(outside_part)
        if area(part) > AREA_EPS:
            outside.append(part)
        remaining = clean(inside_part)
    return outside, remaining if area(remaining) > AREA_EPS else []


def split_by_footprints(parts, footprints):
    selected = []
    for footprint, box in footprints:
        next_parts = []
        for part in parts:
            if not overlaps(bounds(part), box):
                next_parts.append(part)
                continue
            outside, inside = subtract_convex(part, footprint)
            next_parts.extend(outside)
            if inside:
                selected.append(inside)
        parts = next_parts
    return parts, selected


def split_scope(poly, scope):
    if not overlaps(bounds(poly), scope['bounds']) or max(p[2] for p in poly) > 1 or min(p[2] for p in poly) < -.01:
        return [poly], []
    eligible, protected = split_by_footprints([poly], scope['protect'])
    outside, removed = split_by_footprints(eligible, scope['remove'])
    if sum(map(area, removed)) <= AREA_EPS:
        return [poly], []
    return protected + outside, removed


def apply(op, mesh_fingerprint, folder):
    import bpy
    scope = build_scope(folder)
    for name in sorted(ROADS):
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != 'MESH' or mesh_fingerprint(obj.data) != op['road_mesh_sha256'][name]:
            raise ValueError('Road baseline hash differs: ' + name)
        if obj.data.users != 1 or obj.data.uv_layers or obj.modifiers or obj.parent or obj.constraints or obj.animation_data:
            raise ValueError('Unsupported road mesh state: ' + name)
        if any(abs(obj.matrix_world[r][c] - (r == c)) > 1e-6 for r in range(4) for c in range(4)):
            raise ValueError('Non-identity road transform')
    audit = {'source_attribution': scope['audit'], 'objects': {}}
    for name in sorted(ROADS):
        obj = bpy.data.objects[name]
        original = obj.data
        coords = [tuple(v.co) for v in original.vertices]
        faces, materials, smooth = [], [], []
        cut_faces, removed_area, rounding_error = 0, 0.0, 0.0
        for face in original.polygons:
            ids = list(face.vertices)
            poly = [coords[i] for i in ids]
            kept, removed = split_scope(poly, scope)
            if not removed:
                faces.append(ids)
                materials.append(face.material_index)
                smooth.append(face.use_smooth)
                continue
            cut_faces += 1
            removed_area += sum(map(area, removed))
            actual_area = 0.0
            for part in kept:
                rounded = clean([tuple(f32(v) for v in p) for p in part])
                if area(rounded) <= AREA_EPS:
                    continue
                actual_area += area(rounded)
                start = len(coords)
                coords.extend(rounded)
                faces.append(list(range(start, len(coords))))
                materials.append(face.material_index)
                smooth.append(face.use_smooth)
            rounding_error += abs(sum(map(area, kept)) - actual_area)
        if not cut_faces or rounding_error > .1:
            raise ValueError('Missing removal or excessive rounding error: ' + name)
        mesh = bpy.data.meshes.new('OTW plaza outline correction / ' + name)
        mesh.from_pydata(coords, [], faces)
        mesh.update()
        for material in original.materials:
            mesh.materials.append(material)
        for face, material, use_smooth in zip(mesh.polygons, materials, smooth):
            face.material_index = material
            face.use_smooth = use_smooth
        obj.data = mesh
        audit['objects'][name] = {'cut_faces': cut_faces, 'removed_surface_area_m2': removed_area,
                                  'rounding_area_error_m2': rounding_error,
                                  'original_vertices_retained': len(original.vertices),
                                  'new_vertices': len(coords) - len(original.vertices)}
    bpy.context.scene['otw_plaza_outline_audit'] = json.dumps(audit, sort_keys=True)
    return audit
