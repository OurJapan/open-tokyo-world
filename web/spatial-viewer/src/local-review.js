// One explicit, read-only development profile. Production never opts into it.
export const LOCAL_FEATURE='bldg_af7335da-7542-44dd-964d-8cccd2b046ff';
export const LOCAL_PROFILE='data221-af7335da';
export const LOCAL_MANIFEST='/__otw_local__/data221-af7335da/manifest.json';
export const MAX_LOCAL_BYTES=5*1024*1024;

export function localReviewSelection(search,dev=false){
  const parameters=new URLSearchParams(search),values=parameters.getAll('local_model');
  if(!values.length)return null;
  if(!dev)throw new Error('ローカル建物表示は開発serverで開いてください。');
  if(values.length!==1||values[0]!==LOCAL_PROFILE)throw new Error('未対応のローカル建物です。');
  return {id:LOCAL_PROFILE,manifest:LOCAL_MANIFEST};
}

export function validateLocalManifest(manifest){
  if(manifest.schema_version!=='otw-spatial-manifest/0.1'||manifest.fixture!==false||manifest.local_only!==true
     ||manifest.assets?.length!==1||manifest.frame?.registration_status!=='unregistered'
     ||manifest.frame.units!=='meters'||manifest.frame.render_axes!=='east-up-south')
    throw new Error('ローカル建物のmanifestが未対応です。');
  const asset=manifest.assets[0];
  if(asset.feature_id!==LOCAL_FEATURE||asset.fixture!==false||asset.redistribution!=='local-review-only'
     ||asset.url!=='model.glb'||!Number.isSafeInteger(asset.bytes)||asset.bytes<=0||asset.bytes>MAX_LOCAL_BYTES
     ||!/^[a-f0-9]{64}$/.test(asset.sha256)||asset.triangles!==466)
    throw new Error('ローカル建物のID・容量・出典範囲が一致しません。');
  const bounds=asset.bounds_render_m;
  if(!Array.isArray(bounds)||bounds.length!==6||bounds.some(n=>!Number.isFinite(n))
     ||bounds.slice(0,3).some((n,i)=>n>=bounds[i+3]))throw new Error('建物の範囲・尺度が不正です。');
  return asset;
}

export function validateLocalGlb(bytes){
  const view=new DataView(bytes);
  if(bytes.byteLength<20||view.getUint32(0,true)!==0x46546c67||view.getUint32(4,true)!==2
     ||view.getUint32(8,true)!==bytes.byteLength||view.getUint32(16,true)!==0x4e4f534a)
    throw new Error('ローカルGLBの形式が不正です。');
  const length=view.getUint32(12,true);
  if(length>bytes.byteLength-20)throw new Error('ローカルGLBが途中で切れています。');
  const document=JSON.parse(new TextDecoder().decode(new Uint8Array(bytes,20,length)).trim());
  if(document.buffers?.some(buffer=>buffer.uri!==undefined)||document.images?.some(image=>image.uri!==undefined||!Number.isInteger(image.bufferView)))
    throw new Error('ローカルGLBの画像とbufferは内蔵してください。');
  return document;
}

export function validateLocalMeasurements(asset,{bounds,triangles,featureIds}){
  if(triangles!==asset.triangles||featureIds.length!==1||featureIds[0]!==asset.feature_id
     ||bounds.length!==6||bounds.some((n,i)=>!Number.isFinite(n)||Math.abs(n-asset.bounds_render_m[i])>1e-3))
    throw new Error('GLBの建物ID・形状範囲・三角形数がmanifestと一致しません。');
}

export function localView(bounds,aspect=1,verticalFov=48){
  if(!Number.isFinite(aspect)||aspect<=0)throw new Error('表示領域が不正です。');
  const size=bounds.slice(0,3).map((n,i)=>bounds[i+3]-n);
  const target=bounds.slice(0,3).map((n,i)=>(n+bounds[i+3])/2);
  const radius=Math.hypot(...size)/2,halfVertical=verticalFov*Math.PI/360;
  const halfHorizontal=Math.atan(Math.tan(halfVertical)*aspect);
  const distance=radius/Math.sin(Math.min(halfVertical,halfHorizontal))*1.12;
  const direction=[1,.45,.55],length=Math.hypot(...direction);
  return {target,position:target.map((n,i)=>n+direction[i]/length*distance),
    radius,near:Math.max(.01,radius/1000),far:radius*50,minDistance:radius*.25,maxDistance:radius*20};
}

// Fit the home view on resize. A user's orbit/pan/zoom remains under their control.
export function resizeLocalView(bounds,camera,controls,atHome){
  const home=localView(bounds,camera.aspect,camera.fov);
  if(atHome){
    camera.position.fromArray(home.position);controls.target.fromArray(home.target);controls.update();
  }
  return home;
}
