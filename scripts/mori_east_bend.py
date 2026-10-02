# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Local-only production and matched neighborhood review of one footway bend."""
import argparse
import json
from pathlib import Path
import subprocess
import time
from tower_approach import read, write, digest
import mori_plaza_east_bend_v1 as bend

ROOT = Path(__file__).resolve().parents[1]


def compare(before, after):
    if not before['ok'] or not after['ok']:
        raise ValueError('Scene validation failed')
    old, new = before['objects'], after['objects']
    if set(new)-set(old) != {bend.SEAM} or set(old)-set(new):
        raise ValueError('Unexpected object additions/removals')
    for name, previous in old.items():
        actual = dict(new[name])
        if name in bend.ROADS:
            for key in ('mesh', 'smooth_sha256'):
                actual[key] = previous[key]
        if actual != previous:
            raise ValueError('Unexpected object change: '+name)
    for key in ('assets', 'scene_state', 'text_hashes', 'warnings'):
        if before[key] != after[key]:
            raise ValueError('Protected state differs: '+key)
    props = dict(after['scene_properties']); props.pop(bend.AUDIT_KEY, None)
    if props != before['scene_properties']:
        raise ValueError('Existing scene properties changed')
    collections = json.loads(json.dumps(after['collections']))
    collections['Mori JP podium']['objects'].remove(bend.SEAM)
    if collections != before['collections']:
        raise ValueError('Existing collections changed')
    return {'ok': True, 'unchanged_objects': len(old)-3, 'changed_road_objects': sorted(bend.ROADS),
            'added_objects': [bend.SEAM], 'unchanged_assets': len(before['assets']),
            'unchanged_collections_except_seam_membership': len(before['collections']),
            'unchanged_warning_count': len(before['warnings']), 'embedded_texts_unchanged': len(before['text_hashes'])}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('input', 'blender', 'output', 'plan', 'road-inputs'):
        p.add_argument('--'+key, type=Path, required=True)
    p.add_argument('--device', choices=('CPU', 'OPTIX'), default='OPTIX')
    p.add_argument('--phase', choices=('build-check', 'render', 'duplicate'), default='build-check')
    a = p.parse_args(); out = a.output.resolve()
    if not out.is_relative_to(ROOT/'data/local'):
        raise ValueError('Output must be in this worktree data/local')
    if digest(a.input) != bend.INPUT_SHA256:
        raise ValueError('Pinned input differs')
    patch_file = ROOT/'patches/mori-plaza-east-bend-v1.json'
    patch = read(patch_file)
    if digest(a.plan) != patch['plan_sha256'] or set(patch['road_mesh_sha256']) != bend.ROADS:
        raise ValueError('Pinned patch/plan differs')
    if (patch['input_sha256'] != bend.INPUT_SHA256 or tuple(patch['center_uv_m']) != bend.CENTER or
            tuple(patch['core_half_size_m']) != bend.CORE or tuple(patch['outer_half_size_m']) != bend.OUTER or
            patch['top_z_m'] != bend.TOP_Z):
        raise ValueError('Declared geometry differs from the bounded implementation')
    if a.phase == 'build-check':
        out.mkdir(parents=True, exist_ok=False)
        job = {'input':str(a.input.resolve()), 'output':str(out), 'plan':str(a.plan.resolve()),
               'road_inputs':str(a.road_inputs.resolve()), 'patch':patch,
               'features':read(ROOT/'areas/tokyo-tower/mori-plaza-connection-accepted-features.json'),
               'settings':{'blender_version':'4.5.1 LTS','device':a.device,'width':960,'height':540,'samples':16,'seed':0}}
        write(out/'job.json', job)
        summary = {'ok': False, 'input_sha256':bend.INPUT_SHA256, 'jobs':{},
                   'base_commit':'102ad0a41a84b5336795bb8d5b2aeb5e8c81eb39', 'patch_sha256':digest(patch_file)}
        phases = [('build', a.input.resolve()), ('validate-after', out/'after.blend')]
    else:
        job = read(out/'job.json'); summary = read(out/'run.json')
        if job['input'] != str(a.input.resolve()) or job['patch'] != patch or job['plan'] != str(a.plan.resolve()):
            raise ValueError('Resume inputs differ')
        phases = [('duplicate', out/'after.blend')] if a.phase == 'duplicate' else [
            ('render-before', a.input.resolve()), ('render-after', out/'after.blend')]
    summary['ok'] = False
    try:
        for phase, blend in phases:
            if (out/(phase+'.json')).exists():
                raise ValueError('Phase output exists; preserve completed results')
            cmd = [str(a.blender.resolve()), '--factory-startup', '--disable-autoexec', '--background', str(blend),
                   '--threads', '2', '--python-exit-code', '1', '--python', str(ROOT/'scripts/mori_east_bend_blender.py'),
                   '--', '--job', str(out/'job.json'), '--phase', phase, '--report', str(out/(phase+'.json'))]
            start = time.monotonic(); print('START', phase, flush=True)
            with (out/(phase+'.log')).open('w', encoding='utf-8') as log:
                process = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=1200)
            summary['jobs'][phase] = {'exit_code':process.returncode, 'seconds':round(time.monotonic()-start,3)}
            if process.returncode or not read(out/(phase+'.json'))['ok']:
                raise ValueError('Failed '+phase+'; inspect saved log')
            print('PASS',phase,flush=True)
        summary['preservation'] = compare(read(out/'validate-before.json'), read(out/'validate-after.json'))
        summary['after_sha256'] = digest(out/'after.blend')
        summary['input_unchanged'] = digest(a.input) == bend.INPUT_SHA256
        summary['ok'] = summary['input_unchanged']
        code = sorted(ROOT.glob('scripts/*east*bend*.py'))
        code += [ROOT/'scripts/mori_plaza_connection_v1.py', ROOT/'scripts/mori_plaza_outline_v1.py',
                 ROOT/'scripts/mori_plaza_landscape_v1.py', ROOT/'scripts/blender_worker.py',
                 ROOT/'scripts/tower_approach_blender.py', ROOT/'scripts/city_catalog_blender.py']
        summary['code_sha256'] = {f.relative_to(ROOT).as_posix():digest(f) for f in code}
    finally:
        write(out/'run.json', summary)
    print(json.dumps({'ok':summary['ok'],'report':str(out/'run.json')}))


if __name__ == '__main__':
    main()
