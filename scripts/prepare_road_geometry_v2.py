# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Bounded source-centred road outline plan; dimensions remain model estimates."""
import argparse,json,math
from collections import Counter
from pathlib import Path
import shapely as sh
from prepare_tower_footway_v5 import prepare,mesh
from tower_site_geometry_v8 import grade,subdivide
from tower_footway_geometry_v5 import world,local
ROOT=Path(__file__).resolve().parents[1]
SCOPES=[(-72.,-65.,-37.,38.),(-37.,-100.,40.,-55.)]

def graded_mesh(zone,top,bottom=None):
 vs=[];fs=[];lookup={}
 def vertex(x,y,z):
  key=(round(x,6),round(y,6),round(z,6))
  if key not in lookup:lookup[key]=len(vs);vs.append((key[0],key[1],key[2]+grade(*key[:2])))
  return lookup[key]
 xmin,ymin,xmax,ymax=zone.bounds
 for x in range(math.floor(xmin),math.ceil(xmax)):
  for y in range(math.floor(ymin),math.ceil(ymax)):
   piece=sh.set_precision(sh.intersection(zone,sh.box(x,y,x+1,y+1)),.001)
   for poly in sh.get_parts(piece):
    if poly.geom_type!='Polygon' or poly.area<1e-7:continue
    for tri in sh.get_parts(sh.constrained_delaunay_triangles(sh.orient_polygons(poly))):
     ring=list(sh.orient_polygons(tri).exterior.coords)[:3];fs.append([vertex(a,b,top) for a,b in ring])
 top_faces=list(fs)
 if bottom is not None:
  boundary=Counter(tuple(sorted((a,b))) for f in fs for a,b in zip(f,f[1:]+f[:1]))
  for f in top_faces:fs.append([vertex(vs[i][0],vs[i][1],bottom) for i in reversed(f)])
  for f in top_faces:
   for a,b in zip(f,f[1:]+f[:1]):
    if boundary[tuple(sorted((a,b)))]==1:
     midpoint=sh.Point((vs[a][0]+vs[b][0])/2,(vs[a][1]+vs[b][1])/2)
     assert midpoint.distance(zone.boundary)<.002,'Internal tessellation crack'
     fs.append([a,vertex(vs[a][0],vs[a][1],bottom),vertex(vs[b][0],vs[b][1],bottom),b])
  closed=Counter(tuple(sorted((a,b))) for f in fs for a,b in zip(f,f[1:]+f[:1]));assert set(closed.values())=={2}
 return dict(vertices=vs,faces=fs,area_m2=zone.area)

def main():
 p=argparse.ArgumentParser();p.add_argument('--osm',type=Path,required=True);p.add_argument('--surfaces',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 assert not a.output.exists()
 old=json.loads((ROOT/'areas/tokyo-tower/tower-site-v8-plan.json').read_text())
 plan=prepare(a.osm,cap_polygons=old['masks'],scope_bounds=SCOPES)
 # More samples resolve the round joins without shifting the mapped centre line.
 roads=[];outer=[]
 for route in plan['routes']:
  typ=route['tags']['highway'];line=sh.LineString(route['points']);w=route['width_m'];pedestrian=typ in ('footway','path','steps','pedestrian')
  if not pedestrian:roads.append(line.buffer(w/2,cap_style=2,join_style=1,quad_segs=24))
  outer.append(line.buffer(w/2+(0 if pedestrian else 1.05),cap_style=2,join_style=1,quad_segs=24))
 scope=sh.union_all([sh.box(*b) for b in SCOPES])
 from tower_foundation_geometry_v4 import grid
 rows=grid();apron=sh.Polygon(rows[0]+[r[-1] for r in rows[1:]]+list(reversed(rows[-1][:-1]))+[r[0] for r in reversed(rows[1:-1])])
 mask=sh.union_all([apron,*[sh.Polygon(r) for r in old['masks']]])
 road=sh.union_all(roads).difference(mask);walk=sh.union_all(outer).difference(sh.union_all(roads)).difference(mask)
 walk=walk.buffer(-.22,quad_segs=24).buffer(.22,quad_segs=24).intersection(walk)
 gutter=road.difference(road.buffer(-.24,join_style=1,quad_segs=24))
 zones={n:sh.set_precision(g.intersection(scope),.001) for n,g in [('asphalt 15s road detail',road.difference(gutter)),('gutter 15s road detail',gutter),('pavement_0 unified road',walk)]}
 zones['gutter 15s road detail']=zones['gutter 15s road detail'].difference(zones['asphalt 15s road detail'])
 zones['pavement_0 unified road']=zones['pavement_0 unified road'].difference(sh.union_all([zones['asphalt 15s road detail'],zones['gutter 15s road detail']]))
 replacements={}
 for name,zone in zones.items():
  replacements[name]=graded_mesh(zone,.46 if name.startswith('pavement') else .3,.3 if name.startswith('pavement') else None)
 # Preserve the inherited parking footprint outside the physical road bands.
 # Re-tessellation makes its grade follow the same grid as the adjoining road.
 source=json.loads(a.surfaces.read_text(encoding='utf-8'))['parking mapped land use'];vertices=[local(p) for p in source['vertices']]
 rings=[]
 for face in source['polygons']:
  points=[vertices[i] for i in face]
  if len(points)>2:
   poly=sh.Polygon([p[:2] for p in points])
   if poly.is_valid and poly.area>1e-7 and poly.intersects(scope):rings.append(poly)
 parking=sh.set_precision(sh.union_all(rings).intersection(scope).difference(sh.union_all(list(zones.values()))),.001)
 replacements['parking mapped land use']=graded_mesh(parking,.11)
 plan.update(version=2,scopes=SCOPES,replacement=replacements,curve_samples_per_quadrant=24,grade_basis='Adopted tower-site-v8 grade, no new terrain anchors.',joint_basis='Nearest saved OSM centre-line arc length and signed cross-track distance; inferred paving layout.',limits=['Road centres and tagged/nominal widths retained. Curbs, gutter width and corner radius are model choices, not surveyed dimensions.','Existing v8 relative grade is retained. No regional elevation reconstruction.','Only west and south edit rectangles are rebuilt.','Drain and marking locations require independent evidence; no invented road markings.'])
 a.output.write_text(json.dumps(plan,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
 print({n:dict(vertices=len(r['vertices']),faces=len(r['faces']),area_m2=round(r['area_m2'],3)) for n,r in replacements.items()})
if __name__=='__main__':main()
