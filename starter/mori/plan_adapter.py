# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Closed adapter for one procedural recipe. Locators are identifiers, never code."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'starter/plateau')]
import object_registry as registry
import tile

FEATURE = 'otw:jp:tokyo:minato:azabudai-mori-jp'
SOURCE = 'plateau:minato:2025:data221'
MODEL = 'otw:mori:procedural-v1'
REVISION = 'standalone-v1'
PROFILE = 'mori-standalone'
INVENTORY = 'sources/plateau-minato-2025-data221.json'
MANIFEST = 'starter/mori/model-manifest.json'
REGISTRY = 'registry/mori.json'
LOCK = 'registry/mori.lock.json'
FRAME = {'id': 'legacy-tokyo-display-v1', 'units': 'm', 'axes': 'east-north-up',
         'definition': 'glTF (x,-z,y) + RTC -> ECEF -> ENU at 139.74543,35.65858,0m ellipsoid; each building minimum Z shifted to 0.32m. Display heights, not survey datum.'}
PARTS = {
    'podium-aluminum': 'Mori JP podium / aluminum',
    'podium-ceiling': 'Mori JP podium / ceiling',
    'podium-clear-glass': 'Mori JP podium / clear glass',
    'podium-gasket': 'Mori JP podium / gasket',
    'podium-leaf': 'Mori JP podium / leaf',
    'podium-soil': 'Mori JP podium / soil',
    'podium-stone': 'Mori JP podium / stone',
    'podium-wood': 'Mori JP podium / wood',
    'facade-glass': 'Mori continuous pearl glass / pearl grey coated glass',
    'facade-spandrel': 'Mori continuous pearl glass / recessed spandrel',
    'facade-joint': 'Mori continuous pearl glass / sealing joint',
    'facade-mullion': 'Mori continuous pearl glass / slender mullion',
    'floors-roof': 'Mori independent / floors and roof',
}
CODE_FILES = (
    'scripts/object_registry.py', 'starter/mori/plan_adapter.py',
    'starter/mori/run.py', 'starter/mori/scene.py', 'starter/mori/profile.py',
    'starter/mori/facade.py', 'starter/plateau/tile.py', 'starter/plateau/scene.py',
    'starter/plaza/scene.py', 'scripts/mori_shape.py', 'scripts/mori_crown_v2.py',
    'scripts/mori_crown_material.py', 'scripts/mori_facade_v2.py',
    'scripts/mori_podium_v3.py', 'scripts/mori_entrance_v1.py',
    'scripts/mori_terrace_v1.py', 'scripts/mori_plaza_v1.py', 'scripts/mori_plaza_link_v1.py',
)
require = registry.require


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_hashes(root=ROOT):
    return {name: hashlib.sha256((root / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
            for name in CODE_FILES}


def contract(root=ROOT):
    inventory = read(root / INVENTORY)
    pins = {name: {'url': url, 'bytes': size, 'sha256': sha}
            for name, (url, size, sha) in tile.FILES.items()}
    require(inventory['schema_version'] == 1 and inventory['files'] == pins, 'Source inventory pins mismatch')
    ids = inventory['object_ids']
    require(len(ids) == len(set(ids)) == 24 and ids.count(tile.FEATURE_ID) == 1, 'Source inventory IDs mismatch')
    manifest = read(root / MANIFEST)
    require(manifest['schema_version'] == 1 and manifest['adapter'] == 'mori-standalone-v1'
            and manifest['model_id'] == MODEL and manifest['version'] == REVISION,
            'Unsupported procedural model manifest')
    require(manifest['source_inventory_sha256'] == file_hash(root / INVENTORY), 'Source inventory hash mismatch')
    require(manifest['parts'] == PARTS, 'Procedural model parts mismatch')
    require(manifest['code_sha256_lf'] == code_hashes(root), 'Procedural model code hash mismatch')
    source = {'id': SOURCE, 'revision': '2025.1.0', 'sha256': pins['data221.b3dm']['sha256'],
              'license': 'PLATEAU source-specific terms; see starter/plateau/NOTICE.md',
              'attribution': 'MLIT Project PLATEAU / Minato 2025', 'object_ids': ids,
              'inventory_sha256': file_hash(root / INVENTORY), 'files': pins}
    model = {'id': MODEL, 'version': REVISION, 'sha256': file_hash(root / MANIFEST),
             'format': 'procedural-manifest', 'locator': MANIFEST,
             'license': 'CC-BY-4.0 for original additions only; PLATEAU source terms retained',
             'attribution': 'ark4ez / OurJapan; see starter/mori/provenance.json', 'source_refs': [SOURCE]}
    return inventory, manifest, source, model


def validate_plan(plan, root=ROOT):
    inventory, manifest, source, model = contract(root)
    require(plan.get('schema_version') == 1 and plan.get('review_only') is False, 'Review-only/unknown plan refused')
    require(plan['frame'] == FRAME and plan['profile'] == PROFILE, 'Mori frame/profile mismatch')
    require(plan['sources'] == {SOURCE: source}, 'Mori source mismatch')
    require(plan['models'] == {MODEL: model}, 'Mori model hash/locator mismatch')
    require(plan['selected'] == {FEATURE: REVISION} and plan['build_order'] == [FEATURE]
            and plan['dependencies'] == {FEATURE: []}, 'Mori selection/dependency mismatch')
    neighbors = ['otw:jp:tokyo:minato:' + gid for gid in inventory['object_ids'] if gid != tile.FEATURE_ID]
    require(plan['review_neighbors'] == {FEATURE: neighbors}
            and plan['review_features'] == sorted([FEATURE, *neighbors]), 'Mori review scope mismatch')
    ops = [{'feature': FEATURE, 'revision': REVISION, 'action': 'suppress', 'part': 'source-building'}]
    ops += [{'feature': FEATURE, 'revision': REVISION, 'action': 'add', 'part': part,
             'models': {PROFILE: MODEL}, 'position_m': [0, 0, 0], 'yaw_degrees': 0} for part in PARTS]
    require(plan['operations'] == ops, 'Mori operations/parts mismatch')
    expected = []
    for part in ['source-building', *PARTS]:
        is_source = part == 'source-building'
        expected.append({'feature': FEATURE, 'part': part, 'kind': 'building', 'owner_area': 'azabudai',
                         'source_binding': {'source': SOURCE, 'object_id': tile.FEATURE_ID} if is_source else None,
                         'geometry': None if is_source else {'model': MODEL, 'position_m': [0, 0, 0], 'yaw_degrees': 0},
                         'material': None})
    require(plan['parts'] == sorted(expected, key=lambda p: p['part']), 'Mori source binding/part state mismatch')
    return {'feature_id': FEATURE, 'source_gml_id': next(p['source_binding']['object_id'] for p in plan['parts'] if p['source_binding']),
            'parts': {p['part']: manifest['parts'][p['part']] for p in plan['parts'] if p['geometry']},
            'source_ids': inventory['object_ids'], 'plan_sha256': registry.digest(plan),
            'model_sha256': model['sha256'], 'code_sha256_lf': manifest['code_sha256_lf']}


def compile_checked(registry_path=None, lock_path=None, root=ROOT):
    plan = registry.compile_plan(read(registry_path or root / REGISTRY), read(lock_path or root / LOCK))
    validate_plan(plan, root)
    return plan


def verify_inputs(payload, plan, root=ROOT):
    context = validate_plan(plan, root)
    require(set(payload) == set(tile.FILES), 'Source file set mismatch')
    for name, raw in payload.items():
        tile.verify(name, raw)
    _, _, ids = tile.parse(payload['data221.b3dm'])
    require(ids == context['source_ids'], 'Imported source inventory mismatch')
    tile.parent(payload['tileset.json'])
    return context


def load_bundle(out):
    """Recompile copied registry/lock on every worker invocation, including reopen."""
    plan = compile_checked(out / 'registry.json', out / 'registry.lock.json')
    require(read(out / 'plan.json') == plan, 'Saved plan differs from registry/lock')
    context = validate_plan(plan)
    require(file_hash(out / 'model-manifest.json') == context['model_sha256'], 'Saved model manifest mismatch')
    return plan, context
