# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Pinned west/south road joins, route-aligned joints and inherited surface details."""
import argparse,json,math,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import tower_footway_geometry_v5 as xy
from tower_site_geometry_v8 import grade
from road_finish_v1 import digest,write,snapshot
SOURCE_SHA='959610fc3c3b1f6eca725de5666a2c5fd218f7ea33cc90b8bf5f7300e65bb877'
PLAN=ROOT/'areas/tokyo-tower/road-geometry-v2-plan.json'
CONFIG=ROOT/'areas/tokyo-tower/road-geometry-v2-input.json'
CAMERAS=ROOT/'areas/tokyo-tower/road-geometry-v2-cameras.json'
SURFACES=set(xy.TARGETS)|{'parking mapped land use'}
DETAILS={'Close detail iron','Close detail rim','Skywalk visible detail white'}
TARGETS=SURFACES|DETAILS

def rows(m):return [[list(p.vertices),p.material_index,p.use_smooth,p.hide,p.select] for p in m.polygons]

def state():
 r=snapshot()
 for n in TARGETS:r['metadata']['objects'][n].pop('mesh_flags_sha256',None)
 return r

def ungraded(poly):return [(x,y,z-grade(x,y)) for x,y,z in poly]

def partition(poly,plan):
 # The current source has already received v8's nonlinear grade. Clipping
 # therefore preserves actual saved 3D heights, rather than warping twice.
 if not any(min(p[0] for p in poly)<c and max(p[0] for p in poly)>a and min(p[1] for p in poly)<d and max(p[1] for p in poly)>b for a,b,c,d in plan['scopes']):return [poly],[]
 if max(p[2] for p in ungraded(poly))>.6201:return [poly],[]
 return xy.subtract(poly,plan['scopes'])

def route_uv(p,routes):
 best=None
 for route in routes:
  arc=0.
  for a,b in zip(route['points'],route['points'][1:]):
   dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
   if length<1e-8:continue
   t=max(0.,min(1.,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length**2));qx,qy=a[0]+dx*t,a[1]+dy*t
   distance=math.hypot(p[0]-qx,p[1]-qy);cross=((p[1]-qy)*dx-(p[0]-qx)*dy)/length
   if best is None or distance<best[0]:best=(distance,arc+t*length,cross)
   arc+=length
 assert best
 return best[1:]

def scope_distance(p):
 # Boundary of the two adjoining declared rectangles; the common edge is
 # internal and must not introduce a false raised seam.
 ring=[(-72,-65),(-37,-65),(-37,-100),(40,-100),(40,-55),(-37,-55),(-37,38),(-72,38)]
 distances=[]
 for a,b in zip(ring,ring[1:]+ring[:1]):
  dx,dy=b[0]-a[0],b[1]-a[1];t=max(0.,min(1.,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy)))
  distances.append(math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy))
 return min(distances)

def walking_offsets(vertices,tree):
 from mathutils import Vector
 result={};fallback=0
 for i,p in enumerate(vertices):
  d=scope_distance(p)
  if d>=2 or abs(p[2]-grade(*p[:2])-.46)>1e-5:continue
  co,no,face,distance=tree.ray_cast(Vector(xy.world((p[0],p[1],12))),Vector((0,0,-1)),20)
  # Inherited road faces can have downward winding. Their first downward ray
  # hit still measures the geometric top; do not discard that height merely
  # because the legacy normal points down.
  if co is None or abs(no.z)<.1:
   # Source gaps have no measurable top. Retain the inherited regional
   # nominal level rather than treating a missing ray as a zero elevation.
   old=(.46 if 33.5<=p[0]<=67 and -63<=p[1]<=-30 else .6)+grade(*p[:2]);fallback+=1
  else:old=co.z
  t=d/2;fade=1-t*t*(3-2*t);offset=(old-p[2])*fade
  assert abs(offset)<.18,'Unexpected source curb height'
  if abs(offset)>1e-7:result[str(i)]=offset
 return result,fallback

def aligned_material(original):
 mat=original.copy();mat.name='OTW Road geometry v2 / '+original.name;nodes=mat.node_tree.nodes
 uv=nodes.new('ShaderNodeUVMap');uv.name='OTW v2 / route coordinates';uv.uv_map='OTW route joints'
 mat.node_tree.links.new(uv.outputs['UV'],nodes['OTW finish / paving joints'].inputs['Vector'])
 return mat

def build(src,out,plan):
 import bpy
 from mathutils import Vector
 bpy.ops.wm.open_mainfile(filepath=str(src));bpy.context.scene.frame_set(1)
 before=state();write(out/'baseline.json',before);audit={}
 for name in sorted(SURFACES):
  o=bpy.data.objects[name];m=o.data
  assert m.users==1 and not m.uv_layers and not m.shape_keys and not o.modifiers and not o.parent and not o.constraints and not o.animation_data
  assert all(abs(o.matrix_world[i][j]-(i==j))<1e-7 for i in range(4) for j in range(4))
  vs=[tuple(v.co) for v in m.vertices];oldvs=list(vs);source_rows=rows(m);flags=[(v.hide,v.select) for v in m.vertices]
  edges={tuple(sorted(e.vertices)):(e.hide,e.select,e.use_seam,e.use_edge_sharp) for e in m.edges};local=[xy.local(p) for p in vs]
  fs=[];attributes=[];cut=0
  for ids,mat,smooth,hide,select in source_rows:
   parts,removed=partition([local[i] for i in ids],plan)
   if sum(xy.area(p) for p in removed)<1e-8:fs.append(ids);attributes.append((mat,smooth,hide,select));continue
   cut+=1
   for part in parts:
    start=len(vs);vs.extend(xy.world(p) for p in part);fs.append(list(range(start,len(vs))));attributes.append((mat,smooth,hide,select))
  retained=len(fs);offset=len(vs);rep=plan['replacement'][name];top_offsets={};fallback=0
  if name.startswith('pavement'):
   from mathutils.bvhtree import BVHTree
   source_tree=BVHTree.FromObject(o,bpy.context.evaluated_depsgraph_get());top_offsets,fallback=walking_offsets(rep['vertices'],source_tree)
  vs.extend(xy.world((p[0],p[1],p[2]+top_offsets.get(str(i),0))) for i,p in enumerate(rep['vertices']))
  fs.extend([[offset+i for i in f] for f in rep['faces']]);matindex=0
  if name in ['pavement_0 unified road','gutter 15s road detail']:m.materials.append(aligned_material(m.materials[0]));matindex=len(m.materials)-1
  attributes.extend((matindex,False,False,False) for f in rep['faces'])
  m.clear_geometry();m.from_pydata(vs,[],fs);m.update()
  for p,row in zip(m.polygons,attributes):p.material_index,p.use_smooth,p.hide,p.select=row
  for v,row in zip(m.vertices,flags):v.hide,v.select=row
  for e in m.edges:
   if tuple(sorted(e.vertices)) in edges:e.hide,e.select,e.use_seam,e.use_edge_sharp=edges[tuple(sorted(e.vertices))]
  if matindex:
   uv=m.uv_layers.new(name='OTW route joints')
   values={i:route_uv(p,plan['routes']) for i,p in enumerate(rep['vertices'])}
   for face in list(m.polygons)[retained:]:
    for loop in face.loop_indices:uv.data[loop].uv=values[m.loops[loop].vertex_index-offset]
  audit[name]=dict(original_vertices=len(oldvs),retained_faces=retained,replacement_vertex_start=offset,cut_faces=cut,replacement_faces=len(rep['faces']),source_rows=source_rows,source_vertices=oldvs,source_flags=flags,source_edge_flags=[[list(k),list(v)] for k,v in edges.items()],material_index=matindex,top_offsets=top_offsets,boundary_height_fallback_vertices=fallback)
 details=reproject_details(plan)
 write(out/'detail-audit.json',details)
 (out/'audit.json').write_text(json.dumps(audit,separators=(',',':')),encoding='utf-8')
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'after.blend'),compress=True)
 return dict(ok=True,audit_sha256=digest(out/'audit.json'),detail_audit_sha256=digest(out/'detail-audit.json'),detail_vertices={n:len(r) for n,r in details.items()},surfaces={n:{k:v for k,v in a.items() if not k.startswith('source_')} for n,a in audit.items()},new_materials=2)

def support_trees():
 import bpy
 from mathutils.bvhtree import BVHTree
 return [(n,bpy.data.objects[n],BVHTree.FromObject(bpy.data.objects[n],bpy.context.evaluated_depsgraph_get())) for n in SURFACES|{'OTW Tokyo Tower site v3 / site-paving'}]

def surface_hit(p,trees):
 from mathutils import Vector
 hits=[];origin=Vector(xy.world((p[0],p[1],12)))
 for n,o,t in trees:
  inv=o.matrix_world.inverted();co,no,i,d=t.ray_cast(inv@origin,inv.to_3x3()@Vector((0,0,-1)),20)
  if co is not None:hits.append((float((o.matrix_world@co).z),n))
 return max(hits) if hits else None

def reproject_details(plan):
 import bpy
 from tower_site_geometry_v8 import components
 trees=support_trees();anchors=[];result={}
 o=bpy.data.objects['Close detail iron'];vs=[xy.local(v.co) for v in o.data.vertices]
 for group in components(vs,[list(f.vertices) for f in o.data.polygons]):
  ps=[vs[i] for i in group];lo=[min(p[k] for p in ps) for k in range(3)];hi=[max(p[k] for p in ps) for k in range(3)]
  if hi[0]-lo[0]<.4 or hi[1]-lo[1]<.4:continue
  if not all(xy.inside(p,plan['scopes'],-.01) for p in ps):continue
  anchors.append((lo,hi))
 for name in sorted(DETAILS):
  o=bpy.data.objects[name];changes=[]
  for v in o.data.vertices:
   p=xy.local(v.co)
   if not xy.inside(p,plan['scopes'],-.01):continue
   if name!='Skywalk visible detail white' and not any(lo[0]-.07<p[0]<hi[0]+.07 and lo[1]-.07<p[1]<hi[1]+.07 for lo,hi in anchors):continue
   hit=surface_hit(p,trees)
   if not hit:continue
   h,surface=hit
   # Parking lines remain on the lot/apron, never migrate onto new curbs.
   if name=='Skywalk visible detail white':
    if surface not in ['parking mapped land use','OTW Tokyo Tower site v3 / site-paving']:continue
    z=h+.005
   else:z=h+(p[2]-grade(*p[:2])-.3)
   dz=z-p[2]
   if abs(dz)<.001 or abs(dz)>.25:continue
   old=list(v.co);v.co.z+=dz;changes.append(dict(index=v.index,before=old,after=list(v.co),support=surface,height=h,offset=z-h))
  o.data.update();result[name]=changes
 return result

def validate(src,out,plan):
 import bpy
 bpy.ops.wm.open_mainfile(filepath=str(out/'after.blend'));bpy.context.scene.frame_set(1)
 before=json.loads((out/'baseline.json').read_text());after=state();audit=json.loads((out/'audit.json').read_text());build=json.loads((out/'build.json').read_text())
 assert digest(out/'audit.json')==build['audit_sha256']
 assert digest(out/'detail-audit.json')==build['detail_audit_sha256']
 assert before['metadata']==after['metadata'],'Protected metadata changed'
 assert before['assets']==after['assets'] and before['lights']==after['lights']
 for name,row in before['objects'].items():
  if name not in TARGETS:assert row==after['objects'][name],'Protected object changed: '+name
  else:
   want={k:v for k,v in row.items() if k not in ['mesh','materials']}
   assert want=={k:v for k,v in after['objects'][name].items() if k not in ['mesh','materials']}
   if name in DETAILS:assert row['materials']==after['objects'][name]['materials'] and before['slots'][name]==after['slots'][name]
 for name,fp in before['materials'].items():assert fp==after['materials'][name],'Original material changed: '+name
 for k,v in before['data_counts'].items():assert after['data_counts'][k]==v+(2 if k=='materials' else 0)
 checks={}
 details=json.loads((out/'detail-audit.json').read_text(encoding='utf-8'));trees=support_trees()
 # A fresh source load independently verifies the complete preserved detail
 # vertex array and topology, including all vertices omitted from the audit.
 detail_saved={n:([[float(q) for q in v.co] for v in bpy.data.objects[n].data.vertices],rows(bpy.data.objects[n].data)) for n in DETAILS}
 for name,a in audit.items():
  m=bpy.data.objects[name].data;vs=[list(v.co) for v in m.vertices];rr=rows(m);oldvs=a['source_vertices'];oldlocal=[xy.local(p) for p in oldvs]
  assert vs[:len(oldvs)]==oldvs and [[v.hide,v.select] for v in list(m.vertices)[:len(oldvs)]]==a['source_flags']
  print('Validate surface:',name,flush=True)
  retained=Counter(json.dumps(r) for r in rr[:a['retained_faces']]);outside=0.;area_expected=0.
  for row in a['source_rows']:
   parts,removed=partition([oldlocal[i] for i in row[0]],plan)
   if sum(xy.area(p) for p in removed)<1e-8:
    key=json.dumps(row);assert retained[key]>0,'Outside face changed';retained[key]-=1;outside+=1
   else:area_expected+=sum(xy.area(p) for p in parts)
  area_saved=0.
  for encoded,count in retained.items():
   if count:area_saved+=count*xy.area([xy.local(vs[i]) for i in json.loads(encoded)[0]])
  assert abs(area_expected-area_saved)<.05
  rep=plan['replacement'][name];start=a['replacement_vertex_start'];new=vs[start:]
  assert len(new)==len(rep['vertices']) and [[i-start for i in r[0]] for r in rr[a['retained_faces']:]]==rep['faces']
  if name.startswith('pavement'):
   from mathutils.bvhtree import BVHTree
   source_tree=BVHTree.FromPolygons(oldvs,[r[0] for r in a['source_rows']]);expected,fallback=walking_offsets(rep['vertices'],source_tree)
   assert expected==a['top_offsets'] and fallback==a['boundary_height_fallback_vertices']
  assert all(math.dist(xy.local(p),(q[0],q[1],q[2]+a['top_offsets'].get(str(i),0)))<3e-5 for i,(p,q) in enumerate(zip(new,rep['vertices'])))
  assert all(xy.inside(p,plan['scopes']) for p in rep['vertices'])
  assert all(xy.area([new[i] for i in f])>1e-9 for f in rep['faces'])
  assert after['slots'][name][:2]==before['slots'][name]
  if a['material_index']:
   assert len(m.uv_layers)==1 and m.uv_layers.active.name=='OTW route joints'
   for f in list(m.polygons)[a['retained_faces']:]:
    assert f.material_index==a['material_index']
    for li in f.loop_indices:assert math.dist(m.uv_layers.active.data[li].uv,route_uv(rep['vertices'][m.loops[li].vertex_index-start],plan['routes']))<.0001
  checks[name]=dict(original_vertices_exact=True,outside_faces_exact=outside,outside_area_error_m2=abs(area_expected-area_saved),replacement_matches_plan=True)
  if name.startswith('pavement'):
   edges=Counter(tuple(sorted((x,y))) for f in rep['faces'] for x,y in zip(f,f[1:]+f[:1]));assert set(edges.values())=={2};checks[name]['replacement_closed']=True
 for name,changes in details.items():
  for r in changes:
   hit=surface_hit(xy.local(r['after']),trees);assert hit and hit[1]==r['support'] and abs(hit[0]-r['height'])<.0001
   assert abs(r['after'][2]-hit[0]-r['offset'])<.0001
 bpy.ops.wm.open_mainfile(filepath=str(src));bpy.context.scene.frame_set(1)
 for name in DETAILS:
  expected=[[float(q) for q in v.co] for v in bpy.data.objects[name].data.vertices]
  for r in details[name]:assert expected[r['index']]==r['before'];expected[r['index']]=r['after']
  assert expected==detail_saved[name][0] and rows(bpy.data.objects[name].data)==detail_saved[name][1]
  checks[name]=dict(changed_vertices=len(details[name]),other_vertices_exact=True,topology_preserved=True,surface_contacts_verified=True)
 return dict(ok=True,objects=len(after['objects']),checks=checks,source_unchanged=digest(src)==SOURCE_SHA,warnings=after['warnings'],limits=plan['limits']+after['limits'])

def main():
 import bpy
 p=argparse.ArgumentParser();p.add_argument('--phase',required=True,choices=['build','validate','render-before','render-after']);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--preview',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 src=a.input.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);plan=json.loads(PLAN.read_text());config=json.loads(CONFIG.read_text());report=out/(a.phase+'.json')
 assert not report.exists() and src!=out/'after.blend' and digest(src)==SOURCE_SHA and digest(PLAN)==config['plan_sha256']
 assert bpy.app.version_string=='4.5.1 LTS' and not bpy.context.preferences.filepaths.use_scripts_auto_execute
 code={n:digest(ROOT/'scripts'/n) for n in ['road_geometry_v2.py','prepare_road_geometry_v2.py','road_finish_v1.py','tower_footway_geometry_v5.py','tower_site_geometry_v8.py','blender_worker.py','validate_tower_foottown.py']}
 candidate=digest(out/'after.blend') if a.phase!='build' else None
 if a.phase=='build':assert not (out/'after.blend').exists();result=build(src,out,plan)
 elif a.phase=='validate':result=validate(src,out,plan)
 else:
  from blender_worker import render
  bpy.ops.wm.open_mainfile(filepath=str(src if a.phase=='render-before' else out/'after.blend'));cameras=json.loads(CAMERAS.read_text())
  if a.preview:cameras['views']=[v for v in cameras['views'] if v['id'] in ['west-road-vehicle','south-road-vehicle']]
  settings=dict(width=768 if a.preview else 1280,height=509 if a.preview else 848,samples=12 if a.preview else 32,seed=0,device='OPTIX')
  phase=a.phase.replace('render-','');normal=dict(cameras,views=[v for v in cameras['views'] if v['id']!='surface-details-close']);diagnostic=dict(cameras,views=[v for v in cameras['views'] if v['id']=='surface-details-close'])
  result=render(dict(output=str(out),cameras=normal,settings=settings),phase)
  if diagnostic['views']:
   collection=bpy.data.objects['Close detail iron'].users_collection[0];visibility=collection.hide_render;flags={o.name:o.hide_render for o in collection.objects}
   try:
    collection.hide_render=False
    for o in collection.objects:o.hide_render=o.name not in ['Close detail iron','Close detail rim']
    detail=render(dict(output=str(out),cameras=diagnostic,settings=settings),phase);assert detail['devices']==result['devices'];result['views'].extend(detail['views'])
   finally:
    collection.hide_render=visibility
    for name,hidden in flags.items():bpy.data.objects[name].hide_render=hidden
   result['surface_detail_visibility_override']=dict(view='surface-details-close',visible_objects=['Close detail iron','Close detail rim'],stored_collection_hidden=visibility,saved_scene_visibility_unchanged=True)
  result.update(settings=settings,cameras_sha256=digest(CAMERAS))
 assert digest(src)==SOURCE_SHA
 if candidate:assert digest(out/'after.blend')==candidate
 assert all(digest(ROOT/'scripts'/n)==h for n,h in code.items())
 result.update(input_sha256=SOURCE_SHA,candidate_sha256=digest(out/'after.blend'),plan_sha256=digest(PLAN),code_sha256=code,blender_version=bpy.app.version_string)
 write(report,result);print(a.phase,'OK',flush=True)
if __name__=='__main__':main()
