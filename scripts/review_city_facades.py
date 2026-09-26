# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Create a separate, pinned city facade candidate and compare it with the original."""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review import ROOT, digest, make_html, read_json, require, validate_cameras, write_json

CONFIG = ROOT / 'manifests/city-facades-v1.json'
CAMERAS = ROOT / 'areas/tokyo-tower/city-facades-v1-cameras.json'


def compare(before, after, config):
    require(before['ok'] and after['ok'], 'Scene validation failed')
    require(before['objects'].keys() == after['objects'].keys(), 'Object set changed')
    require(before['counts'] == after['counts'], 'Geometry counts changed')
    targets = config['targets']
    changed = []
    for name, old in before['objects'].items():
        new = after['objects'][name]
        if name in targets:
            require(old['mesh'] == targets[name]['mesh'] and old['materials'] == [targets[name]['material']], 'Pinned target differs: ' + name)
            require({k: v for k, v in old.items() if k != 'materials'} == {k: v for k, v in new.items() if k != 'materials'},
                    'Change outside material scope: ' + name)
            require(len(new['materials']) == 1 and new['materials'] != old['materials'], 'Expected material change missing: ' + name)
            changed.append(name)
        else:
            require(old == new, 'Unexpected object change: ' + name)
    require(set(changed) == set(targets), 'Missing target objects')
    removed = config['removed_image']
    matched = [a for a in before['assets'] if a == removed]
    require(len(matched) == 1, 'Pinned atlas asset differs')
    require([a for a in before['assets'] if a != removed] == after['assets'], 'Unexpected asset change')
    return sorted(changed)


def run_phase(blender, phase, output, source, timeout):
    report = output / (phase + '.json')
    command = [str(blender), '--factory-startup', '--disable-autoexec', '--background', str(source),
               '--python-exit-code', '1', '--python', str(Path(__file__).resolve()), '--', '--worker',
               '--job', str(output / 'job.json'), '--phase', phase, '--report', str(report)]
    start = time.monotonic()
    with (output / (phase + '.log')).open('w', encoding='utf8') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, check=False)
    require(result.returncode == 0 and report.is_file(), phase + ': Blender failed; see local log')
    require(read_json(report).get('ok') is True, phase + ': validation failed')
    return {'seconds': round(time.monotonic() - start, 3), 'report_sha256': digest(report)}


def worker():
    import bpy
    import city_facades
    from blender_worker import render
    p = argparse.ArgumentParser()
    p.add_argument('--worker', action='store_true'); p.add_argument('--job', required=True)
    p.add_argument('--phase', required=True); p.add_argument('--report', required=True)
    a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
    job = read_json(a.job)
    result = {'ok': False}
    try:
        require(bpy.app.version_string == job['settings']['blender_version'], 'Blender version differs')
        if a.phase == 'prepare': result = city_facades.prepare(job)
        elif a.phase in ('validate-before', 'validate-after'): result = city_facades.validate(job, a.phase)
        elif a.phase in ('render-before', 'render-after'): result = render(job, a.phase)
        else: raise ValueError('Unsupported facade worker phase')
        require(result['ok'], 'Blender validation failed')
    except Exception as e:
        result['error'] = str(e)
        raise
    finally:
        write_json(a.report, result)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--blender', type=Path, required=True)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True, help='New local directory; never an existing edit')
    p.add_argument('--device', choices=['CPU', 'OPTIX'], default='CPU')
    p.add_argument('--width', type=int, default=960); p.add_argument('--height', type=int, default=540)
    p.add_argument('--samples', type=int, default=32); p.add_argument('--timeout', type=int, default=900)
    a = p.parse_args(argv)
    config, cameras = read_json(CONFIG), read_json(CAMERAS)
    source, output = a.input.resolve(), a.output.resolve()
    require(not output.exists(), 'Refusing to reuse an output directory')
    require(0 < a.width <= 4096 and 0 < a.height <= 4096 and 0 < a.samples <= 1024 and a.timeout > 0, 'Invalid resource settings')
    require(source.stat().st_size == config['input']['bytes'] and digest(source) == config['input']['sha256'], 'Pinned city input differs')
    validate_cameras(cameras)
    output.mkdir(parents=True)
    settings = dict(blender_version=config['input']['blender_version'], device=a.device, width=a.width, height=a.height, samples=a.samples, seed=0)
    # No new feature tags: allow only the five empty legacy placeholders already
    # documented for this pinned scene, none of which is a facade target.
    features = {'features': [], 'legacy_empty_objects': config['legacy_empty_objects']}
    job = dict(output=str(output), config=config, cameras=cameras, features=features, settings=settings)
    write_json(output / 'job.json', job)
    summary = dict(version=1, ok=False, status='local-candidate-human-review-pending', input_sha256=config['input']['sha256'],
                   config_sha256=digest(CONFIG), cameras_sha256=digest(CAMERAS), jobs={}, **settings)
    summary['code_files'] = {str(path.relative_to(ROOT)).replace('\\', '/'): digest(path) for path in (
        Path(__file__).resolve(), ROOT / 'scripts/city_facades.py', ROOT / 'scripts/review.py', ROOT / 'scripts/blender_worker.py')}
    summary['limitations'] = ['Illustrative window placement; no real-world accuracy claim.',
        'Original scene and full-city redistribution approval remain unchanged.',
        'Checks use the review harness mesh/material/asset fingerprints; no complete modifier, animation or node-group audit.']
    try:
        shutil.copyfile(source, output / 'before.blend')
        require(digest(output / 'before.blend') == config['input']['sha256'], 'Baseline copy differs')
        for phase, scene in [('prepare', 'before.blend'), ('validate-before', 'before.blend'), ('validate-after', 'after.blend')]:
            summary['jobs'][phase] = run_phase(a.blender, phase, output, output / scene, a.timeout)
        before, after = read_json(output / 'validate-before.json'), read_json(output / 'validate-after.json')
        summary['changed_objects'] = compare(before, after, config)
        require(read_json(output / 'prepare.json')['material_graph_hashes'] == after['material_graph_hashes'], 'Shader graph changed after save/reload')
        summary['counts'] = after['counts']
        summary['remaining_packed_images'] = sum(x.get('type') == 'image' and bool(x.get('packed_sha256')) for x in after['assets'])
        for phase in ('render-before', 'render-after'):
            summary['jobs'][phase] = run_phase(a.blender, phase, output, output / (phase.removeprefix('render-') + '.blend'), a.timeout)
        summary['output_blends'] = {name: digest(output / name) for name in ('before.blend', 'after.blend')}
        require(digest(source) == config['input']['sha256'], 'Original input changed')
        summary['ok'] = True
        make_html(output, cameras, summary)
    except Exception as e:
        summary['error'] = str(e)
        raise
    finally:
        write_json(output / 'run.json', summary)
    print('Facade comparison:', output / 'review.html')


if __name__ == '__main__':
    if '--' in sys.argv and '--worker' in sys.argv[sys.argv.index('--') + 1:]: worker()
    else: main()
