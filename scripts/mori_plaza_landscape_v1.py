# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Bounded, source-based lawn repair and a provisional plaza path connection.

The OSM and intermediate geometry remain external. Plan preparation needs the
pinned production Python environment; Blender application uses only stdlib/bpy.
Elevations and the short entrance connector are explicitly inferred.
"""
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import mori_plaza_outline_v1 as outline

FEATURE = outline.FEATURE
ANCHOR = outline.ANCHOR
PARK = 'park mapped land use'
PAVING = 'OTW Mori Central Green / paving'
CHANGED = {PARK}
ADDED = {PAVING}
PARK_HASH = '607d8e5c7e9d0bd92a04361864ed10dbd747ad706f779de722025d503ef30d25'
INPUT_SHA256 = '1141a1408727d04860d5f722681e92fa63c363efe8da67b9c5e12f4b12d8f9a8'
SOURCE_FILES = {**outline.SOURCE_FILES,
    'work/tower15_env/landuse.npz': (90409, '8aed717b555ac8593146afd9d8a7fd4ba3a93c51c60ab05e982ab866878434a8')}
PARK_IDS = ['1443867471', '1443867472', '1443867473', '1443867474',
            '1443867475', '1443867476', '1443867479']
TOP_Z = .11
BOTTOM_Z = -.01
PLAN_KEYS = {'version', 'input_sha256', 'sources', 'park_ids', 'top_z', 'bottom_z',
             'lawn_triangles', 'paving_triangles', 'paving_rings', 'connector_triangles', 'audit'}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_sources(folder):
    for name, (size, expected) in SOURCE_FILES.items():
        path = Path(folder) / name
        if path.stat().st_size != size or digest(path) != expected:
            raise ValueError('Landscape source differs: ' + name)


def world(u, v, z=0):
    return (-419.8+(2*u+v)/math.sqrt(5), 290.82+(-u+2*v)/math.sqrt(5), z)


def connector_edges():
    """Inferred 7m to 3.6m paved turn from the adopted end to the west path.

    A cubic curve, 24 intervals; start is exactly on v=32, with no extension
    over the adopted paving. It is a design approximation, not an OSM path.
    """
    control = [(0, 32), (0, 45), (-15, 41), (-20, 46)]
    left, right = [], []
    for i in range(25):
        t = i/24
        b = [(1-t)**3, 3*(1-t)**2*t, 3*(1-t)*t*t, t**3]
        p = [sum(b[j]*control[j][k] for j in range(4)) for k in (0, 1)]
        tangent = [sum(3*(control[j+1][k]-control[j][k])*[(1-t)**2, 2*(1-t)*t, t*t][j]
                       for j in range(3)) for k in (0, 1)]
        length = math.hypot(*tangent)
        width = 3.5-1.7*min(t*2, 1)
        normal = (-tangent[1]/length*width, tangent[0]/length*width)
        left.append((p[0]+normal[0], p[1]+normal[1]))
        right.append((p[0]-normal[0], p[1]-normal[1]))
    return left + list(reversed(right))


def prepare_plan(folder):
    import sys
    import numpy as np
    import shapely as sh
    if (sys.version_info[:2] != (3, 12) or np.__version__ != '2.3.5' or
            sh.__version__ != '2.1.2' or sh.geos_version_string != '3.13.1'):
        raise ValueError('Use the pinned Python 3.12 / NumPy 2.3.5 / Shapely 2.1.2 / GEOS 3.13.1 environment')
    verify_sources(folder)
    folder = Path(folder)
    scope = outline.build_scope(folder)
    target = sh.union_all([sh.Polygon(p) for p, _ in scope['remove']])
    protected = sh.union_all([sh.Polygon(p) for p, _ in scope['protect']])
    mask = target.difference(protected)
    root = ET.parse(folder / 'work/osm.xml').getroot()
    nodes = {n.get('id'): ((float(n.get('lon'))-139.74543)*111320*math.cos(math.radians(35.65858)),
                         (float(n.get('lat'))-35.65858)*110950) for n in root.findall('node')}
    ways = {w.get('id'): w for w in root.findall('way')}
    shapes, records = {}, []
    for ident in [outline.WAY_ID, *PARK_IDS]:
        way = ways[ident]
        refs = [n.get('ref') for n in way.findall('nd')]
        tags = {t.get('k'): t.get('v') for t in way.findall('tag')}
        if refs[0] != refs[-1]:
            raise ValueError('Landscape source must be a closed way')
        if ident in PARK_IDS and not (tags.get('landuse') == 'grass' or tags.get('leisure') == 'garden'):
            raise ValueError('Unexpected landscape classification')
        geom = sh.Polygon([nodes[r] for r in refs])
        if not geom.is_valid:
            raise ValueError('Invalid fixed source polygon')
        shapes[ident] = geom
        records.append({'way_id': ident, 'version': way.get('version'), 'timestamp': way.get('timestamp'),
                        'tags': tags, 'area_m2': geom.area})
    source_park = sh.union_all([shapes[i] for i in PARK_IDS])
    with np.load(folder / 'work/tower15_env/landuse.npz', allow_pickle=False) as raw:
        old_park = sh.union_all(sh.polygons(raw['park'].reshape(-1, 3, 3)[:, :, :2]))
    adopted = sh.union_all([sh.Polygon([world(u, v)[:2] for u, v in ring]) for ring in [
        [(-10, 7.5), (10, 7.5), (10, 22), (-10, 22)],
        [(-7, 22), (7, 22), (5, 32), (-5, 32)]]])
    connector = sh.Polygon([world(u, v)[:2] for u, v in connector_edges()])
    if not connector.is_valid:
        raise ValueError('Invalid inferred connector')
    connector = connector.difference(adopted).difference(protected)
    # A union around the source road perimeter restores only the lawn that
    # the proven wrong road used to cover, preserving other parks and roads.
    lawn = source_park.intersection(mask).difference(old_park).difference(adopted).difference(connector)
    paving = shapes[outline.WAY_ID].difference(protected).difference(source_park).difference(adopted).union(connector)

    def snapped(geometry):
        return sh.orient_polygons(sh.set_precision(geometry, .001))

    lawn, paving, connector = [snapped(g) for g in (lawn, paving, connector)]
    # Reapply a small protection margin after the 1mm triangulation grid.
    paving = snapped(paving.difference(protected.buffer(.002)))
    lawn = snapped(lawn.difference(protected.buffer(.002)).difference(paving.buffer(.001)))
    if any(g.is_empty or not g.is_valid for g in (lawn, paving, connector)):
        raise ValueError('Empty or invalid landscape plan')

    def triangles(geometry):
        result = []
        for triangle in sh.get_parts(sh.constrained_delaunay_triangles(geometry)):
            xy = list(triangle.exterior.coords)[:3]
            if outline.signed_area(xy) < 0:
                xy.reverse()
            rounded = [[outline.f32(v) for v in p] for p in xy]
            if abs(outline.signed_area(rounded)) <= 1e-8:
                raise ValueError('Triangulation loses a face at float32 precision')
            result.append(rounded)
        return result

    rings = []
    for polygon in sh.get_parts(paving):
        if polygon.geom_type != 'Polygon':
            raise ValueError('Unexpected paving geometry')
        rings.extend([[[outline.f32(v) for v in xy] for xy in ring.coords[:-1]]
                      for ring in [polygon.exterior, *polygon.interiors]])
    result = {'version': 1, 'input_sha256': INPUT_SHA256,
              'sources': {name: spec[1] for name, spec in SOURCE_FILES.items()},
              'park_ids': PARK_IDS, 'top_z': TOP_Z, 'bottom_z': BOTTOM_Z,
              'lawn_triangles': triangles(lawn), 'paving_triangles': triangles(paving),
              'paving_rings': rings, 'connector_triangles': triangles(connector),
              'audit': {'source_records': records, 'restored_lawn_area_m2': lawn.area,
                        'paving_area_m2': paving.area, 'inferred_connector_area_m2': connector.area,
                        'old_lawn_cut_for_connector_m2': old_park.intersection(connector).area,
                        'protected_overlap_m2': paving.union(lawn).intersection(protected).area,
                        'lawn_paving_overlap_m2': lawn.intersection(paving).area,
                        'coordinate_grid_m': .001, 'top_z_m': TOP_Z,
                        'elevation_basis': 'Inherited 0.11m lawn and adopted entrance-link end, not surveyed terrain.',
                        'connector_basis': 'Inferred short turn to the mapped west path; no source-way ID or survey claimed.',
                        'runtime': {'python': '3.12', 'numpy': np.__version__,
                                    'shapely': sh.__version__, 'geos': sh.geos_version_string}}}
    validate_plan(result)
    return result


def validate_plan(plan):
    if set(plan) != PLAN_KEYS or plan['version'] != 1 or plan['input_sha256'] != INPUT_SHA256:
        raise ValueError('Wrong landscape plan or baseline')
    if (plan['sources'] != {name: spec[1] for name, spec in SOURCE_FILES.items()} or
            plan['park_ids'] != PARK_IDS or plan['top_z'] != TOP_Z or plan['bottom_z'] != BOTTOM_Z):
        raise ValueError('Wrong landscape source or height')
    for key in ('lawn_triangles', 'paving_triangles', 'connector_triangles', 'paving_rings'):
        if not isinstance(plan[key], list) or not 1 <= len(plan[key]) <= 20000:
            raise ValueError('Invalid landscape polygon count')
        for ring in plan[key]:
            if (len(ring) != 3 if key.endswith('triangles') else len(ring) < 3):
                raise ValueError('Invalid landscape face')
            for point in ring:
                if len(point) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in point):
                    raise ValueError('Invalid landscape coordinate')
                if not (-460 < point[0] < -320 and 285 < point[1] < 425):
                    raise ValueError('Landscape coordinate outside the reviewed neighborhood')
            if abs(outline.signed_area(ring)) <= 1e-8:
                raise ValueError('Degenerate landscape face')
            if key.endswith('triangles') and outline.signed_area(ring) < 0:
                raise ValueError('Landscape top face must point upward')


def load_plan(path, expected_hash):
    if digest(path) != expected_hash:
        raise ValueError('Landscape plan hash differs')
    plan = json.loads(Path(path).read_text(encoding='utf-8'))
    validate_plan(plan)
    return plan


def paving_mesh(plan):
    """A closed thin paved slab, with common vertex indices at every edge."""
    coords, faces, index = [], [], {}

    def vertex(xy, z):
        point = tuple(xy) + (outline.f32(z),)
        if point not in index:
            index[point] = len(coords)
            coords.append(point)
        return index[point]

    for triangle in plan['paving_triangles']:
        faces.append([vertex(p, TOP_Z) for p in triangle])
        faces.append([vertex(p, BOTTOM_Z) for p in reversed(triangle)])
    for ring in plan['paving_rings']:
        for a, b in zip(ring, ring[1:]+ring[:1]):
            faces.append([vertex(a, BOTTOM_Z), vertex(b, BOTTOM_Z), vertex(b, TOP_Z), vertex(a, TOP_Z)])
    return coords, faces


def apply(op, mesh_fingerprint, path):
    import bpy
    plan = load_plan(path, op['plan_sha256'])
    obj = bpy.data.objects.get(PARK)
    if not obj or obj.type != 'MESH' or mesh_fingerprint(obj.data) != op['park_mesh_sha256']:
        raise ValueError('Landscape park baseline differs')
    if obj.data.users != 1 or obj.data.uv_layers or obj.modifiers or obj.parent or obj.constraints or obj.animation_data:
        raise ValueError('Unsupported park mesh state')
    if any(abs(obj.matrix_world[r][c]-(r == c)) > 1e-6 for r in range(4) for c in range(4)):
        raise ValueError('Unexpected park transform')
    if bpy.data.objects.get(PAVING):
        raise ValueError('Landscape already applied')
    original = obj.data
    coords = [tuple(v.co) for v in original.vertices]
    faces, materials, smooth = [], [], []
    removal = [(outline.normalize_ring(p), outline.bounds(p)) for p in plan['connector_triangles']]
    scope = {'remove': removal, 'protect': [], 'bounds': outline.bounds([p for ring, _ in removal for p in ring])}
    changed, removed_area = 0, 0.
    for face in original.polygons:
        ids = list(face.vertices)
        poly = [coords[i] for i in ids]
        kept, removed = outline.split_scope(poly, scope)
        if not removed:
            faces.append(ids); materials.append(face.material_index); smooth.append(face.use_smooth)
            continue
        changed += 1
        removed_area += sum(map(outline.area, removed))
        for part in kept:
            part = outline.clean([tuple(outline.f32(v) for v in p) for p in part])
            if outline.area(part) <= 1e-8:
                continue
            start = len(coords); coords.extend(part)
            faces.append(list(range(start, len(coords)))); materials.append(face.material_index); smooth.append(face.use_smooth)
    for triangle in plan['lawn_triangles']:
        start = len(coords)
        coords.extend(tuple(p)+(outline.f32(TOP_Z),) for p in triangle)
        faces.append(list(range(start, len(coords)))); materials.append(0); smooth.append(False)
    mesh = bpy.data.meshes.new('OTW Central Green repaired lawn')
    mesh.from_pydata(coords, [], faces); mesh.update()
    for mat in original.materials:
        mesh.materials.append(mat)
    for face, mat, flag in zip(mesh.polygons, materials, smooth):
        face.material_index = mat; face.use_smooth = flag
    obj.data = mesh
    coords, faces = paving_mesh(plan)
    mesh = bpy.data.meshes.new(PAVING)
    mesh.from_pydata(coords, [], faces); mesh.update()
    mesh.materials.append(bpy.data.materials['pavement'])
    paving = bpy.data.objects.new(PAVING, mesh)
    bpy.data.collections['Mori JP podium'].objects.link(paving)
    paving['otw_feature_id'] = FEATURE
    paving['otw_part'] = 'Mapped plaza paving with inferred entrance connector and inherited flat elevation'
    audit = {'plan_sha256': op['plan_sha256'], 'plan': plan['audit'],
             'original_park_vertices_retained': len(original.vertices),
             'park_cut_faces': changed, 'park_cut_area_m2': removed_area,
             'restored_lawn_triangles': len(plan['lawn_triangles']),
             'paving_vertices': len(coords), 'paving_faces': len(faces)}
    bpy.context.scene['otw_plaza_landscape_audit'] = json.dumps(audit, sort_keys=True)
    return audit
