// Run only against a freshly migrated, enabled local Wrangler database.
// Deliberately fixed loopback URL and dummy credential: never targets production.
import assert from 'node:assert/strict';
const url='http://127.0.0.1:8787/v1/observations';
const photo=new Uint8Array([255,216,255,0]);
const sha256=Buffer.from(await crypto.subtle.digest('SHA-256',photo)).toString('hex');
const draft=id=>({schema_version:'otw-observation-draft/0.1',client_submission_id:id,
  description:'Local quota test',observation_type:'no_issue',feature_id:null,camera_pose:null,
  fixture:true,review_status:'local_draft',image:{bytes:photo.length,sha256},
  consent:{evidence_storage:true,public_display:false,visual_map:false,model_training:false,policy_revision:'private-poc-v1'}});
async function send(d,token='local-test-only') {
  const form=new FormData();form.set('observation',JSON.stringify(d));
  form.set('photo',new Blob([photo],{type:'image/jpeg'}),'photo.jpg');
  const r=await fetch(url,{method:'POST',headers:{Origin:'https://ourjapan.github.io',Authorization:`Bearer ${token}`},body:form});
  return {status:r.status,body:await r.json()};
}
assert.equal((await send(draft(crypto.randomUUID()),'wrong')).status,401);
const first=draft(crypto.randomUUID());
assert.equal((await send(first)).status,201);
assert.equal((await send(first)).status,200);
const results=await Promise.all(Array.from({length:35},()=>send(draft(crypto.randomUUID()))));
assert.equal(results.filter(r=>r.status===201).length,29,JSON.stringify(results));
assert.equal(results.filter(r=>r.status===429&&r.body.error==='daily_limit').length,6);
assert.equal((await send(first)).status,200,'Existing receipt still works when quota is exhausted');
console.log('PASS: unauthorized rejected; duplicate reused; 36 unique concurrent/serial submissions accept exactly 30; existing receipt works after exhaustion.');
