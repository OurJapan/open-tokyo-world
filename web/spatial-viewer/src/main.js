import './style.css';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { zipSync, strToU8 } from 'fflate';
import { Sensors } from './sensors.js';
import { fresh, cameraQuaternion, geoGate, containRect } from './spatial.js';
import { makeDraft, validateDraft, sha256 } from './observation.js';
import { submitObservation } from './submission.js';

const $=id=>document.getElementById(id);
const stage=$('stage'),video=$('camera'),host=$('canvas-host');
let manifest,model,renderer,scene,camera,controls,grid;
let active=false,busy=false,viewPose=null,photo=null,draft=null,previewURL=null,packedFile=null;
let capturing=false,draftGeneration=0;
let sending=false,submissionSnapshot=null;
const submissionEndpoint=import.meta.env.VITE_OBSERVATION_API_URL||'';
const testAnchor=new THREE.Vector3(0,0,-25);
const sensors=new Sensors({onChange:()=>{
  for(const type of ['camera','location','orientation'])$(type+'-status').textContent=sensors.state[type];
}});
const say=text=>{$('notice').textContent=text;};
function resetView() {
  if(active)return;
  camera.position.set(27,20,33);camera.up.set(0,1,0);controls.target.set(0,6,0);controls.update();
}
function resize() {
  if(!renderer)return;
  const {width,height}=stage.getBoundingClientRect();
  const rect=active&&video.videoWidth?containRect(width,height,video.videoWidth,video.videoHeight):{width,height,left:0,top:0};
  host.style.inset='auto';Object.assign(host.style,{left:rect.left+'px',top:rect.top+'px',width:rect.width+'px',height:rect.height+'px'});
  renderer.setSize(rect.width,rect.height);camera.aspect=rect.width/rect.height;
  camera.fov=active?2*Math.atan(Math.tan(Math.PI/6)/camera.aspect)*180/Math.PI:48;
  camera.updateProjectionMatrix();
}
function setOpacity() {
  const opacity=Number($('opacity').value)/100;$('opacity-label').value=Math.round(opacity*100)+'%';
  model?.traverse(o=>{if(o.isMesh){o.material.transparent=true;o.material.opacity=opacity;o.material.depthWrite=opacity>.99;}});
}
function anchorTest() {
  camera.position.set(0,1.6,0);
  if(fresh(sensors.orientation,Date.now(),2000))camera.quaternion.copy(cameraQuaternion(sensors.orientation));
  else camera.quaternion.identity();
  const direction=new THREE.Vector3(0,0,-1).applyQuaternion(camera.quaternion);direction.y=0;
  if(direction.length()<.1)direction.set(0,0,-1);direction.normalize();
  testAnchor.copy(direction.multiplyScalar(25));
}
function stop(message='カメラを終了しました。') {
  active=false;busy=false;sensors.stop();video.pause();video.srcObject=null;video.hidden=true;
  stage.classList.remove('camera-active');$('start').hidden=false;$('start').disabled=!model;
  $('stop').hidden=true;$('capture').disabled=!draft;$('reset-view').disabled=false;
  if(model){model.position.set(0,0,0);model.visible=true;}if(grid)grid.visible=true;
  if(controls){controls.enabled=true;resetView();resize();}
  $('mode-label').textContent='3Dビュー';viewPose=null;say(message);
}
async function start() {
  if(busy||active||!model)return;
  busy=true;$('start').disabled=true;$('stop').hidden=false;say('カメラへのアクセスを許可してください。');
  try {
    const started=await sensors.start(video);if(!started)return;
    active=true;controls.enabled=false;grid.visible=false;video.hidden=false;
    stage.classList.add('camera-active');$('start').hidden=true;$('stop').hidden=false;
    $('capture').disabled=false;$('reset-view').disabled=true;anchorTest();resize();
    $('mode-label').textContent='カメラ';
  } catch(e){stop(e.message);}finally{busy=false;if(!active)$('start').disabled=false;}
}
function clearDraft() {
  submissionSnapshot=null;$('submission-consent').checked=false;$('submission-token').value='';$('send-observation').disabled=false;
  $('description').disabled=false;$('observation-type').disabled=false;
  draftGeneration++;if(previewURL)URL.revokeObjectURL(previewURL);previewURL=null;
  photo=null;draft=null;packedFile=null;$('photo-preview').removeAttribute('src');$('description').value='';
  $('observation-type').value='reality_difference';$('draft-dialog').close();
  $('capture').textContent='写真を撮る';$('capture').disabled=!active;
}
async function capture() {
  if(!active||capturing||video.readyState<2||!video.videoWidth)return;
  capturing=true;$('capture').disabled=true;
  const token=++draftGeneration;
  try {
    const now=Date.now(),scale=Math.min(1,2048/Math.max(video.videoWidth,video.videoHeight));
    const canvas=document.createElement('canvas');canvas.width=Math.round(video.videoWidth*scale);canvas.height=Math.round(video.videoHeight*scale);
    canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);
    const snapshot=makeDraft({id:crypto.randomUUID(),now,manifest,location:sensors.location,orientation:sensors.orientation,
      placement:$('placement').value,pose:viewPose,settings:sensors.stream?.getVideoTracks()[0]?.getSettings()??{},
      width:canvas.width,height:canvas.height,assetVisible:model.visible&&Number($('opacity').value)>0});
    const blob=await new Promise((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(new Error('写真を作成できませんでした。')),'image/jpeg',.9));
    const bytes=await blob.arrayBuffer();snapshot.image.sha256=await sha256(bytes);snapshot.image.bytes=blob.size;
    if(token!==draftGeneration)return;
    if(previewURL)URL.revokeObjectURL(previewURL);
    draft=snapshot;photo=bytes;packedFile=null;previewURL=URL.createObjectURL(blob);$('photo-preview').src=previewURL;
    $('description').value='';$('observation-type').value='reality_difference';
    $('capture-summary').textContent=`${new Date(now).toLocaleString('ja-JP')} · ${canvas.width} × ${canvas.height} · ${snapshot.location?'位置あり':'位置なし'} · 対象未指定`;
    $('draft-status').textContent='撮影した写真に3Dモデルは含まれません。';$('capture').textContent='下書きを開く';$('draft-dialog').showModal();
  } catch(e){say(e.message);}finally{capturing=false;$('capture').disabled=!active&&!draft;}
}
function packageDraft() {
  draft.description=$('description').value;draft.observation_type=$('observation-type').value;validateDraft(draft);
  const readme='Open Tokyo World — local observation draft\n\n未送信の下書きです。写真には3D overlayを含みません。\n位置・時刻を含むため共有前に確認してください。地物とposeは未確定です。\n観測受付やAI修正は自動実行されません。\n';
  const zipped=zipSync({'observation.json':strToU8(JSON.stringify(draft,null,2)),'photo.jpg':new Uint8Array(photo),'README.txt':strToU8(readme)},{level:0});
  return new File([zipped],`otw-observation-${draft.client_submission_id}.zip`,{type:'application/zip'});
}
function saveDraft(e) {
  e.preventDefault();if(!draft||!photo)return;
  try {
    packedFile=packageDraft();
    const url=URL.createObjectURL(packedFile),a=document.createElement('a');a.href=url;a.download=packedFile.name;
    document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
    $('draft-status').textContent='ZIPを作成しました。ダウンロード先をご確認ください。';
  } catch(e){$('draft-status').textContent=e.message;}
}
let lastDiagnostic=0;
function frame(now) {
  if(!renderer)return;
  if(!document.hidden){
    if(active&&model){
      const time=Date.now(),orientation=fresh(sensors.orientation,time,2000)?sensors.orientation:null;
      if(orientation)camera.quaternion.copy(cameraQuaternion(orientation));
      let message,position;
      if($('placement').value==='geo') {
        const gate=geoGate(sensors.location,sensors.orientation,manifest.origin,Number($('radius').value),time);
        model.visible=gate.ok;model.position.set(0,0,0);
        if(gate.ok){camera.position.set(gate.position.east,1.6,-gate.position.north);position=gate.position;}
        message=gate.ok?'現在地に合わせて概略表示しています。':gate.reason;
      }else{
        camera.position.set(0,1.6,0);model.position.copy(testAnchor);model.visible=true;
        message=orientation?'カメラ前方に仮配置しています。':'方位を取得中です。現在は画面に固定して表示しています。';
      }
      viewPose={frame:position?'tokyo-tower-legacy-display':'device-test-session',position_render_m:camera.position.toArray(),quaternion_xyzw:camera.quaternion.toArray(),timestamp:time,
        height_assumption_m:1.6,method:'display-only-estimate',orientation_measured:!!orientation};
      if(now-lastDiagnostic>500){say(message);}
      if(!sensors.stream?.getVideoTracks().some(t=>t.readyState==='live'))stop('カメラが停止しました。もう一度カメラを開始してください。');
    }else controls?.update();
    renderer.render(scene,camera);
    if(now-lastDiagnostic>500){
      $('diagnostics').textContent=JSON.stringify({secure_context:window.isSecureContext,mode:active?'camera':'viewer',
        location:sensors.location,orientation:sensors.orientation,display_pose:viewPose,
        frame:manifest?.frame,model_bytes:manifest?.assets[0].bytes,triangles:renderer.info.render.triangles},null,2);
      lastDiagnostic=now;
    }
  }
  requestAnimationFrame(frame);
}
async function init() {
  $('start').disabled=true;
  try {
    renderer=new THREE.WebGLRenderer({alpha:true,antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));host.append(renderer.domElement);
    scene=new THREE.Scene();camera=new THREE.PerspectiveCamera(48,1,.1,1500);
    controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.minDistance=10;controls.maxDistance=100;controls.maxPolarAngle=Math.PI*.49;
    scene.add(new THREE.HemisphereLight(0xd9edff,0x36536a,2.7));const sun=new THREE.DirectionalLight(0xffdbc4,3);sun.position.set(8,20,12);scene.add(sun);
    grid=new THREE.GridHelper(60,12,0xd4d4d8,0xe7e7eb);grid.material.transparent=true;grid.material.opacity=.45;scene.add(grid);resetView();resize();requestAnimationFrame(frame);
    const response=await fetch(`${import.meta.env.BASE_URL}data/manifest.json`);if(!response.ok)throw new Error('表示データを取得できませんでした。');manifest=await response.json();
    if(manifest.schema_version!=='otw-spatial-manifest/0.1'||!manifest.fixture||manifest.assets.length!==1)throw new Error('未対応の表示データです。');
    const asset=manifest.assets[0];if(asset.bytes>5*1024*1024||!asset.fixture||asset.feature_id!==null)throw new Error('検証用assetの範囲を超えています。');
    const assetURL=new URL(`${import.meta.env.BASE_URL}data/${asset.url}`,location.href);if(assetURL.origin!==location.origin)throw new Error('配信元が異なるassetは読み込めません。');
    const r=await fetch(assetURL);if(!r.ok)throw new Error('3Dモデルを取得できませんでした。');
    const bytes=await r.arrayBuffer();if(bytes.byteLength!==asset.bytes||await sha256(bytes)!==asset.sha256)throw new Error('3Dモデルの内容がmanifestと一致しません。');
    const gltf=await new GLTFLoader().parseAsync(bytes,'');model=gltf.scene;scene.add(model);setOpacity();
    $('loading').hidden=true;$('start').disabled=false;
    renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();stop('3D描画が中断されました。ページを再読み込みしてください。');$('start').disabled=true;});
  }catch(e){$('loading').textContent=`${e.message} ページを再読み込みしてください。`;$('start').disabled=true;}
}
$('start').addEventListener('click',start);$('stop').addEventListener('click',()=>stop());$('reset-view').addEventListener('click',resetView);
$('capture').addEventListener('click',()=>{if(draft)$('draft-dialog').showModal();else capture();});
$('close-draft').addEventListener('click',()=>{$('draft-dialog').close();say('下書きを保持しています。「下書きを開く」で再開できます。撮り直す場合は下書きを削除してください。');});
$('delete-draft').addEventListener('click',()=>{clearDraft();say('下書きの写真と位置情報をこのタブから削除しました。保存済みZIPは端末側で削除してください。');});
$('draft-form').addEventListener('submit',saveDraft);$('opacity').addEventListener('input',setOpacity);
$('submission-controls').hidden=!submissionEndpoint;
$('send-observation').addEventListener('click',async()=>{
  if(sending||!draft||!photo)return;
  if(!$('submission-consent').checked||!$('submission-token').value.trim()){
    $('draft-status').textContent='参加用コードと保存への同意をご確認ください。';return;
  }
  sending=true;
  for(const id of ['send-observation','delete-draft','description','observation-type'])$(id).disabled=true;
  const generation=draftGeneration;
  let sent=false;
  try {
    if(!submissionSnapshot){
      draft.description=$('description').value;draft.observation_type=$('observation-type').value;validateDraft(draft);
      submissionSnapshot=structuredClone(draft);
      submissionSnapshot.consent={evidence_storage:true,public_display:false,visual_map:false,model_training:false,policy_revision:'private-poc-v1'};
    }
    $('draft-status').textContent='送信しています…';
    const id=await submitObservation({endpoint:submissionEndpoint,token:$('submission-token').value.trim(),draft:submissionSnapshot,photo});
    if(generation===draftGeneration)$('draft-status').textContent=`受け付けました。受付番号：${id}`;
    sent=true;
  } catch(e){if(generation===draftGeneration)$('draft-status').textContent=e.name==='AbortError'?'受付結果を確認できませんでした。同じ下書きで再送すると受付を確認できます。':e.message;}
  finally {
    sending=false;$('delete-draft').disabled=false;
    $('send-observation').disabled=sent;
    // Freeze the payload after the first attempt so retries have an identical identity.
    $('description').disabled=!!submissionSnapshot;$('observation-type').disabled=!!submissionSnapshot;
  }
});
$('placement').addEventListener('change',()=>{
  $('placement-help').textContent=$('placement').value==='geo'?'東京タワーから300m以内で利用できます。位置や方位が不明な場合は表示されません。':'カメラ前方に仮配置します。実際の位置とは一致しません。';
  if(active)anchorTest();
});
window.addEventListener('resize',resize);video.addEventListener('resize',resize);new ResizeObserver(resize).observe(stage);
document.addEventListener('visibilitychange',()=>{if(document.hidden&&(active||busy))stop('画面を離れたためカメラとセンサーを停止しました。ボタンから再開できます。');});
window.addEventListener('pagehide',()=>{sensors.stop();clearDraft();});
  init();
