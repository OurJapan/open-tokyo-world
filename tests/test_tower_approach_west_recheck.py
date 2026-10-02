# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Do not reuse accepted footway metrics after a stored mesh change."""
from pathlib import Path
import sys
import tempfile
import unittest
try:
    import numpy as np
except ImportError:
    np = None

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
if np is not None:
    from tower_approach_west_recheck import arrays_equal


@unittest.skipIf(np is None,'Optional NumPy needed for saved-scene array replay')
class WestReplayGuards(unittest.TestCase):
    def test_same_arrays_can_be_repacked_without_geometry_change(self):
        with tempfile.TemporaryDirectory() as folder:
            b,a = Path(folder)/'reference.npz',Path(folder)/'repacked.npz'
            data = np.array([[0,0,.46],[1,0,.46]],dtype=np.float32)
            np.savez(b,vertices=data); np.savez_compressed(a,vertices=data)
            self.assertEqual(arrays_equal(b,a),['vertices'])

    def test_height_or_dtype_change_blocks_metric_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            b,a = Path(folder)/'reference.npz',Path(folder)/'changed.npz'
            data = np.array([[0,0,.46],[1,0,.46]],dtype=np.float32); np.savez(b,vertices=data)
            changed = data.copy(); changed[0,2] += .0001
            for value in (changed,data.astype(np.float64)):
                np.savez(a,vertices=value)
                with self.assertRaisesRegex(ValueError,'West saved array changed'):
                    arrays_equal(b,a)


if __name__ == '__main__': unittest.main()
