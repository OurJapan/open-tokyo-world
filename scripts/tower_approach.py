# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Build and review an isolated eight-tree candidate from the accepted city input."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import shutil
import subprocess
import time

from tower_approach_plan import check_plan, added_names, source_names, COLLECTION

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n',encoding='utf-8')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def compare(before, after, names):
    b, a = before['objects'], after['objects']
    if set(a)-set(b) != names or set(b)-set(a):
        raise ValueError('Unexpected added/removed objects')
    changed = []; suppressed = []
    for name in b:
        if a[name] == b[name]:
            continue
        adjusted = dict(a[name])
        if name in source_names() and a[name].get('hide_viewport') is True and b[name].get('hide_viewport') is False:
            adjusted['hide_viewport'] = False
            if adjusted == b[name]:
                suppressed.append(name)
                continue
        changed.append(name)
    if changed:
        raise ValueError('Existing objects changed: '+', '.join(changed))
    if before['assets'] != after['assets'] or before['scene_state'] != after['scene_state']:
        raise ValueError('Existing assets or scene state changed')
    if set(after['collections'])-set(before['collections']) != {COLLECTION}:
        raise ValueError('Unexpected collection addition')
    for name, row in before['collections'].items():
        if after['collections'].get(name) != row:
            raise ValueError('Existing collection changed: '+name)
    return {'ok':True,'unchanged_existing_objects':len(b)-len(suppressed),'added_objects':len(names),
            'existing_geometry_material_transform_preserved':len(b),
            'original_source_viewport_suppression':sorted(suppressed),
            'unchanged_existing_collections':len(before['collections']),
            'unchanged_assets':len(before['assets']), 'existing_object_changes':[]}


def make_html(output, plan, summary):
    rows = ''.join(f'<section><h2>{html.escape(v["label"])}</h2><div class="pair">'
                   f'<figure><figcaption>Before</figcaption><img src="before-{v["id"]}.png"></figure>'
                   f'<figure><figcaption>After</figcaption><img src="after-{v["id"]}.png"></figure></div></section>'
                   for v in plan['cameras']['views'])
    page = '<!doctype html><html lang="ja"><meta charset="utf-8"><title>東京タワー北東アプローチ並木</title>'
    page += '<style>body{font:16px system-ui;background:#eef2ef;color:#183327;margin:30px}h1{font-size:26px}.pair{display:flex;gap:12px}figure{margin:0;flex:1}img{width:100%}section{margin:30px 0}figcaption{padding:6px}</style>'
    page += '<h1>東京タワー北東アプローチ：8本の並木と植樹枡</h1><p>旧モデルの推定配置を保持し、根元・縁を既存モデルの高さに合わせた制作候補です。現地測量・現況植生の復元ではありません。</p>'
    page += f'<p>Cycles / {summary["device"]} / {summary["width"]}×{summary["height"]} / {summary["samples"]} samples / seed 0。同じ入力の照明・地形・道路・建物で比較。</p>'
    page += rows + '<p>市街地画像・blendはローカル確認用。共通city登録・元モデル・通常Blender設定は変更していません。</p></html>'
    (output / 'review.html').write_text(page,encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True); parser.add_argument('--blender',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--plan',type=Path,default=ROOT/'areas/tokyo-tower/approach-trees-v1.json')
    parser.add_argument('--device',choices=['CPU','OPTIX'],default='CPU')
    parser.add_argument('--width',type=int,default=960); parser.add_argument('--height',type=int,default=540)
    parser.add_argument('--samples',type=int,default=16); parser.add_argument('--timeout',type=int,default=1200)
    args = parser.parse_args(); source = args.input.resolve(); output = args.output.resolve()
    plan = check_plan(read(args.plan)); lock = plan['input']
    if (not source.is_file() or source.stat().st_size != lock['bytes'] or digest(source) != lock['sha256']):
        raise ValueError('Use the exact accepted city scene; registration is not modified')
    if output.exists() or not output.is_relative_to(ROOT/'data/local'):
        raise ValueError('Use a new output directory inside this worktree data/local/')
    if min(args.width,args.height,args.samples) <= 0:
        raise ValueError('Positive render settings required')
    summary = {'version':1,'ok':False,'input_sha256':lock['sha256'],'input_bytes':lock['bytes'],
               'base_commit':plan['base_commit'],'plan_sha256':digest(args.plan),'device':args.device,
               'width':args.width,'height':args.height,'samples':args.samples,'seed':0,'jobs':{},
               'limits':['Human visual and adoption review pending.','Not a surveyed planting or terrain reconstruction.',
                         'No city redistribution, push, PR, merge or shared registration update.',
                         'Timing is one local run, not a warmed-up performance median.']}
    code = ['scripts/tower_approach.py','scripts/tower_approach_plan.py','scripts/tower_approach_blender.py',
            'scripts/blender_worker.py','scripts/component_contracts.py','scripts/city_catalog_blender.py',
            'assets/procedural-components/provenance.json']
    summary['code_and_provenance_sha256'] = {p:digest(ROOT/p) for p in code}
    output.mkdir(parents=True)
    features = read(ROOT/'areas/tokyo-tower/mori-plaza-connection-accepted-features.json')
    job = {'output':str(output),'plan':plan,'cameras':plan['cameras'],'features':features,
           'settings':{'blender_version':'4.5.1 LTS','device':args.device,'width':args.width,
                       'height':args.height,'samples':args.samples,'seed':0}}
    write(output/'job.json',job)
    try:
        shutil.copyfile(source,output/'before.blend')
        if digest(output/'before.blend') != lock['sha256']:
            raise ValueError('Baseline copy hash differs')
        for phase, blend in [('build',output/'before.blend'),('validate-before',output/'before.blend'),
                             ('validate-after',output/'after.blend'),('validate-additions',None),('render-before',output/'before.blend'),
                             ('render-after',output/'after.blend')]:
            command = [str(args.blender),'--factory-startup','--disable-autoexec','--background'] + ([str(blend)] if blend else []) + [
                       '--threads','4','--python-exit-code','1','--python',str(ROOT/'scripts/tower_approach_blender.py'),
                       '--','--job',str(output/'job.json'),'--phase',phase,'--report',str(output/(phase+'.json'))]
            started = time.monotonic(); print('START',phase,flush=True)
            with (output/(phase+'.log')).open('w',encoding='utf-8') as log:
                process = subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=args.timeout)
            summary['jobs'][phase] = {'exit_code':process.returncode,'seconds':round(time.monotonic()-started,3)}
            if process.returncode or not read(output/(phase+'.json')).get('ok'):
                raise ValueError('Worker failed: '+phase+'; see local log')
            if phase == 'validate-after':
                summary['preservation'] = compare(read(output/'validate-before.json'),read(output/'validate-after.json'),added_names(plan))
            print('PASS',phase,summary['jobs'][phase]['seconds'],flush=True)
        summary['build'] = read(output/'build.json')
        summary['delta_validation'] = read(output/'validate-additions.json')
        summary['placement'] = read(output/'validate-after.json')['placement']
        summary['render'] = {p:read(output/(p+'.json')) for p in ('render-before','render-after')}
        summary['outputs'] = {p:{'bytes':(output/p).stat().st_size,'sha256':digest(output/p)}
                              for p in ('after.blend','approach-additions.blend')}
        summary['original_input_unchanged'] = digest(source) == lock['sha256']
        if not summary['original_input_unchanged']:
            raise ValueError('Original source changed during review')
        summary['ok'] = True; make_html(output,plan,summary)
    finally:
        write(output/'run.json',summary)
    print('REVIEW_OK',output/'review.html',flush=True)


if __name__ == '__main__':
    main()
