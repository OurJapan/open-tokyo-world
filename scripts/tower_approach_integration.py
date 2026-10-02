# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Review the immutable eight-tree delta on the PR47 west-path city candidate."""
import argparse
import math
from pathlib import Path
import shutil
import subprocess
import time

from tower_approach import read, write, digest, compare, make_html
from tower_approach_plan import check_plan, added_names

ROOT = Path(__file__).resolve().parents[1]
WEST_SHA = '2a6f63658722beecdb8af2158baed62c044f33a22084df0d227c70c67332ae5b'
DELTA_SHA = 'bd190345084c7e93cf82adec5134f184b4d1867fb93c860740eb930f556aeb58'
ASTRA_SHA = '4b2d6d0af6813e7748bf6890b608c217751945b55c88b733ba31adeac6188243'


def pinned(path, expected):
    if not path.is_file() or digest(path) != expected:
        raise ValueError('Pinned integration input differs: '+path.name)


def xy_separation(a, b):
    """Conservative minimum distance between two enclosing XY rectangles."""
    for box in (a,b):
        if any(len(box[k]) != 3 for k in ('minimum','maximum')) or not all(
                math.isfinite(v) for k in ('minimum','maximum') for v in box[k]):
            raise ValueError('Non-finite or malformed spatial bounds')
        if any(box['minimum'][k] > box['maximum'][k] for k in range(3)):
            raise ValueError('Reversed spatial bounds')
    gaps = [max(0,b['minimum'][k]-a['maximum'][k],a['minimum'][k]-b['maximum'][k]) for k in (0,1)]
    if not all(math.isfinite(v) for v in gaps):
        raise ValueError('Non-finite spatial bounds')
    return math.hypot(*gaps)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('input','delta','blender','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--astra-target',type=Path)
    p.add_argument('--delta-sha256',default=DELTA_SHA,help='Explicit pinned received/rebuilt delta digest')
    p.add_argument('--timeout',type=int,default=900)
    a = p.parse_args(); output = a.output.resolve()
    pinned(a.input,WEST_SHA); pinned(a.delta,a.delta_sha256)
    if a.astra_target: pinned(a.astra_target,ASTRA_SHA)
    if output.exists() or not output.is_relative_to(ROOT/'data/local'):
        raise ValueError('Use a new output directory within this worktree data/local/')
    plan = check_plan(read(ROOT/'areas/tokyo-tower/approach-trees-v1.json'))
    cameras = {'version':1,'views':list(plan['cameras']['views'])}
    west_cameras = read(ROOT/'areas/tokyo-tower/mori-plaza-west-path-cameras.json')
    cameras['views'] += [dict(v,label=v['id']) for v in west_cameras['views']
                         if v['id'] in ('west-path-walk','west-path-edge')]
    settings = {'blender_version':'4.5.1 LTS','device':'OPTIX','width':960,'height':540,'samples':16,'seed':0}
    output.mkdir(parents=True)
    shutil.copyfile(a.input,output/'before.blend')
    shutil.copyfile(a.delta,output/'approach-additions.blend')
    pinned(output/'before.blend',WEST_SHA); pinned(output/'approach-additions.blend',a.delta_sha256)
    job = {'output':str(output),'delta':str((output/'approach-additions.blend').resolve()),
           'plan':plan,'features':read(ROOT/'areas/tokyo-tower/mori-plaza-connection-accepted-features.json'),
           'cameras':cameras,'settings':settings}
    if a.astra_target: job['astra_target'] = str(a.astra_target.resolve())
    write(output/'job.json',job)
    summary = {'version':1,'ok':False,'code_base_commit':'234b163210ac19d61f33e86b6920b8b26f9d453a',
               'production_commit':'b92061b5ccc99b23198288891e8b0107f6ed227c',
               'input_sha256':WEST_SHA,'delta_sha256':a.delta_sha256,'jobs':{}, **settings}
    code = ['scripts/tower_approach_integration.py','scripts/tower_approach_integration_blender.py',
            'scripts/tower_approach_blender.py','scripts/tower_approach_plan.py','scripts/tower_approach.py',
            'scripts/blender_worker.py','scripts/component_contracts.py','scripts/city_catalog_blender.py',
            'scripts/tower_approach_shell_audit_blender.py',
            'areas/tokyo-tower/approach-trees-v1.json','areas/tokyo-tower/mori-plaza-west-path-cameras.json',
            'assets/procedural-components/provenance.json']
    summary['code_and_provenance_sha256'] = {n:digest(ROOT/n) for n in code}
    def command(phase,blend,worker,report=None):
        return [str(a.blender),'--factory-startup','--disable-autoexec','--background']+([str(blend)] if blend else [])+[
                '--threads','2','--python-exit-code','1','--python',str(ROOT/'scripts'/worker),
                '--','--job',str(output/'job.json'),'--phase',phase,'--report',str(output/((report or phase)+'.json'))]
    def run(phase,blend,worker):
        print('START',phase,flush=True); started = time.monotonic()
        with (output/(phase+'.log')).open('w',encoding='utf-8') as log:
            result = subprocess.run(command(phase,blend,worker),stdout=log,stderr=subprocess.STDOUT,timeout=a.timeout)
        summary['jobs'][phase] = {'exit_code':result.returncode,'seconds':round(time.monotonic()-started,3)}
        if result.returncode or not read(output/(phase+'.json')).get('ok'):
            raise ValueError('Integration worker failed: '+phase)
        print('PASS',phase,summary['jobs'][phase]['seconds'],flush=True)
    try:
        run('append',output/'before.blend','tower_approach_integration_blender.py')
        for phase,blend in [('validate-before',output/'before.blend'),('validate-after',output/'after.blend'),
                            ('validate-additions',None)]:
            run(phase,blend,'tower_approach_blender.py')
        before,after = (read(output/('validate-'+stage+'.json')) for stage in ('before','after'))
        summary['preservation'] = compare(before,after,added_names(plan))
        if before['warnings'] != after['warnings']:
            raise ValueError('Inherited warning set changed')
        summary['placement'] = after['placement']; summary['inherited_warnings'] = len(after['warnings'])
        phase = 'shell-surface-audit'; started = time.monotonic()
        shell_command = [str(a.blender),'--factory-startup','--disable-autoexec','--background',str(output/'after.blend'),
                         '--threads','2','--python-exit-code','1','--python',str(ROOT/'scripts/tower_approach_shell_audit_blender.py'),
                         '--','--plan',str(ROOT/'areas/tokyo-tower/approach-trees-v1.json'),
                         '--output',str(output/(phase+'.json')),'--require-clear']
        print('START',phase,flush=True)
        with (output/(phase+'.log')).open('w',encoding='utf-8') as log:
            audit = subprocess.run(shell_command,stdout=log,stderr=subprocess.STDOUT,timeout=a.timeout)
        summary['jobs'][phase] = {'exit_code':audit.returncode,'seconds':round(time.monotonic()-started,3)}
        summary['shell_surface_audit'] = read(output/(phase+'.json'))
        if audit.returncode or not summary['shell_surface_audit']['ok']:
            raise ValueError('Saved candidate shell/surface audit failed')
        print('PASS',phase,summary['jobs'][phase]['seconds'],flush=True)
        west_objects = ('asphalt 15s road detail','gutter 15s road detail','pavement_0 unified road',
                        'OTW Mori west path / seam fill')
        summary['west_path_objects_unchanged'] = {n:before['objects'][n] == after['objects'][n] for n in west_objects}
        if not all(summary['west_path_objects_unchanged'].values()):
            raise ValueError('West path preservation failed')
        saved_hash = digest(output/'after.blend')
        with (output/'duplicate-refusal.log').open('w',encoding='utf-8') as log:
            refused = subprocess.run(command('append',output/'after.blend','tower_approach_integration_blender.py',
                                             report='duplicate-refusal-worker'),
                                     stdout=log,stderr=subprocess.STDOUT,timeout=a.timeout)
        refusal = read(output/'duplicate-refusal-worker.json')
        if not refused.returncode or 'refusing duplicate additions' not in refusal.get('error',''):
            raise ValueError('Duplicate guard failed')
        if digest(output/'after.blend') != saved_hash:
            raise ValueError('Duplicate attempt changed the saved candidate')
        write(output/'duplicate-refusal.json',{'ok':True,'exit_code':refused.returncode,'error':refusal['error'],
                                              'candidate_unchanged':True})
        summary['duplicate_refusal'] = read(output/'duplicate-refusal.json')
        for phase,blend in [('render-before',output/'before.blend'),('render-after',output/'after.blend')]:
            run(phase,blend,'tower_approach_blender.py')
        if a.astra_target:
            run('inspect-astra',None,'tower_approach_integration_blender.py')
            # Complete enclosing bounds include crowns, not only bed centers.
            append = read(output/'append.json')
            astra = read(output/'inspect-astra.json')
            distance = xy_separation(append['world_bounds'],astra['world_bounds'])
            if distance <= 0: raise ValueError('Astra and tree bounding boxes overlap')
            summary['astra_scope_check'] = {**astra,'target_sha256':ASTRA_SHA,'minimum_xy_distance_m':distance,
                                           'file_scope_disjoint':True,'combined_astra_city_not_generated':True}
        summary['outputs'] = {n:{'bytes':(output/n).stat().st_size,'sha256':digest(output/n)}
                              for n in ('after.blend','approach-additions.blend')}
        pinned(a.input,WEST_SHA); pinned(a.delta,a.delta_sha256)
        if a.astra_target: pinned(a.astra_target,ASTRA_SHA)
        if digest(output/'after.blend') != saved_hash:
            raise ValueError('Read-only inspection changed the saved candidate')
        summary['original_inputs_unchanged'] = True
        summary['render'] = {s:read(output/(s+'.json')) for s in ('render-before','render-after')}
        summary['ok'] = True
        make_html(output,{'cameras':cameras},summary)
    finally:
        write(output/'run.json',summary)
    print('INTEGRATION_OK',output/'review.html',flush=True)


if __name__ == '__main__':
    main()
