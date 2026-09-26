# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Replay reviewed map/layout processors in a new directory and compare their outputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from workspace import ROOT, digest, inside, read_json, verify_file, write_json

# These complete scripts were inspected: only local reads, geometry computation
# and outputs below their own work/ directory. Fetch/render/scene pipelines are
# deliberately outside this allowlist. Changing a pin requires a new review.
STAGES = [
    ('work/wide_detail/roads.py', '32a4b939bf1d4dfac44f5549477d363ecfc4113374fa62da5835b46ee670cc93',
     ['work/wide_detail/wide_roads.npz', 'work/wide_detail/road_checks.json']),
    ('work/tower15_env/surfaces.py', '2e781f8224a28f83f0611a4d2d4d5750e6544598240a511e444a5a5fc0937df8',
     ['work/tower15_env/road_detail.npz', 'work/tower15_env/shrubs.json', 'work/tower15_env/surface_checks.json']),
    ('work/tower15_env/landuse.py', 'f3366a0057dea02dd5b0b6d3a74b721061226f669f41b30c2f95018f45e90c37',
     ['work/tower15_env/landuse.npz', 'work/tower15_env/landuse_areas.json']),
    ('work/street_detail/prepare.py', '261aa24afdc3ed7c24782a752ab046beb4cd280ea0dd1544dcaeca67e7370f9d',
     ['work/street_detail/placements.json']),
    ('work/tokyo_traffic/layout.py', 'f5b779c16cd313efb4c7a3ee5b210990f7738c387e955053e92364e2a4088958',
     ['work/tokyo_traffic/layout.json', 'work/tokyo_traffic/road_boundary.wkb.npy']),
    ('work/tokyo_traffic/tree_filter.py', '4238b16ac0a857c9683a216653783609663631e2a835df486edce5fc041cbca9',
     ['work/tokyo_traffic/tree_keep.json']),
    ('work/street_detail/facade_layout.py', '53e9f21604184009df83e923f8b82d0eea5f1ad099c095bea3329cb97181cee2',
     ['work/street_detail/facade_layouts.json']),
]


def canonical_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf8')


def content_signature(path):
    path = Path(path)
    if path.suffix == '.json':
        return {'kind': 'json-values', 'sha256': hashlib.sha256(canonical_json(read_json(path))).hexdigest()}
    import numpy as np
    def array_signature(array):
        if array.dtype.hasobject or not np.isfinite(array).all():
            raise ValueError('Invalid numeric array')
        return {'dtype': array.dtype.str, 'shape': list(array.shape),
                'sha256': hashlib.sha256(array.tobytes(order='C')).hexdigest()}
    if path.suffix == '.npz':
        with np.load(path, allow_pickle=False) as arrays:
            return {'kind': 'npz-arrays', 'arrays': {key: array_signature(arrays[key]) for key in sorted(arrays.files)}}
    if path.suffix == '.npy':
        return {'kind': 'npy-array', **array_signature(np.load(path, allow_pickle=False))}
    raise ValueError('Unsupported comparison format')


def preflight(sources, inputs, output):
    if Path(output).exists():
        raise ValueError('Use a new replay output directory')
    manifest = read_json(ROOT / 'manifests/legacy-production-inputs.json')
    code = read_json(ROOT / 'manifests/legacy-production-sources.json')
    for name, pin, _ in STAGES:
        if code['files'][name]['sha256'] != pin:
            raise ValueError('Review the changed source pin before replay')
        verify_file(inside(sources, name), code['files'][name])
    files = {name: spec for name, spec in manifest['files'].items() if spec['kind'] == 'production-input'}
    for name, spec in files.items():
        verify_file(inside(inputs, name), spec)
    outputs = {name for _, _, names in STAGES for name in names}
    if not outputs <= files.keys():
        raise ValueError('Replay output is absent from the reference input manifest')
    return files, outputs


def replay(sources, inputs, output, dependencies=None, timeout=600):
    sources, inputs, output = Path(sources).resolve(), Path(inputs).resolve(), Path(output).resolve()
    files, generated = preflight(sources, inputs, output)
    if dependencies:
        dependencies = Path(dependencies).resolve()
        sys.path.insert(0, str(dependencies))
    import numpy as np
    import shapely
    runtime = {'python': sys.version.split()[0], 'numpy': np.__version__, 'shapely': shapely.__version__,
               'geos': shapely.geos_version_string, 'platform': sys.platform}
    if (sys.version_info[:2] != (3, 12) or np.__version__ != '2.3.5'
            or shapely.__version__ != '2.1.2' or shapely.geos_version_string != '3.13.1'):
        raise ValueError('Use Python 3.12, NumPy 2.3.5, Shapely 2.1.2 and GEOS 3.13.1')
    output.mkdir(parents=True)
    # Never seed a generated file with the reference output. Each must actually
    # be written by its producer before comparison.
    for name in sorted(files.keys() - generated):
        target = inside(output, name); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(inside(inputs, name), target)
    for name, _, _ in STAGES:
        target = inside(output, name); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(inside(sources, name), target)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    if dependencies:
        env['PYTHONPATH'] = str(dependencies)
    report = {'version': 1, 'ok': False, 'runtime': runtime, 'stages': [],
              'reference_inputs': files, 'seed_files': sorted(files.keys() - generated),
              'code_sha256_lf': hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
              'scope': 'Seven data processors only. Existing footprint/surface/canopy records are pinned seed inputs; no full city rebuild or new rights grant.'}
    try:
        for index, (name, pin, outputs) in enumerate(STAGES):
            start = time.monotonic()
            with (output / f'stage-{index + 1}.log').open('w', encoding='utf8') as log:
                subprocess.run([sys.executable, '-B', str(inside(output, name))], cwd=output, env=env,
                               stdout=log, stderr=subprocess.STDOUT, check=True, timeout=timeout)
            checks = []
            for relative in outputs:
                reference, actual = inside(inputs, relative), inside(output, relative)
                before, after = content_signature(reference), content_signature(actual)
                checks.append({'path': relative, 'raw_bytes_match': digest(reference) == digest(actual),
                               'content_match': before == after, 'reference': before, 'generated': after})
            stage = {'script': name, 'code_sha256': pin, 'seconds': round(time.monotonic() - start, 3), 'outputs': checks}
            report['stages'].append(stage)
            write_json(output / 'replay.json', report)
            if not all(c['content_match'] for c in checks):
                raise ValueError('Regenerated values differ: ' + name)
            print('Verified:', name, flush=True)
        report['ok'] = True
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        report['inputs_unchanged'] = all(digest(inside(inputs, name)) == spec['sha256'] for name, spec in files.items())
        report['source_code_unchanged'] = all(digest(inside(sources, name)) == pin for name, pin, _ in STAGES)
        report['ok'] = report['ok'] and report['inputs_unchanged'] and report['source_code_unchanged']
        write_json(output / 'replay.json', report)
    if not report['ok']:
        raise ValueError('Replay or immutable-input verification failed')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', type=Path, default=ROOT / 'data/local/sources/legacy-production-defac576')
    parser.add_argument('--inputs', type=Path, default=ROOT / 'data/local/sources/legacy-production-inputs-v1')
    parser.add_argument('--dependencies', type=Path, help='Optional isolated directory containing the pinned Python packages')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    result = replay(args.sources, args.inputs, args.output, args.dependencies, args.timeout)
    print(json.dumps({'ok': result['ok'], 'stages': len(result['stages'])}))


if __name__ == '__main__':
    main()
