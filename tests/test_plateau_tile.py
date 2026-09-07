# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import importlib.util
import json
import struct
import unittest
from pathlib import Path
from unittest.mock import patch

PATH=Path(__file__).resolve().parents[1]/'starter/plateau/tile.py'
spec=importlib.util.spec_from_file_location('plateau_tile_contract',PATH)
tile=importlib.util.module_from_spec(spec);spec.loader.exec_module(tile)


def fixture(change=None):
    ids=['bldg_'+str(i) for i in range(24)];ids[5]=tile.FEATURE_ID
    doc={'nodes':[{'mesh':0}],'scenes':[{'nodes':[0]}],'buffers':[{'byteLength':4}],
         'images':[{'mimeType':'image/webp','bufferView':0}],
         'extensionsUsed':['CESIUM_RTC','EXT_texture_webp','KHR_draco_mesh_compression'],
         'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':4}]}
    if change:change(doc)
    js=json.dumps(doc).encode();js+=b' '*(-len(js)%4)
    glb=struct.pack('<4sII',b'glTF',2,28+len(js)+4)+struct.pack('<II',len(js),0x4E4F534A)+js+struct.pack('<II',4,0x004E4942)+b'abcd'
    ft=json.dumps({'BATCH_LENGTH':24}).encode();bt=json.dumps({'gml_id':ids}).encode()
    return struct.pack('<4s6I',b'b3dm',1,28+len(ft)+len(bt)+len(glb),len(ft),0,len(bt),0)+ft+bt+glb


class TileTests(unittest.TestCase):
    def test_identity_and_embedded_buffer(self):
        doc,data,ids=tile.parse(fixture())
        self.assertEqual(data,b'abcd');self.assertEqual(ids[5],tile.FEATURE_ID)

    def test_truncated_and_wrong_version(self):
        for data in [b'',fixture()[:-1],fixture()[:4]+struct.pack('<I',2)+fixture()[8:]]:
            with self.assertRaises(ValueError):tile.parse(data)

    def test_external_image_rejected(self):
        with self.assertRaises(ValueError):tile.parse(fixture(lambda d:d['images'][0].update(uri='file:///private.png')))

    def test_unknown_transform_and_extension_rejected(self):
        for change in [lambda d:d['nodes'][0].update(translation=[1,0,0]),lambda d:d['extensionsUsed'].append('OTHER')]:
            with self.assertRaises(ValueError):tile.parse(fixture(change))

    def test_outside_buffer_rejected(self):
        with self.assertRaises(ValueError):tile.parse(fixture(lambda d:d['bufferViews'][0].update(byteLength=5)))

    def test_hash_not_only_size(self):
        import hashlib
        with patch.dict(tile.FILES,{'test':('https://example.invalid',3,hashlib.sha256(b'abc').hexdigest())}):
            self.assertEqual(tile.verify('test',b'abc'),b'abc')
            for data in [b'abd',b'abcd']:
                with self.assertRaises(ValueError):tile.verify('test',data)

    def test_parent_transform_rejected(self):
        leaf={'content':{'uri':'data/data221.b3dm'},'boundingVolume':{'region':[0]*6}}
        node=leaf
        for i in reversed([1,2,0,3,0]):
            children=[{} for _ in range(i+1)];children[i]=node;node={'children':children}
        self.assertEqual(tile.parent(json.dumps({'root':node})),[0]*6)
        node['transform']=[1]*16
        with self.assertRaises(ValueError):tile.parent(json.dumps({'root':node}))
