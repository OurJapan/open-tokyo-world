import test from 'node:test';
import assert from 'node:assert/strict';
import {LOCAL_FEATURE,localReviewSelection,validateLocalManifest,validateLocalGlb,validateLocalMeasurements,localView} from '../src/local-review.js';

const manifest=()=>({schema_version:'otw-spatial-manifest/0.1',fixture:false,local_only:true,
  frame:{registration_status:'unregistered',units:'meters',render_axes:'east-up-south'},
  assets:[{feature_id:LOCAL_FEATURE,fixture:false,redistribution:'local-review-only',url:'model.glb',
    bytes:100,sha256:'a'.repeat(64),triangles:466,bounds_render_m:[-20,.32,-80,60,260,30]}]});

test('local profile is explicit and cannot be selected in production or via arbitrary paths',()=>{
  assert.equal(localReviewSelection('?area=tokyo-tower',true),null);
  assert.equal(localReviewSelection('?local_model=data221-af7335da',true).id,'data221-af7335da');
  for(const [query,dev] of [['?local_model=data221-af7335da',false],['?local_model=../private',true],['?local_model=data221-af7335da&local_model=data221-af7335da',true]])
    assert.throws(()=>localReviewSelection(query,dev));
});

test('single local source contract rejects different IDs, scales, public claims and capacity',()=>{
  assert.equal(validateLocalManifest(manifest()).feature_id,LOCAL_FEATURE);
  for(const mutate of [m=>m.fixture=true,m=>m.local_only=false,m=>m.assets.push({...m.assets[0]}),
    m=>m.frame.units='centimeters',m=>m.frame.registration_status='surveyed',
    m=>m.assets[0].feature_id='another-building',m=>m.assets[0].url='../model.glb',
    m=>m.assets[0].redistribution='approved',m=>m.assets[0].bytes=6*1024*1024,
    m=>m.assets[0].bounds_render_m[3]=-100,m=>m.assets[0].triangles=0]){
    const value=manifest();mutate(value);assert.throws(()=>validateLocalManifest(value));
  }
});

function glb(doc){
  const json=JSON.stringify(doc),length=Math.ceil(new TextEncoder().encode(json).length/4)*4;
  const buffer=new ArrayBuffer(20+length),view=new DataView(buffer);
  [0x46546c67,2,buffer.byteLength,length,0x4e4f534a].forEach((value,i)=>view.setUint32(i*4,value,true));
  new Uint8Array(buffer,20).fill(32);new Uint8Array(buffer,20).set(new TextEncoder().encode(json));return buffer;
}

test('local GLB uses embedded resources and rejects remote texture requests before loading',()=>{
  assert.equal(validateLocalGlb(glb({asset:{version:'2.0'},buffers:[{byteLength:0}],images:[{bufferView:0}]})).asset.version,'2.0');
  for(const document of [{buffers:[{uri:'https://example.invalid/model.bin'}]},{images:[{uri:'https://example.invalid/photo.png'}]}])
    assert.throws(()=>validateLocalGlb(glb(document)));
  assert.throws(()=>validateLocalGlb(new ArrayBuffer(2)));
});

test('loaded scene must retain its ID, triangle count and metre bounds',()=>{
  const asset=manifest().assets[0],measurement={bounds:[...asset.bounds_render_m],triangles:466,featureIds:[LOCAL_FEATURE]};
  validateLocalMeasurements(asset,measurement);
  for(const value of [{...measurement,triangles:465},{...measurement,featureIds:[]},
    {...measurement,bounds:measurement.bounds.map(v=>v/100)},{...measurement,bounds:[0,0,0,1,1,1]}])
    assert.throws(()=>validateLocalMeasurements(asset,value));
});

test('framing fits portrait and landscape views while preserving translated metre coordinates',()=>{
  const bounds=manifest().assets[0].bounds_render_m;
  for(const aspect of [.4,1,2]){
    const view=localView(bounds,aspect),distance=Math.hypot(...view.position.map((v,i)=>v-view.target[i]));
    const halfVertical=48*Math.PI/360,halfHorizontal=Math.atan(Math.tan(halfVertical)*aspect);
    assert.ok(Math.asin(view.radius/distance)<Math.min(halfVertical,halfHorizontal));
    const translated=localView(bounds.map((v,i)=>v+[1200,30,-600][i%3]),aspect);
    for(let i=0;i<3;i++)assert.ok(Math.abs(translated.position[i]-view.position[i]-[1200,30,-600][i])<1e-9);
  }
});
