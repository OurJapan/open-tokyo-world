import test from 'node:test';import assert from 'node:assert/strict';
import {createAutoUpload} from '../src/auto-upload.js';
function setup(submit){const rows=new Map();const store={async list(){return structuredClone([...rows.values()]);},async put(r){rows.set(r.id,structuredClone(r));}};const queue=createAutoUpload({store,submit});const add=id=>rows.set(id,{id,autoUpload:true,submissionSnapshot:{id,consent:{evidence_storage:true}},photo:new ArrayBuffer(1)});return {rows,queue,add};}
test('new capture during an in-flight upload is drained without another user action',async()=>{
 let release;const gate=new Promise(r=>{release=r;});const sent=[];const {rows,queue,add}=setup(async({draft})=>{sent.push(draft.id);if(draft.id==='one')await gate;return draft.id;});
 add('one');const running=queue.enable('secret');await new Promise(r=>setImmediate(r));add('two');await queue.pump();release();await running;
 assert.deepEqual(sent,['one','two']);assert.ok([...rows.values()].every(r=>r.receipt));assert.ok(!JSON.stringify([...rows.values()]).includes('secret'));
});
test('failure retains the original payload, stops retries, and never submits a local-only record',async()=>{
 let fail=true;const payloads=[];const {rows,queue,add}=setup(async({draft})=>{payloads.push(JSON.stringify(draft));if(fail)throw Error('offline');return draft.id;});
 add('one');rows.set('local',{id:'local',autoUpload:false});await queue.enable('secret');assert.equal(payloads.length,1);assert.equal(rows.get('one').uploadError,'offline');fail=false;await queue.pump();assert.equal(payloads[0],payloads[1]);assert.equal(rows.get('local').receipt,undefined);
});
test('stopping auto-send prevents subsequent queued photos from being dispatched',async()=>{
 let release;const gate=new Promise(r=>{release=r;});const sent=[];const {rows,queue,add}=setup(async({draft})=>{sent.push(draft.id);await gate;return draft.id;});add('one');add('two');const running=queue.enable('secret');await new Promise(r=>setImmediate(r));queue.disable();release();await running;assert.deepEqual(sent,['one']);assert.equal(rows.get('two').receipt,undefined);
});
