"""Bounded entry plaza candidate; remove mistaken pedestrian-outline road layers.

Dimensions and planting are inferred. Clip only the approved local rectangle;
keep all original road geometry beyond it. Never replace whole-city road objects.
"""
import math,random,hashlib,json
from mori_entrance_v1 import point as world, ORIGIN
from mori_terrace_v1 import Mesh, ORIGIN as OLD_ORIGIN
FEATURE='otw:jp:tokyo:minato:azabudai-mori-jp'
ANCHOR='Mori JP podium / stone'
ROADS={'asphalt 15s road detail','gutter 15s road detail','pavement_0 unified road','paint_0 unified road'}
ADDED={'OTW Mori entry plaza / '+s for s in ('paving','planters','planting')}
BOUNDS=(-10.0,10.0,7.5,22.0)
def local(p):
 x,y=p[0]-ORIGIN[0],p[1]-ORIGIN[1]
 return ((2*x-y)/math.sqrt(5),(x+2*y)/math.sqrt(5),p[2])
def surface(v):return .38-(v-7.5)*.08/14.5

def half(poly,axis,value,sign):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  da=sign*(a[axis]-value);db=sign*(b[axis]-value)
  if da>=0:out.append(a)
  if (da<0)!=(db<0):
   t=da/(da-db);out.append(tuple(a[k]+t*(b[k]-a[k]) for k in range(3)))
 # Remove adjacent duplicate points created by exact boundary intersections.
 clean=[]
 for p in out:
  if not clean or math.dist(p,clean[-1])>1e-8:clean.append(p)
 if len(clean)>1 and math.dist(clean[0],clean[-1])<1e-8:clean.pop()
 return clean

def subtract_rectangle(poly):
 remaining=poly;outside=[]
 for axis,value,sign in [(0,-10,1),(0,10,-1),(1,7.5,1),(1,22,-1)]:
  part=half(remaining,axis,value,-sign)
  if len(part)>=3:outside.append(part)
  remaining=half(remaining,axis,value,sign)
  if len(remaining)<3:return outside,[]
 return outside,remaining

def area(poly):
 if len(poly)<3:return 0
 a=poly[0];total=0
 for b,c in zip(poly[1:-1],poly[2:]):
  x=[b[i]-a[i] for i in range(3)];y=[c[i]-a[i] for i in range(3)]
  total+=math.sqrt(sum(v*v for v in (x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],x[0]*y[1]-x[1]*y[0])))/2
 return total

def geometry(part):
 m=Mesh();rng=random.Random(707)
 if part=='paving':
  # 1m courses, narrow joints; sealed foundation below prevents holes.
  top=[(-10,7.5,.38),(10,7.5,.38),(10,22,.30),(-10,22,.30)]
  pts=top+[(u,v,.015) for u,v,z in top]
  # Mesh.poly expects world positions in its original terrace coordinate system.
  from mori_terrace_v1 import point
  m.poly([point(*p) for p in pts],[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],0)
  for i in range(20):
   for j in range(15):
    u=-10+i;v=7.5+j;end=min(v+1,22)
    if end-v<.01:continue
    # Overlay only shader-like thin relief; bottom intersects solid substrate.
    z0=surface(v);z1=surface(end)
    ps=[(u+.004,v+.004,z0+.003),(u+.996,v+.004,z0+.003),(u+.996,end-.004,z1+.003),(u+.004,end-.004,z1+.003)]
    qs=[(x,y,z-.006) for x,y,z in ps]
    m.poly([point(*p) for p in qs+ps],[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],1+rng.randrange(3))
 elif part=='planters':
  for u in (-9.5,7.1):
   for j in range(10):
    v=11+j;z=surface(v+1)
    m.box(u,v,z,2.4,1,.46,0)
    for x,y,w,d in [(u,v,.10,1),(u+2.3,v,.10,1)]:m.box(x,y,z,w,d,.52,1)
   for v in (11,20.9):m.box(u,v,surface(v),2.4,.10,.52,1)
 elif part=='planting':
  for u in (-8.3,8.3):
   for j in range(24):
    v=11.4+j*.38
    for x in (-.65,0,.65):m.crown(u+x,v,surface(v)+.72,.36,.32,.38,rng.randrange(4))
   for v,h in [(14,3.0),(18.5,3.6)]:
    z=surface(v)+.46;m.beam((u,v,z),(u+.06,v,z+h*.75),.065,4,10)
    for i in range(8):
     a=i*2.399;x=u+math.cos(a)*.55;y=v+math.sin(a)*.55;cz=z+h*(.55+.25*rng.random())
     m.beam((u,v,z+h*.4),(x,y,cz),.022,4,6);m.crown(x,y,cz,.6,.6,.78,i%4)
 else:raise ValueError('Unknown plaza part')
 # Convert reusable primitive coordinates into the entry coordinate system.
 m.vertices=[world((2*(x-OLD_ORIGIN[0])-(y-OLD_ORIGIN[1]))/math.sqrt(5),((x-OLD_ORIGIN[0])+2*(y-OLD_ORIGIN[1]))/math.sqrt(5),z) for x,y,z in m.vertices]
 return m

def apply(op,mesh_fingerprint):
 import bpy
 from mathutils import Vector
 for name in ADDED:
  if bpy.data.objects.get(name):raise ValueError('Plaza object already exists')
 for name in ROADS:
  o=bpy.data.objects.get(name)
  if o is None or o.type!='MESH' or mesh_fingerprint(o.data)!=op['road_mesh_sha256'][name]:raise ValueError('Road baseline hash differs: '+name)
  if o.data.users!=1 or o.data.uv_layers or o.modifiers or o.parent or o.constraints or o.animation_data:raise ValueError('Unsupported road mesh state: '+name)
  if any(abs(o.matrix_world[r][c]-(r==c))>1e-6 for r in range(4) for c in range(4)):raise ValueError('Non-identity road')
 audit={}
 for name in sorted(ROADS):
  o=bpy.data.objects[name];old=o.data;coords=[tuple(v.co) for v in old.vertices];uv=[local(p) for p in coords];faces=[];mats=[];smooth=[];cut=0;removed=0
  for p in old.polygons:
   ids=list(p.vertices);poly=[uv[i] for i in ids]
   if max(x[2] for x in poly)>1 or max(x[0] for x in poly)<=-10 or min(x[0] for x in poly)>=10 or max(x[1] for x in poly)<=7.5 or min(x[1] for x in poly)>=22:
    faces.append(ids);mats.append(p.material_index);smooth.append(p.use_smooth);continue
   if len(ids)>4:raise ValueError('Non-convex source polygon unsupported')
   parts,inside=subtract_rectangle(poly)
   if area(inside)<1e-9:
    faces.append(ids);mats.append(p.material_index);smooth.append(p.use_smooth);continue
   cut+=1;removed+=area(inside)
   for part in parts:
    if area(part)<1e-9:continue
    start=len(coords);coords.extend(world(*v) for v in part);faces.append(list(range(start,start+len(part))));mats.append(p.material_index);smooth.append(p.use_smooth)
  mesh=bpy.data.meshes.new('OTW clipped entry surface / '+name);mesh.from_pydata(coords,[],faces);mesh.update()
  for mat in old.materials:mesh.materials.append(mat)
  for p,mat,s in zip(mesh.polygons,mats,smooth):p.material_index=mat;p.use_smooth=s
  o.data=mesh;audit[name]={'cut_faces':cut,'removed_surface_area_m2':removed,'original_vertex_count':len(old.vertices),'original_vertices_retained':True}
 for name in sorted(ADDED):
  part=name.split(' / ')[1];g=geometry(part);mesh=bpy.data.meshes.new(name);mesh.from_pydata(g.vertices,[],g.faces);mesh.update()
  colors={'paving':[(.22,.23,.22),(.32,.33,.31),(.35,.35,.33),(.29,.30,.29)],'planters':[(.075,.055,.027),(.29,.30,.28)],'planting':[(.035,.095,.015),(.075,.16,.026),(.11,.20,.035),(.055,.125,.022),(.13,.085,.045)]}[part]
  for i,col in enumerate(colors):
   mat=bpy.data.materials.new(f'OTW plaza v1 / {part} / {i}');mat.use_nodes=True;mat.diffuse_color=(*col,1);p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*col,1);p.inputs['Roughness'].default_value=.85;p.inputs['Emission Strength'].default_value=0;mesh.materials.append(mat)
  for p,mat,s in zip(mesh.polygons,g.materials,g.smooth):p.material_index=mat;p.use_smooth=s
  o=bpy.data.objects.new(name,mesh);bpy.data.collections['Mori JP podium'].objects.link(o);o['otw_feature_id']=FEATURE;o['otw_part']='ground entry plaza '+part+'; inferred limited footprint and planting'
 bpy.context.scene['otw_plaza_cut_audit']=json.dumps(audit)
 return audit
