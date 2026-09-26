# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from component_contracts import reviewed_nodes, signature


class ReviewedComponentContracts(unittest.TestCase):
    def test_changed_source_is_rejected_even_outside_selected_range(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'old.py'
            source = b'x = 1\nprint("unselected")\n'
            pin = hashlib.sha256(source).hexdigest()
            path.write_bytes(source + b'print("changed")\n')
            with self.assertRaisesRegex(ValueError, 'Unreviewed legacy source'):
                reviewed_nodes(path, pin, [(1, 1)])

    def test_partial_block_cannot_be_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'old.py'
            source = b'for x in range(2):\n    print(x)\n'
            path.write_bytes(source)
            with self.assertRaisesRegex(ValueError, 'complete reviewed statements'):
                reviewed_nodes(path, hashlib.sha256(source).hexdigest(), [(2, 2)])

    def test_only_complete_approved_blocks_are_returned_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'old.py'
            source = b'raise RuntimeError("never execute")\nx = 2; y = 3\nfor i in range(2):\n    x += i\n'
            path.write_bytes(source)
            nodes = reviewed_nodes(path, hashlib.sha256(source).hexdigest(), [(2, 4)])
            self.assertEqual([(n.lineno, n.end_lineno) for n in nodes], [(2, 2), (2, 2), (3, 4)])

    def test_signature_rejects_non_finite_values(self):
        with self.assertRaises(ValueError):
            signature({'value': float('nan')})

    def test_exported_polygon_arrays_match_tuples_without_reordering_points(self):
        in_memory = [{'polygons': [[(1.25, 3.0), (2.0, 4.0)]], 'step': 2.7}]
        saved = [{'polygons': [[[1.25, 3.0], [2.0, 4.0]]], 'step': 2.7}]
        self.assertEqual(signature(in_memory), signature(saved))
        saved[0]['polygons'][0].reverse()
        self.assertNotEqual(signature(in_memory), signature(saved))


if __name__ == '__main__':
    unittest.main()
