import { geolocationSample, orientationSample } from './spatial.js';
export class Sensors {
  constructor({nav=navigator,win=window,onChange=()=>{}}={}) {
    this.nav=nav; this.win=win; this.onChange=onChange; this.generation=0;
    this.stream=null;this.watch=null;this.location=null;this.orientation=null;this.state={camera:'停止中',location:'未取得',orientation:'未取得'};
    this.onOrientation=e=>{
      const sample=orientationSample(e,this.win.screen?.orientation?.angle ?? this.win.orientation ?? 0);
      if (!sample) return;
      // Prefer an earth-referenced event while it remains fresh.
      if(sample.reference==='relative' && this.orientation?.reference!=='relative' && Date.now()-this.orientation?.timestamp<1000)return;
      this.orientation=sample;this.state.orientation=sample.reference==='relative'?'相対方向のみ':'概略方位';this.onChange();
    };
  }
  async start(video) {
    this.stop();const generation=++this.generation;
    if (!this.win.isSecureContext) throw new Error('カメラはHTTPSで開いてください。iPhoneからPCのHTTPアドレスを開く方法では利用できません。');
    if(!this.nav.mediaDevices?.getUserMedia)throw new Error('このブラウザではカメラを利用できません。Safariで開いてください。');
    this.state={camera:'許可を確認中',location:'取得中',orientation:'許可を確認中'};this.onChange();
    // Start permission request in the original tap, before any await.
    let permission;
    try {permission=this.win.DeviceOrientationEvent?.requestPermission?.() ?? Promise.resolve('granted');}
    catch {permission=Promise.resolve('denied');}
    Promise.resolve(permission).then(result=>{
      if(generation!==this.generation)return;
      if(result==='granted') {
        this.win.addEventListener('deviceorientation',this.onOrientation);
        this.win.addEventListener('deviceorientationabsolute',this.onOrientation);
        this.state.orientation='イベント待ち';
      } else this.state.orientation='許可なし';
      this.onChange();
    }).catch(()=>{if(generation===this.generation){this.state.orientation='許可なし';this.onChange();}});
    if(this.nav.geolocation) this.watch=this.nav.geolocation.watchPosition(p=>{
      if(generation!==this.generation)return;
      this.location=geolocationSample(p);this.state.location=this.location?`誤差 ±${Math.round(this.location.accuracy_m)}m`:'値が不明';this.onChange();
    },e=>{if(generation===this.generation){this.location=null;this.state.location=e.code===1?'許可なし':'取得できません';this.onChange();}},
    {enableHighAccuracy:true,maximumAge:0,timeout:10000});
    else this.state.location='非対応';
    try {
      const stream=await this.nav.mediaDevices.getUserMedia({audio:false,video:{facingMode:{ideal:'environment'},width:{ideal:1280},height:{ideal:720}}});
      if(generation!==this.generation){stream.getTracks().forEach(t=>t.stop());return false;}
      this.stream=stream; video.srcObject=stream;await video.play();
      if(generation!==this.generation)return false;
      this.state.camera='使用中';this.onChange();return true;
    } catch(e) {
      if(generation!==this.generation)return false;
      this.stop();throw new Error(e.name==='NotAllowedError'?'カメラが許可されませんでした。Safariのサイト設定を確認して再開してください。':'カメラを開始できませんでした。他のアプリを閉じて再開してください。');
    }
  }
  stop() {
    this.generation++;
    this.stream?.getTracks().forEach(t=>t.stop());this.stream=null;
    if(this.watch!==null)this.nav.geolocation?.clearWatch(this.watch);this.watch=null;
    this.win.removeEventListener('deviceorientation',this.onOrientation);this.win.removeEventListener('deviceorientationabsolute',this.onOrientation);
    this.location=null;this.orientation=null;this.state={camera:'停止中',location:'未取得',orientation:'未取得'};this.onChange();
  }
}
