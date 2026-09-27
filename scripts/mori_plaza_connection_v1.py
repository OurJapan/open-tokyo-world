# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""A bounded model-space height correction at the inherited footway junction.

Keep XY footprints and every face outside the 16m square. A flat 8m core
meets the adopted 0.11m paving; four 4m transition strips return continuously
to the original heights. This is an inferred repair, not surveyed terrain.
"""
import json
import math
from functools import cache
from pathlib import Path
import xml.etree.ElementTree as ET

import mori_plaza_outline_v1 as outline
from mori_plaza_landscape_v1 import world, digest, paving_mesh

FEATURE, ANCHOR, ROADS = outline.FEATURE, outline.ANCHOR, outline.ROADS
SEAM = 'OTW Mori entrance junction / seam fill'
ADDED = {SEAM}
INPUT_SHA256 = '2e2cce08aa581ef6a99d60c9fe993b8c4e53ff7f5cffb687f9d9c4cee19dc544'
CENTER = (-22., 50.)
CORE = 4.
OUTER = 8.
TOP_Z = .11
FOOTWAY = '1443867478'


def local(x, y):
    x, y = x + 419.8, y - 290.82
    return ((2*x-y)/math.sqrt(5), (x+2*y)/math.sqrt(5))


def factor(x, y):
    u, v = local(x, y)
    radius = max(abs(u-CENTER[0]), abs(v-CENTER[1]))
    return min(1., max(0., (radius-CORE)/(OUTER-CORE)))


@cache
def cells():
    def square(radius):
        return [world(CENTER[0]+u*radius, CENTER[1]+v*radius)[:2]
                for u, v in [(-1,-1), (1,-1), (1,1), (-1,1)]]
    inner, outer = square(CORE), square(OUTER)
    return [inner] + [outline.normalize_ring([inner[i], outer[i],
                       outer[(i+1)%4], inner[(i+1)%4]]) for i in range(4)]


@cache
def scope_bounds():
    return outline.bounds([p for ring in cells() for p in ring])


def partition(poly):
    """Return untouched exterior and affine height cells, including curbs."""
    if not outline.overlaps(outline.bounds(poly), scope_bounds()):
        return [poly], []
    outside = [poly]
    selected = []
    for cell in cells():
        remainder = []
        for part in outside:
            rest, inside = outline.subtract_convex(part, cell)
            remainder.extend(rest)
            if inside:
                selected.append(inside)
        outside = remainder
    return outside, selected


def lowered(poly):
    result = outline.clean([tuple(outline.f32(v) for v in
                (x, y, TOP_Z + (z-TOP_Z)*factor(x, y))) for x, y, z in poly])
    if outline.area(result) <= outline.AREA_EPS:
        return []  # The old vertical riser disappears in the flat core.
    if abs(max(p[2] for p in poly)-min(p[2] for p in poly)) < 1e-6:
        if outline.signed_area(result) < 0:
            result.reverse()  # New walking surfaces face upward.
    return result


def source_attribution(folder):
    """Match the nearby footway to the fixed seed, without executing old code."""
    outline.verify_sources(folder)
    folder = Path(folder)
    root = ET.parse(folder/'work/osm.xml').getroot()
    way = next(w for w in root.findall('way') if w.get('id') == FOOTWAY)
    tags = {t.get('k'):t.get('v') for t in way.findall('tag')}
    if tags != {'highway':'footway', 'surface':'paving_stones'}:
        raise ValueError('Unexpected connection source semantics')
    nodes = {n.get('id'):((float(n.get('lon'))-139.74543)*111320*math.cos(math.radians(35.65858)),
                         (float(n.get('lat'))-35.65858)*110950) for n in root.findall('node')}
    points = [nodes[n.get('ref')] for n in way.findall('nd')]
    seed = json.loads((folder/'work/twin_towers/tower_surfaces.json').read_text(encoding='utf-8'))
    counts = {}
    for width, z in [(4.1, .23), (2., .30)]:
        matches, _ = outline.match_seed(seed['pavement'], outline.legacy_rectangles(points, width), z)
        counts[str(width)] = len(matches)
    return {'way_id':FOOTWAY, 'version':way.get('version'), 'timestamp':way.get('timestamp'),
            'tags':tags, 'matched_seed_faces_by_width_m':counts,
            'source_sha256':{k:v[1] for k,v in outline.SOURCE_FILES.items()},
            'basis':'Exact float32 ring and height match. Height transitions are provisional model-space choices.'}


def validate_plan(plan):
    if (set(plan)!={'version','input_sha256','paving_triangles','paving_rings','audit'} or
            plan['version']!=1 or plan['input_sha256']!=INPUT_SHA256):
        raise ValueError('Wrong connection plan or input')
    for key in ('paving_triangles','paving_rings'):
        if not isinstance(plan[key],list) or not 1<=len(plan[key])<=10000:
            raise ValueError('Invalid seam polygon count')
        for ring in plan[key]:
            if len(ring)<3 or key=='paving_triangles' and len(ring)!=3:
                raise ValueError('Invalid seam polygon')
            for point in ring:
                if len(point)!=2 or not all(isinstance(x,(float,int)) and math.isfinite(x) for x in point):
                    raise ValueError('Invalid seam coordinate')
                u,v=local(*point)
                if max(abs(u-CENTER[0]),abs(v-CENTER[1]))>CORE-.019:
                    raise ValueError('Seam outside flat core')
            area=outline.signed_area(ring)
            if abs(area)<1e-10 or key=='paving_triangles' and area<0:
                raise ValueError('Degenerate or inverted seam polygon')
    if sum(outline.signed_area(p) for p in plan['paving_triangles'])>.5:
        raise ValueError('Seam fill exceeds bounded area')


def load_plan(path,expected_hash):
    if digest(path)!=expected_hash:raise ValueError('Connection plan hash differs')
    plan=json.loads(Path(path).read_text(encoding='utf-8'))
    validate_plan(plan)
    return plan


def apply(op, mesh_fingerprint, folder, plan_path):
    import bpy
    attribution = source_attribution(folder)
    plan=load_plan(plan_path,op['plan_sha256'])
    if bpy.data.objects.get(SEAM):raise ValueError('Connection already applied')
    for name in sorted(ROADS):
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != 'MESH' or mesh_fingerprint(obj.data) != op['road_mesh_sha256'][name]:
            raise ValueError('Connection road baseline differs: '+name)
        if obj.data.users != 1 or obj.data.uv_layers or obj.modifiers or obj.parent or obj.constraints or obj.animation_data:
            raise ValueError('Unsupported road state: '+name)
        if any(abs(obj.matrix_world[r][c]-(r==c)) > 1e-6 for r in range(4) for c in range(4)):
            raise ValueError('Unexpected road transform')
    audit = {'source_attribution':attribution, 'center_uv_m':CENTER, 'flat_half_width_m':CORE,
             'outer_half_width_m':OUTER, 'flat_height_m':TOP_Z, 'objects':{}}
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
            if not selected or all(factor(*p[:2]) > 1-1e-8 for part in selected for p in part):
                faces.append(ids); materials.append(face.material_index); smooth.append(face.use_smooth)
                continue
            if any(not .29999 <= p[2] <= .46001 for p in poly):
                raise ValueError('Unexpected road elevation in correction scope: '+name)
            changed += 1
            pieces = [outline.clean([tuple(outline.f32(v) for v in p) for p in part]) for part in kept]
            for part in selected:
                mapped = lowered(part)
                if mapped: pieces.append(mapped)
                else: collapsed += 1
            for part in pieces:
                if outline.area(part) <= outline.AREA_EPS:
                    raise ValueError('Degenerate cut outside flattened riser')
                start = len(coords); coords.extend(part)
                faces.append(list(range(start,len(coords))))
                materials.append(face.material_index); smooth.append(face.use_smooth)
        if not changed:
            raise ValueError('Missing local road correction: '+name)
        mesh = bpy.data.meshes.new('OTW local junction height / '+name)
        mesh.from_pydata(coords, [], faces); mesh.update()
        for mat in original.materials: mesh.materials.append(mat)
        for face, mat, flag in zip(mesh.polygons, materials, smooth):
            face.material_index = mat; face.use_smooth = flag
        obj.data = mesh
        audit['objects'][name] = {'changed_original_faces':changed, 'collapsed_riser_fragments':collapsed,
                                  'original_vertices_retained':len(original.vertices),
                                  'new_vertices':len(coords)-len(original.vertices)}
    coords,faces=paving_mesh(plan)
    mesh=bpy.data.meshes.new(SEAM);mesh.from_pydata(coords,[],faces);mesh.update()
    mesh.materials.append(bpy.data.materials['pavement'])
    obj=bpy.data.objects.new(SEAM,mesh)
    bpy.data.collections['Mori JP podium'].objects.link(obj)
    obj['otw_feature_id']=FEATURE
    obj['otw_part']='Millimetric seam infill at the provisional entrance junction'
    audit['seam_fill']={'plan_sha256':op['plan_sha256'],**plan['audit']}
    bpy.context.scene['otw_plaza_connection_audit'] = json.dumps(audit,sort_keys=True)
    return audit
