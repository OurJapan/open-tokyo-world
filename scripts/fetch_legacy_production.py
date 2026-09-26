# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Fetch pinned legacy source text for inspection; never import or execute it."""
import argparse
import base64
import hashlib
import json
import re
from pathlib import Path
import subprocess

from workspace import ROOT, copy_verified, inside, read_json, verify_file, write_json

MANIFEST = ROOT / 'manifests/legacy-production-sources.json'
UPSTREAM = 'ark4ez/tokyo-tower-blender'


def fetch_blob(target, specification):
    if target.exists():
        return verify_file(target, specification)
    try:
        result = subprocess.run(['gh', 'api', f'repos/{UPSTREAM}/git/blobs/{specification["git_blob_sha1"]}'],
                                capture_output=True, text=True, encoding='utf8', timeout=60)
    except FileNotFoundError as error:
        raise ValueError('GitHub CLI (gh) with access to the private upstream is required; or use --inputs PATH') from error
    if result.returncode:
        raise ValueError('Cannot read the private upstream. Check gh authentication/read access, or use --inputs PATH')
    blob = json.loads(result.stdout)
    if blob.get('encoding') != 'base64':
        raise ValueError('Unexpected GitHub blob encoding')
    data = base64.b64decode(blob['content'])
    git_hash = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    if (len(data) != specification['bytes'] or hashlib.sha256(data).hexdigest() != specification['sha256']
            or git_hash != specification['git_blob_sha1']):
        raise ValueError('Downloaded source differs from pinned bytes/hash: ' + target.name)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as handle:
        handle.write(data)
    return target


def fetch(output, inputs=None):
    manifest = read_json(MANIFEST)
    commit = manifest['upstream']['commit']
    if manifest.get('version') != 1 or not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Unsupported source manifest')
    if manifest['upstream']['repository'] != f'https://github.com/{UPSTREAM}':
        raise ValueError('Unsupported upstream repository')
    output = Path(output).resolve()
    # Validate the entire path list before any writes or downloads.
    destinations = {name: inside(output, name) for name in manifest['files']}
    for name, specification in manifest['files'].items():
        if not re.fullmatch('[0-9a-f]{40}', specification['git_blob_sha1']):
            raise ValueError('Invalid Git blob hash')
        expected_url = f'https://api.github.com/repos/{UPSTREAM}/git/blobs/{specification["git_blob_sha1"]}'
        if (specification['url'] != expected_url
                or specification['source_url'] != f'https://github.com/{UPSTREAM}/blob/{commit}/{name}'):
            raise ValueError('Source URL is not pinned to the recorded upstream commit')
        if not isinstance(specification['bytes'], int) or not 0 < specification['bytes'] <= 1024 * 1024:
            raise ValueError('Invalid source size')
        if not re.fullmatch('[0-9a-f]{64}', specification['sha256']):
            raise ValueError('Invalid source hash')
    for name, specification in manifest['files'].items():
        if inputs is None:
            fetch_blob(destinations[name], specification)
        else:
            copy_verified(inside(inputs, name), destinations[name], specification)
    record = {'version': 1, 'upstream': manifest['upstream'], 'files': manifest['files'],
              'purpose': 'Read-only production-source inspection; not a complete city build.',
              'all_files_verified': True, 'executed_legacy_code': False,
              'license_scope': 'No new grant for these historical files or their inputs/outputs.'}
    write_json(output / 'source-record.json', record)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/local/sources/legacy-production-defac576')
    parser.add_argument('--inputs', type=Path, help='Copy already downloaded files after verifying the same pinned bytes')
    args = parser.parse_args(argv)
    result = fetch(args.output, args.inputs)
    print('Verified legacy source text:', result)
    print('Inspection only. See docs/city-production-sources.md for missing inputs and correspondence limits.')


if __name__ == '__main__':
    main()
