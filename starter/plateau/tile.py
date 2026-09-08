# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Strict reader for the pinned data221 profile, not a generic 3D Tiles reader."""
import hashlib
import json
import math
import struct

BASE = 'https://assets.cms.plateau.reearth.io/assets/c7/ffcc73-1d33-434b-a49a-aa0289160814/13103_minato-ku_pref_2025_citygml_1_op_bldg_3dtiles_13103_minato-ku_lod3/'
FILES = {
    'tileset.json': (BASE+'tileset.json', 412889, 'edec4c24d137eaf08a8525cecea505a3f21a30823b9ef4fb530e10774cea1323'),
    'data221.b3dm': (BASE+'data/data221.b3dm', 1246040, 'dc8c7539b2bb22d8c6659689c37aafa53b4896650bbd6bcfe7f791ab8b1a38d2'),
}
FEATURE_ID = 'bldg_433bc5b3-db73-4644-ac24-a28d51b7ecd5'


def verify(name, data):
    _, size, digest = FILES[name]
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('Pinned source mismatch: '+name)
    return data


def section(data, offset, length):
    if offset < 0 or length < 0 or offset+length > len(data):
        raise ValueError('Binary section outside buffer')
    return data[offset:offset+length]


def parse(data):
    if len(data) < 28:
        raise ValueError('Short b3dm')
    magic, version, size, fj, fb, bj, bb = struct.unpack_from('<4s6I', data)
    if magic != b'b3dm' or version != 1 or size != len(data) or fb != 0:
        raise ValueError('Unsupported b3dm header')
    ft = json.loads(section(data,28,fj))
    if ft != {'BATCH_LENGTH':24}:
        raise ValueError('Unexpected feature table')
    bt = json.loads(section(data,28+fj,bj))
    section(data,28+fj+bj,bb)
    glb = data[28+fj+bj+bb:]
    if len(glb)<20 or struct.unpack_from('<4sII',glb)!=(b'glTF',2,len(glb)):
        raise ValueError('Unsupported GLB header')
    n, typ = struct.unpack_from('<II',glb,12)
    if typ!=0x4E4F534A:
        raise ValueError('Missing JSON chunk')
    doc=json.loads(section(glb,20,n))
    length,typ=struct.unpack('<II',section(glb,20+n,8))
    if typ!=0x004E4942 or 28+n+length!=len(glb):
        raise ValueError('Invalid BIN chunk')
    binary=section(glb,28+n,length)
    if doc.get('nodes')!=[{'mesh':0}] or doc.get('scenes')!=[{'nodes':[0]}]:
        raise ValueError('Unsupported node transform/hierarchy')
    if len(doc['buffers'])!=1 or any('uri' in x for k in ['buffers','images'] for x in doc.get(k,[])):
        raise ValueError('External buffer/image unsupported')
    if set(doc.get('extensionsUsed',[]))!={'CESIUM_RTC','EXT_texture_webp','KHR_draco_mesh_compression'}:
        raise ValueError('Unexpected extensions')
    if doc['images']!=[{'mimeType':'image/webp','bufferView':0}]:
        raise ValueError('Unexpected image layout')
    ids=bt['gml_id']
    if len(ids)!=24 or len(set(ids))!=24 or ids[5]!=FEATURE_ID:
        raise ValueError('Unexpected feature identity')
    for view in doc['bufferViews']:
        if view.get('buffer')!=0: raise ValueError('Unexpected buffer')
        section(binary,view.get('byteOffset',0),view['byteLength'])
    return doc,binary,ids


def parent(data):
    node=json.loads(data)['root']
    for step in [None,1,2,0,3,0]:
        if step is not None: node=node['children'][step]
        if 'transform' in node: raise ValueError('Unexpected tile transform')
    if node['content']['uri']!='data/data221.b3dm':
        raise ValueError('Wrong selected tile')
    return node['boundingVolume']['region']


def enu(points, center):
    """numpy loaded only inside Blender; retain ECEF-derived ENU in float64."""
    import numpy as np
    p=np.asarray(points,dtype=np.float64)
    c=np.asarray(center,dtype=np.float64)
    if p.ndim!=2 or p.shape[1]!=3 or c.shape!=(3,) or not np.isfinite(p).all() or not np.isfinite(c).all():
        raise ValueError('Invalid coordinates')
    xyz=p[:,[0,2,1]]*np.array([1,-1,1])+c
    lon,lat=map(math.radians,[139.74543,35.65858])
    a,e2=6378137.,0.0066943799901413165
    n=a/math.sqrt(1-e2*math.sin(lat)**2)
    origin=np.array([n*math.cos(lat)*math.cos(lon),n*math.cos(lat)*math.sin(lon),n*(1-e2)*math.sin(lat)])
    rotation=np.array([[-math.sin(lon),math.cos(lon),0],[-math.sin(lat)*math.cos(lon),-math.sin(lat)*math.sin(lon),math.cos(lat)],[math.cos(lat)*math.cos(lon),math.cos(lat)*math.sin(lon),math.sin(lat)]])
    return (xyz-origin)@rotation.T


def decode(doc,binary):
    """Call Blender's installed Draco library; do not bundle the library."""
    import ctypes as c
    import numpy as np
    from io_scene_gltf2.io.com.draco import dll_path
    path=dll_path().resolve()
    lib=c.CDLL(str(path))
    signatures={
        'decoderCreate':(c.c_void_p,[]), 'decoderRelease':(None,[c.c_void_p]),
        'decoderDecode':(c.c_bool,[c.c_void_p,c.c_void_p,c.c_size_t]),
        'decoderReadAttribute':(c.c_bool,[c.c_void_p,c.c_uint32,c.c_size_t,c.c_char_p]),
        'decoderGetAttributeByteLength':(c.c_size_t,[c.c_void_p,c.c_uint32]),
        'decoderCopyAttribute':(None,[c.c_void_p,c.c_uint32,c.c_void_p]),
        'decoderReadIndices':(c.c_bool,[c.c_void_p,c.c_size_t]),
        'decoderGetIndicesByteLength':(c.c_size_t,[c.c_void_p]),
        'decoderCopyIndices':(None,[c.c_void_p,c.c_void_p]),
    }
    for name,(ret,args) in signatures.items():
        getattr(lib,name).restype=ret;getattr(lib,name).argtypes=args
    result=[]
    for prim in doc['meshes'][0]['primitives']:
        if prim.get('mode',4)!=4: raise ValueError('Only triangles supported')
        ext=prim['extensions']['KHR_draco_mesh_compression'];view=doc['bufferViews'][ext['bufferView']]
        payload=section(binary,view.get('byteOffset',0),view['byteLength'])
        decoder=lib.decoderCreate()
        if not decoder: raise ValueError('No Draco decoder')
        try:
            if not lib.decoderDecode(decoder,payload,len(payload)): raise ValueError('Draco failed')
            arrays={}
            for name in ['POSITION','_BATCHID','TEXCOORD_0']:
                if name not in prim['attributes']:
                    if name=='TEXCOORD_0': continue
                    raise ValueError('Missing attribute '+name)
                acc=doc['accessors'][prim['attributes'][name]];aid=ext['attributes'][name]
                expected={'POSITION':(5126,'VEC3',3),'_BATCHID':(5121,'SCALAR',1),'TEXCOORD_0':(5126,'VEC2',2)}[name]
                if (acc['componentType'],acc['type'])!=expected[:2]:raise ValueError('Unexpected accessor')
                if not lib.decoderReadAttribute(decoder,aid,acc['componentType'],acc['type'].encode()):raise ValueError('Attribute decode failed')
                size=lib.decoderGetAttributeByteLength(decoder,aid)
                if size!=acc['count']*expected[2]*(1 if name=='_BATCHID' else 4):raise ValueError('Attribute count mismatch')
                buf=c.create_string_buffer(size);lib.decoderCopyAttribute(decoder,aid,buf)
                arrays[name]=np.frombuffer(buf.raw,dtype='u1' if name=='_BATCHID' else '<f4').copy().reshape((-1,) if name=='_BATCHID' else (-1,expected[2]))
            if not lib.decoderReadIndices(decoder,5125):raise ValueError('Index decode failed')
            size=lib.decoderGetIndicesByteLength(decoder)
            if size!=doc['accessors'][prim['indices']]['count']*4:raise ValueError('Index count mismatch')
            buf=c.create_string_buffer(size);lib.decoderCopyIndices(decoder,buf)
            ix=np.frombuffer(buf.raw,dtype='<u4').copy().reshape(-1,3)
            batch=arrays['_BATCHID']
            if ix.max()>=len(batch) or batch.max()>=24 or not np.all(batch[ix]==batch[ix[:,0]][:,None]):raise ValueError('Mixed or invalid batch IDs')
            if not all(np.isfinite(a).all() for a in arrays.values()):raise ValueError('Nonfinite geometry/UV')
            result.append((arrays,ix,prim['material']))
        finally:
            lib.decoderRelease(decoder)
    if sum(len(ix) for _,ix,_ in result)!=4804:raise ValueError('Unexpected triangle count')
    return result,hashlib.sha256(path.read_bytes()).hexdigest()
