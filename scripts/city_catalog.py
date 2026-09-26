# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Build a local illustrated inventory from the immutable, pinned city scene."""
import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'manifests/city-catalog-v1.json'
WORKER = ROOT / 'scripts/city_catalog_blender.py'
TEMPLATE = ROOT / 'scripts/city_catalog_template.html'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8', newline='\n')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def classify(row, groups):
    matches = []
    for group in groups:
        sel = group['selector']
        if (row['object'] in sel.get('names', [])
                or any(row['object'].startswith(p) for p in sel.get('prefixes', []))
                or set(row['collections']) & set(sel.get('collections', []))):
            matches.append(group['id'])
    require(len(matches) == 1, 'Missing or overlapping classification: ' + row['object'])
    return matches[0]


def load_grants(input_hash):
    tower = read(ROOT / 'assets/tokyo-tower/provenance.json')
    mori = read(ROOT / 'starter/mori/provenance.json')
    plaza = read(ROOT / 'starter/plaza/provenance.json')
    require(tower['baseline']['sha256'] == input_hash, 'Tower grant references another city version')
    records = {}
    for part in tower['parts']:
        records[part['object']] = {'kind': 'same-input-record', 'reference': 'assets/tokyo-tower/provenance.json',
                                    'scope': part['scope']}
    for part in mori['parts']:
        records[part['object']] = {'kind': 'same-name-record', 'reference': 'starter/mori/provenance.json',
                                    'scope': part['scope']}
    for part in plaza['assets']:
        records[part['name']] = {'kind': 'same-name-record', 'reference': 'starter/plaza/provenance.json',
                                'scope': 'Original parts only; exact legacy shape/material correspondence not checked here.'}
    return records


def associate_record(name, source_url, grants):
    if name in grants:
        return dict(grants[name])
    if source_url:
        return {'kind': 'source-claim', 'reference': 'sources/city-pr12-geometry-audit.json',
                'scope': 'Embedded source URL, not verified source geometry or a redistribution grant.'}
    return {'kind': 'unconfirmed', 'reference': None, 'scope': 'Authorship and source inputs need identification.'}


def json_for_html(data):
    # Scene strings are data, including closing script tags or HTML-like names.
    return json.dumps(data, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def make_page(output, config, inventory, renders):
    data = {'input_sha256': config['input']['sha256'], 'reference_commit': config['reference_commit'],
            'groups': config['groups'], 'inventory': inventory, 'renders': renders}
    template = TEMPLATE.read_text(encoding='utf8')
    require(template.count('__CATALOG_DATA__') == 1, 'Invalid catalog template')
    (output / 'index.html').write_text(template.replace('__CATALOG_DATA__', json_for_html(data)), encoding='utf8', newline='\n')


def run_phase(blender, source, output, phase, timeout):
    report = output / (phase + '.json')
    command = [str(blender), '--factory-startup', '--disable-autoexec', '--background', str(source),
               '--python-exit-code', '1', '--python', str(WORKER), '--', '--job', str(output / 'job.json'),
               '--phase', phase, '--report', str(report)]
    start = time.monotonic()
    with (output / (phase + '.log')).open('w', encoding='utf8') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, check=False)
    require(result.returncode == 0 and report.is_file(), phase + ' failed; see local log')
    require(read(report).get('ok') is True, phase + ' failed; see local report')
    return {'seconds': round(time.monotonic() - start, 3), 'report_sha256': sha(report)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--blender', type=Path, required=True)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True, help='New local directory; no blend is saved')
    p.add_argument('--device', choices=['CPU', 'OPTIX'], default='CPU')
    p.add_argument('--width', type=int, default=900); p.add_argument('--height', type=int, default=560)
    p.add_argument('--samples', type=int, default=16); p.add_argument('--timeout', type=int, default=1200)
    a = p.parse_args(argv)
    source, output = a.input.resolve(), a.output.resolve()
    config = read(CONFIG)
    require(not output.exists(), 'Refusing to overwrite a catalog')
    require(0 < a.width <= 2048 and 0 < a.height <= 2048 and 0 < a.samples <= 256 and a.timeout > 0, 'Invalid resource settings')
    require(source.stat().st_size == config['input']['bytes'] and sha(source) == config['input']['sha256'], 'Pinned city input differs')
    ids = [g['id'] for g in config['groups']]
    require(len(ids) == len(set(ids)) and all(re.fullmatch('[a-z][a-z0-9-]*', i) for i in ids), 'Invalid group IDs')
    output.mkdir(parents=True)
    settings = dict(device=a.device, width=a.width, height=a.height, samples=a.samples, seed=0, frame=1)
    write(output / 'job.json', dict(output=str(output), config=config, settings=settings))
    summary = dict(version=1, ok=False, input_sha256=config['input']['sha256'], config_sha256=sha(CONFIG),
                   output_kind='local-illustrated-inventory-no-blend', jobs={}, settings=settings)
    code = [Path(__file__).resolve(), WORKER, TEMPLATE, ROOT / 'scripts/blender_worker.py', ROOT / 'scripts/audit_image_sources.py']
    summary['code_files_sha256_lf'] = {f.relative_to(ROOT).as_posix(): hashlib.sha256(f.read_bytes().replace(b'\r\n', b'\n')).hexdigest() for f in code}
    summary['record_files_sha256_lf'] = {p: hashlib.sha256((ROOT / p).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        for p in ['assets/tokyo-tower/provenance.json', 'starter/mori/provenance.json', 'starter/plaza/provenance.json']}
    try:
        for phase in ('inventory', 'render'):
            summary['jobs'][phase] = run_phase(a.blender, source, output, phase, a.timeout)
        inventory, renders = read(output / 'inventory.json'), read(output / 'render.json')
        require(inventory['mesh_objects'] == config['expected_mesh_objects'], 'Unexpected mesh coverage')
        require({r['id'] for r in renders['groups']} == set(ids), 'Incomplete gallery')
        make_page(output, config, inventory, renders)
        summary.update(mesh_objects=inventory['mesh_objects'], groups=len(ids),
                       image_count=sum(len(g['images']) for g in renders['groups']), counts=inventory['counts'])
        summary['ok'] = True
    except Exception as e:
        summary['error'] = str(e)
        raise
    finally:
        summary['input_unchanged'] = sha(source) == config['input']['sha256']
        if not summary['input_unchanged']: summary['ok'] = False
        write(output / 'run.json', summary)
    require(summary['input_unchanged'], 'Original input changed')
    print('Local city catalog:', output / 'index.html')


if __name__ == '__main__':
    main()
