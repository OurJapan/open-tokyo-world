import test from 'node:test';
import assert from 'node:assert/strict';
import {Sensors} from '../src/sensors.js';
function environment({permission=Promise.resolve('granted'),getCamera}={}){
  const events=new Map(),calls=[];const track={stop:()=>calls.push('stop'),readyState:'live'};
  const stream={getTracks:()=>[track]};
  const win={isSecureContext:true,DeviceOrientationEvent:{requestPermission:()=>{calls.push('permission');return permission;}},
    addEventListener:(n,f)=>events.set(n,f),removeEventListener:n=>events.delete(n)};
  let onPosition;
  const nav={mediaDevices:{getUserMedia:getCamera??(async()=>{calls.push('camera');return stream;})},
    geolocation:{watchPosition:cb=>{onPosition=cb;calls.push('watch');return 42;},clearWatch:id=>calls.push('clear:'+id)}};
  const video={srcObject:null,play:async()=>{calls.push('play');}};
  return {s:new Sensors({nav,win}),win,nav,video,stream,events,calls,position:p=>onPosition(p)};
}
test('permission request starts before camera await; stopping releases tracks and watches',async()=>{
  const e=environment();assert.equal(await e.s.start(e.video),true);assert.ok(e.calls.indexOf('permission')<e.calls.indexOf('camera'));
  assert.equal(e.events.size,2);e.s.stop();assert.equal(e.events.size,0);assert.ok(e.calls.includes('stop'));assert.ok(e.calls.includes('clear:42'));
  assert.equal(e.s.location,null);assert.equal(e.s.orientation,null);
});
test('late camera permission result cannot restart a stopped session',async()=>{
  let release;const e=environment({getCamera:()=>new Promise(r=>release=r)});const pending=e.s.start(e.video);
  e.s.stop();release(e.stream);assert.equal(await pending,false);assert.equal(e.s.stream,null);assert.ok(e.calls.includes('stop'));assert.equal(e.video.srcObject,null);
});
test('late orientation grant cannot attach listeners after stopping',async()=>{
  let grant;const e=environment({permission:new Promise(r=>grant=r)});await e.s.start(e.video);e.s.stop();grant('granted');await Promise.resolve();assert.equal(e.events.size,0);
});
test('camera permission refusal cleans up sensors',async()=>{
  const e=environment({getCamera:async()=>{throw Object.assign(new Error(),{name:'NotAllowedError'});}});
  await assert.rejects(e.s.start(e.video),/カメラが許可/);assert.equal(e.events.size,0);assert.ok(e.calls.includes('clear:42'));
});
test('location and orientation denial do not prevent camera preview',async()=>{
  const e=environment({permission:Promise.resolve('denied')});assert.equal(await e.s.start(e.video),true);assert.equal(e.s.state.orientation,'許可なし');assert.equal(e.events.size,0);e.s.stop();
});
test('insecure iPhone-style origin is rejected before sensor requests',async()=>{
  const e=environment();e.win.isSecureContext=false;await assert.rejects(e.s.start(e.video),/HTTPS/);assert.equal(e.calls.includes('camera'),false);assert.equal(e.calls.includes('permission'),false);
});
