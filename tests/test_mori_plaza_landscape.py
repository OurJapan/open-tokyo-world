# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import copy
from collections import Counter
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import mori_plaza_landscape_v1 as landscape
from review import validate_patch


def fixture():
    a, b, c, d = [[-410, 310], [-400, 310], [-400, 320], [-410, 320]]
    return {'version': 1, 'input_sha256': landscape.INPUT_SHA256,
            'sources': {n:s[1] for n,s in landscape.SOURCE_FILES.items()},
            'park_ids': landscape.PARK_IDS, 'top_z': landscape.TOP_Z, 'bottom_z': landscape.BOTTOM_Z,
            'lawn_triangles': [[a,b,c]], 'paving_triangles': [[a,b,c],[a,c,d]],
            'paving_rings': [[a,b,c,d]], 'connector_triangles': [[a,b,c]], 'audit': {}}


class LandscapeTests(unittest.TestCase):
    def test_paving_is_closed_and_oriented(self):
        vertices, faces = landscape.paving_mesh(fixture())
        edges = Counter(tuple(sorted((a,b))) for f in faces for a,b in zip(f,f[1:]+f[:1]))
        directed = Counter((a,b) for f in faces for a,b in zip(f,f[1:]+f[:1]))
        self.assertTrue(edges)
        self.assertEqual(set(edges.values()), {2})
        self.assertTrue(all(directed[(b,a)]==count for (a,b),count in directed.items()))
        self.assertEqual(len(vertices),8)
        self.assertEqual(len(faces),8)
        self.assertTrue(all(p[2] in (landscape.outline.f32(.11),landscape.outline.f32(-.01)) for p in vertices))

    def test_hole_boundary_remains_open_in_plan_but_slab_is_closed(self):
        p = fixture()
        a,b,c,d=p['paving_rings'][0]
        e,f,g,h=[[-408,312],[-402,312],[-402,318],[-408,318]]
        p['paving_rings']=[[a,b,c,d],[e,h,g,f]]
        p['paving_triangles']=[[a,b,f],[a,f,e],[b,c,g],[b,g,f],[c,d,h],[c,h,g],[d,a,e],[d,e,h]]
        vertices,faces=landscape.paving_mesh(p)
        edges=Counter(tuple(sorted((a,b))) for face in faces for a,b in zip(face,face[1:]+face[:1]))
        self.assertEqual(set(edges.values()),{2})
        area=sum(landscape.outline.signed_area(t) for t in p['paving_triangles'])
        self.assertAlmostEqual(area,64)

    def test_plan_rejects_other_city_source_or_height(self):
        p=fixture()
        landscape.validate_plan(p)
        for key,value in [('input_sha256','0'*64),('sources',{}),('park_ids',[]),('top_z',.46)]:
            bad=copy.deepcopy(p);bad[key]=value
            with self.assertRaises(ValueError):landscape.validate_plan(bad)

    def test_plan_rejects_nonfinite_faraway_and_degenerate_geometry(self):
        for triangle in [[[-410,310],[math.nan,311],[-402,320]],
                         [[0,0],[1,0],[1,1]],
                         [[-410,310],[-400,320],[-400,310]],
                         [[-410,310],[-405,315],[-400,320]]]:
            bad=fixture();bad['lawn_triangles']=[triangle]
            with self.assertRaises(ValueError):landscape.validate_plan(bad)

    def test_mutated_plan_is_not_loaded(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'plan.json'
            path.write_text(json.dumps(fixture()),encoding='utf-8')
            digest=landscape.digest(path)
            landscape.load_plan(path,digest)
            path.write_text(path.read_text(encoding='utf-8')+' ',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'hash differs'):landscape.load_plan(path,digest)

    def test_changed_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source';path.write_bytes(b'fixed')
            with patch.dict(landscape.SOURCE_FILES,{'source':(5,landscape.digest(path))},clear=True):
                landscape.verify_sources(folder)
                path.write_bytes(b'other')
                with self.assertRaises(ValueError):landscape.verify_sources(folder)

    def test_connector_starts_on_adopted_paving_end(self):
        points=landscape.connector_edges()
        self.assertEqual(points[0],(-3.5,32.))
        self.assertEqual(points[-1],(3.5,32.))
        self.assertTrue(all(-23<u<5 and 30<v<49 for u,v in points))

    def test_patch_scope_is_exact_and_standalone(self):
        p=json.loads((ROOT/'patches/mori-plaza-landscape-v1.json').read_text(encoding='utf-8'))
        validate_patch(p)
        for key,value in [('park_mesh_sha256','0'*64),('added_objects',['other']),('object','ground')]:
            bad=copy.deepcopy(p);bad['operations'][0][key]=value
            with self.assertRaises(ValueError):validate_patch(bad)
        p['operations'].append(copy.deepcopy(p['operations'][0]))
        with self.assertRaises(ValueError):validate_patch(p)
