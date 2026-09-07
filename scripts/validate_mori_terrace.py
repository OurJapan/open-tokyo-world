import bpy,sys,json,math
from pathlib import Path
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--candidate',required=True,type=Path)
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.output.exists():raise ValueError('Refusing to overwrite audit output')
sys.path.insert(0,str(Path(__file__).resolve().parent))
from mori_terrace_v1 import TARGETS,geometry,DECK,ORIGIN
bpy.ops.wm.open_mainfile(filepath=str(args.candidate.resolve()))
import numpy as np
from collections import Counter
result={}
for name in sorted(TARGETS):
 o=bpy.data.objects[name];g=geometry(name.split(' / ')[1]);m=o.data
 xyz=np.empty(len(m.vertices)*3,dtype=np.float32);m.vertices.foreach_get('co',xyz);xyz=xyz.reshape(-1,3)
 assert np.array_equal(xyz,np.array(g.vertices,dtype=np.float32));assert [tuple(p.vertices) for p in m.polygons]==g.faces
 m.calc_loop_triangles();areas=[t.area for t in m.loop_triangles];assert min(areas)>1e-8
 edges=Counter()
 for p in m.polygons:
  f=list(p.vertices)
  for a,b in zip(f,f[1:]+f[:1]):edges[(a,b)]+=1
 assert all(edges[(b,a)]==n for (a,b),n in edges.items())
 assert all(mat.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value==0 for mat in m.materials)
 result[name]={'vertices':len(m.vertices),'polygons':len(m.polygons),'triangles':len(m.loop_triangles),'minimum_triangle_area':min(areas),'closed_oriented_edges':True,'generated_coordinates_exact_float32':True,'emission_zero':True}
# Roof support uses the untouched source-derived stone mesh, not all-scene raycasts.
stone=bpy.data.objects['Mori JP podium / stone'];stone.data.calc_loop_triangles()
roof=[]
for t in stone.data.loop_triangles:
 a=np.array([stone.data.vertices[i].co[:] for i in t.vertices]);
 if np.ptp(a[:,2])<.01 and abs(a[:,2].mean()-DECK)<.01:roof.append(a)
def supported(p):
 for tri in roof:
  a,b,c=tri[:,:2];mat=np.array([b-a,c-a]).T
  if abs(np.linalg.det(mat))<1e-8:continue
  q=np.linalg.solve(mat,np.array(p[:2])-a)
  if q.min()>-1e-4 and q.sum()<1.0001:return True
 return False
for name in ('Mori JP podium / soil','Mori JP podium / gasket'):
 g=geometry(name.split(' / ')[1]);assert all(supported(p) for p in g.vertices),name
report={'ok':True,'objects':result,'all_planter_and_railing_vertices_over_source_roof':True,'limitations':['Source parapet retained; railing placement inferred','No whole-city manifold, measured accuracy or regulatory clearance','Source roof support test does not validate tree species or photo registration']}
args.output.write_text(json.dumps(report,indent=2),encoding='utf8')
print('Terrace saved geometry audit passed')
