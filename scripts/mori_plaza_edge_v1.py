"""Remove misgenerated road sheets on either side of accepted plaza connection.

Repair bounds are inferred. Clip only the two declared side polygons;
keep all original road geometry beyond it. Never replace whole-city road objects.
"""
import math,random,hashlib,json
from mori_entrance_v1 import point as world, ORIGIN
from mori_terrace_v1 import Mesh, ORIGIN as OLD_ORIGIN
FEATURE='otw:jp:tokyo:minato:azabudai-mori-jp'
ANCHOR='Mori JP podium / stone'
ROADS={'asphalt 15s road detail','gutter 15s road detail','pavement_0 unified road','paint_0 unified road'}
ADDED=set()
BOUNDS=(-16.0,18.0,22.0,38.0)
FOOTPRINTS=[[(-16,22),(-7,22),(-5,32),(-5,38),(-16,38)],[(7,22),(18,22),(18,38),(5,38),(5,32)]]
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

def subtract_one(poly,footprint):
 # Historical helper name retained for audit reuse; actual scope is a convex trapezoid.
 remaining=poly;outside=[]
 for a,b in zip(footprint,footprint[1:]+footprint[:1]):
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


def subtract_scope(poly):
 remaining=[poly];removed=[]
 for footprint in FOOTPRINTS:
  next_parts=[]
  for p in remaining:
   outside,inside=subtract_one(p,footprint);next_parts.extend(outside)
   if area(inside)>1e-9:removed.append(inside)
  remaining=next_parts
 return remaining,removed


def area(poly):
 if len(poly)<3:return 0
 a=poly[0];total=0
 for b,c in zip(poly[1:-1],poly[2:]):
  x=[b[i]-a[i] for i in range(3)];y=[c[i]-a[i] for i in range(3)]
  total+=math.sqrt(sum(v*v for v in (x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],x[0]*y[1]-x[1]*y[0])))/2
 return total


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
   if max(x[2] for x in poly)>1 or max(x[0] for x in poly)<=-16 or min(x[0] for x in poly)>=18 or max(x[1] for x in poly)<=22 or min(x[1] for x in poly)>=38:
    faces.append(ids);mats.append(p.material_index);smooth.append(p.use_smooth);continue
   if len(ids)>8:raise ValueError('Unexpected source polygon')
   parts,inside=subtract_scope(poly)
   if sum(map(area,inside))<1e-9:
    faces.append(ids);mats.append(p.material_index);smooth.append(p.use_smooth);continue
   cut+=1;removed+=sum(map(area,inside))
   for part in parts:
    if area(part)<1e-9:continue
    start=len(coords);coords.extend(world(*v) for v in part);faces.append(list(range(start,start+len(part))));mats.append(p.material_index);smooth.append(p.use_smooth)
  mesh=bpy.data.meshes.new('OTW clipped plaza edge surface / '+name);mesh.from_pydata(coords,[],faces);mesh.update()
  for mat in old.materials:mesh.materials.append(mat)
  for p,mat,s in zip(mesh.polygons,mats,smooth):p.material_index=mat;p.use_smooth=s
  o.data=mesh;audit[name]={'cut_faces':cut,'removed_surface_area_m2':removed,'original_vertex_count':len(old.vertices),'original_vertices_retained':True}
 bpy.context.scene['otw_plaza_edge_cut_audit']=json.dumps(audit)
 return audit
