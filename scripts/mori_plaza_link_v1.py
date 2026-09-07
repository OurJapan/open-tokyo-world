"""Bounded plaza connection candidate, from accepted entry paving to mapped green.

Dimensions and planting are inferred. Clip only the approved local rectangle;
keep all original road geometry beyond it. Never replace whole-city road objects.
"""
import math,random,hashlib,json
from mori_entrance_v1 import point as world, ORIGIN
from mori_terrace_v1 import Mesh, ORIGIN as OLD_ORIGIN
FEATURE='otw:jp:tokyo:minato:azabudai-mori-jp'
ANCHOR='Mori JP podium / stone'
ROADS={'asphalt 15s road detail','gutter 15s road detail','pavement_0 unified road','paint_0 unified road'}
ADDED={'OTW Mori plaza link / '+s for s in ('paving','planters','planting')}
BOUNDS=(-7.0,7.0,22.0,32.0)
FOOTPRINT=[(-7.0,22.0),(7.0,22.0),(5.0,32.0),(-5.0,32.0)]
def local(p):
 x,y=p[0]-ORIGIN[0],p[1]-ORIGIN[1]
 return ((2*x-y)/math.sqrt(5),(x+2*y)/math.sqrt(5),p[2])
def surface(v):return .30-(v-22)*.19/10

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
 # Historical helper name retained for audit reuse; actual scope is a convex trapezoid.
 remaining=poly;outside=[]
 for a,b in zip(FOOTPRINT,FOOTPRINT[1:]+FOOTPRINT[:1]):
  dx,dy=b[0]-a[0],b[1]-a[1]
  def split(points,sign):
   result=[]
   for p,q in zip(points,points[1:]+points[:1]):
    dp=sign*(dx*(p[1]-a[1])-dy*(p[0]-a[0]));dq=sign*(dx*(q[1]-a[1])-dy*(q[0]-a[0]))
    if dp>=0:result.append(p)
    if (dp<0)!=(dq<0):
     t=dp/(dp-dq);result.append(tuple(p[k]+t*(q[k]-p[k]) for k in range(3)))
   clean=[]
   for p in result:
    if not clean or math.dist(p,clean[-1])>1e-8:clean.append(p)
   if len(clean)>1 and math.dist(clean[0],clean[-1])<1e-8:clean.pop()
   return clean
  part=split(remaining,-1)
  if len(part)>=3:outside.append(part)
  remaining=split(remaining,1)
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
 from mori_terrace_v1 import point
 m=Mesh();rng=random.Random(709)
 def solid(poly,top,bottom,mat):
  if area([(u,v,0) for u,v in poly])<1e-8:return
  n=len(poly);coords=[point(u,v,bottom(u,v)) for u,v in poly]+[point(u,v,top(u,v)) for u,v in poly]
  m.poly(coords,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],mat)
 if part=='paving':
  solid(FOOTPRINT,lambda u,v:surface(v),lambda u,v:.015,0)
  for i in range(-7,7):
   for j in range(10):
    v=22+j
    tile=[(i+.004,v+.004,0),(i+.996,v+.004,0),(i+.996,v+.996,0),(i+.004,v+.996,0)]
    _,inside=subtract_rectangle(tile)
    solid([(u,v) for u,v,z in inside],lambda u,v:surface(v)+.003,lambda u,v:surface(v)-.006,1+rng.randrange(3))
 elif part=='planters':
  for sign in (-1,1):
   poly=[(sign*6.85,22.5),(sign*5.25,22.5),(sign*3.75,31.5),(sign*4.95,31.5)]
   if sign>0:poly.reverse()
   solid(poly,lambda u,v:surface(v)+.14,lambda u,v:surface(v)-.02,0)
   # Slim stone edging follows the taper; no extra trees in the passage.
   for a,b in zip(poly,poly[1:]+poly[:1]):
    dx,dy=b[0]-a[0],b[1]-a[1];length=(dx*dx+dy*dy)**.5;nx,ny=-dy/length*.07,dx/length*.07
    strip=[a,b,(b[0]+nx,b[1]+ny),(a[0]+nx,a[1]+ny)]
    solid(strip,lambda u,v:surface(v)+.17,lambda u,v:surface(v)-.02,1)
 elif part=='planting':
  for sign in (-1,1):
   for j in range(21):
    v=23+j*.4;u=sign*(6.05-(v-22.5)*.17)
    for d in (-.22,.22):m.crown(u+d,v,surface(v)+.33,.27,.28,.24,rng.randrange(4))
 else:raise ValueError('Unknown link part')
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
   if max(x[2] for x in poly)>1 or max(x[0] for x in poly)<=-7 or min(x[0] for x in poly)>=7 or max(x[1] for x in poly)<=22 or min(x[1] for x in poly)>=32:
    faces.append(ids);mats.append(p.material_index);smooth.append(p.use_smooth);continue
   if len(ids)>8:raise ValueError('Unexpected source polygon')
   parts,inside=subtract_rectangle(poly)
   if area(inside)<1e-9:
    faces.append(ids);mats.append(p.material_index);smooth.append(p.use_smooth);continue
   cut+=1;removed+=area(inside)
   for part in parts:
    if area(part)<1e-9:continue
    start=len(coords);coords.extend(world(*v) for v in part);faces.append(list(range(start,start+len(part))));mats.append(p.material_index);smooth.append(p.use_smooth)
  mesh=bpy.data.meshes.new('OTW clipped plaza link surface / '+name);mesh.from_pydata(coords,[],faces);mesh.update()
  for mat in old.materials:mesh.materials.append(mat)
  for p,mat,s in zip(mesh.polygons,mats,smooth):p.material_index=mat;p.use_smooth=s
  o.data=mesh;audit[name]={'cut_faces':cut,'removed_surface_area_m2':removed,'original_vertex_count':len(old.vertices),'original_vertices_retained':True}
 for name in sorted(ADDED):
  part=name.split(' / ')[1];g=geometry(part);mesh=bpy.data.meshes.new(name);mesh.from_pydata(g.vertices,[],g.faces);mesh.update()
  colors={'paving':[(.22,.23,.22),(.32,.33,.31),(.35,.35,.33),(.29,.30,.29)],'planters':[(.075,.055,.027),(.29,.30,.28)],'planting':[(.035,.095,.015),(.075,.16,.026),(.11,.20,.035),(.055,.125,.022),(.13,.085,.045)]}[part]
  for i,col in enumerate(colors):
   mat=bpy.data.materials.new(f'OTW plaza link v1 / {part} / {i}');mat.use_nodes=True;mat.diffuse_color=(*col,1);p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*col,1);p.inputs['Roughness'].default_value=.85;p.inputs['Emission Strength'].default_value=0;mesh.materials.append(mat)
  for p,mat,s in zip(mesh.polygons,g.materials,g.smooth):p.material_index=mat;p.use_smooth=s
  o=bpy.data.objects.new(name,mesh);bpy.data.collections['Mori JP podium'].objects.link(o);o['otw_feature_id']=FEATURE;o['otw_part']='ground plaza link '+part+'; inferred limited footprint and planting'
 bpy.context.scene['otw_plaza_link_cut_audit']=json.dumps(audit)
 return audit
