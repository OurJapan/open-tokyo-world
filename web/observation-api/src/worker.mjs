const MAX_BODY = 5100000;
const RETENTION = 30 * 86400000;
const json = (body, status=200) => Response.json(body, {status});
export function periods(now) {
  const date = new Date(now + 9 * 3600000).toISOString();
  return {day: date.slice(0,10), month: date.slice(0,7)};
}
export async function limitedBody(request, max=MAX_BODY) {
  if (Number(request.headers.get('content-length')) > max) throw new Error('body_limit');
  if (!request.body) throw new Error('invalid_payload');
  const reader=request.body.getReader(), chunks=[]; let size=0;
  while (true) {
    const {value,done}=await reader.read(); if(done)break;
    size+=value.byteLength;
    if(size>max){await reader.cancel();throw new Error('body_limit');}
    chunks.push(value);
  }
  return new Blob(chunks);
}
async function digest(bytes) {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)), b=>b.toString(16).padStart(2,'0')).join('');
}
export function validate(d, photo) {
  if (!d || d.schema_version!=='otw-observation-draft/0.1' ||
      !/^[a-f0-9-]{36}$/.test(d.client_submission_id) ||
      !['reality_difference','addition','outdated','digital_correction','no_issue'].includes(d.observation_type) ||
      typeof d.description!=='string' || d.description.length>2000 ||
      d.feature_id!==null || d.camera_pose!==null || d.fixture!==true ||
      d.review_status!=='local_draft' || d.consent?.evidence_storage!==true ||
      d.consent?.public_display!==false || d.consent?.visual_map!==false || d.consent?.model_training!==false ||
      d.consent?.policy_revision!=='private-poc-v1' ||
      !photo || photo.type!=='image/jpeg' || photo.size<3 || photo.size>5000000 ||
      d.image?.bytes!==photo.size) throw new Error('invalid_payload');
}
async function intake(request, env) {
  if(env.INTAKE_ENABLED!=='true')return json({error:'intake_paused'},503);
  if(!env.SUBMISSION_TOKEN || request.headers.get('Authorization')!==`Bearer ${env.SUBMISSION_TOKEN}`)
    return json({error:'unauthorized'},401);
  const body=await limitedBody(request);
  const form=await new Response(body,{headers:{'Content-Type':request.headers.get('Content-Type')||''}}).formData();
  const raw=form.get('observation'), photo=form.get('photo');
  if(typeof raw!=='string'||raw.length>50000)throw new Error('invalid_payload');
  const d=JSON.parse(raw); validate(d,photo);
  const bytes=await photo.arrayBuffer();
  const magic=new Uint8Array(bytes);
  if(magic[0]!==255||magic[1]!==216||magic[2]!==255||await digest(bytes)!==d.image.sha256)throw new Error('invalid_payload');
  const id=d.client_submission_id, fingerprint=await digest(new TextEncoder().encode(raw));
  const existing=await env.DB.prepare('SELECT status,fingerprint FROM observations WHERE id=?').bind(id).first();
  if(existing) return existing.fingerprint!==fingerprint ? json({error:'id_conflict'},409) :
    existing.status==='ready' ? json({observation_id:id},200) : json({error:'submission_pending_or_expired'},409);
  const now=Date.now(), {day,month}=periods(now);
  // Reserve before R2 I/O. Never release an uncertain write or retry its PUT.
  await env.DB.prepare('INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?)')
    .bind(id,fingerprint,photo.size,now,day,month,now+RETENTION,'pending',raw).run();
  await env.PHOTOS.put(`observations/${id}.jpg`,bytes,{httpMetadata:{contentType:'image/jpeg'}});
  await env.DB.prepare("UPDATE observations SET status='ready' WHERE id=? AND status='pending'").bind(id).run();
  return json({observation_id:id},201);
}
export async function cleanup(env, now=Date.now()) {
  const {results}=await env.DB.prepare("SELECT id FROM observations WHERE status!='deleted' AND expires_at<=? LIMIT 50").bind(now).all();
  for(const {id} of results) {
    await env.PHOTOS.delete(`observations/${id}.jpg`);
    // Capacity is released only after confirmed deletion; retain quota tombstones.
    await env.DB.prepare("UPDATE observations SET status='deleted',metadata=NULL WHERE id=?").bind(id).run();
  }
  // Keep tombstones through two months to prevent resetting current monthly quota.
  await env.DB.prepare("DELETE FROM observations WHERE status='deleted' AND created_at<?").bind(now-93*86400000).run();
}
export default {
  async fetch(request,env) {
    const origin=request.headers.get('Origin');
    if(origin!==env.ALLOWED_ORIGIN)return json({error:'origin_denied'},403);
    let response;
    if(new URL(request.url).pathname!=='/v1/observations')response=json({error:'not_found'},404);
    else if(request.method==='OPTIONS')response=new Response(null,{status:204});
    else if(request.method!=='POST')response=json({error:'method_not_allowed'},405);
    else try {response=await intake(request,env);} catch(e) {
      const code=['intake_paused','photo_limit','daily_limit','monthly_limit','storage_limit','body_limit','invalid_payload'].find(c=>String(e.message).includes(c));
      response=json({error:code||'temporarily_unavailable'},code?.endsWith('_limit')?429:code==='invalid_payload'?400:503);
    }
    response.headers.set('Access-Control-Allow-Origin',env.ALLOWED_ORIGIN);
    response.headers.set('Access-Control-Allow-Methods','POST, OPTIONS');
    response.headers.set('Access-Control-Allow-Headers','Authorization, Content-Type');
    response.headers.set('Vary','Origin'); response.headers.set('Cache-Control','no-store');
    return response;
  },
  async scheduled(_event,env) {await cleanup(env);}
};
