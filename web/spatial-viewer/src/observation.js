import { fresh } from './spatial.js';
export const TYPES=['reality_difference','addition','outdated','digital_correction','no_issue'];
export function makeDraft({id,now,manifest,location,orientation,placement,pose,settings,width,height,assetVisible}) {
  return {
    schema_version:'otw-observation-draft/0.1',client_submission_id:id,observation_id:null,received_at:null,
    captured_at:new Date(now).toISOString(),time_source:'device-clock',clock_uncertainty_ms:null,
    observation_type:'reality_difference',description:'',
    location:fresh(location,now)?structuredClone(location):null,
    orientation:fresh(orientation,now,2000)?structuredClone(orientation):null,
    camera_pose:null, // No calibrated or localized camera pose in this spike.
    display_pose:pose?structuredClone(pose):null,
    camera_intrinsics:{status:'estimated',horizontal_fov_deg:60,width,height,crop:'none',mirrored:false},
    area_id:manifest.area_id,world_version:manifest.world_version,
    displayed_models:assetVisible?manifest.assets.map(a=>({asset_id:a.id,sha256:a.sha256,model_version:a.model_version,feature_id:null})):[],
    feature_id:null,part_id:null,feature_candidates:[],
    confidence:{pose:'unknown',feature:'unknown',reason:'fixture-only-no-localization'},
    image:{file:'photo.jpg',mime:'image/jpeg',width,height,sha256:null,bytes:null,overlay:false},
    device:{stream:{width:settings.width??null,height:settings.height??null,facing_mode:settings.facingMode??null}},
    source_user:null,consent:{evidence_storage:false,public_display:false,visual_map:false,model_training:false,policy_revision:'local-draft-v1'},
    review_status:'local_draft',placement,fixture:true,links:{},
  };
}
export function validateDraft(d) {
  if(d.schema_version!=='otw-observation-draft/0.1'||!TYPES.includes(d.observation_type))throw new Error('下書きの形式が不正です。');
  if(typeof d.description!=='string'||d.description.length>2000)throw new Error('コメントは2,000文字以内で入力してください。');
  if(d.feature_id!==null||d.camera_pose!==null||d.review_status!=='local_draft')throw new Error('検証モデルの観測は確定した地物や測定poseとして保存できません。');
  if(!d.image.sha256?.match(/^[a-f0-9]{64}$/)||d.image.bytes<=0)throw new Error('写真の検証に失敗しました。');
  return d;
}
export async function sha256(bytes) {
  const hash=await crypto.subtle.digest('SHA-256',bytes);
  return Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join('');
}
