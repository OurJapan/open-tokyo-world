import contextlib
import copy
import importlib.util
import io
import math
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('plateau_evidence', ROOT / 'scripts/plateau_evidence.py')
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.audit, self.tile = evidence.load_audit()
        self.records = evidence.index_records(self.audit)

    def saved_georeference(self):
        return {
            'origin': {'longitude': 139.74543, 'latitude': 35.65858, 'ellipsoid_height': 0},
            'features': [
                {'gml_id': row['gml_id'], 'batch_id': row['batch_id'], 'triangles': row['triangles'],
                 'source_enu_min': list(row['source_enu_min_m']),
                 'source_enu_max': list(row['source_enu_max_m']),
                 'legacy_z_shift_m': row['legacy_z_shift_m']}
                for row in self.records
            ],
        }

    def test_all_identities_and_replacement_lookup(self):
        self.assertEqual(len(self.records), 24)
        self.assertEqual(sum(row['triangles'] for row in self.records), 4804)
        for row in self.records:
            self.assertEqual(evidence.select_records(self.records, feature=row['gml_id']), [row])
        mori = [row for row in self.records if row['replacement']]
        self.assertEqual(len(mori), 1)
        self.assertEqual(mori[0]['batch_id'], 5)
        self.assertEqual(mori[0]['scene_lookup']['mori_after_property'], 'otw_feature_id')
        self.assertAlmostEqual(mori[0]['legacy_z_shift_m'], -55.02574326150053)
        self.assertEqual(mori[0]['audit_ref'], 'docs/plateau-data221.json#/features/5')
        with self.assertRaisesRegex(ValueError, 'Unknown data221'):
            evidence.select_records(self.records, feature='bldg_unverified')

    def test_near_search_uses_bounds_including_edges_and_empty_results(self):
        north = evidence.select_records(self.records, near=(-430, 390), radius_m=20)
        self.assertEqual([row['batch_id'] for row in north], [15])
        self.assertEqual(north[0]['distance_to_xy_bbox_m'], 0)
        self.assertEqual(evidence.select_records(self.records, near=(0, 0), radius_m=1), [])
        row = self.records[0]
        lo, hi = row['source_enu_min_m'], row['source_enu_max_m']
        near = (lo[0] - 5, (lo[1] + hi[1]) / 2)
        self.assertEqual(evidence.select_records([row], near=near, radius_m=4.99), [])
        hit = evidence.select_records([row], near=near, radius_m=5)
        self.assertAlmostEqual(hit[0]['distance_to_xy_bbox_m'], 5)
        same_distance = evidence.select_records(self.records, near=(-490, 365), radius_m=0)
        self.assertEqual([row['batch_id'] for row in same_distance], [2, 15])

    def test_invalid_query_coordinates_are_rejected(self):
        for near, radius in [((math.nan, 1), 30), ((1, math.inf), 30), ((1, 1), -1), ((1, 1), math.nan)]:
            with self.subTest(near=near, radius=radius), self.assertRaises(ValueError):
                evidence.select_records(self.records, near=near, radius_m=radius)

    def test_identity_and_bounds_corruption_are_rejected(self):
        for mutation in [
            lambda a: a['features'][0].update(gml_id=a['features'][1]['gml_id']),
            lambda a: a['features'][0].update(batch_id=1),
            lambda a: a.update(replacement_candidate_gml_id='bldg_unverified'),
            lambda a: a['features'][0].update(triangles=0),
            lambda a: a['features'][0].update(enu_min=[math.nan, 0, 0]),
            lambda a: a['features'][0].update(enu_min=list(a['features'][0]['enu_max'])),
        ]:
            audit = copy.deepcopy(self.audit)
            mutation(audit)
            with self.assertRaises(ValueError):
                evidence.index_records(audit)

    def test_document_table_is_current_and_stale_values_fail(self):
        document = (ROOT / evidence.DOCUMENT).read_text(encoding='utf8')
        self.assertEqual(evidence.check_document(self.records, document)['features'], 24)
        table = evidence.markdown_table(self.records)
        for bad in [document.replace(table, table.replace('236.33', '236.00')),
                    document.replace(evidence.START, ''), document + evidence.END]:
            with self.assertRaises(ValueError):
                evidence.check_document(self.records, bad)

    def test_saved_origin_identity_and_coordinates_are_checked(self):
        saved = self.saved_georeference()
        self.assertEqual(evidence.check_georeference(self.records, saved)['features'], 24)
        for mutation in [
            lambda s: s['origin'].update(latitude=35.65859),
            lambda s: s['features'].pop(),
            lambda s: s['features'][0].update(gml_id=s['features'][1]['gml_id']),
            lambda s: s['features'][0].update(batch_id=1),
            lambda s: s['features'][0].update(triangles=947),
            lambda s: s['features'][0]['source_enu_min'].__setitem__(0, -461),
            lambda s: s['features'][0].update(legacy_z_shift_m=0.32),
            lambda s: s['features'][0].update(legacy_z_shift_m=math.nan),
        ]:
            corrupted = copy.deepcopy(saved)
            mutation(corrupted)
            with self.assertRaises(ValueError):
                evidence.check_georeference(self.records, corrupted)

    def test_batch_binary_columns_respect_buffer_bounds(self):
        import struct
        table = {'_lod': {'type': 'SCALAR', 'componentType': 'BYTE', 'byteOffset': 0}}
        self.assertEqual(evidence.batch_values(table, struct.pack('<24b', *([2] * 24)), '_lod', self.tile), [2] * 24)
        table['_lod']['byteOffset'] = 1
        with self.assertRaises(ValueError):
            evidence.batch_values(table, b'\x02' * 24, '_lod', self.tile)

    def test_local_source_and_existing_output_mismatch_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / 'tileset.json').write_bytes(b'unpinned source')
            with self.assertRaisesRegex(ValueError, 'Pinned source mismatch'):
                evidence.check_inputs(self.audit, self.tile, folder)
            report = folder / 'existing.json'
            report.write_text('preserve this result', encoding='utf8')
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                self.assertEqual(evidence.main(['--output', str(report)]), 1)
            self.assertIn('File exists', errors.getvalue())
            self.assertEqual(report.read_text(encoding='utf8'), 'preserve this result')


if __name__ == '__main__':
    unittest.main()
