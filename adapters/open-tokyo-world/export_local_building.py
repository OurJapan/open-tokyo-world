"""Export only the retained af7335da Blender candidate for local Web review.

Uses existing Blender glTF export. No download, registration, public-directory
copy or deployment. Inputs and existing output directories are never rewritten.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import time

ROOT=Path(__file__).resolve().parents[2]
FEATURE='bldg_af7335da-7542-44dd-964d-8cccd2b046ff'
PROFILE='data221-af7335da'
MAX_BYTES=5*1024*1024


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def glb_document(path):
    data=path.read_bytes()
    if len(data)<20 or struct.unpack_from('<III',data)!=(0x46546c67,2,len(data)):
        raise ValueError('Invalid GLB header')
    size,kind=struct.unpack_from('<II',data,12)
    if kind!=0x4e4f534a or size>len(data)-20:raise ValueError('Invalid GLB JSON chunk')
    doc=json.loads(data[20:20+size])
    if any('uri' in row for row in doc.get('buffers',[])) or any('uri' in row for row in doc.get('images',[])):
        raise ValueError('GLB must embed all buffers and textures')
    return doc


def checked_output(root,output):
    root=root.resolve();output=output.resolve();allowed=root/'data/local'
    if not output.is_relative_to(allowed) or output==allowed:
        raise ValueError('Choose a fresh output inside data/local/')
    if output.exists():raise ValueError('Output already exists; choose a fresh directory')
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender',type=Path,required=True)
    parser.add_argument('--input',type=Path,required=True,help='PR49 target.blend, not the full city')
    parser.add_argument('--input-sha256',required=True)
    parser.add_argument('--inputs',type=Path,required=True,help='Already retained pinned PLATEAU files')
    parser.add_argument('--output',type=Path,default=ROOT/'data/local/web-exports'/PROFILE)
    args=parser.parse_args()
    source=args.input.resolve();out=checked_output(ROOT,args.output)
    if source.stat().st_size>MAX_BYTES:raise ValueError('Use the isolated target.blend, not the full city')
    if digest(source)!=args.input_sha256:raise ValueError('Input SHA-256 mismatch')
    worker=Path(__file__).with_name('local_building_blender.py')
    source_files=[Path(__file__),worker,ROOT/'starter/plateau/tile.py']
    code={p.relative_to(ROOT).as_posix():digest(p) for p in source_files}
    out.mkdir(parents=True)
    job={'input':str(source),'input_sha256':args.input_sha256,'inputs':str(args.inputs.resolve()),
         'output':str(out),'feature':FEATURE,'code_sha256':code}
    job_path=out/'job.json';job_path.write_text(json.dumps(job,indent=2)+'\n',encoding='utf8')
    phases={}
    for phase in ('export','verify'):
        command=[str(args.blender.resolve()),'--background','--factory-startup','--threads','2',
                 '--python-exit-code','1','--python',str(worker),'--','--job',str(job_path),'--phase',phase]
        started=time.monotonic()
        with (out/(phase+'.log')).open('w',encoding='utf8') as log:
            result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        phases[phase]={'exit_code':result.returncode,'seconds':round(time.monotonic()-started,3)}
        if result.returncode:raise RuntimeError(phase+' failed; see '+str(out/(phase+'.log')))
        print(phase+': passed',flush=True)
    if digest(source)!=args.input_sha256:raise ValueError('Source changed during export')
    if any(digest(ROOT/p)!=value for p,value in code.items()):raise ValueError('Code changed during export')
    model=out/'model.glb';doc=glb_document(model)
    if model.stat().st_size>MAX_BYTES:raise ValueError('Single local asset exceeds 5 MiB')
    export=json.loads((out/'geometry-export.json').read_text(encoding='utf8'))
    baseline=json.loads((ROOT/'manifests/legacy-baseline.json').read_text(encoding='utf8'))
    asset={'id':PROFILE,'url':'model.glb','fixture':False,'feature_id':FEATURE,'source_batch_id':15,
           'sha256':digest(model),'bytes':model.stat().st_size,'triangles':466,
           'model_version':'local-'+digest(model)[:16],'redistribution':'local-review-only',
           'bounds_render_m':export['bounds_render_m']}
    manifest={'schema_version':'otw-spatial-manifest/0.1','area_id':'tokyo-tower','fixture':False,'local_only':True,
              'origin':baseline['coordinates'],
              'frame':{'id':'tokyo-tower-legacy-display','revision':'data221-local-review-1',
                       'registration_status':'unregistered','units':'meters','render_axes':'east-up-south',
                       'height_note':'Per-feature minimum z=0.32m is retained legacy display placement, not surveyed terrain.'},
              'assets':[asset],'known_features':[{'feature_id':FEATURE,'status':'retained-source-id'}],
              'source_refs':['docs/plateau-data221.json','docs/data221-af7335da-topology-evidence.json'],
              'attribution':{'source':'3D都市モデル（Project PLATEAU）港区（2025年度）',
                             'dataset_url':'https://www.geospatial.jp/ckan/dataset/plateau-13103-minato-ku-2025',
                             'policy_url':'https://www.mlit.go.jp/plateau/site-policy/',
                             'processing':'OurJapan: isolated source feature, legacy display placement, exact welding, procedural base-color bake and local GLB conversion.',
                             'license_scope':'Existing source terms retained. Local review only; no new asset license or permission to publish the model.'}}
    manifest['world_version']='sha256:'+hashlib.sha256(json.dumps(manifest,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf8')).hexdigest()
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (out/'run.json').write_text(json.dumps({'ok':True,'input_preserved':True,'input_sha256':args.input_sha256,
        'code_sha256':code,'phases':phases,'asset':asset,'images':len(doc.get('images',[])),
        'scope':'One local source feature only. No public assets, registry updates or deployment.',
        'limits':['The procedural base colour is sampled into a 1024px texture; this is not an exact procedural shader export.',
                  'GLB uses the preserved metre geometry and legacy display frame, not surveyed placement.',
                  'No permission for model/texture publication is added.']},indent=2)+'\n',encoding='utf8')
    print(json.dumps({'ok':True,'bytes':asset['bytes'],'triangles':466,'sha256':asset['sha256'],'output':str(out)}))


if __name__=='__main__':main()
