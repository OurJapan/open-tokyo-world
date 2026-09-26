# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Read-only inventory of embedded geometry source claims; never grants rights.

Blender --factory-startup --disable-autoexec --background INPUT
        --python-exit-code 1 --python scripts/audit_city_geometry.py -- OUTPUT.json
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


def main():
    import bpy
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / 'manifests/city-facades-v1.json').read_text(encoding='utf8'))
    output = Path(sys.argv[sys.argv.index('--') + 1])
    if output.exists():
        raise ValueError('Use a new output file')
    source = Path(bpy.data.filepath)
    def sha():
        with source.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()
    input_hash = sha()
    if input_hash != config['input']['sha256']:
        raise ValueError('Inventory requires the pinned PR12 city')
    records = []
    for obj in sorted(bpy.context.scene.objects, key=lambda o: o.name):
        if obj.type != 'MESH':
            continue
        # Only known source fields. Do not export unrelated custom properties,
        # coordinates, mesh bytes or images. Keep this full inventory local.
        claims = {k: str(obj[k]) for k in ('source', 'source_url', 'gml_id', 'otw_feature_id') if k in obj}
        records.append({'object': obj.name, 'collections': sorted(c.name for c in obj.users_collection),
                        'vertices': len(obj.data.vertices), 'polygons': len(obj.data.polygons),
                        'claims': claims})
    result = {'version': 1, 'input_sha256': input_hash, 'blender_version': bpy.app.version_string,
              'mesh_objects': len(records), 'with_source_url_claim': sum(bool(r['claims'].get('source_url')) for r in records),
              'source_claim_counts': dict(sorted(Counter(r['claims'].get('source', '(none)') for r in records).items())),
              'collections': dict(sorted(Counter(c for r in records for c in r['collections']).items())),
              'objects': records,
              'limits': ['Embedded claims have not been verified against source geometry or permission records.',
                         'Collection membership can overlap; collection counts must not be summed as unique objects.',
                         'No material, modifier, animation, dependency or real-world accuracy certification.']}
    if sha() != input_hash:
        raise ValueError('Input changed during inventory')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('objects', 'collections')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
