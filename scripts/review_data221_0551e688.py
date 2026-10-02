"""Local batch-0 edit; preserves previous building work and never registers/publishes."""
import argparse
import html
import json
from pathlib import Path
import subprocess
import time

import data221_0551e688_mesh as repair
from review_data221_af7335da import digest

ROOT = Path(__file__).resolve().parents[1]
VIEWS = [
    {'id':'south','center':[-438,326,11],'offset':[85,-110,65],'scale':70,'isolated':True},
    {'id':'north','center':[-438,326,11],'offset':[-90,100,70],'scale':70,'isolated':True},
    {'id':'roof','center':[-438,326,11],'offset':[10,-20,150],'scale':65,'isolated':True},
    {'id':'context','center':[-438,326,14],'offset':[100,-170,100],'scale':130,'isolated':False},
]
FILES = ['scripts/data221_0551e688_mesh.py','scripts/data221_0551e688_worker.py',
         'scripts/review_data221_0551e688.py','scripts/data221_af7335da_mesh.py',
         'scripts/data221_af7335da_worker.py','scripts/review_data221_af7335da.py',
         'scripts/validate_data221_af7335da_integration.py','scripts/blender_worker.py',
         'starter/plateau/tile.py','areas/tokyo-tower/mori-plaza-connection-accepted-features.json']


def compare_images(before, after):
    expected_ids = [view['id'] for view in VIEWS]
    if any([v['id'] for v in report['views']] != expected_ids for report in (before, after)):
        raise ValueError('Expected every review view exactly once and in order')
    if before['settings'] != after['settings']:
        raise ValueError('Render settings differ')
    comparison = []
    for a,b in zip(before['views'], after['views']):
        if a['pixels_sha256'] != b['pixels_sha256']:
            raise ValueError('Appearance changed: '+a['id'])
        comparison.append({'view':a['id'],'pixel_identical':True,'pixels_sha256':a['pixels_sha256']})
    return comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source, out = args.input.resolve(), args.output.resolve()
    if out.exists(): raise ValueError('Choose a new output directory')
    if out == source.parent or out in source.parents: raise ValueError('Output overlaps input')
    if digest(source) != repair.INPUT_SHA256: raise ValueError('Pinned predecessor city SHA-256 mismatch')
    from sys import path
    path.insert(0, str(ROOT/'starter/plateau'))
    import tile
    inputs = args.inputs.resolve()
    for name in ('data221.b3dm','tileset.json'):
        tile.verify(name, (inputs/name).read_bytes())
    out.mkdir(parents=True)
    code = {name:digest(ROOT/name) for name in FILES}
    head = subprocess.run(['git','-c','safe.directory='+ROOT.as_posix(),'rev-parse','HEAD'],
        cwd=ROOT, text=True, check=True, capture_output=True).stdout.strip()
    job = {'input':str(source),'input_sha256':repair.INPUT_SHA256,'inputs':str(inputs),
           'output':str(out),'views':VIEWS,'code_base_commit':head,'code_files':code}
    job_path = out/'job.json'; job_path.write_text(json.dumps(job,indent=2)+'\n',encoding='utf8')
    runs = {}
    for phase in ('build','validate','render-before','render-after','reopen-edit'):
        command = [str(args.blender.resolve()),'--background','--factory-startup','--disable-autoexec',
                   '--threads','2','--python-exit-code','1','--python',
                   str(ROOT/'scripts/data221_0551e688_worker.py'),'--','--job',str(job_path),'--phase',phase]
        started = time.monotonic()
        with (out/(phase+'.log')).open('w',encoding='utf8') as log:
            result = subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        runs[phase] = {'exit_code':result.returncode,'seconds':round(time.monotonic()-started,3)}
        if result.returncode: raise RuntimeError(phase+' failed; see '+str(out/(phase+'.log')))
        print(phase+': passed',flush=True)
    if digest(source) != repair.INPUT_SHA256: raise ValueError('Original city changed')
    for name in ('data221.b3dm','tileset.json'):
        tile.verify(name, (inputs/name).read_bytes())
    if any(digest(ROOT/name) != value for name,value in code.items()): raise ValueError('Code changed during run')
    before = json.loads((out/'render-before.json').read_text(encoding='utf8'))
    after = json.loads((out/'render-after.json').read_text(encoding='utf8'))
    comparison = compare_images(before, after)
    outputs = {name:digest(out/name) for name in ['after.blend','target.blend',
        'before-neighborhood.blend','after-neighborhood.blend','edit-neighborhood.blend']}
    report = {'ok':True,'feature':repair.FEATURE,'input_sha256':repair.INPUT_SHA256,'input_preserved':True,
        'code_base_commit':head,'code_files':code,'jobs':runs,'output_blends':outputs,
        'image_comparisons':comparison,'source_hashes':{name:tile.FILES[name][2] for name in ('data221.b3dm','tileset.json')},
        'limits':['Local candidate only; no registration, push, PR or merge.',
                  'Three isolated views and one data221-neighborhood view; no roads/full-city render.',
                  'Existing textures, synthetic material and legacy height retained; no real-world detail added.',
                  'Self-intersections and solid/physics suitability not certified.']}
    (out/'run.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    rows = ''.join('<tr><th>'+html.escape(v['id'])+'</th><td><img width="400" src="before-'+v['id']+'.png"></td><td><img width="400" src="after-'+v['id']+'.png"></td></tr>' for v in VIEWS)
    page = '<!doctype html><meta charset="utf-8"><title>data221 batch 0 topology review</title><style>body{font:16px system-ui;max-width:1000px;margin:auto}td,th{padding:8px}img{max-width:100%}</style><h1>One editable building; preserved appearance</h1><p>2,838 vertices → 475. All 946 triangles, UVs, materials and winding retained. Before/After decoded pixels match in all four views. The first three views isolate the target; context includes all 23 retained data221 features. These images do not establish real-world accuracy.</p><p><a href="edit-neighborhood.blend">Editable selected neighborhood</a> · <a href="after.blend">City candidate</a> · <a href="validation.json">Reopen validation</a> · <a href="production.json">Measurements</a> · <a href="run.json">Hashes</a></p><table><tr><th>View</th><th>Before</th><th>After</th></tr>'+rows+'</table>'
    (out/'review.html').write_text(page,encoding='utf8')
    print('Completed: '+str(out/'review.html'))


if __name__ == '__main__': main()
