# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Fail-closed runner contracts without Blender, network or third-party assets."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'starter/mori'))
import plan_adapter as adapter
spec = importlib.util.spec_from_file_location('mori_plan_runner', ROOT / 'starter/mori/run.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class MoriPlanContracts(unittest.TestCase):
    def setUp(self):
        self.registry = adapter.read(ROOT / adapter.REGISTRY)
        self.lock = adapter.read(ROOT / adapter.LOCK)

    def reject_runner(self, registry=None, lock=None, expected='.', compile_effect=None):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            r = registry or self.registry
            l = lock or {**self.lock, 'registry_sha256': adapter.registry.digest(r)}
            for name, value in [('registry.json', r), ('lock.json', l)]:
                (folder / name).write_text(json.dumps(value), encoding='utf8')
            out = folder / 'absent-parent/output'
            with patch.object(runner.subprocess, 'run') as launch, patch.object(runner.urllib.request, 'urlopen') as network:
                with patch.object(adapter, 'compile_checked', side_effect=compile_effect) if compile_effect else patch.object(adapter, 'compile_checked', wraps=adapter.compile_checked):
                    with self.assertRaisesRegex(ValueError, expected):
                        runner.main(['--blender', sys.executable, '--registry', str(folder / 'registry.json'),
                                     '--lock', str(folder / 'lock.json'), '--output', str(out)])
                launch.assert_not_called()
                network.assert_not_called()
            self.assertFalse(out.parent.exists())

    def test_real_registry_fixed_manifest_and_stable_parts(self):
        plan = adapter.compile_checked()
        context = adapter.validate_plan(plan)
        self.assertEqual(len(context['source_ids']), 24)
        self.assertEqual(len(plan['parts']), 14)
        self.assertEqual(len(context['parts']), 13)
        self.assertEqual(len(plan['review_neighbors'][adapter.FEATURE]), 23)
        self.assertNotEqual(set(context['parts']), set(context['parts'].values()))
        self.assertEqual(set(context['parts'].values()), {p['object'] for p in adapter.read(ROOT / 'starter/mori/provenance.json')['parts']})
        suppressed = next(p for p in plan['parts'] if p['part'] == 'source-building')
        self.assertIsNone(suppressed['geometry'])
        self.assertEqual(suppressed['source_binding']['object_id'], adapter.tile.FEATURE_ID)

    def test_lock_mismatch_before_output_or_blender(self):
        self.lock['registry_sha256'] = '0' * 64
        self.reject_runner(lock=self.lock, expected='Registry lock mismatch')

    def test_relocked_mismatches_before_output_or_blender(self):
        cases = ['source-hash', 'source-inventory', 'target-id', 'part', 'model-hash', 'locator',
                 'operation', 'position', 'yaw', 'frame', 'profile', 'selection', 'neighbor-scope']
        for case in cases:
            with self.subTest(case=case):
                r = copy.deepcopy(self.registry)
                l = copy.deepcopy(self.lock)
                feature = r['features'][0]
                ops = feature['revisions'][0]['operations']
                if case == 'source-hash': r['sources'][0]['sha256'] = '0' * 64
                elif case == 'source-inventory': r['sources'][0]['object_ids'].reverse()
                elif case == 'target-id': feature['parts'][0]['source_binding']['object_id'] = r['sources'][0]['object_ids'][0]
                elif case == 'part':
                    feature['parts'][1]['id'] = 'unknown-part'
                    ops[1]['part'] = 'unknown-part'
                elif case == 'model-hash': r['models'][0]['sha256'] = '0' * 64
                elif case == 'locator': r['models'][0]['locator'] = 'https://example.invalid/execute.py'
                elif case == 'operation': ops.pop(0)
                elif case == 'position': ops[1]['position_m'][0] = 1
                elif case == 'yaw': ops[1]['yaw_degrees'] = 90
                elif case == 'frame': r['frames'][0]['definition'] = 'another origin'
                elif case == 'profile':
                    l['profile'] = 'far'
                    for op in ops[1:]: op['models'] = {'far': adapter.MODEL}
                elif case == 'selection':
                    feature['revisions'][0]['id'] = 'unreviewed'
                    l['selections'][0]['revision'] = 'unreviewed'
                elif case == 'neighbor-scope': feature['review_neighbors'].pop()
                l['registry_sha256'] = adapter.registry.digest(r)
                self.reject_runner(registry=r, lock=l)

    def test_candidate_and_review_only_refused_before_output_or_blender(self):
        self.registry['features'][0]['revisions'][0]['status'] = 'candidate'
        self.reject_runner(expected='Candidate requires')
        self.lock['registry_sha256'] = adapter.registry.digest(self.registry)
        plan = adapter.registry.compile_plan(self.registry, self.lock, allow_candidates=True)
        def review_plan(*args):
            adapter.validate_plan(plan)
            return plan
        self.reject_runner(expected='Review-only', compile_effect=review_plan)

    def test_manifest_parts_inventory_and_code_pins_are_enforced(self):
        compile_checked = adapter.compile_checked
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in [*adapter.CODE_FILES, adapter.REGISTRY, adapter.LOCK, adapter.MANIFEST, adapter.INVENTORY]:
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, root / name)
            self.assertTrue(adapter.compile_checked(root=root))
            for field in ['parts', 'code_sha256_lf', 'source_inventory_sha256']:
                with self.subTest(field=field):
                    manifest = adapter.read(ROOT / adapter.MANIFEST)
                    manifest[field] = {} if isinstance(manifest[field], dict) else '0' * 64
                    (root / adapter.MANIFEST).write_text(json.dumps(manifest), encoding='utf8')
                    self.reject_runner(compile_effect=lambda *args: compile_checked(root=root))
            shutil.copyfile(ROOT / adapter.MANIFEST, root / adapter.MANIFEST)
            for name in ['starter/mori/scene.py', 'starter/mori/plan_adapter.py', 'scripts/mori_entrance_v1.py', 'scripts/object_registry.py']:
                with self.subTest(code=name):
                    original = (root / name).read_bytes()
                    (root / name).write_bytes(original + b'\n# altered\n')
                    self.reject_runner(expected='code hash mismatch', compile_effect=lambda *args: compile_checked(root=root))
                    (root / name).write_bytes(original)

    def test_corrupt_source_never_creates_output_or_launches_blender(self):
        for bad_name in adapter.tile.FILES:
            with self.subTest(file=bad_name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                inputs = root / 'inputs'
                inputs.mkdir()
                for name in adapter.tile.FILES: (inputs / name).write_bytes(b'corrupt')
                real_verify = adapter.tile.verify
                def verify(name, raw):
                    return real_verify(name, raw) if name == bad_name else raw
                with patch.object(runner.tile, 'verify', side_effect=verify), patch.object(runner.subprocess, 'run') as launch:
                    with self.assertRaisesRegex(ValueError, 'Pinned source mismatch: ' + bad_name):
                        runner.main(['--blender', sys.executable, '--inputs', str(inputs), '--output', str(root / 'output')])
                    launch.assert_not_called()
                self.assertFalse((root / 'output').exists())

    def test_generic_planner_records_procedural_locator_without_execution(self):
        self.registry['models'][0]['locator'] = 'do-not-execute:arbitrary.py'
        self.lock['registry_sha256'] = adapter.registry.digest(self.registry)
        with patch('urllib.request.urlopen') as network:
            plan = adapter.registry.compile_plan(self.registry, self.lock)
            network.assert_not_called()
        self.assertEqual(plan['models'][adapter.MODEL]['locator'], 'do-not-execute:arbitrary.py')
        with self.assertRaisesRegex(ValueError, 'locator mismatch'): adapter.validate_plan(plan)

    def test_district_recipe_pins_all_execution_and_contract_files(self):
        import district_distribution as dist
        catalog = adapter.read(ROOT / 'manifests/district-distribution.json')
        lock = dist.plan(catalog, ['mori'], [])
        expected = {*adapter.CODE_FILES, adapter.INVENTORY, adapter.MANIFEST, adapter.REGISTRY, adapter.LOCK}
        self.assertTrue(expected <= set(lock['code_sha256_lf']))
        for name, pin in adapter.code_hashes().items(): self.assertEqual(lock['code_sha256_lf'][name], pin)


if __name__ == '__main__': unittest.main()
