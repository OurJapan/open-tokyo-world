import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {makeDraft,validateDraft,sha256} from '../src/observation.js';
import {zipSync,unzipSync,strToU8,strFromU8} from 'fflate';
const manifest=JSON.parse(await readFile(new URL('../public/data/manifest.json',import.meta.url)));
const base={id:'test',now:20000,manifest,location:{timestamp:20000,latitude:1},orientation:{timestamp:20000,alpha:1},placement:'device-test',pose:{position_render_m:[0,1.6,0]},settings:{},width:960,height:720,assetVisible:true};
test('capture snapshots do not mutate when live sensors change',()=>{
  const input=structuredClone(base),draft=makeDraft(input);input.location.latitude=9;input.pose.position_render_m[0]=10;
  assert.equal(draft.location.latitude,1);assert.equal(draft.display_pose.position_render_m[0],0);
  assert.equal(draft.camera_pose,null);assert.equal(draft.feature_id,null);assert.equal(draft.observation_id,null);
  assert.equal(draft.review_status,'local_draft');assert.equal(draft.image.overlay,false);
  assert.equal(draft.consent.visual_map,false);assert.equal(draft.consent.public_display,false);
});
test('old sensor data is omitted and invisible assets are not reported as displayed',()=>{
  const d=makeDraft({...base,now:40000,assetVisible:false});assert.equal(d.location,null);assert.equal(d.orientation,null);assert.deepEqual(d.displayed_models,[]);
});
test('hash binds image bytes and ZIP round-trips snapshot and photo',async()=>{
  const photo=new Uint8Array([255,216,255,217]),d=makeDraft(base);d.image.sha256=await sha256(photo);d.image.bytes=photo.length;
  assert.equal(validateDraft(d),d);
  const archive=unzipSync(zipSync({'observation.json':strToU8(JSON.stringify(d)),'photo.jpg':photo}));
  const restored=JSON.parse(strFromU8(archive['observation.json']));
  assert.equal(await sha256(archive['photo.jpg']),restored.image.sha256);
  assert.throws(()=>validateDraft({...d,feature_id:'invented'}));
  assert.throws(()=>validateDraft({...d,description:'x'.repeat(2001)}));
  assert.throws(()=>validateDraft({...d,observation_type:'execute-python'}));
});
test('public fixture is a valid length-bounded GLB with no legacy ID assignment',async()=>{
  const a=manifest.assets[0],bytes=await readFile(new URL('../public/data/'+a.url,import.meta.url));
  assert.equal(await sha256(bytes),a.sha256);assert.equal(bytes.length,a.bytes);assert.ok(bytes.length<5*1024*1024);
  assert.equal(bytes.readUInt32LE(0),0x46546c67);assert.equal(bytes.readUInt32LE(4),2);assert.equal(bytes.readUInt32LE(8),bytes.length);
  const length=bytes.readUInt32LE(12),gltf=JSON.parse(bytes.subarray(20,20+length).toString());
  assert.equal(gltf.asset.version,'2.0');assert.ok(gltf.nodes.every(n=>n.extras.fixture&&n.extras.feature_id===null));
  assert.equal(manifest.origin.latitude,35.65858);assert.equal(manifest.origin.vertical_datum,'unknown');
  assert.equal(manifest.frame.registration_status,'unregistered');
});
