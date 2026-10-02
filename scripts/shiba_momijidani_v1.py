"""Add a bounded woodland/layout study to the pinned city, without replacing it.

OSM supplies the woodland and path plan. Planting, widths and flat elevations
are inferred; this first pass does not reconstruct the waterfall or relief.
"""
import hashlib
import json
import math
import random
from pathlib import Path

FEATURE = 'otw:jp:tokyo:minato:shiba-momijidani'
ANCHOR_FEATURE = 'otw:jp:tokyo:minato:tokyo-tower'
ANCHOR = 'Tokyo Tower structure / stone'
INPUT_SHA256 = '9c142f54cc85689cb8a8bc00794dfe8e9b6bc9098f121c9fb02cdbc1aa3dbbc4'
OSM_SHA256 = 'f04e8e70ab24a61ca749375d1ef37401feb0fdc840cc506b670ef71454a6a8ab'
COLLECTION = 'OTW Shiba Momijidani v1'
PREFIX = 'OTW Shiba Momijidani / '
PARTS = ('forest floor', 'paths', 'trunks', 'crowns', 'understory')
ADDED = {PREFIX + part for part in PARTS}
CHANGED = set()
BOUNDS = (24., -182., 136., 4.)
ROAD_OBJECTS = {'asphalt 15s road detail', 'gutter 15s road detail',
                'pavement_0 unified road', 'asphalt_7 unified road', 'pavement_7 unified road'}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def inside(point, ring):
    x, y = point[:2]
    odd = False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            odd = not odd
    return odd


def validate_plan(plan):
    if plan.get('version') != 1 or plan.get('input_sha256') != INPUT_SHA256:
        raise ValueError('Shiba plan input/version differs')
    if plan.get('sources', {}).get('osm', {}).get('sha256') != OSM_SHA256:
        raise ValueError('Shiba OSM source differs')
    road_mask = plan.get('sources', {}).get('road_mask', {})
    def valid_hash(value):
        return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
    if road_mask.get('input_sha256') != INPUT_SHA256 or not valid_hash(road_mask.get('sha256')):
        raise ValueError('Shiba saved-road mask source differs')
    roads = road_mask.get('roads', [])
    if len(roads) != len(ROAD_OBJECTS) or {r.get('name') for r in roads} != ROAD_OBJECTS or not all(valid_hash(r.get('mesh_sha256')) for r in roads):
        raise ValueError('Shiba saved-road mesh scope differs')
    boundary = plan.get('boundary', [])
    if not 3 <= len(boundary) <= 100:
        raise ValueError('Invalid woodland boundary')
    for p in boundary:
        if len(p) != 2 or not all(finite(v) for v in p):
            raise ValueError('Invalid boundary coordinates')
        if not (BOUNDS[0] <= p[0] <= BOUNDS[2] and BOUNDS[1] <= p[1] <= BOUNDS[3]):
            raise ValueError('Boundary outside Shiba scope')
    for key, zrange in [('forest_floor', (.12, .16)), ('path_surface', (.49, .53))]:
        mesh = plan.get(key, {})
        verts, faces = mesh.get('vertices', []), mesh.get('faces', [])
        if not (4 <= len(verts) <= 500000 and 4 <= len(faces) <= 500000):
            raise ValueError('Invalid Shiba mesh counts')
        for p in verts:
            if len(p) != 3 or not all(finite(v) for v in p):
                raise ValueError('Invalid Shiba coordinates')
            if not (BOUNDS[0] <= p[0] <= BOUNDS[2] and BOUNDS[1] <= p[1] <= BOUNDS[3] and
                    zrange[0]-1e-7 <= p[2] <= zrange[1]+1e-7):
                raise ValueError('Shiba mesh outside allowed bounds')
        for face in faces:
            if len(face) != 3 or any(type(i) is not int or i < 0 or i >= len(verts) for i in face):
                raise ValueError('Invalid Shiba triangle')
            a, b, c = [verts[i] for i in face]
            u, v = [[p[i]-a[i] for i in range(3)] for p in (b, c)]
            cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
            if sum(n*n for n in cross) < 1e-18:
                raise ValueError('Degenerate Shiba triangle')
    for kind, limits in [('trees', (2.8, 4.8, 7., 12.)), ('shrubs', (.4, 1., .4, 1.))]:
        items = plan.get(kind, [])
        if not 1 <= len(items) <= 1000:
            raise ValueError('Invalid Shiba planting count')
        for item in items:
            if not all(finite(item.get(k)) for k in ('x', 'y', 'radius', 'height')):
                raise ValueError('Invalid planting coordinates')
            if type(item.get('seed')) is not int:
                raise ValueError('Invalid planting seed')
            if not limits[0] <= item['radius'] <= limits[1] or not limits[2] <= item['height'] <= limits[3]:
                raise ValueError('Invalid planting dimensions')
            if not inside((item['x'], item['y']), boundary):
                raise ValueError('Planting outside woodland')
    return plan


class Mesh:
    def __init__(self):
        self.vertices, self.faces, self.materials = [], [], []

    def append(self, vertices, faces, material=0):
        offset = len(self.vertices)
        self.vertices.extend(vertices)
        self.faces.extend(tuple(offset+i for i in face) for face in faces)
        self.materials.extend([material]*len(faces))

    def ellipsoid(self, center, scale, rng, material=0, rings=6, segments=10):
        # Separate poles avoid collapsed quads / zero-area triangles.
        vertices = [(center[0], center[1], center[2]+scale[2])]
        for j in range(1, rings):
            phi = math.pi*j/rings
            for i in range(segments):
                theta = 2*math.pi*i/segments
                wobble = rng.uniform(.87, 1.)
                vertices.append((center[0]+scale[0]*math.sin(phi)*math.cos(theta)*wobble,
                                 center[1]+scale[1]*math.sin(phi)*math.sin(theta)*wobble,
                                 center[2]+scale[2]*math.cos(phi)*wobble))
        bottom = len(vertices)
        vertices.append((center[0], center[1], center[2]-scale[2]))
        faces = [(0, 1+i, 1+(i+1)%segments) for i in range(segments)]
        for j in range(rings-2):
            a, b = 1+j*segments, 1+(j+1)*segments
            for i in range(segments):
                n = (i+1)%segments
                faces.extend([(a+i, b+i, b+n), (a+i, b+n, a+n)])
        last = 1+(rings-2)*segments
        faces.extend((last+i, bottom, last+(i+1)%segments) for i in range(segments))
        self.append(vertices, faces, material)

    def branch(self, start, end, r0, r1, material=0):
        from mathutils import Vector
        a, b = Vector(start), Vector(end)
        axis = (b-a).normalized()
        u = axis.cross(Vector((0, 1, 0))).normalized()
        if u.length < .1:
            u = axis.cross(Vector((1, 0, 0))).normalized()
        v = axis.cross(u).normalized()
        vertices = [tuple(c+r*(math.cos(i*math.tau/8)*u+math.sin(i*math.tau/8)*v))
                    for c, r in ((a, r0), (b, r1)) for i in range(8)]
        vertices += [tuple(a), tuple(b)]
        faces = []
        for i in range(8):
            n = (i+1)%8
            faces.extend([(i, n, n+8), (i, n+8, i+8), (16, n, i), (17, i+8, n+8)])
        self.append(vertices, faces, material)

    def foliage(self, center, scale, rng, count):
        """Small lobed leaf surfaces; no opaque proxy spheres in the canopy."""
        outline = [(0,1),(.17,.50),(.68,.64),(.46,.18),(.89,.02),
                   (.36,-.24),(0,-.72),(-.36,-.24),(-.89,.02),
                   (-.46,.18),(-.68,.64),(-.17,.50)]
        for _ in range(count):
            while True:
                q = [rng.uniform(-1,1) for _ in range(3)]
                if .04 < sum(v*v for v in q) < 1:
                    break
            c = [center[i]+scale[i]*q[i] for i in range(3)]
            angle, tilt, size = rng.random()*math.tau, rng.uniform(-1.0,1.0), rng.uniform(.17,.30)
            u = (math.cos(angle), math.sin(angle), 0)
            v = (-math.sin(angle)*math.cos(tilt), math.cos(angle)*math.cos(tilt), math.sin(tilt))
            vertices = [tuple(c)]
            for a,b in outline:
                vertices.append(tuple(c[i]+size*(a*u[i]+b*v[i])+(size*.07 if i==2 else 0) for i in range(3)))
            self.append(vertices,[(0,1+i,1+(i+1)%len(outline)) for i in range(len(outline))],rng.randrange(5))


def vegetation(plan):
    trunks, crowns, understory = Mesh(), Mesh(), Mesh()
    for tree in plan['trees']:
        rng = random.Random(tree['seed'])
        x, y, r, h = (tree[k] for k in ('x', 'y', 'radius', 'height'))
        base = (x, y, .16)
        fork = (x+rng.uniform(-.3,.3), y+rng.uniform(-.3,.3), .16+h*.38)
        trunks.branch(base, fork, h*.027, h*.018)
        # Broadleaf branching and overlapping, irregular crown clusters.
        for k in range(7):
            angle = k*math.tau/7+rng.uniform(-.18,.18)
            distance = r*rng.uniform(.34,.52)
            tip = (x+math.cos(angle)*distance, y+math.sin(angle)*distance, .16+h*rng.uniform(.60,.79))
            joint = tuple(fork[i]+(tip[i]-fork[i])*.55 for i in range(3))
            trunks.branch(fork, joint, h*.012, h*.007)
            trunks.branch(joint, tip, h*.007, .025)
            for j in range(3):
                ca = angle+j*math.tau/3
                c = (tip[0]+math.cos(ca)*r*.10, tip[1]+math.sin(ca)*r*.10, tip[2]+j*h*.035)
                crowns.foliage(c, (r*.26,r*.26,h*.115), rng, 115)
        crowns.foliage((x,y,.16+h*.80), (r*.42,r*.42,h*.14), rng, 290)
    for shrub in plan['shrubs']:
        rng = random.Random(shrub['seed'])
        x,y,r,h = (shrub[k] for k in ('x','y','radius','height'))
        for i in range(3):
            a = i*math.tau/3
            understory.ellipsoid((x+math.cos(a)*r*.3,y+math.sin(a)*r*.3,.16+h*.5),
                                (r*.55,r*.55,h*.5), rng, rng.randrange(3), rings=5, segments=8)
    return trunks, crowns, understory


def material(name, color, noise=False, roughness=.85):
    import bpy
    name = PREFIX + name
    if bpy.data.materials.get(name):
        raise ValueError('Shiba material already exists: '+name)
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color,1)
    shader.inputs['Roughness'].default_value = roughness
    if noise:
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        texture = nodes.new('ShaderNodeTexNoise')
        texture.inputs['Scale'].default_value = 2.5
        texture.inputs['Detail'].default_value = 3
        ramp = nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color = (*(c*.60 for c in color),1)
        ramp.color_ramp.elements[1].color = (*(min(c*1.4,1) for c in color),1)
        links.new(texture.outputs['Fac'],ramp.inputs['Fac'])
        links.new(ramp.outputs['Color'],shader.inputs['Base Color'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .2
        bump.inputs['Distance'].default_value = .06
        links.new(texture.outputs['Fac'],bump.inputs['Height'])
        links.new(bump.outputs['Normal'],shader.inputs['Normal'])
    return mat


def apply(obj, op, plan_path):
    import bpy
    if obj.name != ANCHOR or obj.get('otw_feature_id') != ANCHOR_FEATURE:
        raise ValueError('Unexpected Shiba anchor')
    if digest(plan_path) != op['plan_sha256']:
        raise ValueError('Shiba plan hash differs at application')
    plan = validate_plan(json.loads(Path(plan_path).read_text(encoding='utf8')))
    if bpy.data.collections.get(COLLECTION) or ADDED.intersection(bpy.data.objects.keys()):
        raise ValueError('Shiba candidate already exists')
    coll = bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(coll)
    coll['otw_feature_id'] = FEATURE
    coll['otw_accuracy'] = 'OSM horizontal layout; inferred planting/width/flat elevation. Water and relief pending.'
    coll['otw_plan_sha256'] = op['plan_sha256']
    floor_mat = material('woodland soil', (.095,.12,.049), True)
    path_mat = material('path asphalt', (.19,.19,.175), True)
    bark_mat = material('bark', (.15,.112,.077), True)
    greens = [material('leaf '+str(i), c, True) for i,c in enumerate([
        (.07,.19,.033),(.095,.23,.044),(.14,.26,.05),(.065,.16,.025),(.17,.27,.063)])]
    for mat in greens:
        mat.node_tree.nodes.get('Principled BSDF').inputs['Subsurface Weight'].default_value = .08
    shrubs = [material('low foliage '+str(i),c,True) for i,c in enumerate([
        (.07,.15,.035),(.09,.20,.045),(.15,.24,.07)])]
    trunks, crowns, understory = vegetation(plan)
    geometries = [plan['forest_floor'],plan['path_surface'],trunks,crowns,understory]
    materials = [[floor_mat],[path_mat],[bark_mat],greens,shrubs]
    for part, geometry, mats in zip(PARTS,geometries,materials):
        name = PREFIX+part
        mesh = bpy.data.meshes.new(name)
        verts, faces = (geometry['vertices'],geometry['faces']) if isinstance(geometry,dict) else (geometry.vertices,geometry.faces)
        mesh.from_pydata(verts,[],faces)
        mesh.update()
        new = bpy.data.objects.new(name,mesh)
        coll.objects.link(new)
        for mat in mats: mesh.materials.append(mat)
        if not isinstance(geometry,dict):
            for poly,index in zip(mesh.polygons,geometry.materials):
                poly.material_index=index
                poly.use_smooth=True
        new['otw_feature_id'] = FEATURE
        new['otw_part_id'] = 'shiba-momijidani-v1-'+part.replace(' ','-')
        new['otw_plan_sha256'] = op['plan_sha256']
        new['otw_source'] = 'OpenStreetMap contributors; fixed local snapshot; ODbL'
        new['otw_accuracy'] = 'Mapped woodland/path XY. Inferred planting, dimensions, material and flat Z.'
    return sorted(ADDED)
