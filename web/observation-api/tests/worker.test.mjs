import test from 'node:test';
import assert from 'node:assert/strict';
import worker,{periods,limitedBody,cleanup} from '../src/worker.mjs';

test('accepted upload reserves before PUT and duplicate receipt does not PUT again',async()=>{
  const calls=[];let row=null;
  const bytes=new Uint8Array([255,216,255,0]);
  const hash=Buffer.from(await crypto.subtle.digest('SHA-256',bytes)).toString('hex');
  const d={schema_version:'otw-observation-draft/0.1',client_submission_id:'11111111-1111-4111-8111-111111111111',description:'',observation_type:'addition',feature_id:null,camera_pose:null,fixture:true,review_status:'local_draft',consent:{evidence_storage:true,public_display:false,visual_map:false,model_training:false,policy_revision:'private-poc-v1'},image:{bytes:4,sha256:hash}};
  const request=()=>{const form=new FormData();form.set('observation',JSON.stringify(d));form.set('photo',new Blob([bytes],{type:'image/jpeg'}),'photo.jpg');return new Request('https://api.test/v1/observations',{method:'POST',headers:{Origin:'https://viewer.test',Authorization:'Bearer secret'},body:form});};
  const env={ALLOWED_ORIGIN:'https://viewer.test',INTAKE_ENABLED:'true',SUBMISSION_TOKEN:'secret',
    DB:{prepare(sql){let args;return {bind(...a){args=a;return this;},async first(){return row;},async run(){if(sql.startsWith('INSERT')){calls.push('reserve');row={fingerprint:args[1],status:'pending'};}else {calls.push('ready');row.status='ready';}}};}},
    PHOTOS:{async put(){calls.push('put');}}};
  assert.equal((await worker.fetch(request(),env)).status,201);
  assert.equal((await worker.fetch(request(),env)).status,200);
  assert.deepEqual(calls,['reserve','put','ready']);
  d.description='changed';assert.equal((await worker.fetch(request(),env)).status,409);
});

test('JST day and month roll over at 15:00 UTC',()=>{
  assert.deepEqual(periods(Date.parse('2026-09-30T14:59:59Z')),{day:'2026-09-30',month:'2026-09'});
  assert.deepEqual(periods(Date.parse('2026-09-30T15:00:00Z')),{day:'2026-10-01',month:'2026-10'});
});
test('streamed body cannot evade the byte limit',async()=>{
  const request=new Request('https://api.test',{method:'POST',body:'123456'});
  await assert.rejects(limitedBody(request,5),/body_limit/);
});
test('paused and unauthorized requests never access storage',async()=>{
  for(const [enabled,token,status] of [['false','secret',503],['true','wrong',401]]) {
    const result=await worker.fetch(new Request('https://api.test/v1/observations',{method:'POST',headers:{Origin:'https://viewer.test',Authorization:`Bearer ${token}`}}),{ALLOWED_ORIGIN:'https://viewer.test',INTAKE_ENABLED:enabled,SUBMISSION_TOKEN:'secret'});
    assert.equal(result.status,status);
  }
});
test('failed R2 deletion never releases reserved capacity',async()=>{
  let updated=false;
  const env={DB:{prepare(sql){return {bind(){return this;},async all(){return {results:[{id:'one'}]};},async run(){updated=true;}};}},PHOTOS:{async delete(){throw new Error('unavailable');}}};
  await assert.rejects(cleanup(env),/unavailable/);assert.equal(updated,false);
});
test('successful cleanup deletes photo before releasing capacity',async()=>{
  const calls=[];
  const env={DB:{prepare(sql){return {bind(){return this;},async all(){return {results:[{id:'one'}]};},async run(){calls.push(sql.startsWith('UPDATE')?'release':'prune');}};}},PHOTOS:{async delete(){calls.push('delete');}}};
  await cleanup(env);assert.deepEqual(calls,['delete','release','prune']);
});
