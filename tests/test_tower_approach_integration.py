# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Immutable input and conservative cross-task spatial guards."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from tower_approach_integration import pinned,xy_separation


class IntegrationGuards(unittest.TestCase):
    def test_only_exact_received_input_bytes_are_accepted_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'model.blend'; data = b'approved immutable fixture'
            path.write_bytes(data)
            pinned(path,hashlib.sha256(data).hexdigest())
            with self.assertRaisesRegex(ValueError,'Pinned integration input differs'):
                pinned(path,hashlib.sha256(data+b'edit').hexdigest())
            self.assertEqual(path.read_bytes(),data)

    def test_missing_model_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'Pinned integration input differs'):
                pinned(Path(directory)/'absent.blend','0'*64)

    def test_distance_uses_entire_bounds_in_both_axes(self):
        a = {'minimum':[0,0,0],'maximum':[2,2,10]}
        b = {'minimum':[5,6,0],'maximum':[8,9,300]}
        self.assertEqual(xy_separation(a,b),5)
        self.assertEqual(xy_separation(b,a),5)

    def test_touching_or_overlapping_boxes_have_no_clearance(self):
        a = {'minimum':[0,0,0],'maximum':[2,2,10]}
        for low in ([2,1,0],[1,1,0]):
            self.assertEqual(xy_separation(a,{'minimum':low,'maximum':[5,5,50]}),0)

    def test_nan_cannot_be_hidden_by_zero_clamp(self):
        a = {'minimum':[0,0,0],'maximum':[2,2,10]}
        with self.assertRaisesRegex(ValueError,'Non-finite'):
            xy_separation(a,{'minimum':[float('nan'),4,0],'maximum':[5,5,20]})

    def test_reversed_or_malformed_bounds_are_rejected(self):
        a = {'minimum':[0,0,0],'maximum':[2,2,10]}
        for box in ({'minimum':[5,0,0],'maximum':[4,2,10]},
                    {'minimum':[5,0],'maximum':[6,2,10]}):
            with self.assertRaises(ValueError): xy_separation(a,box)


if __name__ == '__main__': unittest.main()
