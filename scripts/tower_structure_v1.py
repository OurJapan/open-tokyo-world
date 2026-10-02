# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Bounded, photo-guided Tokyo Tower exterior corrections, not engineering CAD."""
import math

INPUT_SHA256 = 'aa80b552f267d935d3c5d943ac95d0d410d6ec7abb170346bef707eee6cae2e2'  # PR #56 composed city
FEATURE = 'otw:jp:tokyo:minato:tokyo-tower'
ANCHOR = 'Tokyo Tower structure / stone'
ORANGE = 'Tokyo Tower structure / orange'
WHITE = 'Tokyo Tower structure / white'
DARK = 'Tokyo Tower structure / darkmetal'
BASELINE_HASHES = {
    ANCHOR: '83c51bad1b8f8e02a71901e21ec06c5ef2ac24cb02510d9f338639aff7085943',
    ORANGE: 'b6adab8152af75c884184a2f2fd5b49a1a227315324963deb7932ad97f8283db',
    WHITE: '3ffc88b2d5537dc28070fd486bf2866bfde63b5dc933c5060b12798280e3b722',
    DARK: '22d54047bb948c1985adaf15bb1c171c61d526d3ca3d8b7db5e404de7573539f',
}
CHANGED = {ORANGE, WHITE, DARK}
COLLECTION = 'OTW Tokyo Tower structure v1'
PREFIX = 'OTW Tokyo Tower structure / '
GROUPS = ('foottown-shell', 'foottown-glazing', 'foottown-metal', 'foottown-roof',
          'base-connections', 'lower-shaft-frame', 'lower-shaft-glazing',
          'stairs-frame', 'stairs-treads', 'stairs-guards', 'roof-access',
          'upper-shaft-frame', 'upper-guide-rails', 'upper-support-links',
          'upper-platforms', 'lift-cars', 'lift-glazing', 'upper-suspension',
          'upper-landing-doors', 'upper-car-shell', 'upper-car-glass',
          'upper-car-mirror', 'upper-car-floor', 'upper-car-rigging', 'upper-car-dark',
          'upper-service-stairs')
ADDED = {PREFIX + group for group in GROUPS}
STAIR_BOTTOM, STAIR_TOP = 16.2, 145.1
STAIR_FLIGHTS, STEPS_PER_FLIGHT = 46, 13
UPPER_BOTTOM, UPPER_TOP = 154.0, 246.1
RESCUE_LEVELS = (184.0, 217.0)  # Existence sourced; levels and dimensions inferred.


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sub(a, b): return tuple(a[i] - b[i] for i in range(3))
def dot(a, b): return sum(a[i] * b[i] for i in range(3))
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def unit(a):
    size = math.sqrt(dot(a, a))
    require(size > 1e-9, 'Zero-length vector')
    return tuple(x / size for x in a)


class MeshBuilder:
    """Closed boxes and capped beams; disconnected solids may meet at joints."""
    def __init__(self):
        self.groups = {}

    def add(self, group, vertices, faces):
        require(all(math.isfinite(x) for v in vertices for x in v), 'Nonfinite geometry')
        target = self.groups.setdefault(group, {'vertices': [], 'faces': []})
        offset = len(target['vertices'])
        target['vertices'].extend(tuple(v) for v in vertices)
        target['faces'].extend(tuple(offset+i for i in face) for face in faces)

    def box(self, group, center, size):
        require(all(x > 0 for x in size), 'Invalid box size')
        vertices = [(center[0]+x*size[0]/2, center[1]+y*size[1]/2, center[2]+z*size[2]/2)
                    for z in (-1, 1) for x, y in ((-1,-1),(1,-1),(1,1),(-1,1))]
        self.add(group, vertices, [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])

    def beam(self, group, a, b, radius, sides=8):
        require(radius > 0 and sides >= 3, 'Invalid beam section')
        axis = unit(sub(b, a))
        u = unit(cross(axis, (0,0,1) if abs(axis[2]) < .98 else (0,1,0)))
        v = cross(axis, u)
        vertices = [tuple(p[k] + radius*(math.cos(i*math.tau/sides)*u[k] + math.sin(i*math.tau/sides)*v[k])
                          for k in range(3)) for p in (a,b) for i in range(sides)]
        self.add(group, vertices, [tuple(range(sides-1,-1,-1)), tuple(range(sides,2*sides))] +
                 [(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)])


def tower_half_width(z):
    levels = (155,180,205,230,250)
    widths = (8.4,7,5.7,4.3,3.25)
    for a,b,wa,wb in zip(levels, levels[1:], widths, widths[1:]):
        if z <= b:
            return wa+(wb-wa)*(z-a)/(b-a)
    return widths[-1]


def railing(builder, group, a, b, height=1.1, spacing=.9):
    top_a = (a[0],a[1],a[2]+height)
    top_b = (b[0],b[1],b[2]+height)
    builder.beam(group, top_a, top_b, .034)
    builder.beam(group, (a[0],a[1],a[2]+.50), (b[0],b[1],b[2]+.50), .024)
    length = math.sqrt(dot(sub(b,a),sub(b,a)))
    count = max(1, math.ceil(length/spacing))
    for i in range(count+1):
        p = tuple(a[k]+(b[k]-a[k])*i/count for k in range(3))
        builder.beam(group, p, (p[0],p[1],p[2]+height), .024)


def stairs_geometry(b):
    rise = (STAIR_TOP-STAIR_BOTTOM)/STAIR_FLIGHTS
    tread_rise = rise/STEPS_PER_FLIGHT
    for flight in range(STAIR_FLIGHTS):
        direction = 1 if flight%2 == 0 else -1
        y = 3.60 if direction == 1 else 5.20
        bottom = STAIR_BOTTOM + flight*rise
        for step in range(STEPS_PER_FLIGHT):
            x = direction*(-2.85+(step+.5)*5.7/STEPS_PER_FLIGHT)
            top = bottom+(step+1)*tread_rise
            b.box('stairs-treads', (x,y,top-.045), (5.7/STEPS_PER_FLIGHT+.025,1.35,.09))
        for yy in (y-.68, y+.68):
            a=(-direction*2.85,yy,bottom-.12)
            end=(direction*2.85,yy,bottom+rise-.12)
            b.beam('stairs-frame',a,end,.075)
            railing(b,'stairs-guards',(-direction*2.85,yy,bottom),(direction*2.85,yy,bottom+rise),spacing=.65)
        # Half-turn landing joins adjacent flights, rather than isolated treads.
        landing_x = direction*3.40
        b.box('stairs-treads',(landing_x,4.40,bottom+rise-.065),(1.10,2.95,.13))
        railing(b,'stairs-guards',(direction*3.95,2.925,bottom+rise),(direction*3.95,5.875,bottom+rise))
    for x in (-3.96,3.96):
        for y in (2.90,5.90):
            b.beam('stairs-frame',(x,y,STAIR_BOTTOM),(x,y,STAIR_TOP+.03),.095)
    # Roof landing and simple access doorway; no unverified signs or shop plan.
    b.box('stairs-treads',(-3.40,4.40,STAIR_BOTTOM-.06),(1.10,2.95,.12))
    # West doorway keeps a walk-in opening to the starting roof landing.
    for yy in (3.15,5.65):
        b.box('roof-access',(-4.72,yy,17.55),(.16,1.1,2.7))
    b.box('roof-access',(-4.72,4.4,18.6),(.16,1.4,.6))
    b.box('stairs-treads',(-4.35,4.4,STAIR_BOTTOM-.06),(.8,1.4,.12))
    for yy in (2.65,6.15):
        b.box('roof-access',(-3.5,yy,17.55),(2.6,.14,2.7))
    b.box('roof-access',(-3.5,4.4,18.98),(2.8,3.7,.16))


def lower_lift_geometry(b):
    low, high, half = .45, STAIR_TOP+.25, 2.20
    for x in (-half,half):
        for y in (-half,half):
            b.box('lower-shaft-frame',(x,y,(low+high)/2),(.14,.14,high-low))
    # A weather-enclosed lower elevator envelope, separately from the open upper lift.
    panel_count=math.ceil((high-low)/4)
    panel_height=(high-low)/panel_count
    for i in range(panel_count):
        z=low+i*panel_height
        for sign in (-1,1):
            b.box('lower-shaft-frame',(0,sign*half,z+.06),(4.4,.14,.12))
            b.box('lower-shaft-frame',(sign*half,0,z+.06),(.14,4.4,.12))
            b.box('lower-shaft-glazing',(0,sign*half,z+panel_height/2),(4.16,.025,panel_height-.14))
            b.box('lower-shaft-glazing',(sign*half,0,z+panel_height/2),(.025,4.16,panel_height-.14))
    for x in (-.74,.74):
        b.box('lower-shaft-frame',(x,-half,(low+high)/2),(.075,.12,high-low))


def upper_lift_geometry(b):
    from tower_upper_lift_v2 import geometry as upper_geometry
    upper_geometry(b)
    # Preserve the separate, simple lower lift envelope from the first revision.
    for z in (80.0,):
        b.box('lift-cars',(0,0,z),(2.65,2.60,.20))
        b.box('lift-cars',(0,0,z+2.85),(2.65,2.60,.18))
        b.box('lift-cars',(0,1.22,z+1.42),(2.55,.12,2.65))
        for x in (-1.26,1.26):
            b.box('lift-cars',(x,0,z+.60),(.11,2.5,1.0))
            b.box('lift-glazing',(x,0,z+1.92),(.024,2.4,1.55))
        b.box('lift-glazing',(0,-1.25,z+1.42),(2.44,.024,2.65))
        for x in (-1.26,0,1.26):
            b.box('lift-cars',(x,-1.27,z+1.42),(.055,.06,2.68))


def geometry():
    from tower_foottown_v1 import geometry as foottown_geometry
    b=MeshBuilder()
    foottown_geometry(b)
    stairs_geometry(b)
    lower_lift_geometry(b)
    upper_lift_geometry(b)
    # Base plates occupy the current leg/plinth joints. Plate/bolt sizes inferred.
    for sx in (-1,1):
        for sy in (-1,1):
            center=(sx*46.6066666667,sy*46.6066666667)
            for dx in (-3.366,3.366):
                for dy in (-3.366,3.366):
                    x,y=center[0]+dx,center[1]+dy
                    b.box('base-connections',(x,y,2.015),(1.06,1.06,.19))
                    for bx in (-.40,.40):
                        for by in (-.40,.40):
                            b.beam('base-connections',(x+bx,y+by,2.10),(x+bx,y+by,2.28),.065,6)
    require(set(b.groups)==set(GROUPS),'Incomplete tower geometry groups')
    return b.groups


def trim_indices(name, vertices):
    """Only discard the pinned historical core/stair pieces, not tower lattice."""
    if name==ORANGE:
        selected=set(range(70464,72584))  # Core box + 88 old stair-rail girders.
        require(len(vertices)==75064, 'Unexpected orange vertex count')
        require(all(abs(vertices[i][0])<3.1 and -2.21<=vertices[i][1]<=4.91 and 15.9<=vertices[i][2]<=144
                    for i in selected),'Pinned stair/core vertex bounds differ')
        return selected
    if name==WHITE:
        selected={i for i,p in enumerate(vertices) if abs(p[0])<3.1 and 3.3<p[1]<4.9 and 16.9<p[2]<144}
        require(len(selected)==4576,'Expected exactly 572 historical stair treads')
        return selected
    raise ValueError('Unsupported trim target')


def trimmed_mesh(name, vertices, faces):
    removed=trim_indices(name,vertices)
    kept_faces=[]
    for face in faces:
        hits=sum(i in removed for i in face)
        require(hits in (0,len(face)),'Trim would cut an existing structural member')
        if not hits:kept_faces.append(tuple(face))
    kept=[i for i in range(len(vertices)) if i not in removed]
    mapping={old:new for new,old in enumerate(kept)}
    return [vertices[i] for i in kept],[tuple(mapping[i] for i in f) for f in kept_faces]


def apply(op, fingerprint):
    import bpy
    require(op['target_mesh_sha256']==BASELINE_HASHES,'Tower target hash manifest differs')
    require(not bpy.data.collections.get(COLLECTION),'Tower structure correction already applied')
    require(not any(bpy.data.objects.get(n) for n in ADDED),'Tower addition name collision')
    for name,expected in BASELINE_HASHES.items():
        obj=bpy.data.objects.get(name)
        require(obj and obj.type=='MESH' and fingerprint(obj.data)==expected,'Tower baseline differs: '+name)
        require(obj.get('otw_feature_id')==FEATURE,'Tower target feature differs: '+name)
    data=geometry()
    for name in (ORANGE,WHITE):
        obj=bpy.data.objects[name]
        require(not obj.data.uv_layers,'Cannot silently drop existing UVs')
        removed=trim_indices(name,[tuple(v.co) for v in obj.data.vertices])
        face_state=[(p.material_index,p.use_smooth) for p in obj.data.polygons
                    if not any(i in removed for i in p.vertices)]
        vertices,faces=trimmed_mesh(name,[tuple(v.co) for v in obj.data.vertices],
                                  [tuple(p.vertices) for p in obj.data.polygons])
        mesh=bpy.data.meshes.new(name+' / structure v1')
        mesh.from_pydata(vertices,[],faces);mesh.update()
        for material in obj.data.materials:mesh.materials.append(material)
        for polygon,(material_index,smooth) in zip(mesh.polygons,face_state):
            polygon.material_index=material_index;polygon.use_smooth=smooth
        obj.data=mesh
        obj['otw_structure_revision']='v1'
    # Replace the old single opaque panel with lower-shaft guide members.
    guides=MeshBuilder()
    for x in (-1.70,1.70):
        guides.box('guide',(x,0,(.45+STAIR_TOP)/2),(.12,.16,STAIR_TOP-.45))
    obj=bpy.data.objects[DARK];new_mesh=bpy.data.meshes.new(DARK+' / guides v1')
    new_mesh.from_pydata(guides.groups['guide']['vertices'],[],guides.groups['guide']['faces']);new_mesh.update()
    for material in obj.data.materials:new_mesh.materials.append(material)
    obj.data=new_mesh;obj['otw_structure_revision']='v1'
    collection=bpy.data.collections.new(COLLECTION);bpy.context.scene.collection.children.link(collection)
    collection['otw_feature_id']=FEATURE
    collection['otw_structure_revision']='v1'
    specs={
        'orange':((.66,.054,.012,1),.28,.31,0),
        'brown':((.145,.060,.042,1),.08,.57,0),
        'steel':((.44,.49,.51,1),.68,.28,0),
        'roof':((.38,.40,.39,1),0,.80,0),
        'glass':((.24,.37,.42,1),.18,.12,.45),
        'light':((.71,.73,.72,1),.55,.30,0),
        'clear':((.92,.97,.98,1),0,.035,1),
        'mirror':((.92,.94,.96,1),1,.035,0),
        'stainless':((.55,.58,.61,1),.86,.23,0),
        'dark':((.022,.027,.031,1),.38,.38,0),
        'floor':((.035,.037,.039,1),0,.86,0),
    }
    materials={}
    for key,(color,metal,rough,transmission) in specs.items():
        material=bpy.data.materials.new('OTW Tower structure v1 / '+key);material.use_nodes=True
        material.diffuse_color=color
        shader=material.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value=color;shader.inputs['Metallic'].default_value=metal
        shader.inputs['Roughness'].default_value=rough;shader.inputs['Transmission Weight'].default_value=transmission
        materials[key]=material
    # Match the already reviewed PR56 bands in the original local coordinates.
    # Copy the shader without mutating any original material or its users.
    materials['banded']=bpy.data.objects[ORANGE].data.materials[0].copy()
    materials['banded'].name='OTW Tower structure v1 / banded'
    assignment={'foottown-shell':'brown','foottown-glazing':'glass','foottown-metal':'light','foottown-roof':'roof',
                'lower-shaft-frame':'steel','lower-shaft-glazing':'glass','roof-access':'light',
                'upper-guide-rails':'steel','upper-platforms':'steel','lift-cars':'light','lift-glazing':'glass',
                'upper-suspension':'dark','upper-landing-doors':'stainless',
                'upper-car-shell':'stainless','upper-car-glass':'clear','upper-car-mirror':'mirror',
                'upper-car-floor':'floor','upper-car-rigging':'steel','upper-car-dark':'dark'}
    assignment.update({name:'banded' for name in
                       ('upper-shaft-frame','upper-support-links','upper-service-stairs')})
    for group in GROUPS:
        mesh=bpy.data.meshes.new(PREFIX+group)
        mesh.from_pydata(data[group]['vertices'],[],data[group]['faces']);mesh.update()
        mesh.materials.append(materials[assignment.get(group,'orange')])
        obj=bpy.data.objects.new(PREFIX+group,mesh);collection.objects.link(obj)
        obj['otw_feature_id']=FEATURE;obj['otw_part_id']='tokyo-tower-structure-v1-'+group
        obj['otw_structure_revision']='v1';obj['otw_accuracy']='photo-guided; dimensions and layout inferred'
