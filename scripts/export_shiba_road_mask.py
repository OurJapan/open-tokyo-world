"""Export local protected road footprints from the pinned, immutable city.

Run with Blender 4.5.1 LTS --factory-startup --disable-autoexec --background
CITY --python this_script.py -- --output NEW_JSON. No blend is saved.
The extracted legacy geometry remains an ignored local input, not a public asset.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import shiba_momijidani_v1 as shiba
import validate_shiba_momijidani as checks


def export(output):
    import bpy
    from blender_worker import mesh_fingerprint
    checks.require(not output.exists(), 'Refusing to overwrite the local road mask')
    checks.require(bpy.app.version_string=='4.5.1 LTS', 'Use Blender 4.5.1 LTS')
    checks.require(not bpy.context.preferences.filepaths.use_scripts_auto_execute, 'Disable Blender auto-execution')
    source=Path(bpy.data.filepath).resolve()
    input_hash=checks.digest(source)
    checks.require(input_hash==shiba.INPUT_SHA256, 'Road-mask export requires the pinned accepted city')
    dependencies=[Path(__file__).resolve(),Path(checks.__file__),Path(shiba.__file__),Path(__file__).with_name('blender_worker.py')]
    code_hashes={path.name:checks.digest(path) for path in dependencies}
    bpy.context.scene.frame_set(1)
    xmin,ymin,xmax,ymax=shiba.BOUNDS
    roads=[]
    for name in checks.ROADS:
        obj=bpy.data.objects.get(name)
        checks.require(obj is not None and obj.type=='MESH', 'Missing protected road mesh: '+name)
        checks.require(not obj.modifiers and not obj.animation_data and not obj.constraints,
                       'Unsupported protected road state: '+name)
        obj.data.calc_loop_triangles()
        vertices=[tuple(obj.matrix_world@vertex.co) for vertex in obj.data.vertices]
        triangles=[]
        for face in obj.data.loop_triangles:
            triangle=[vertices[i] for i in face.vertices]
            if not checks.horizontal_road_projection(triangle):continue
            if max(p[0] for p in triangle)<xmin or min(p[0] for p in triangle)>xmax or \
                    max(p[1] for p in triangle)<ymin or min(p[1] for p in triangle)>ymax:continue
            triangles.append([list(point[:2]) for point in triangle])
        roads.append({'name':name,'mesh_sha256':mesh_fingerprint(obj.data),'triangles':triangles})
    checks.require(sum(len(road['triangles']) for road in roads)>0, 'No protected road footprint was found')
    checks.require(checks.digest(source)==input_hash, 'Accepted city changed during read-only export')
    checks.require(all(checks.digest(path)==code_hashes[path.name] for path in dependencies),
                   'Export code changed during extraction')
    result={'version':1,'input_sha256':input_hash,'blender_version':bpy.app.version_string,
            'frame':1,'autoexec_enabled':False,'scene_saved':False,'roads':roads,
            'bounds_m':list(shiba.BOUNDS),'road_z_range_m':[.1,.6],
            'selection':'Full horizontal triangles whose XY bounding boxes overlap the scope; both winding directions.',
            'code_sha256':code_hashes,
            'distribution':'Local legacy geometry; not approved for redistribution.'}
    output.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation also prevents a concurrent run from replacing this input.
    with output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'output':str(output),'sha256':checks.digest(output),
                      'triangles':{road['name']:len(road['triangles']) for road in roads}}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    export(args.output.resolve())


if __name__=='__main__':main()
