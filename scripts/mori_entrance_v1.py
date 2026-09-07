"""Photograph-based plaza-side entrance detail hypothesis; dimensions are estimates.

Preserves the recovered podium and upper tower. Uses three existing hidden
object slots so the review contract can constrain every changed object.
"""
import math

TARGETS = {'Mori JP podium / '+s for s in ('aluminum','ceiling','clear glass')}
ORIGIN = (-419.80, 290.82)
TANGENT = (0.8944, -0.4472)
LENGTH = 32.0
BAYS = 12
DEPTH = 7.0
HEIGHT = 10.8
GROUND = 0.38


def point(u, v, z):
    size=math.hypot(*TANGENT);tx,ty=(n/size for n in TANGENT)
    # Positive v faces northeast, away from the recovered source wall.
    return (ORIGIN[0]+tx*u-ty*v, ORIGIN[1]+ty*u+tx*v, z)


def roof(u,v):
    return HEIGHT + 0.25*(u/(LENGTH/2))**2 + 0.05*v


def geometry(part):
    """Return independent closed solids, materials and smooth-face flags."""
    vertices=[];faces=[];materials=[];smooth=[]
    def poly(points,polys,mat=0,shade=False):
        start=len(vertices);vertices.extend(points)
        for face in polys:
            faces.append(tuple(start+i for i in face));materials.append(mat);smooth.append(shade and len(face)==4)
    def prism(top,thickness,mat=0):
        n=len(top);bottom=[(x,y,z-thickness) for x,y,z in top]
        poly(bottom+top,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],mat)
    def beam(a,b,r,mat=0,sides=12):
        direction=[b[i]-a[i] for i in range(3)];length=math.sqrt(sum(x*x for x in direction))
        if length<1e-5:raise ValueError('Zero length member')
        w=[x/length for x in direction];ref=(0,0,1) if abs(w[2])<.9 else (1,0,0)
        cross=lambda x,y:(x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],x[0]*y[1]-x[1]*y[0])
        axis=cross(w,ref);n=math.sqrt(sum(x*x for x in axis));axis=[x/n for x in axis];other=cross(w,axis)
        pts=[tuple(p[j]+r*(axis[j]*math.cos(2*math.pi*i/sides)+other[j]*math.sin(2*math.pi*i/sides)) for j in range(3)) for p in (a,b) for i in range(sides)]
        poly(pts,[tuple(reversed(range(sides))),tuple(range(sides,2*sides))]+[(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)],mat,True)
    # 12 bays, two strips: diagonal lattice similar to the official photograph.
    rows=[1.6,4.3,DEPTH]
    us=[-LENGTH/2+i*LENGTH/BAYS for i in range(BAYS+1)]
    if part=='aluminum':
        edges=set()
        for i in range(BAYS):
            for j in range(2):
                a=(i,j);b=(i+1,j);c=(i+1,j+1);d=(i,j+1)
                for x,y in [(a,b),(b,c),(c,d),(d,a),(a,c) if (i+j)%2==0 else (b,d)]:edges.add(tuple(sorted((x,y))))
        for a,b in sorted(edges):
            u,v=us[a[0]],rows[a[1]];s,t=us[b[0]],rows[b[1]]
            beam(point(u,v,roof(u,v)),point(s,t,roof(s,t)),.085)
        for v in (1.6,DEPTH):
            for i in range(BAYS):beam(point(us[i],v,roof(us[i],v)),point(us[i+1],v,roof(us[i+1],v)),.16)
        # Tall entrance glazing divisions and several paired door frames.
        for u in range(-15,16,3):beam(point(u,.18,GROUND),point(u,.18,HEIGHT-.35),.045,1,8)
        for z in (GROUND+3.0,HEIGHT-.35):beam(point(-15,.18,z),point(15,.18,z),.065,1,8)
        for u in (-12,-6,0,6,12):
            for offset in (-1.2,0,1.2):beam(point(u+offset,.23,GROUND),point(u+offset,.23,GROUND+3),.045,0,8)
            for offset in (-.16,.16):beam(point(u+offset,.34,1.25),point(u+offset,.34,1.85),.03,0,8)
    elif part=='ceiling':
        # Seven silver circular columns, recessed soffit and narrow paving apron.
        for u in range(-15,16,5):
            beam(point(u,1.05,GROUND),point(u,1.05,roof(u,1.05)-.1),.72,0,32)
            for z in (3.9,7.2):beam(point(u,1.05,z),point(u,1.05,z+.026),.726,2,32)
        for i in range(BAYS):
            a,b=us[i],us[i+1]
            prism([point(a,-.6,roof(a,0)),point(b,-.6,roof(b,0)),point(b,1.6,roof(b,1.6)),point(a,1.6,roof(a,1.6))],.2,1)
            prism([point(a,-.5,GROUND),point(b,-.5,GROUND),point(b,DEPTH+.5,GROUND),point(a,DEPTH+.5,GROUND)],.10,3)
    elif part=='clear glass':
        for i in range(BAYS):
            for j in range(2):
                points=[(us[i],rows[j]),(us[i+1],rows[j]),(us[i+1],rows[j+1]),(us[i],rows[j+1])]
                for indices in ((0,1,2),(0,2,3)) if (i+j)%2==0 else ((0,1,3),(1,2,3)):
                    prism([point(*points[k],roof(*points[k])+.075) for k in indices],.025)
    else:raise ValueError('Unknown entrance part')
    return vertices,faces,materials,smooth


def apply(obj):
    import bpy
    if obj.name not in TARGETS or obj.type!='MESH' or obj.data.users!=1 or obj.data.shape_keys:
        raise ValueError('Expected exact single-user entrance target')
    if any(abs(obj.matrix_world[r][c]-(1 if r==c else 0))>1e-6 for r in range(4) for c in range(4)):
        raise ValueError('Expected identity transform')
    part=obj.name.split(' / ')[1]
    vertices,faces,indices,smooth=geometry(part)
    mesh=bpy.data.meshes.new('OTW plaza-side entrance v1 / '+part)
    mesh.from_pydata(vertices,[],faces);mesh.update()
    presets=([(0.62,0.65,0.65, .75,.26,0),(0.07,0.09,0.10,.5,.28,0)] if part=='aluminum' else
             [(0.6,0.62,0.61,.72,.3,0),(0.65,0.65,0.60,.15,.5,0),(0.16,0.18,0.18,.65,.3,0),(0.34,0.35,0.33,0,.78,0)] if part=='ceiling' else
             [(0.30,0.39,0.42,.1,.12,.8)])
    for i,(r,g,b,metal,rough,transmission) in enumerate(presets):
        mat=bpy.data.materials.new(f'OTW entrance v1 / {part} / {i}');mat.use_nodes=True
        mat.diffuse_color=(r,g,b,1);bsdf=mat.node_tree.nodes.get('Principled BSDF')
        for key,value in {'Base Color':(r,g,b,1),'Metallic':metal,'Roughness':rough,'Transmission Weight':transmission,'Emission Strength':0}.items():bsdf.inputs[key].default_value=value
        mesh.materials.append(mat)
    for p,i,s in zip(mesh.polygons,indices,smooth):p.material_index=i;p.use_smooth=s
    obj.data=mesh
    for mod in list(obj.modifiers):obj.modifiers.remove(mod)
    obj.hide_render=False;obj.hide_viewport=False
    obj['otw_part']='plaza-side entrance photo hypothesis; dimensions and registration estimated'
