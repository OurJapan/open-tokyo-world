"""One northeast roof garden hypothesis, registered to source roof at z=20.08m.

Plant locations, species, railing height and spacing are inferred, not surveyed.
The source solid parapet stays intact; railing is inset on the terrace side.
"""
import math
import random
TARGETS={'Mori JP podium / '+s for s in ('soil','wood','leaf','gasket')}
ORIGIN=(-402.80,282.29)
DECK=20.08
TREE_POSITIONS=((3.5,12.6,3.8),(7.0,12.8,3.3),(11.4,12.7,4.1),(2.7,6.5,3.4))

def point(u,v,z):
    return (ORIGIN[0]+(2*u+v)/math.sqrt(5),ORIGIN[1]+(-u+2*v)/math.sqrt(5),z)

class Mesh:
    def __init__(self):self.vertices=[];self.faces=[];self.materials=[];self.smooth=[]
    def poly(self,points,faces,mat=0,smooth=False):
        start=len(self.vertices);self.vertices.extend(points)
        for f in faces:self.faces.append(tuple(start+i for i in f));self.materials.append(mat);self.smooth.append(smooth)
    def box(self,u,v,z,w,d,h,mat=0):
        pts=[point(u+x*w,v+y*d,z+k*h) for k in (0,1) for x,y in ((0,0),(1,0),(1,1),(0,1))]
        self.poly(pts,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
    def beam(self,a,b,r,mat=0,sides=8):
        a=point(*a);b=point(*b);w=[b[i]-a[i] for i in range(3)];n=math.sqrt(sum(x*x for x in w))
        if n<1e-6:raise ValueError('Degenerate beam')
        w=[x/n for x in w];ref=(0,0,1) if abs(w[2])<.9 else (1,0,0)
        cross=lambda a,b:(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
        x=cross(w,ref);n=math.sqrt(sum(t*t for t in x));x=[t/n for t in x];y=cross(w,x)
        pts=[tuple(p[j]+r*(x[j]*math.cos(i*2*math.pi/sides)+y[j]*math.sin(i*2*math.pi/sides)) for j in range(3)) for p in (a,b) for i in range(sides)]
        self.poly(pts,[tuple(reversed(range(sides))),tuple(range(sides,2*sides))]+[(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)],mat,True)
    def crown(self,u,v,z,rx,ry,rz,mat):
        # Deterministic closed leaf diamonds within each crown volume.
        # No downloaded textures, alpha planes or heavyweight tree assets.
        rng=random.Random(round(u*10000)+round(v*1000)+round(z*100))
        count=160 if max(rx,ry,rz)>.5 else 45
        for _ in range(count):
            az=rng.random()*2*math.pi;t=rng.uniform(-1,1);rad=rng.random()**(1/3)
            horizontal=math.sqrt(1-t*t)
            center=point(u+rx*rad*horizontal*math.cos(az),v+ry*rad*horizontal*math.sin(az),z+rz*rad*t)
            angle=rng.random()*2*math.pi;tilt=rng.uniform(-.75,.75)
            a=(math.cos(angle)*math.cos(tilt),math.sin(angle)*math.cos(tilt),math.sin(tilt));b=(-math.sin(angle),math.cos(angle),0)
            n=(-math.sin(tilt)*math.cos(angle),-math.sin(tilt)*math.sin(angle),math.cos(tilt))
            length=rng.uniform(.065,.14);width=length*.42;thickness=.006
            offsets=[tuple(a[k]*length for k in range(3)),tuple(b[k]*width for k in range(3)),tuple(-a[k]*length for k in range(3)),tuple(-b[k]*width for k in range(3)),tuple(n[k]*thickness for k in range(3)),tuple(-n[k]*thickness for k in range(3))]
            self.poly([tuple(center[k]+o[k] for k in range(3)) for o in offsets],[(0,1,4),(1,2,4),(2,3,4),(3,0,4),(1,0,5),(2,1,5),(3,2,5),(0,3,5)],rng.randrange(4),False)

def geometry(part):
    m=Mesh();rng=random.Random(507)
    beds=[(1.5,11.5,12.5,2.65),(1.5,3,2.1,8.5)]
    if part=='soil':
        for u,v,w,d in beds:
            # Solid soil with low bronze-colored planter rim; no floating bottom.
            m.box(u,v,DECK+.015,w,d,.48,0)
            for a,b,c,e in [(u,v,w,.10),(u,v+d-.10,w,.10),(u,v,.10,d),(u+w-.10,v,.10,d)]:m.box(a,b,DECK+.01,c,e,.54,1)
    elif part=='gasket':
        # Inset L-shaped railing avoids editing the coarse source parapet.
        for a,b in [((1.05,2.5),(1.05,14.6)),((1.05,14.6),(14.8,14.6))]:
            length=math.dist(a,b);count=math.ceil(length/.16)
            for i in range(count+1):
                u=a[0]+(b[0]-a[0])*i/count;v=a[1]+(b[1]-a[1])*i/count
                m.beam((u,v,DECK+.07),(u,v,DECK+1.2),.014,0,6)
            for z in (DECK+.12,DECK+1.2):m.beam((*a,z),(*b,z),.035,0,10)
            for i in range(math.ceil(length/1.8)+1):
                t=i/math.ceil(length/1.8);u=a[0]+(b[0]-a[0])*t;v=a[1]+(b[1]-a[1])*t
                m.beam((u,v,DECK+.02),(u,v,DECK+1.2),.045,0,8)
    elif part in ('wood','leaf'):
        for u,v,h in TREE_POSITIONS:
            z=DECK+.48
            if part=='wood':m.beam((u,v,z),(u+.12,v,z+h*.75),.085,0,10)
            for i in range(9):
                ang=i*2.399;distance=.5+rng.random()*.55
                x=u+math.cos(ang)*distance;y=v+math.sin(ang)*distance;cz=z+h*(.53+.3*rng.random())
                if part=='wood':m.beam((u,v,z+h*.4),(x,y,cz),.027,0,6)
                else:m.crown(x,y,cz,.55+rng.random()*.4,.55+rng.random()*.4,.7+rng.random()*.35,i%4)
        if part=='leaf':
            for u,v,w,d in beds:
                for i in range(int(w*3)):
                    for j in range(int(d*2)):
                        x=u+.25+(w-.5)*(i+.5)/int(w*3);y=v+.25+(d-.5)*(j+.5)/int(d*2)
                        m.crown(x,y,DECK+.6+rng.random()*.15,.30+rng.random()*.12,.30+rng.random()*.12,.30+rng.random()*.14,rng.randrange(4))
    else:raise ValueError('Unknown terrace part')
    return m

def apply(obj):
    import bpy
    if obj.name not in TARGETS or obj.type!='MESH' or obj.data.users!=1 or obj.data.shape_keys:raise ValueError('Wrong terrace target')
    if not obj.hide_render:raise ValueError('Expected unused hidden baseline slot')
    if any(abs(obj.matrix_world[r][c]-(r==c))>1e-6 for r in range(4) for c in range(4)):raise ValueError('Non-identity terrace transform')
    part=obj.name.split(' / ')[1];g=geometry(part)
    mesh=bpy.data.meshes.new('OTW northeast terrace v1 / '+part);mesh.from_pydata(g.vertices,[],g.faces);mesh.update()
    colors={'soil':[(.075,.049,.027),(.19,.15,.095)],'wood':[(.13,.085,.045)],'gasket':[(.20,.16,.10)],'leaf':[(.035,.095,.015),(.075,.16,.026),(.11,.20,.035),(.055,.125,.022)]}[part]
    for i,color in enumerate(colors):
        mat=bpy.data.materials.new(f'OTW terrace v1 / {part} / {i}');mat.use_nodes=True;mat.diffuse_color=(*color,1)
        p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=.4 if part=='gasket' else .8;p.inputs['Metallic'].default_value=.65 if part=='gasket' else 0;p.inputs['Emission Strength'].default_value=0
        mesh.materials.append(mat)
    for face,mat,smooth in zip(mesh.polygons,g.materials,g.smooth):face.material_index=mat;face.use_smooth=smooth
    obj.data=mesh
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
    obj.hide_render=False;obj.hide_viewport=False;obj['otw_part']='northeast roof terrace / '+part+'; photo hypothesis; inferred dimensions and planting species'
