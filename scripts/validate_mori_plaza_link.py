"""Read-only saved plaza audit. Run with Blender --python ... -- --before ... --after ... --output ..."""
import bpy,sys,json,argparse,math
from pathlib import Path
from collections import Counter
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from mori_plaza_link_v1 import ROADS,ADDED,local,subtract_rectangle,area,geometry,surface,FOOTPRINT
p=argparse.ArgumentParser();p.add_argument('--before',required=True);p.add_argument('--after',required=True);p.add_argument('--output',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output)
if out.exists():raise ValueError('Audit output exists')
def road_data():
 result={}
 for name in sorted(ROADS):
  m=bpy.data.objects[name].data;v=np.array([v.co[:] for v in m.vertices],dtype=np.float32);polys=[tuple(p.vertices) for p in m.polygons];result[name]=(v,polys)
 return result
bpy.ops.wm.open_mainfile(filepath=a.before);before=road_data()
bpy.ops.wm.open_mainfile(filepath=a.after);after=road_data();checks={}
for name in sorted(ROADS):
 v,f=before[name];w,g=after[name];assert np.array_equal(v,w[:len(v)]),name
 after_original={tuple(p) for p in g};preserved=0;inside_before=0;inside_after=0
 for poly in f:
  ps=[local(v[i]) for i in poly]
  if max(x[2] for x in ps)>1:assert poly in after_original;continue
  outside,inside=subtract_rectangle(ps);size=area(inside);inside_before+=size
  if size<1e-9:assert poly in after_original,(name,poly);preserved+=1
 for poly in g:
  ps=[local(w[i]) for i in poly]
  if max(x[2] for x in ps)>1:continue
  _,inside=subtract_rectangle(ps);inside_after+=area(inside)
 assert inside_after<.01,(name,inside_after)
 # All source surfaces outside the edit rectangle must retain their area.
 total_before=sum(area([tuple(v[i]) for i in p]) for p in f);total_after=sum(area([tuple(w[i]) for i in p]) for p in g)
 error=abs(total_before-inside_before-total_after);assert error<.03,(name,error)
 checks[name]={'original_vertices_exact':True,'unclipped_faces_preserved':preserved,'removed_inside_area_m2':inside_before,'remaining_inside_area_m2':inside_after,'outside_area_error_m2':error}
new={}
for name in sorted(ADDED):
 o=bpy.data.objects[name];m=o.data;expected=geometry(name.split(' / ')[1]);xyz=np.array([v.co[:] for v in m.vertices],dtype=np.float32)
 assert np.array_equal(xyz,np.array(expected.vertices,dtype=np.float32));assert [tuple(p.vertices) for p in m.polygons]==expected.faces
 edges=Counter()
 for p in m.polygons:
  vs=list(p.vertices)
  for x,y in zip(vs,vs[1:]+vs[:1]):edges[(x,y)]+=1
 assert all(edges[(y,x)]==n for (x,y),n in edges.items())
 m.calc_loop_triangles();minimum=min(t.area for t in m.loop_triangles);assert minimum>1e-10
 for pos in xyz:
  u,v,z=local(pos);assert 21.999<v<32.001 and abs(u)<7.001-.2*(v-22) and z>=.014,(name,u,v,z)
 assert all(mat.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value==0 for mat in m.materials)
 new[name]={'vertices':len(m.vertices),'polygons':len(m.polygons),'triangles':len(m.loop_triangles),'min_triangle_area':minimum,'closed_oriented_edges':True,'in_footprint':True}
assert abs(surface(22)-.30)<1e-8
assert abs(surface(32)-.11)<1e-8
from mathutils import Vector
from mori_entrance_v1 import point
dg=bpy.context.evaluated_depsgraph_get();seams=[]
for u in (-3.25,.25,3.25):
 for v in (21.99,22.01,24.25,28.25,31.99,32.01):
  hit,pos,normal,index,obj,matrix=bpy.context.scene.ray_cast(dg,Vector(point(u,v,5)),Vector((0,0,-1)),distance=10)
  expected='OTW Mori entry plaza / paving' if v<22 else ('park mapped land use' if v>32 else 'OTW Mori plaza link / paving')
  assert hit and obj.name==expected,(u,v,obj.name if hit else None)
  expected_z=(.30 if v<22 else .11 if v>32 else surface(v))
  assert abs(pos.z-expected_z)<.006,(u,v,pos.z,expected_z)
  seams.append({'u':u,'v':v,'z':pos.z,'object':obj.name})
result={'ok':True,'road_checks':checks,'new_objects':new,'join_height_m':surface(22)+.003,'accepted_paving_edge_m':.303,'lawn_join_height_m':surface(32)+.003,'mapped_lawn_height_m':.11,'minimum_unplanted_width_m':7.4,'limitations':['Outside this small footprint, old pedestrian-outline road artifacts remain.','Source road sheets are clipped surfaces, not asserted watertight solids.','Inferred landscape layout, not surveyed or regulatory accessibility approval.','This connection ends at mapped green; complete Central Green paths and elevations remain unresolved.']}
result['saved_surface_rays']=seams
out.write_text(json.dumps(result,indent=2),encoding='utf8');print('Saved plaza validation passed')
