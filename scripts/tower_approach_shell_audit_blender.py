# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Read-only triangle-shell and planting-surface audit of the saved candidate."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from blender_worker import array_prop
from city_catalog_blender import enabled_meshes
from tower_approach import read,write,digest
from tower_approach_plan import COLLECTION,SOIL,EDGING
from tower_approach_blender import surface,height


def cropped_tree(obj,low,high):
    mesh = obj.data; mesh.calc_loop_triangles()
    xyz = array_prop(mesh.vertices,'co',3,np.float32).reshape(-1,3)
    ix = array_prop(mesh.loop_triangles,'vertices',3,np.int32).reshape(-1,3)
    matrix = np.asarray(obj.matrix_world,dtype=np.float64)
    selected = []
    for start in range(0,len(ix),100000):
        tri = xyz[ix[start:start+100000]].astype(np.float64)
        tri = tri @ matrix[:3,:3].T + matrix[:3,3]
        keep = np.all(tri.max(axis=1) >= low-1e-6,axis=1) & np.all(tri.min(axis=1) <= high+1e-6,axis=1)
        if keep.any(): selected.append(tri[keep])
    if not selected: return None,0
    tri = np.concatenate(selected)
    return BVHTree.FromPolygons(tri.reshape(-1,3).tolist(),np.arange(tri.size//3).reshape(-1,3).tolist()),len(tri)


def main():
    p = argparse.ArgumentParser(); p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True); p.add_argument('--require-clear',action='store_true')
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    if bpy.app.version_string != '4.5.1 LTS' or bpy.context.preferences.filepaths.use_scripts_auto_execute:
        raise ValueError('Use pinned Blender without automatic scripts')
    source = Path(bpy.data.filepath); initial = digest(source)
    bpy.context.scene.frame_set(1); bpy.context.view_layer.update()
    plan = read(a.plan); enabled = enabled_meshes()
    trees = [o for o in bpy.data.collections[COLLECTION].objects if o.name not in (SOIL,EDGING)]
    corners = np.asarray([o.matrix_world @ Vector(v) for o in trees for v in o.bound_box])
    low,high = corners.min(axis=0),corners.max(axis=0)
    obstacles = {}; triangle_counts = {}
    for obj in bpy.context.scene.objects:
        building = 'PLATEAU' in obj.name or obj.name == 'roof' or obj.name in {f'wall{i}' for i in range(8)}
        road = obj.name in ('pavement_0 unified road','asphalt 15s road detail','gutter 15s road detail')
        if obj.type != 'MESH' or obj.name not in enabled or not (building or road): continue
        box = np.asarray([obj.matrix_world @ Vector(v) for v in obj.bound_box])
        obstacle_low = low.copy()
        if road: obstacle_low[2] = 0
        if np.any(box.max(axis=0) < obstacle_low) or np.any(box.min(axis=0) > high): continue
        tree,count = cropped_tree(obj,obstacle_low,high)
        if tree is not None: obstacles[obj.name] = tree; triangle_counts[obj.name] = count
    intersections = {}
    for obj in trees:
        shell = surface(obj.name)
        hits = {name:len(shell.overlap(tree)) for name,tree in obstacles.items()}
        intersections[obj.name] = hits
    pavement = obstacles.get('pavement_0 unified road')
    samples = []
    for row in plan['trees']:
        x,y = row['source_matrix_world'][0][3],row['source_matrix_world'][1][3]
        probes = [height(pavement,x+dx,y+dy) if pavement else None
                  for dx,dy in [(0,0),(-.5,-.5),(-.5,.5),(.5,-.5),(.5,.5)]]
        samples.append({'seed':row['index'],'pavement_z_at_center_and_corners':probes,
                        'soil_top_m':plan['beds']['soil_top_m'],
                        'soil_obscured_by_pavement':any(v is not None and v > plan['beds']['soil_top_m']+1e-5 for v in probes)})
    unchanged = digest(source) == initial
    clear = all(not any(hits.values()) for hits in intersections.values()) and not any(r['soil_obscured_by_pavement'] for r in samples)
    result = {'ok':clear and unchanged,'read_only':True,'input_sha256':initial,'input_unchanged':unchanged,
              'obstacle_candidate_triangles':triangle_counts,'tree_shell_overlap_pairs':intersections,
              'surface_samples':samples,'limits':['Stored mesh triangle shell checks, not containment or complete evaluated-modifier collision certification.',
                                                  'Five planting-surface probes per bed; not a structural support or accessibility certification.']}
    write(a.output,result)
    print(json.dumps({'ok':result['ok'],'intersections':sum(sum(v.values()) for v in intersections.values()),
                      'obscured_soil_beds':sum(r['soil_obscured_by_pavement'] for r in samples)}))
    if a.require_clear and not result['ok']: raise ValueError('Saved candidate shell/surface audit failed')


if __name__ == '__main__':
    main()
