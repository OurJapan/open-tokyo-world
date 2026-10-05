# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Extract the pinned parking footprint locally; never save the source scene."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from road_geometry_v2 import SOURCE_SHA
from road_finish_v1 import digest

def main():
 import bpy
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 assert digest(a.input)==SOURCE_SHA and not a.output.exists()
 bpy.ops.wm.open_mainfile(filepath=str(a.input.resolve()),use_scripts=False);bpy.context.scene.frame_set(1)
 o=bpy.data.objects['parking mapped land use'];vertices=[list(o.matrix_world@v.co) for v in o.data.vertices]
 polygons=[list(f.vertices) for f in o.data.polygons if any(abs(vertices[i][0])<160 and abs(vertices[i][1])<160 for i in f.vertices)]
 a.output.write_text(json.dumps({o.name:dict(vertices=vertices,polygons=polygons)},separators=(',',':')),encoding='utf-8')
 assert digest(a.input)==SOURCE_SHA
 print('Parking footprint exported; source unchanged.')
if __name__=='__main__':main()
