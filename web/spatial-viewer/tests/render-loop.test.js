import test from 'node:test';
import assert from 'node:assert/strict';
import {createRenderLoop} from '../src/render-loop.js';

function clock() {
  let next = 0;
  const queued = new Map();
  return {
    requestFrame(callback) {const id=next++;queued.set(id,callback);return id;},
    cancelFrame(id) {queued.delete(id);},
    tick(time) {const callbacks=[...queued.values()];queued.clear();for(const callback of callbacks)callback(time);},
    get pending() {return queued.size;},
  };
}

test('scene changes coalesce and the unchanged viewer has no queued work', () => {
  const timer=clock(),timestamps=[],loop=createRenderLoop(now=>timestamps.push(now)&&false,timer);
  assert.equal(timer.pending,0);
  loop.requestRender();loop.requestRender();loop.requestRender();
  assert.equal(timer.pending,1);
  timer.tick(16);
  assert.deepEqual(timestamps,[16]);assert.equal(timer.pending,0);
  loop.requestRender();timer.tick(32);
  assert.deepEqual(timestamps,[16,32]);assert.equal(timer.pending,0);
});

test('camera or damping continues until draw reports that it has settled', () => {
  const timer=clock();let moving=true,frames=0;
  const loop=createRenderLoop(()=>{frames++;return moving;},timer);
  loop.requestRender();timer.tick(16);timer.tick(32);
  assert.equal(frames,2);assert.equal(timer.pending,1);
  moving=false;timer.tick(48);
  assert.equal(frames,3);assert.equal(timer.pending,0);
});

test('a controls change dispatched during draw keeps exactly one next frame', () => {
  const timer=clock();let frames=0;
  const loop=createRenderLoop(()=>{frames++;if(frames===1){loop.requestRender();return true;}return false;},timer);
  loop.requestRender();timer.tick(16);
  assert.equal(timer.pending,1);
  timer.tick(32);assert.equal(frames,2);assert.equal(timer.pending,0);
});

test('visibility or context loss cancels pending work and resume redraws once', () => {
  const timer=clock();let frames=0;
  const loop=createRenderLoop(()=>{frames++;return false;},timer);
  loop.requestRender();loop.pause();loop.requestRender();timer.tick(16);
  assert.equal(frames,0);assert.equal(timer.pending,0);
  loop.resume();loop.resume();assert.equal(timer.pending,1);
  timer.tick(32);assert.equal(frames,1);assert.equal(timer.pending,0);
});

test('pausing during an active frame prevents its continuous reschedule', () => {
  const timer=clock();let frames=0;
  const loop=createRenderLoop(()=>{frames++;loop.pause();return true;},timer);
  loop.requestRender();timer.tick(16);
  assert.equal(frames,1);assert.equal(timer.pending,0);
  loop.requestRender();assert.equal(timer.pending,0);
});
