"""Run isolated Blender review jobs. Python standard library only."""
import argparse
import hashlib
import html
import json
import math
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / 'scripts' / 'blender_worker.py'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_cameras(config):
    require(config.get('version') == 1, 'Unsupported camera version')
    views = config.get('views', [])
    require(bool(views), 'At least one camera is required')
    ids = set()
    for view in views:
        name = view['id']
        require(re.fullmatch(r'[a-z0-9][a-z0-9-]*', name) and name not in ids, 'Invalid or duplicate camera ID')
        ids.add(name)
        m = view['matrix_world']
        require(len(m) == 4 and all(len(r) == 4 for r in m), 'Expected 4x4 camera matrix')
        numbers = [x for row in m for x in row] + [view[k] for k in ('lens_mm', 'sensor_width_mm', 'sensor_height_mm', 'clip_start', 'clip_end', 'shift_x', 'shift_y')]
        require(all(isinstance(x, (int, float)) and math.isfinite(x) for x in numbers), 'Non-finite camera')
        require(m[3] == [0, 0, 0, 1], 'Non-affine camera matrix')
        # Require a rigid, right-handed camera transform, not a scaled/singular matrix.
        cols = [[m[r][c] for r in range(3)] for c in range(3)]
        for i in range(3):
            for j in range(3):
                require(abs(sum(a*b for a,b in zip(cols[i],cols[j])) - (1 if i==j else 0)) < 1e-4, 'Non-rigid camera matrix')
        det = (m[0][0]*(m[1][1]*m[2][2]-m[1][2]*m[2][1]) - m[0][1]*(m[1][0]*m[2][2]-m[1][2]*m[2][0]) + m[0][2]*(m[1][0]*m[2][1]-m[1][1]*m[2][0]))
        require(det > 0.999, 'Reflected camera matrix')
        require(0 < view['clip_start'] < view['clip_end'], 'Invalid clipping range')
        require(view['lens_mm'] > 0 and view['sensor_width_mm'] > 0 and view['sensor_height_mm'] > 0, 'Invalid lens/sensor')
        require(view['sensor_fit'] in ('AUTO','HORIZONTAL','VERTICAL'), 'Invalid sensor fit')


def validate_features(config):
    require(config.get('version') == 1, 'Unsupported feature mapping version')
    used, ids = set(), set()
    for feature in config['features']:
        require(feature['id'] not in ids and feature['id'].startswith('otw:'), 'Invalid or duplicate feature ID')
        ids.add(feature['id'])
        require(bool(feature['collections']), 'Empty feature mapping')
        for name in feature['collections']:
            require(name not in used, 'Collection mapped twice')
            used.add(name)


def validate_patch(patch):
    require(patch.get('version') == 1, 'Unsupported patch version')
    require(patch.get('purpose') in ('fixture-test', 'reviewed-change'), 'Patch must declare purpose')
    require(bool(patch.get('reason')) and isinstance(patch.get('source_refs'), list), 'Patch evidence fields missing')
    ops = patch.get('operations')
    require(isinstance(ops, list) and len(ops) > 0, 'Empty patch')
    for op in ops:
        if op['op'] == 'translate_object':
            require(set(op) == {'op','feature_id','object','translation_m'}, 'Unexpected patch keys')
            v = op['translation_m']
            require(len(v) == 3 and all(isinstance(x,(int,float)) and math.isfinite(x) and abs(x) <= 100 for x in v), 'Invalid translation')
        elif op['op'] in ('mori_crown_material_v1','mori_facade_v2'):
            require(set(op) == {'op','feature_id','object','expected_mesh_sha256','expected_material_sha256'}, 'Unexpected material patch keys')
            targets = {'Mori continuous pearl glass / pearl grey coated glass'}
            if op['op']=='mori_facade_v2':
                targets |= {'Mori continuous pearl glass / '+k for k in ('recessed spandrel','slender mullion','sealing joint')}
            require(op['feature_id']=='otw:jp:tokyo:minato:azabudai-mori-jp' and op['object'] in targets, 'Wrong facade material target')
            for key in ('expected_mesh_sha256','expected_material_sha256'):
                require(re.fullmatch('[0-9a-f]{64}',op[key]) is not None, 'Material patch requires hashes')
            require(bool(patch['source_refs']), 'Material hypotheses require evidence')
        elif op['op'] in ('mori_shape_v1','mori_crown_v2'):
            require(set(op) == {'op','feature_id','object','expected_mesh_sha256'}, 'Unexpected shape patch keys')
            require(op['feature_id']=='otw:jp:tokyo:minato:azabudai-mori-jp', 'Wrong shape feature')
            require(re.fullmatch('[0-9a-f]{64}',op['expected_mesh_sha256']) is not None, 'Shape patch requires mesh hash')
            require(bool(patch['source_refs']), 'Shape hypotheses require evidence')
        else:
            raise ValueError('Unsupported patch operation')
        require(bool(op['object']) and op['feature_id'].startswith('otw:'), 'Missing patch target')
    if patch['purpose'] == 'reviewed-change':
        require(bool(patch['source_refs']), 'Real changes require source references')


def compare_reports(before, after, allowed):
    require(before['ok'] and after['ok'], 'Blender validation failed')
    require(set(before['objects']) == set(after['objects']), 'Unexpected object creation/deletion')
    changed = [n for n in before['objects'] if before['objects'][n] != after['objects'][n]]
    require(set(changed) <= set(allowed), 'Unexpected changed objects: ' + ', '.join(sorted(set(changed)-set(allowed))))
    require(before['assets'] == after['assets'], 'Unexpected asset change')
    return changed


def run_job(blender, phase, output, job, source=None, timeout=900):
    report = output / (phase + '.json')
    command = [str(blender), '--factory-startup', '--disable-autoexec', '--background']
    if source:
        command.append(str(source))
    command += ['--python-exit-code', '1', '--python', str(WORKER), '--', '--job', str(job), '--phase', phase, '--report', str(report)]
    started = time.monotonic()
    with (output / (phase + '.log')).open('w', encoding='utf-8') as log:
        completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, check=False)
    require(completed.returncode == 0, f'{phase}: Blender failed ({completed.returncode}); see local log')
    require(report.is_file(), f'{phase}: missing report')
    result = read_json(report)
    require(result.get('ok') is True, f'{phase}: validation failed; see report')
    return {'seconds': round(time.monotonic()-started, 3), 'report_sha256': digest(report)}


def make_html(output, cameras, summary):
    rows = []
    for v in cameras['views']:
        name = v['id']
        rows.append(f'<section><h2>{html.escape(name)}</h2><div><figure><img src="before-{name}.png"><figcaption>Before</figcaption></figure><figure><img src="after-{name}.png"><figcaption>After</figcaption></figure></div></section>')
    page = '<!doctype html><meta charset="utf-8"><title>OurJapan review</title><style>body{font:16px system-ui;max-width:1400px;margin:32px auto;padding:16px;background:#16202b;color:#eee}section div{display:flex}figure{margin:8px;width:50%}img{width:100%}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>OurJapan â€” review evidence</h1><p>Technical comparison. Human review of real-world accuracy is still required.</p>'
    page += ''.join(rows) + '<h2>Run</h2><pre>' + html.escape(json.dumps(summary,ensure_ascii=False,indent=2)) + '</pre>'
    (output/'review.html').write_text(page,encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--blender', required=True, type=Path)
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--lock', required=True, type=Path)
    p.add_argument('--cameras', required=True, type=Path)
    p.add_argument('--features', required=True, type=Path)
    p.add_argument('--patch', type=Path)
    p.add_argument('--output', required=True, type=Path, help='Must not already exist')
    p.add_argument('--device', choices=['CPU','OPTIX'], default='CPU')
    p.add_argument('--width', type=int, default=640)
    p.add_argument('--height', type=int, default=360)
    p.add_argument('--samples', type=int, default=8)
    p.add_argument('--timeout', type=int, default=900, help='Seconds per Blender phase')
    a = p.parse_args()
    source, output = a.input.resolve(), a.output.resolve()
    require(not output.exists(), 'Refusing to reuse an output directory')
    require(0 < a.width <= 4096 and 0 < a.height <= 4096 and 0 < a.samples <= 1024 and a.timeout > 0, 'Invalid resource settings')
    lock, cameras, features = read_json(a.lock), read_json(a.cameras), read_json(a.features)
    validate_cameras(cameras); validate_features(features)
    patch = read_json(a.patch) if a.patch else None
    if patch: validate_patch(patch)
    require(source.stat().st_size == lock['bytes'], 'Input size does not match lock')
    input_hash = digest(source)
    require(input_hash == lock['sha256'], 'Input hash does not match lock')
    if features.get('legacy_empty_objects'):
        require(features.get('waiver_input_sha256') == input_hash, 'Legacy waivers do not match this input')
        require(all(isinstance(reason,str) and reason.strip() for reason in features['legacy_empty_objects'].values()), 'Waivers need reasons')
    output.mkdir(parents=True)
    summary = {'version':1,'ok':False,'mode':'patch-review' if patch else 'baseline-capture','input_sha256':input_hash,'blender_version':lock['blender_version'],'cameras_sha256':digest(a.cameras),'features_sha256':digest(a.features),'patch_sha256':digest(a.patch) if patch else None,'platform':platform.platform(),'device':a.device,'width':a.width,'height':a.height,'samples':a.samples,'seed':0,'jobs':{},'limitations':['Human visual approval is required.','Peak RAM/VRAM and physical accuracy are not measured.','Timing is one run, not a warmed-up median.','Dependency audit and fingerprints cover documented initial checks, not all Blender features.']}
    try:
        revision = subprocess.run(['git','-c',f'safe.directory={ROOT.as_posix()}','-C',str(ROOT),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
        summary['code_base_commit'] = revision
        summary['code_files'] = {f.relative_to(ROOT).as_posix():digest(f) for f in (Path(__file__),WORKER,ROOT/'scripts/mori_shape.py',ROOT/'scripts/mori_crown_v2.py',ROOT/'scripts/mori_crown_material.py',ROOT/'scripts/mori_facade_v2.py')}
        job = {'output':str(output),'cameras':cameras,'features':features,'patch':patch,'settings':{k:summary[k] for k in ('blender_version','device','width','height','samples','seed')}}
        job_path = output/'job.json'; write_json(job_path,job)
        for phase, blend in [('prepare',source),('validate-before',output/'before.blend'),('validate-after',output/'after.blend')]:
            summary['jobs'][phase] = run_job(a.blender,phase,output,job_path,blend,a.timeout)
        before, after = read_json(output/'validate-before.json'), read_json(output/'validate-after.json')
        allowed = [op['object'] for op in patch['operations']] if patch else []
        summary['changed_objects'] = compare_reports(before,after,allowed)
        if patch: require(bool(summary['changed_objects']), 'Patch produced no recorded change')
        for phase in ('render-before','render-after'):
            summary['jobs'][phase] = run_job(a.blender,phase,output,job_path,output/(phase.removeprefix('render-')+'.blend'),a.timeout)
        summary['output_blends'] = {n:digest(output/n) for n in ('before.blend','after.blend')}
        require(digest(source) == input_hash, 'Source changed during review')
        summary['ok'] = True
        make_html(output,cameras,summary)
    except Exception as error:
        summary['error'] = str(error)
        raise
    finally:
        write_json(output/'run.json',summary)
    print(f'Review complete: {output / "review.html"}')


if __name__ == '__main__':
    main()
