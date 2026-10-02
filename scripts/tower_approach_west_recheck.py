# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Replay the accepted west-path audit on the saved tree integration, read-only."""
import argparse
from pathlib import Path
import subprocess
import time
import numpy as np

from tower_approach import read,write,digest

ROOT = Path(__file__).resolve().parents[1]
WEST_BEFORE_SHA = 'eae18eb05bd30f60a377983b8e7b9ed6add9d0979d9063855068798f6a473c12'
WEST_AFTER_SHA = '2a6f63658722beecdb8af2158baed62c044f33a22084df0d227c70c67332ae5b'
PLAN_SHA = '6bb6165ee58f9827162256023a7f5b8ebd514b66f05307b8bf01606df0a0127c'


def arrays_equal(reference,candidate):
    with np.load(reference,allow_pickle=False) as b,np.load(candidate,allow_pickle=False) as a:
        if set(a.files) != set(b.files): raise ValueError('West array fields changed')
        for key in b.files:
            if a[key].dtype != b[key].dtype or a[key].shape != b[key].shape or not np.array_equal(a[key],b[key]):
                raise ValueError('West saved array changed: '+key)
        return sorted(b.files)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('blender','before','after','reference','seam-plan','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--after-sha256',required=True)
    a = p.parse_args(); output = a.output.resolve()
    reference = read(a.reference/'run.json')
    if not reference.get('ok') or reference.get('scene_sha256') != {'before':WEST_BEFORE_SHA,'after':WEST_AFTER_SHA}:
        raise ValueError('Use the accepted PR47 saved-scene audit')
    for path,pin in [(a.before,WEST_BEFORE_SHA),(a.after,a.after_sha256),(a.seam_plan,PLAN_SHA)]:
        if digest(path) != pin: raise ValueError('West replay input pin differs: '+path.name)
    if output.exists() or not output.is_relative_to(ROOT/'data/local'):
        raise ValueError('Use a new local replay output directory')
    output.mkdir(parents=True)
    files = [f'{stage}-{i}.npz' for stage in ('before','after') for i in range(3)]
    files += ['before-rays.json','after-rays.json','boundary-selection.json','saved-patch-audit.json','seam-mesh.json']
    pins = {n:digest(a.reference/n) for n in files}
    started = time.monotonic()
    command = [str(a.blender),'--factory-startup','--disable-autoexec','--background','--threads','2',
               '--python-exit-code','1','--python',str(ROOT/'scripts/validate_mori_plaza_west_path.py'),
               '--','--worker','--before',str(a.before.resolve()),'--after',str(a.after.resolve()),
               '--seam-plan',str(a.seam_plan.resolve()),'--output',str(output)]
    result = {'ok':False,'method':'Fresh Blender export; exact arrays and ray/state replay against accepted PR47 audit',
              'blender_version':'4.5.1 LTS','inputs':{'before':WEST_BEFORE_SHA,'after':a.after_sha256,'seam_plan':PLAN_SHA},
              'code_sha256':{'scripts/tower_approach_west_recheck.py':digest(Path(__file__)),
                             'scripts/validate_mori_plaza_west_path.py':digest(ROOT/'scripts/validate_mori_plaza_west_path.py')}}
    try:
        with (output/'blender.log').open('w',encoding='utf8') as log:
            process = subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=900)
        result['export_exit_code'] = process.returncode
        if process.returncode or not read(output/'export.json').get('ok'):
            raise ValueError('Saved west-path replay export failed')
        result['arrays'] = {n:arrays_equal(a.reference/n,output/n) for n in files if n.endswith('.npz')}
        for name in files:
            if name.endswith('.json') and read(a.reference/name) != read(output/name):
                raise ValueError('West saved rays or patch/seam state changed: '+name)
        result['identical_rays_per_stage'] = len(read(output/'after-rays.json'))
        result['seam_and_patch_state_unchanged'] = True
        result['reference_report_sha256'] = digest(a.reference/'run.json')
        # The accepted GEOS result can be reused because every saved array,
        # probe and infill state consumed by that result is identical.
        result['accepted_metrics_reused_on_identical_geometry'] = reference['result']
        if pins != {n:digest(a.reference/n) for n in files}:
            raise ValueError('Reference audit changed during read-only replay')
        if digest(a.before) != WEST_BEFORE_SHA or digest(a.after) != a.after_sha256 or digest(a.seam_plan) != PLAN_SHA:
            raise ValueError('Saved scene or seam plan changed during replay')
        result['inputs_and_reference_unchanged'] = True; result['ok'] = True
    finally:
        result['seconds'] = round(time.monotonic()-started,3); write(output/'run.json',result)
    print('WEST_REPLAY_OK',result['identical_rays_per_stage'],output/'run.json')


if __name__ == '__main__': main()
