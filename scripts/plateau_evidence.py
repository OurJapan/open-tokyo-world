"""Look up data221 production candidates using the retained source audit.

Standard library only. Optional inputs and saved georeference metadata are read
and checked; source data, scenes and the audit are never rewritten.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = 'docs/plateau-data221.json'
DOCUMENT = 'docs/plateau-data221.md'
START = '<!-- data221-production-index:start -->'
END = '<!-- data221-production-index:end -->'
ORIGIN = {'lon': 139.74543, 'lat': 35.65858, 'ellipsoid_height_m': 0}
GROUND = 0.32


def finite_vector(value, size, label):
    if (not isinstance(value, list) or len(value) != size
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in value)):
        raise ValueError('Invalid finite coordinates: ' + label)
    return value


def load_audit(root=ROOT):
    audit = json.loads((root / AUDIT).read_text(encoding='utf8'))
    spec = importlib.util.spec_from_file_location('evidence_tile', root / 'starter/plateau/tile.py')
    tile = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tile)
    for key, value in ORIGIN.items():
        if audit['enu_origin'].get(key) != value:
            raise ValueError('Audit origin differs from the fixed import profile')
    if audit['replacement_candidate_gml_id'] != tile.FEATURE_ID:
        raise ValueError('Replacement identity differs from the fixed import profile')
    source_files = {row['url']: row for row in audit['source_files']}
    for name, (url, size, digest) in tile.FILES.items():
        row = source_files.get(url, {})
        if (row.get('bytes'), row.get('sha256')) != (size, digest):
            raise ValueError('Audit source pin mismatch: ' + name)
    if (audit['source_sha256'] != tile.FILES['data221.b3dm'][2]
            or audit['tileset_sha256'] != tile.FILES['tileset.json'][2]
            or audit['tileset_child_path'] != [1, 2, 0, 3, 0]):
        raise ValueError('Audit source identity/path mismatch')
    records = index_records(audit)
    replacement = next(row for row in records if row['replacement'])
    if audit['alignment']['excluded_batch'] != replacement['batch_id']:
        raise ValueError('Legacy exclusion differs from the replacement identity')
    return audit, tile


def index_records(audit):
    features = audit['features']
    ids = [f['gml_id'] for f in features]
    batches = [f['batch_id'] for f in features]
    if (len(features) != 24 or len(set(ids)) != 24
            or any(not isinstance(gid, str) or not gid.startswith('bldg_') for gid in ids)
            or any(type(batch) is not int for batch in batches)
            or sorted(batches) != list(range(24))):
        raise ValueError('Expected 24 unique data221 identities/batches')
    if ids.count(audit['replacement_candidate_gml_id']) != 1:
        raise ValueError('Expected exactly one replacement identity')
    if (any(type(f['triangles']) is not int or f['triangles'] <= 0 for f in features)
            or sum(f['triangles'] for f in features) != 4804
            or audit['triangle_count'] != 4804):
        raise ValueError('Unexpected source triangle counts')
    records = []
    for pointer, f in enumerate(features):
        lo = finite_vector(f['enu_min'], 3, f['gml_id'] + ' minimum')
        hi = finite_vector(f['enu_max'], 3, f['gml_id'] + ' maximum')
        bbox = finite_vector(f['source_bbox'], 6, f['gml_id'] + ' source bbox')
        if any(a >= b for a, b in zip(lo, hi)) or any(a >= b for a, b in zip(bbox[:3], bbox[3:])):
            raise ValueError('Invalid ordered bounds: ' + f['gml_id'])
        replacement = f['gml_id'] == audit['replacement_candidate_gml_id']
        records.append({
            'gml_id': f['gml_id'], 'batch_id': f['batch_id'],
            'name': f['name'], 'source_lod': f['source_lod'],
            'data_quality_lod': f['data_quality_lod'], 'triangles': f['triangles'],
            'audit_ref': AUDIT + '#/features/' + str(pointer),
            'source_bbox_lon_lat_attribute_height': bbox,
            'source_enu_min_m': lo, 'source_enu_max_m': hi,
            'bbox_midpoint_xy_m': [(lo[i] + hi[i]) / 2 for i in range(2)],
            'legacy_z_shift_m': GROUND - lo[2],
            'legacy_display_z_range_m': [GROUND, hi[2] - lo[2] + GROUND],
            'replacement': replacement,
            'scene_lookup': {
                'plateau_trial_object_name': f['gml_id'],
                'mori_before_object_name': f['gml_id'],
                'mori_after_property': 'otw_feature_id' if replacement else 'gml_id',
                'mori_after_value': ('otw:jp:tokyo:minato:azabudai-mori-jp'
                                     if replacement else f['gml_id']),
            },
        })
    return sorted(records, key=lambda row: row['batch_id'])


def select_records(records, feature=None, near=None, radius_m=30):
    if feature is not None:
        selected = [row for row in records if row['gml_id'] == feature]
        if not selected:
            raise ValueError('Unknown data221 gml_id: ' + feature)
        return selected
    if near is None:
        return records
    finite_vector(list(near), 2, 'near XY')
    if not math.isfinite(radius_m) or radius_m < 0:
        raise ValueError('Radius must be finite and nonnegative')
    selected = []
    for row in records:
        lo, hi = row['source_enu_min_m'], row['source_enu_max_m']
        distance = math.hypot(*(max(lo[i] - near[i], 0, near[i] - hi[i]) for i in range(2)))
        if distance <= radius_m:
            selected.append(dict(row, distance_to_xy_bbox_m=distance))
    return sorted(selected, key=lambda row: (row['distance_to_xy_bbox_m'], row['batch_id']))


def markdown_table(records):
    lines = [
        '| batch（この版のみ） | gml_id / 取込object名 | XY範囲の中点 m（東, 北） | 互換表示z範囲 m | 三角形 | 森JP置換後 |',
        '|---:|---|---:|---:|---:|---|',
    ]
    for row in records:
        x, y = row['bbox_midpoint_xy_m']
        lo, hi = row['legacy_display_z_range_m']
        role = '詳細森JPへ置換' if row['replacement'] else '公式地物を保持'
        lines.append(f"| {row['batch_id']} | `{row['gml_id']}` | {x:.2f}, {y:.2f} | {lo:.2f}–{hi:.2f} | {row['triangles']} | {role} |")
    return '\n'.join(lines)


def check_document(records, document):
    if document.count(START) != 1 or document.count(END) != 1:
        raise ValueError('Expected one production-index block in ' + DOCUMENT)
    start, end = document.index(START) + len(START), document.index(END)
    if end <= start or document[start:end].strip() != markdown_table(records):
        raise ValueError('Production table is stale; regenerate with --format markdown')
    return {'status': 'matched', 'features': len(records)}


def batch_values(table, binary, key, tile):
    value = table[key]
    if isinstance(value, list) and len(value) == 24:
        return value
    if not isinstance(value, dict) or value.get('type') != 'SCALAR':
        raise ValueError('Unsupported batch column: ' + key)
    fmt = {'BYTE': 'b', 'DOUBLE': 'd'}.get(value.get('componentType'))
    if fmt is None:
        raise ValueError('Unsupported batch component: ' + key)
    size = struct.calcsize('<24' + fmt)
    return list(struct.unpack('<24' + fmt, tile.section(binary, value['byteOffset'], size)))


def check_inputs(audit, tile, folder):
    payloads = {name: tile.verify(name, (folder / name).read_bytes()) for name in tile.FILES}
    region = tile.parent(payloads['tileset.json'])
    bounds = [math.degrees(v) for v in region[:4]] + region[4:]
    if any(abs(a - b) > (1e-9 if i < 4 else 1e-5)
           for i, (a, b) in enumerate(zip(bounds, audit['source_bounds']))):
        raise ValueError('Tileset region differs from the retained audit')
    data = payloads['data221.b3dm']
    tile.parse(data)
    _, _, _, fj, fb, bj, bb = struct.unpack_from('<4s6I', data)
    table = json.loads(tile.section(data, 28 + fj + fb, bj))
    binary = tile.section(data, 28 + fj + fb + bj, bb)
    columns = {key: batch_values(table, binary, key, tile)
               for key in ['gml_id', 'gml:name', '_lod', '_xmin', '_ymin', '_zmin', '_xmax', '_ymax', '_zmax']}
    for f in audit['features']:
        batch = f['batch_id']
        if (columns['gml_id'][batch] != f['gml_id']
                or columns['gml:name'][batch] != f['name']
                or columns['_lod'][batch] != f['source_lod']):
            raise ValueError('Batch identity/name/LOD mismatch: ' + f['gml_id'])
        bbox = [columns[key][batch] for key in ['_xmin', '_ymin', '_zmin', '_xmax', '_ymax', '_zmax']]
        finite_vector(bbox, 6, 'batch bbox')
        if any(abs(a - b) > 1e-10 for a, b in zip(bbox, f['source_bbox'])):
            raise ValueError('Batch source bounds mismatch: ' + f['gml_id'])
        quality = table['attributes'][batch].get('uro:DataQualityAttribute', [])
        lod = sorted({q['uro:lodType'] for q in quality if q.get('uro:lodType')})
        if lod != sorted(f['data_quality_lod']):
            raise ValueError('Batch quality LOD mismatch: ' + f['gml_id'])
    return {'status': 'matched', 'features': 24,
            'files': {name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                      for name, data in payloads.items()},
            'geometry_decoded_this_run': False}


def check_georeference(records, saved):
    origin = saved['origin']
    if origin != {'longitude': ORIGIN['lon'], 'latitude': ORIGIN['lat'], 'ellipsoid_height': 0}:
        raise ValueError('Saved georeference origin mismatch')
    features = saved['features']
    lookup = {f['gml_id']: f for f in features}
    if len(lookup) != 24 or len(features) != 24 or set(lookup) != {r['gml_id'] for r in records}:
        raise ValueError('Saved georeference identity set mismatch')
    max_error = 0.0
    for row in records:
        f = lookup[row['gml_id']]
        if f['batch_id'] != row['batch_id'] or f['triangles'] != row['triangles']:
            raise ValueError('Saved georeference batch/triangles mismatch: ' + row['gml_id'])
        lo = finite_vector(f['source_enu_min'], 3, 'saved minimum')
        hi = finite_vector(f['source_enu_max'], 3, 'saved maximum')
        shift = finite_vector([f['legacy_z_shift_m']], 1, 'saved height shift')[0]
        error = max([abs(a - b) for a, b in zip(lo + hi, row['source_enu_min_m'] + row['source_enu_max_m'])]
                    + [abs(shift - row['legacy_z_shift_m'])])
        if error > 1e-6:
            raise ValueError('Saved georeference coordinates/height shift mismatch: ' + row['gml_id'])
        max_error = max(max_error, error)
    return {'status': 'matched', 'features': 24, 'max_coordinate_error_m': max_error,
            'scene_opened_this_run': False}


def file_record(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    query = parser.add_mutually_exclusive_group()
    query.add_argument('--feature', help='Exact gml_id in the retained data221 revision')
    query.add_argument('--near', type=float, nargs=2, metavar=('EAST', 'NORTH'), help='Blender/ENU XY metres')
    parser.add_argument('--radius-m', type=float, help='Distance to XY bounding box; default 30 with --near')
    parser.add_argument('--inputs', type=Path, help='Explicit local folder containing both pinned official files')
    parser.add_argument('--georeference', type=Path, help='Saved plateau/mori georeference.json to compare')
    parser.add_argument('--check-doc', action='store_true', help='Require the retained production table to match')
    parser.add_argument('--format', choices=['json', 'markdown'], default='json')
    parser.add_argument('--output', type=Path, help='New local report file; existing files are refused')
    args = parser.parse_args(argv)
    if args.radius_m is not None and args.near is None:
        parser.error('--radius-m requires --near')
    try:
        audit, tile = load_audit()
        records = index_records(audit)
        checks = {}
        if args.check_doc:
            checks['document'] = check_document(records, (ROOT / DOCUMENT).read_text(encoding='utf8'))
        if args.inputs:
            checks['official_inputs'] = check_inputs(audit, tile, args.inputs)
        if args.georeference:
            checks['saved_georeference'] = dict(
                check_georeference(records, json.loads(args.georeference.read_text(encoding='utf8'))),
                file=file_record(args.georeference))
        selected = select_records(records, args.feature, args.near, args.radius_m if args.radius_m is not None else 30)
        result = {
            'schema_version': 1, 'ok': True, 'scope': 'data221-source-production-candidates',
            'source_audit_date': audit['verified_date'], 'source_audit_repository_base': audit['repository_base'],
            'inputs': {AUDIT: file_record(ROOT / AUDIT),
                       'starter/plateau/tile.py': file_record(ROOT / 'starter/plateau/tile.py')},
            'tool': {'path': 'scripts/plateau_evidence.py', **file_record(Path(__file__)), 'python': sys.version.split()[0]},
            'source_sha256': audit['source_sha256'], 'tileset_sha256': audit['tileset_sha256'],
            'origin': ORIGIN, 'axis_order': ['east', 'north', 'up'], 'units': 'metres',
            'checks': checks, 'query': {'feature': args.feature, 'near_xy_m': args.near, 'radius_m': args.radius_m if args.radius_m is not None else 30} if args.near is not None else {'feature': args.feature},
            'candidate_count': len(selected), 'candidates': selected,
            'limitations': [
                'XY midpoint and distance refer to axis-aligned bounds, not footprint centres or occupancy.',
                'Per-feature ground at 0.32 m is legacy display placement, not surveyed terrain or a height datum conversion.',
                'Source bounds describe the retained 2025 tile, not current detailed-model geometry.',
                'Optional checks compare source metadata and saved coordinate metadata; they do not open or validate a scene.',
                'OSM, photographs and adjacent tiles are separate evidence; no spatial association is inferred here.',
            ],
        }
        output = markdown_table(selected) if args.format == 'markdown' else json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open('x', encoding='utf8', newline='\n') as stream:
                stream.write(output + '\n')
            print(json.dumps({'ok': True, 'candidate_count': len(selected), 'checks': checks,
                              'output': str(args.output)}, ensure_ascii=False))
        else:
            print(output)
        return 0
    except (ValueError, KeyError, TypeError, OSError, struct.error) as error:
        print('data221 evidence check failed: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
