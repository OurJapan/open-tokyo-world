"""Explicit Blender integration negatives against a completed standalone run."""
import argparse, json, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CASES=['roof-missing','neighbor-changed','glass-link-missing','duplicate-tower']

def mutate(run,out):
    import bpy
    for case in CASES:
        folder=out/case;folder.mkdir()
        for name in ['replacement.json','georeference.json']:shutil.copyfile(run/name,folder/name)
        bpy.ops.wm.open_mainfile(filepath=str(run/'after.blend'),use_scripts=False)
        if case=='roof-missing':bpy.data.objects.remove(bpy.data.objects['Mori independent / floors and roof'],do_unlink=True)
        elif case=='neighbor-changed':
            o=next(o for o in bpy.context.scene.objects if o.get('gml_id'));o.data.vertices[0].co.z+=1
        elif case=='glass-link-missing':
            o=bpy.data.objects['Mori continuous pearl glass / pearl grey coated glass'];m=o.data.materials[0]
            output=next(n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL');m.node_tree.links.remove(output.inputs['Surface'].links[0])
        else:
            o=bpy.data.objects['Mori JP podium / stone'].copy();o.data=o.data.copy();o['gml_id']='bldg_433bc5b3-db73-4644-ac24-a28d51b7ecd5';bpy.context.scene.collection.objects.link(o)
        bpy.ops.wm.save_as_mainfile(filepath=str(folder/'after.blend'),compress=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--blender',type=Path);ap.add_argument('--run',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--mutate',action='store_true')
    a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    if a.mutate:return mutate(a.run.resolve(),a.output.resolve())
    a.output.mkdir(parents=True,exist_ok=False)
    command=[str(a.blender),'--factory-startup','--background','--disable-autoexec','--python-exit-code','1']
    with (a.output/'mutation.log').open('w') as log:
        subprocess.run(command+['--python',str(Path(__file__).resolve()),'--','--run',str(a.run.resolve()),'--output',str(a.output.resolve()),'--mutate'],stdout=log,stderr=subprocess.STDOUT,timeout=300,check=True)
    results={}
    for case in CASES:
        folder=a.output/case
        with (folder/'check.log').open('w') as log:
            p=subprocess.run(command+['--python',str(ROOT/'starter/mori/scene.py'),'--','--folder',str(folder.resolve()),'--phase','after'],stdout=log,stderr=subprocess.STDOUT,timeout=120)
        error=(folder/'check.log').read_text()
        expected='Object set mismatch' if case in ['roof-missing','duplicate-tower'] else 'Object/material fingerprint mismatch'
        if p.returncode==0 or expected not in error:raise AssertionError('Negative did not fail as intended: '+case)
        results[case]={'rejected':True,'expected_error':expected,'exit_code':p.returncode}
    (a.output/'results.json').write_text(json.dumps({'ok':True,'cases':results},indent=2)+'\n')
    print(json.dumps(results))

if __name__=='__main__':main()
