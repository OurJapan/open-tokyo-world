import { Euler, Quaternion, Vector3 } from 'three';
export const MAX_AGE_MS = 10000;
export function fresh(sample, now = Date.now(), age = MAX_AGE_MS) {
  return !!sample && Number.isFinite(sample.timestamp) && now >= sample.timestamp && now - sample.timestamp <= age;
}
export function geolocationSample(position) {
  const c = position.coords;
  if (![c.latitude,c.longitude,c.accuracy].every(Number.isFinite) || Math.abs(c.latitude)>90 || Math.abs(c.longitude)>180 || c.accuracy<0) return null;
  return { latitude:c.latitude, longitude:c.longitude, altitude_m:Number.isFinite(c.altitude)?c.altitude:null,
    altitude_accuracy_m:Number.isFinite(c.altitudeAccuracy)?c.altitudeAccuracy:null, accuracy_m:c.accuracy,
    vertical_datum:'WGS84-ellipsoid-as-reported', timestamp:position.timestamp, provider:'browser-geolocation' };
}
function ecef(lat, lon, height = 0) {
  const phi=lat*Math.PI/180, lambda=lon*Math.PI/180, e2=6.69437999014e-3;
  const N=6378137/Math.sqrt(1-e2*Math.sin(phi)**2);
  return [(N+height)*Math.cos(phi)*Math.cos(lambda),(N+height)*Math.cos(phi)*Math.sin(lambda),(N*(1-e2)+height)*Math.sin(phi)];
}
// Horizontal-only approximation: both heights intentionally use 0, never a measured elevation.
export function horizontalENU(location, origin) {
  const p=ecef(location.latitude,location.longitude), o=ecef(origin.latitude,origin.longitude);
  const [x,y,z]=p.map((v,i)=>v-o[i]), phi=origin.latitude*Math.PI/180, l=origin.longitude*Math.PI/180;
  return {east:-Math.sin(l)*x+Math.cos(l)*y, north:-Math.sin(phi)*Math.cos(l)*x-Math.sin(phi)*Math.sin(l)*y+Math.cos(phi)*z};
}
export function enuToRender(e,n,u) { return [e,u,-n]; }
export function orientationSample(e, screenAngle = 0, now=Date.now()) {
  if (![e.alpha,e.beta,e.gamma].every(Number.isFinite)) return null;
  const compassOK=Number.isFinite(e.webkitCompassHeading) && e.webkitCompassHeading>=0 && e.webkitCompassHeading<360 &&
    (!Number.isFinite(e.webkitCompassAccuracy) || (e.webkitCompassAccuracy>=0 && e.webkitCompassAccuracy<=30));
  return {alpha:e.alpha,beta:e.beta,gamma:e.gamma,heading_deg:compassOK?e.webkitCompassHeading:null,
    absolute:e.absolute===true, reference:compassOK?'webkit-compass':e.absolute===true?'earth-frame':'relative',
    screen_angle:screenAngle,timestamp:now};
}
export function cameraQuaternion(s) {
  const rad=Math.PI/180;
  const alpha=s.heading_deg===null?s.alpha:360-s.heading_deg;
  return new Quaternion().setFromEuler(new Euler(s.beta*rad,alpha*rad,-s.gamma*rad,'YXZ'))
    .multiply(new Quaternion().setFromAxisAngle(new Vector3(1,0,0),-Math.PI/2))
    .multiply(new Quaternion().setFromAxisAngle(new Vector3(0,0,1),-s.screen_angle*rad));
}
export function geoGate(location, orientation, origin, radius, now=Date.now()) {
  if (!fresh(location,now)) return {ok:false,reason:'現在地を取得しています。許可と電波状況を確認してください。'};
  const p=horizontalENU(location,origin), distance=Math.hypot(p.east,p.north);
  if (distance>300) return {ok:false,reason:'選択エリアの検証原点から300mの範囲外です。「目の前に表示」か3Dビューを利用できます。',distance};
  if (location.accuracy_m>50) return {ok:false,reason:'位置の誤差が大きいため、モデルを非表示にしています。',distance};
  if (!fresh(orientation,now,2000) || orientation.reference==='relative') return {ok:false,reason:'北基準の方位を待っています。取得できない場合は「目の前に表示」を利用してください。',distance};
  if (distance>radius) return {ok:false,reason:'モデルが取得範囲の外にあります。周辺の取得範囲を広げてください。',distance};
  return {ok:true,position:p,distance};
}
export function containRect(width,height,sourceWidth,sourceHeight) {
  const scale=Math.min(width/sourceWidth,height/sourceHeight);
  const w=sourceWidth*scale,h=sourceHeight*scale;
  return {width:w,height:h,left:(width-w)/2,top:(height-h)/2};
}
