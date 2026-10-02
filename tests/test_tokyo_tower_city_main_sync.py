import copy
import importlib.util
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sync', ROOT / 'scripts/tokyo_tower_city_main_sync.py')
sync = importlib.util.module_from_spec(spec); spec.loader.exec_module(sync)

class WoodlandPreservation(unittest.TestCase):
    def fixture(self):
        old = {key: {'existing': 'hash'} for key in ('objects', 'materials', 'collections', 'images', 'scene')}
        ref = {key: {'woodland': 'reviewed'} for key in ('objects', 'materials', 'collections')}
        new = copy.deepcopy(old)
        for key in ref: new[key].update(ref[key])
        return old, new, ref

    def test_exact_reviewed_addition_passes(self):
        sync.require_append(*self.fixture())

    def test_existing_or_reviewed_state_change_fails(self):
        for key in ('objects', 'materials', 'collections', 'images', 'scene'):
            args = self.fixture(); args[1][key]['existing'] = 'changed'
            with self.subTest(key=key), self.assertRaises(ValueError): sync.require_append(*args)
        args = self.fixture(); args[1]['objects']['woodland'] = 'changed'
        with self.assertRaises(ValueError): sync.require_append(*args)

    def test_duplicate_or_extra_object_fails(self):
        args = self.fixture(); args[0]['objects']['woodland'] = 'conflict'
        with self.assertRaises(ValueError): sync.require_append(*args)
        args = self.fixture(); args[1]['objects']['extra'] = 'unexpected'
        with self.assertRaises(ValueError): sync.require_append(*args)
