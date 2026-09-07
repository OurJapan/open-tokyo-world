import test from 'node:test';
import assert from 'node:assert/strict';
import {Vector3} from 'three';
import {fresh,geolocationSample,horizontalENU,enuToRender,orientationSample,cameraQuaternion,geoGate,containRect} from '../src/spatial.js';
const origin={latitude:35.65858,longitude:139.74543};
test('ENU origin, east and north are preserved in meter-scale coordinates',()=>{
  const zero=horizontalENU(origin,origin);assert.ok(Math.abs(zero.east)<1e-9&&Math.abs(zero.north)<1e-9);
  const east=horizontalENU({...origin,longitude:origin.longitude+.001},origin);
  const north=horizontalENU({...origin,latitude:origin.latitude+.001},origin);
  assert.ok(east.east>90&&east.east<92&&Math.abs(east.north)<.01);
  assert.ok(north.north>110&&north.north<112&&Math.abs(north.east)<.01);
  assert.deepEqual(enuToRender(3,5,7),[3,7,-5]);
});
test('fresh rejects missing, stale and future timestamps',()=>{
  assert.equal(fresh(null,100),false);assert.equal(fresh({timestamp:101},100),false);
  assert.equal(fresh({timestamp:100},10101),false);assert.equal(fresh({timestamp:100},10100),true);
});
test('geolocation never turns missing altitude into a real zero',()=>{
  const sample=geolocationSample({timestamp:100,coords:{...origin,accuracy:5,altitude:null,altitudeAccuracy:null}});
  assert.equal(sample.altitude_m,null);assert.equal(sample.altitude_accuracy_m,null);
  assert.equal(geolocationSample({coords:{...origin,accuracy:-1}}),null);
  assert.equal(geolocationSample({coords:{...origin,latitude:91,accuracy:1}}),null);
});
test('orientation distinguishes relative, absolute and unavailable readings',()=>{
  assert.equal(orientationSample({alpha:null,beta:0,gamma:0}),null);
  assert.equal(orientationSample({alpha:0,beta:0,gamma:0}).reference,'relative');
  assert.equal(orientationSample({alpha:0,beta:0,gamma:0,absolute:true}).reference,'earth-frame');
  assert.equal(orientationSample({alpha:0,beta:0,gamma:0,webkitCompassHeading:20,webkitCompassAccuracy:-1}).reference,'relative');
});
test('upright rear camera points north, east, south, west from compass',()=>{
  for(const [heading,expected] of [[0,[0,0,-1]],[90,[1,0,0]],[180,[0,0,1]],[270,[-1,0,0]]]){
    const s=orientationSample({alpha:0,beta:90,gamma:0,webkitCompassHeading:heading,webkitCompassAccuracy:5});
    const v=new Vector3(0,0,-1).applyQuaternion(cameraQuaternion(s));
    assert.ok(v.distanceTo(new Vector3(...expected))<1e-10);
  }
});
test('landscape screen rotation preserves viewing direction',()=>{
  const s=orientationSample({alpha:0,beta:90,gamma:0,absolute:true},90);
  assert.ok(new Vector3(0,0,-1).applyQuaternion(cameraQuaternion(s)).distanceTo(new Vector3(0,0,-1))<1e-10);
});
test('geographic overlay rejects inaccurate, stale, relative, remote and out-of-radius fixes',()=>{
  const now=20000,l={...origin,timestamp:now,accuracy_m:5};
  const o=orientationSample({alpha:0,beta:90,gamma:0,absolute:true},0,now);
  assert.equal(geoGate(l,o,origin,100,now).ok,true);
  for(const [loc,ori] of [[{...l,accuracy_m:51},o],[{...l,timestamp:0},o],[l,{...o,reference:'relative'}],[l,{...o,timestamp:0}],[{...l,latitude:36},o]])assert.equal(geoGate(loc,ori,origin,100,now).ok,false);
  assert.equal(geoGate({...l,latitude:l.latitude+.001},o,origin,50,now).ok,false);
  assert.equal(geoGate({...l,latitude:l.latitude+.001},o,origin,300,now).ok,true);
});
test('video and GL canvas share contain rectangle without crop',()=>{
  assert.deepEqual(containRect(400,600,1600,900),{width:400,height:225,left:0,top:187.5});
  assert.deepEqual(containRect(800,400,600,800),{width:300,height:400,left:250,top:0});
});
