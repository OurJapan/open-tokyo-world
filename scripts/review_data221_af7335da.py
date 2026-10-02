"""Produce a local-only, feature-limited city candidate. Never register or publish."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
VIEWS = [
    {'id':'east','center':[-460,404,118],'offset':[360,-140,140],'scale':310},
    {'id':'west','center':[-460,404,118],'offset':[-330,200,130],'scale':310},
    {'id':'roof','center':[-433,392,224],'offset':[110,-85,100],'scale':120},
    {'id':'podium','center':[-460,404,15],'offset':[-110,-130,105],'scale':165},
]


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--blender',type=Path,required=True)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--input-sha256',required=True)
    p.add_argument('--inputs',type=Path,required=True,help='Existing pinned data221.b3dm and tileset.json')
    p.add_argument('--output',type=Path,required=True,help='New directory; existing output is refused')
    args=p.parse_args()
    source=args.input.resolve(); out=args.output.resolve()
    if out.exists(): raise ValueError('Choose a new output directory')
    if out == source.parent or out in source.parents: raise ValueError('Output overlaps input')
    if digest(source) != args.input_sha256: raise ValueError('Input SHA-256 mismatch')
    out.mkdir(parents=True)
    files=['scripts/data221_af7335da_mesh.py','scripts/data221_af7335da_worker.py',
           'scripts/review_data221_af7335da.py','scripts/blender_worker.py','starter/plateau/tile.py',
           'areas/tokyo-tower/mori-plaza-connection-accepted-features.json']
    code={name:digest(ROOT/name) for name in files}
    head=subprocess.run(['git','-c','safe.directory='+ROOT.as_posix(),'rev-parse','HEAD'],
                        cwd=ROOT,text=True,check=True,capture_output=True).stdout.strip()
    job={'input':str(source),'input_sha256':args.input_sha256,'inputs':str(args.inputs.resolve()),
         'output':str(out),'views':VIEWS,'code_base_commit':head,'code_files':code}
    job_path=out/'job.json'; job_path.write_text(json.dumps(job,indent=2)+'\n',encoding='utf8')
    runs={}
    for phase in ['build','validate','render-before','render-after']:
        command=[str(args.blender.resolve()),'--background','--factory-startup','--threads','2',
                 '--python-exit-code','1','--python',str(ROOT/'scripts/data221_af7335da_worker.py'),
                 '--','--job',str(job_path),'--phase',phase]
        started=time.monotonic()
        with (out/(phase+'.log')).open('w',encoding='utf8') as log:
            result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        runs[phase]={'exit_code':result.returncode,'seconds':round(time.monotonic()-started,3)}
        if result.returncode: raise RuntimeError(phase+' failed; see '+str(out/(phase+'.log')))
        print(phase+': passed',flush=True)
    if digest(source) != args.input_sha256: raise ValueError('Original input changed')
    if any(digest(ROOT/name)!=value for name,value in code.items()): raise ValueError('Code changed during run')
    outputs={name:digest(out/name) for name in ['after.blend','target.blend','before-neighborhood.blend','after-neighborhood.blend']}
    report={'ok':True,'input_sha256':args.input_sha256,'input_preserved':True,
            'code_base_commit':head,'code_files':code,'jobs':runs,'output_blends':outputs,
            'scope':'Exact topology repair of data221 batch 15; local candidate only',
            'limits':['No survey/real-world detail improvement claimed.',
                      'Rendered extraction contains the 23 data221 buildings, not roads or the complete city.',
                      'Existing synthetic facade and legacy display height retained.',
                      'No new asset license or permission grant. No publication or registration.']}
    (out/'run.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    rows=''.join('<tr><th>'+html.escape(v['id'])+'</th><td><img width="400" src="before-'+v['id']+'.png"></td><td><img width="400" src="after-'+v['id']+'.png"></td></tr>' for v in VIEWS)
    page='<!doctype html><meta charset="utf-8"><title>data221 af7335da topology review</title><style>body{font:16px system-ui;max-width:1000px;margin:auto}table{border-collapse:collapse}td,th{padding:8px}</style><h1>One editable building, unchanged exterior</h1><p>1,398 disconnected vertices → 235 exact-position vertices. 466 source faces retained. The images verify appearance preservation; this does not add surveyed detail. 23-building extraction, identical CPU Cycles lighting, cameras, 16 samples and seed 0.</p><table><tr><th>View</th><th>Before</th><th>After</th></tr>'+rows+'</table><p><a href="validation.json">Saved-city validation</a> · <a href="production.json">Topology measurements</a> · <a href="run.json">Code and input hashes</a></p>'
    (out/'review.html').write_text(page,encoding='utf8')
    print('Completed: '+str(out/'review.html'))


if __name__=='__main__': main()
