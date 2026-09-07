"""Emit a small original GLB fixture + public contract, without legacy meshes.

Run from anywhere with Python 3.12. Browser code consumes only emitted files.
The known feature registry is provenance, never a claim that the fixture is that feature.
"""
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'web/spatial-viewer/public/data'


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def glb():
    # Cube face vertices with outward normals; meter units, right-handed Y-up.
    faces = [
        ((0,0,1),[(-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)]),
        ((0,0,-1),[(.5,-.5,-.5),(-.5,-.5,-.5),(-.5,.5,-.5),(.5,.5,-.5)]),
        ((1,0,0),[(.5,-.5,.5),(.5,-.5,-.5),(.5,.5,-.5),(.5,.5,.5)]),
        ((-1,0,0),[(-.5,-.5,-.5),(-.5,-.5,.5),(-.5,.5,.5),(-.5,.5,-.5)]),
        ((0,1,0),[(-.5,.5,.5),(.5,.5,.5),(.5,.5,-.5),(-.5,.5,-.5)]),
        ((0,-1,0),[(-.5,-.5,-.5),(.5,-.5,-.5),(.5,-.5,.5),(-.5,-.5,.5)]),
    ]
    vertices=[v for _,vs in faces for v in vs]
    normals=[n for n,_ in faces for _ in range(4)]
    indices=[i*4+j for i in range(6) for j in (0,1,2,0,2,3)]
    data=struct.pack('<72f',*(x for v in vertices for x in v))+struct.pack('<72f',*(x for v in normals for x in v))+struct.pack('<36H',*indices)
    parts=[('base',[0,.25,0],[8,.5,8]),('deck',[0,8,0],[5,.5,5]),('top',[0,12,0],[2,.5,2]),('mast',[0,14,0],[.25,4,.25])]
    for x in (-2,2):
        for z in (-2,2): parts.append(('column',[x,4,z],[.45,8,.45]))
    for x in (-.7,.7):
        for z in (-.7,.7): parts.append(('upper',[x,10,z],[.3,4,.3]))
    nodes=[{'name':f'fixture-{name}-{i}','mesh':0,'translation':position,'scale':scale,'extras':{'fixture':True,'feature_id':None}} for i,(name,position,scale) in enumerate(parts)]
    doc={'asset':{'version':'2.0','generator':'OTW original device-test fixture v1'},'scene':0,'scenes':[{'nodes':list(range(len(nodes)))}],
         'nodes':nodes,'meshes':[{'primitives':[{'attributes':{'POSITION':0,'NORMAL':1},'indices':2,'material':0}]}],
         'materials':[{'name':'test-orange','pbrMetallicRoughness':{'baseColorFactor':[1,.24,.07,1],'metallicFactor':.1,'roughnessFactor':.7}}],
         'buffers':[{'byteLength':len(data)}],
         'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':288,'target':34962},{'buffer':0,'byteOffset':288,'byteLength':288,'target':34962},{'buffer':0,'byteOffset':576,'byteLength':72,'target':34963}],
         'accessors':[{'bufferView':0,'componentType':5126,'count':24,'type':'VEC3','min':[-.5,-.5,-.5],'max':[.5,.5,.5]},
                      {'bufferView':1,'componentType':5126,'count':24,'type':'VEC3'},
                      {'bufferView':2,'componentType':5123,'count':36,'type':'SCALAR'}]}
    text=encoded(doc);text+=b' '*((-len(text))%4);data+=b'\0'*((-len(data))%4)
    return struct.pack('<III',0x46546C67,2,12+8+len(text)+8+len(data))+struct.pack('<II',len(text),0x4E4F534A)+text+struct.pack('<II',len(data),0x004E4942)+data


def main():
    baseline=json.loads((ROOT/'manifests/legacy-baseline.json').read_text(encoding='utf-8'))
    features=json.loads((ROOT/'areas/tokyo-tower/features.json').read_text(encoding='utf-8'))
    model=glb();digest=hashlib.sha256(model).hexdigest()
    manifest={'schema_version':'otw-spatial-manifest/0.1','area_id':'tokyo-tower','fixture':True,
              'origin':baseline['coordinates'],
              'frame':{'id':'tokyo-tower-legacy-display','revision':'fixture-1','registration_status':'unregistered','units':'meters','render_axes':'east-up-south'},
              'known_features':[{'feature_id':f['id'],'status':f['status']} for f in features['features']],
              'source_refs':['manifests/legacy-baseline.json','areas/tokyo-tower/features.json'],
              'assets':[{'id':'device-test-structure','url':'device-test.glb','sha256':digest,'bytes':len(model),'feature_id':None,'fixture':True,
                         'model_version':'device-test-1','redistribution':'original-fixture-only','position_enu_m':[0,0,0],'triangles':144}]}
    manifest['world_version']='sha256:'+hashlib.sha256(encoded(manifest)).hexdigest()
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'device-test.glb').write_bytes(model)
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Generated original fixture: {len(model)} bytes; no legacy geometry or textures')


if __name__=='__main__':main()
