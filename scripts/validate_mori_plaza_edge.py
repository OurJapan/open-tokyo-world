"""Read-only saved plaza audit. Run with Blender --python ... -- --before ... --after ... --output ..."""
import bpy,sys,json,argparse,math
from pathlib import Path
from collections import Counter
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from mori_plaza_edge_v1 import ROADS,local,subtract_scope,area
p=argparse.ArgumentParser();p.add_argument('--before',required=True);p.add_argument('--after',required=True);p.add_argument('--output',required=True);p.add_argument('--source-research',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
if out.exists():raise ValueError('Audit output exists')
def road_data():
 result={}
 for name in sorted(ROADS):
  m=bpy.data.objects[name].data;v=np.array([v.co[:] for v in m.vertices],dtype=np.float32);polys=[tuple(p.vertices) for p in m.polygons];result[name]=(v,polys)
 return result
cut_centres=[]
bpy.ops.wm.open_mainfile(filepath=a.before);before=road_data()
bpy.ops.wm.open_mainfile(filepath=a.after);after=road_data();checks={}
for name in sorted(ROADS):
 v,f=before[name];w,g=after[name];assert np.array_equal(v,w[:len(v)]),name
 after_original={tuple(p) for p in g};preserved=0;inside_before=0;inside_after=0
 for poly in f:
  ps=[local(v[i]) for i in poly]
  if max(x[2] for x in ps)>1:assert poly in after_original;continue
  outside,inside=subtract_scope(ps);size=sum(map(area,inside));inside_before+=size
  for part in inside:
   if area(part)>1e-9:cut_centres.append(tuple(sum(p[k] for p in part)/len(part) for k in (0,1)))
  if size<1e-9:assert poly in after_original,(name,poly);preserved+=1
 for poly in g:
  ps=[local(w[i]) for i in poly]
  if max(x[2] for x in ps)>1:continue
  _,inside=subtract_scope(ps);inside_after+=sum(map(area,inside))
 assert inside_after<.01,(name,inside_after)
 # All source surfaces outside the edit rectangle must retain their area.
 total_before=sum(area([tuple(v[i]) for i in p]) for p in f);total_after=sum(area([tuple(w[i]) for i in p]) for p in g)
 error=abs(total_before-inside_before-total_after);assert error<.03,(name,error)
 checks[name]={'original_vertices_exact':True,'unclipped_faces_preserved':preserved,'removed_inside_area_m2':inside_before,'remaining_inside_area_m2':inside_after,'outside_area_error_m2':error}
# Attribute removed fragments to the saved pedestrian-area source.
source=json.loads(Path(a.source_research).read_text(encoding='utf8'))
assert source['source_sha256']=='f04e8e70ab24a61ca749375d1ef37401feb0fdc840cc506b670ef71454a6a8ab'
ways=source['ways'];target=next(w for w in ways if w['id']=='1443867470')
assert target['tags']['area']=='yes' and target['tags']['highway']=='pedestrian'
others=[w for w in ways if w['id']!=target['id'] and w['tags'].get('tunnel')!='yes' and w['tags'].get('indoor')!='yes' and float(w['tags'].get('layer','0'))>=0]
def distance(p,a,b):
 dx,dy=b[0]-a[0],b[1]-a[1];den=dx*dx+dy*dy;t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den)) if den else 0
 return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
def way_distance(p,w):return min(distance(p,x,y) for x,y in zip(w['pts'],w['pts'][1:]))
assert cut_centres
target_distances=[way_distance(p,target) for p in cut_centres]
other_distances=[min(way_distance(p,w) for w in others) for p in cut_centres]
assert max(target_distances)<7.85, max(target_distances)
assert min(other_distances)>10, min(other_distances)
from mathutils import Vector
from mori_entrance_v1 import point
dg=bpy.context.evaluated_depsgraph_get();rays=[]
for u,v in [(-8,30),(-10,32),(-12,34),(8,28),(10,28),(14,30)]:
 hit,pos,normal,index,obj,matrix=bpy.context.scene.ray_cast(dg,Vector(point(u,v,5)),Vector((0,0,-1)),distance=10)
 assert hit and obj.name not in ROADS and -.01<=pos.z<1,(u,v,obj.name if hit else None,pos.z)
 rays.append({'u':u,'v':v,'z':pos.z,'object':obj.name})
result={'ok':True,'road_checks':checks,'new_objects':[],
 'source_attribution':{'source_sha256':source['source_sha256'],'way_id':target['id'],'tags':target['tags'],'removed_fragment_centres':len(cut_centres),'max_distance_to_area_outline_m':max(target_distances),'min_distance_to_other_surface_highway_m':min(other_distances),'live_osm_verified':False,'note':'Local saved source and fragment centres support attribution; not a direct original face ID mapping.'},
 'saved_ground_rays':rays,'limitations':['Ground below removed sheets is inherited, not surveyed landscape.','Source road sheets are not asserted watertight solids.','Only two side polygons are repaired; out-of-scope road artifacts remain.','Exact real-world paving, steps and terrain remain unresolved.']}
out.write_text(json.dumps(result,indent=2),encoding='utf8');print('Saved edge validation passed')
