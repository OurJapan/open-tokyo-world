import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {selectedArea} from '../src/areas.js';
import {geoGate} from '../src/spatial.js';
import {makeDraft,sha256} from '../src/observation.js';
const load=name=>JSON.parse(readFileSync(new URL('../public/data/'+name,import.meta.url)));
const m=load('manifest-iidabashi.json'),tokyo=load('manifest.json');
test('area query is allowlisted and default stays Tokyo',()=>{
 assert.equal(selectedArea('').id,'tokyo-tower');assert.equal(selectedArea('?area=iidabashi').manifest,'manifest-iidabashi.json');
 assert.throws(()=>selectedArea('?area=../../secret'));assert.throws(()=>selectedArea('?area=constructor'));
});
test('Iidabashi fixes pass only the local gate; distant and inaccurate fixes fail',()=>{
 const now=20000,l={...m.origin,timestamp:now,accuracy_m:5},o={timestamp:now,reference:'earth-frame'};
 assert.equal(geoGate(l,o,m.origin,300,now).ok,true);
 assert.equal(geoGate(l,o,tokyo.origin,300,now).ok,false);
 assert.equal(geoGate({...l,latitude:l.latitude+.004},o,m.origin,300,now).ok,false);
 assert.equal(geoGate({...l,accuracy_m:51},o,m.origin,300,now).ok,false);
});
test('Iidabashi provenance, model hash and photo area remain separate from Tokyo',async()=>{
 const a=m.assets[0];assert.equal(await sha256(readFileSync(new URL('../public/data/'+a.url,import.meta.url))),a.sha256);
 assert.notEqual(m.world_version,tokyo.world_version);assert.equal(m.frame.id,'iidabashi-test-display');
 assert.deepEqual(m.known_features,[]);assert.equal(a.feature_id,null);
 const d=makeDraft({id:'test',now:20000,manifest:m,placement:'geo',pose:{frame:m.frame.id},settings:{},width:100,height:100,assetVisible:true});
 assert.equal(d.area_id,'iidabashi');assert.equal(d.display_pose.frame,m.frame.id);assert.equal(d.feature_id,null);
});
