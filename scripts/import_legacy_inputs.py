# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Import recovered, pinned city inputs into a local workspace without executing them."""
import argparse
from pathlib import Path
import re

from workspace import ROOT, copy_verified, inside, read_json, verify_file, write_json

MANIFEST = ROOT / 'manifests/legacy-production-inputs.json'


def import_inputs(source, output, include_scenes=False):
    manifest = read_json(MANIFEST)
    if manifest.get('version') != 1:
        raise ValueError('Unsupported production input manifest')
    source, output = Path(source).resolve(), Path(output).resolve()
    selected = {}
    for name, specification in manifest['files'].items():
        if specification['kind'] not in ('production-input', 'intermediate-scene'):
            raise ValueError('Unknown production input kind')
        if specification['kind'] == 'intermediate-scene' and not include_scenes:
            continue
        if (not isinstance(specification['bytes'], int) or specification['bytes'] <= 0
                or not re.fullmatch('[0-9a-f]{64}', specification['sha256'])):
            raise ValueError('Invalid production input size/hash')
        selected[name] = (inside(source, name), inside(output, name), specification)
    if not selected:
        raise ValueError('No production inputs selected')
    # Check every source and every existing destination before copying any file.
    for src, dest, specification in selected.values():
        verify_file(src, specification)
        if dest.exists():
            verify_file(dest, specification)
    for src, dest, specification in selected.values():
        copy_verified(src, dest, specification)
    write_json(output / 'source-record.json', {
        'version': 1, 'manifest': MANIFEST.name, 'files': {name: spec for name, (_, _, spec) in selected.items()},
        'source_root': str(source), 'all_files_verified': True, 'include_scenes': include_scenes,
        'executed_legacy_code': False, 'distribution': manifest['distribution'],
        'notice': 'Local import does not grant redistribution rights or verify a complete city rebuild.'})
    return {'inputs': str(output), 'files': len(selected), 'bytes': sum(spec['bytes'] for _, _, spec in selected.values()),
            'intermediate_scenes_included': include_scenes, 'all_files_verified': True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/local/sources/legacy-production-inputs-v1')
    parser.add_argument('--include-scenes', action='store_true', help='Also copy the five intermediate blends (about 2.76 GB)')
    args = parser.parse_args(argv)
    print(import_inputs(args.input, args.output, args.include_scenes))


if __name__ == '__main__':
    main()
