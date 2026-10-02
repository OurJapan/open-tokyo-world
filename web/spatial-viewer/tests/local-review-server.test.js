import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,rm} from 'node:fs/promises';
import {createServer} from 'node:http';
import {tmpdir} from 'node:os';
import path from 'node:path';
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
