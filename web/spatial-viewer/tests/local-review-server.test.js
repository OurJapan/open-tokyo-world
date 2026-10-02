import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,rm,symlink,unlink,rename} from 'node:fs/promises';
import {createServer,request} from 'node:http';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {createServer as createViteServer} from 'vite';
import {localReviewServer} from '../scripts/local-review-server.mjs';

test('development middleware serves only the two local review files, without exposing job paths',async()=>{
  const temporary=await mkdtemp(path.join(tmpdir(),'otw-local-server-'));
  assert.ok(path.resolve(temporary).startsWith(path.resolve(tmpdir())+path.sep));
  const folder=path.join(temporary,'data/local/web-exports/data221-af7335da');await mkdir(folder,{recursive:true});
  await writeFile(path.join(folder,'manifest.json'),'{}');await writeFile(path.join(folder,'model.glb'),'local-test');
  await writeFile(path.join(folder,'job.json'),'private-execution-metadata');
  let middleware;localReviewServer(temporary).configureServer({middlewares:{use:handler=>middleware=handler}});
  const server=createServer((request,response)=>middleware(request,response,()=>response.writeHead(404).end()));
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const url=`http://127.0.0.1:${server.address().port}/__otw_local__/data221-af7335da/`;
  try{
    const manifest=await fetch(url+'manifest.json');assert.equal(manifest.status,200);assert.equal(await manifest.text(),'{}');assert.equal(manifest.headers.get('cache-control'),'no-store');
    assert.equal((await fetch(url+'model.glb',{method:'HEAD'})).status,200);
    assert.equal((await fetch(url+'job.json')).status,404);
    assert.equal((await fetch(url+'manifest.json',{method:'POST'})).status,405);
    assert.throws(()=>localReviewServer(temporary,'../private'));
  }finally{
    await new Promise(resolve=>server.close(resolve));
    assert.ok(path.resolve(temporary).startsWith(path.resolve(tmpdir())+path.sep)&&path.basename(temporary).startsWith('otw-local-server-'));
    await rm(temporary,{recursive:true,force:true});
  }
});

const localRoute='/__otw_local__/data221-af7335da/';
const profile='data/local/web-exports/data221-af7335da';
const outsideMarker='SYNTHETIC_OUTSIDE_DATA_LOCAL';

async function fixture(t){
  const root=await mkdtemp(path.join(tmpdir(),'otw-local-server-'));
  assert.ok(path.resolve(root).startsWith(path.resolve(tmpdir())+path.sep));
  t.after(async()=>{
    assert.ok(path.resolve(root).startsWith(path.resolve(tmpdir())+path.sep)&&path.basename(root).startsWith('otw-local-server-'));
    await rm(root,{recursive:true,force:true});
  });
  const folder=path.join(root,profile),outside=path.join(root,'outside-local-fixture');
  await mkdir(folder,{recursive:true});await mkdir(outside);
  await writeFile(path.join(folder,'manifest.json'),'{}');await writeFile(path.join(folder,'model.glb'),'local-test');
  await writeFile(path.join(outside,'manifest.json'),outsideMarker);await writeFile(path.join(outside,'model.glb'),outsideMarker);
  await writeFile(path.join(root,'normal.txt'),'synthetic-normal-route');
  return {root,folder,outside};
}

async function withProfile(root,directory,check){
  let middleware;localReviewServer(root,directory).configureServer({middlewares:{use:handler=>middleware=handler}});
  const server=createServer((req,res)=>middleware(req,res,()=>res.writeHead(404).end()));
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  try{await check(`http://127.0.0.1:${server.address().port}${localRoute}`);}
  finally{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
}

async function refused(url){
  for(const name of ['manifest.json','model.glb'])for(const method of ['GET','HEAD']){
    const response=await fetch(url+name,{method});assert.equal(response.status,404);
    assert.ok(!(await response.text()).includes(outsideMarker));
  }
}

async function createLink(t,target,link,type){
  try{await symlink(target,link,type);return true;}
  catch(error){
    if(['EPERM','ENOTSUP'].includes(error.code)){t.skip(`${type} links cannot be created by this environment (${error.code})`);return false;}
    throw error;
  }
}

test('actual Vite survives malformed raw URL with 400 and serves later normal and local requests',{timeout:15000},async t=>{
  const {root}=await fixture(t);
  const vite=await createViteServer({root,configFile:false,publicDir:false,cacheDir:path.join(root,'data/local/vite-cache'),
    plugins:[localReviewServer(root)],server:{host:'127.0.0.1',port:0,strictPort:true,watch:null,hmr:false},
    optimizeDeps:{noDiscovery:true,include:[]},logLevel:'silent'});
  try{
    await vite.listen();const port=vite.httpServer.address().port;
    const status=await new Promise((resolve,reject)=>{
      const raw=request({hostname:'127.0.0.1',port,path:'//',headers:{Connection:'close'}},response=>{
        response.resume();response.once('end',()=>resolve(response.statusCode));
      });
      raw.setTimeout(5000,()=>raw.destroy(new Error('Malformed URL response timed out')));raw.once('error',reject);raw.end();
    });
    assert.equal(status,400);
    const url=`http://127.0.0.1:${port}`;
    const normal=await fetch(url+'/normal.txt');assert.equal(normal.status,200);assert.equal(await normal.text(),'synthetic-normal-route');
    const local=await fetch(url+localRoute+'manifest.json');assert.equal(local.status,200);assert.equal(await local.text(),'{}');
  }finally{await vite.close();}
});

test('Windows profile junction outside data/local is refused',{skip:process.platform!=='win32'},async t=>{
  const {root,outside,folder}=await fixture(t),alias=path.join(root,'data/local/junction-profile');
  await symlink(outside,alias,'junction');
  await withProfile(root,'data/local/junction-profile',refused);
  await unlink(alias);await symlink(folder,alias,'junction');
  await withProfile(root,'data/local/junction-profile',async url=>{
    assert.equal((await fetch(url+'manifest.json')).status,200);assert.equal((await fetch(url+'model.glb',{method:'HEAD'})).status,200);
  });
});

test('ordinary directory symlink cannot escape data/local',async t=>{
  const {root,outside}=await fixture(t),alias=path.join(root,'data/local/symlink-profile');
  if(!await createLink(t,outside,alias,'dir'))return;
  await withProfile(root,'data/local/symlink-profile',refused);
});

test('ordinary file symlink cannot escape its profile while a normal replacement still serves',async t=>{
  const {root,folder,outside}=await fixture(t),manifest=path.join(folder,'manifest.json');
  await unlink(manifest);
  if(!await createLink(t,path.join(outside,'manifest.json'),manifest,'file'))return;
  await withProfile(root,profile,async url=>{
    for(const method of ['GET','HEAD'])assert.equal((await fetch(url+'manifest.json',{method})).status,404);
    assert.equal((await fetch(url+'model.glb')).status,200);
  });
  await unlink(manifest);await writeFile(manifest,'{}');
  await withProfile(root,profile,async url=>assert.equal((await fetch(url+'manifest.json')).status,200));
});

test('a file link within the same profile retains normal GET and HEAD access',async t=>{
  const {root,folder}=await fixture(t),manifest=path.join(folder,'manifest.json'),target=path.join(folder,'retained-manifest.json');
  await rename(manifest,target);
  if(!await createLink(t,target,manifest,'file'))return;
  await withProfile(root,profile,async url=>{
    const response=await fetch(url+'manifest.json');assert.equal(response.status,200);assert.equal(await response.text(),'{}');
    assert.equal((await fetch(url+'manifest.json',{method:'HEAD'})).status,200);
  });
});

test('replacing the data/local anchor with an outside directory link is refused',async t=>{
  const {root,outside}=await fixture(t),anchor=path.join(root,'data/local');
  const outsideProfile=path.join(outside,'web-exports/data221-af7335da');await mkdir(outsideProfile,{recursive:true});
  await writeFile(path.join(outsideProfile,'manifest.json'),outsideMarker);await writeFile(path.join(outsideProfile,'model.glb'),outsideMarker);
  await rename(anchor,path.join(root,'data/local-original'));
  if(!await createLink(t,outside,anchor,process.platform==='win32'?'junction':'dir'))return;
  await withProfile(root,profile,refused);
});
