// Manual only: consumes one real post. Run with temporary daily_posts=1.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
if(!process.argv.includes('--confirm-live-test'))throw new Error('Explicit --confirm-live-test required');
const endpoint='https://otw-observation-api.open-tokyo-world-observation-api.workers.dev/v1/observations';
const token=(await readFile('.submission-token','utf8')).trim();
const photo=await readFile('.wrangler/smoke.jpg');
const sha256=Buffer.from(await crypto.subtle.digest('SHA-256',photo)).toString('hex');
const d={schema_version:'otw-observation-draft/0.1',client_submission_id:crypto.randomUUID(),
  description:'Deployment smoke test: generated image, no personal or location data.',
  observation_type:'no_issue',feature_id:null,camera_pose:null,fixture:true,review_status:'local_draft',
  image:{bytes:photo.length,sha256},
  consent:{evidence_storage:true,public_display:false,visual_map:false,model_training:false,policy_revision:'private-poc-v1'}};
// Save ID before network activity so an interrupted test is traceable.
await writeFile('.wrangler/remote-smoke.json',JSON.stringify(d,null,2));
async function send(d,credential=token){
  const form=new FormData();form.set('observation',JSON.stringify(d));form.set('photo',new Blob([photo],{type:'image/jpeg'}),'photo.jpg');
  const response=await fetch(endpoint,{method:'POST',headers:{Origin:'https://ourjapan.github.io',Authorization:`Bearer ${credential}`},body:form});
  return {status:response.status,body:await response.json()};
}
assert.equal((await send(d,'invalid')).status,401);
const accepted=await send(d);assert.equal(accepted.status,201,JSON.stringify(accepted));
assert.equal((await send(d)).status,200);
const over=await send({...d,client_submission_id:crypto.randomUUID()});
assert.equal(over.status,429,JSON.stringify(over));assert.equal(over.body.error,'daily_limit');
console.log(JSON.stringify({result:'PASS',receipt:d.client_submission_id,checks:['unauthorized','upload','idempotency','daily_limit']}));
