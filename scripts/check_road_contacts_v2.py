# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Read-only probes for the two inherited v8 vehicles after road replacement."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from road_geometry_v2 import support_trees,surface_hit
from road_finish_v1 import digest,write
from tower_footway_geometry_v5 import local

def main():
 import bpy
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 assert not a.output.exists();hash_before=digest(a.candidate)
 bpy.ops.wm.open_mainfile(filepath=str(a.candidate.resolve()),use_scripts=False);bpy.context.scene.frame_set(1)
 config=json.loads((ROOT/'areas/tokyo-tower/tower-site-v8-input.json').read_text(encoding='utf-8'));obj=bpy.data.objects['Tokyo traffic • tire'];trees=support_trees();checks=[]
 for car in config['vehicles']:
  start,end=car['ranges'][obj.name];wheels=[]
  for wheel in range(4):
   points=[local(obj.matrix_world@v.co) for v in list(obj.data.vertices)[start+40*wheel:start+40*(wheel+1)]]
   # Probe every tire vertex; top samples are not treated as contact gaps.
   gaps=[]
   for p in points:
    hit=surface_hit(p,trees)
    if hit:gaps.append(p[2]-hit[0])
   assert gaps,'No supporting road beneath inherited wheel'
   minimum=min(gaps);assert -.035<=minimum<=.07,('Wheel contact differs',car['index'],wheel,minimum)
   wheels.append(dict(wheel=wheel,lowest_gap_m=minimum,supported_vertex_probes=len(gaps)))
  checks.append(dict(inherited_vehicle_index=car['index'],wheels=wheels))
 assert digest(a.candidate)==hash_before
 write(a.output,dict(ok=True,candidate_sha256=hash_before,code_sha256=digest(Path(__file__)),checks=checks,limits=['Discrete tire vertex probes; not a continuous collision or traffic simulation.','Stored hidden traffic visibility is unchanged.']))
 print('Vehicle contacts OK; candidate unchanged.')
if __name__=='__main__':main()
