const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({...(process.env.BROWSER_CHANNEL?{channel:process.env.BROWSER_CHANNEL}:{}),headless:true,args:['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream']});
 try {
 const context=await browser.newContext({viewport:{width:390,height:844},geolocation:{latitude:35.7009,longitude:139.745},permissions:['camera','geolocation'],acceptDownloads:true});
 const page=await context.newPage(),errors=[],payloads=[];let fail=true;
 page.on('pageerror',e=>errors.push(e.message));
 await context.route('https://otw-observation-api.open-tokyo-world-observation-api.workers.dev/**',async route=>{
  const body=route.request().postData();if(!body)return route.fulfill({status:204,headers:{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'authorization'}});
  const raw=body.split('name="observation"\r\n\r\n')[1].split('\r\n--')[0];payloads.push(raw);
  await route.fulfill({status:fail?503:201,contentType:'application/json',headers:{'Access-Control-Allow-Origin':'*'},body:JSON.stringify(fail?{error:'temporarily_unavailable'}:{observation_id:JSON.parse(raw).client_submission_id})});
 });
 const rows=()=>page.evaluate(()=>new Promise((resolve,reject)=>{const r=indexedDB.open('otw-field-drafts',1);r.onsuccess=()=>{const db=r.result,t=db.transaction('drafts'),q=t.objectStore('drafts').getAll();q.onsuccess=()=>resolve(q.result.map(r=>({...r,photoBytes:r.photo.byteLength,photo:null})));t.oncomplete=()=>db.close();};r.onerror=()=>reject(r.error);}));
 const ready=()=>page.waitForFunction(()=>!document.querySelector('#start').disabled);
 const start=async()=>{await page.locator('#start').click();await page.waitForFunction(()=>document.querySelector('#camera').readyState>=2);};
 const capture=async count=>{await page.locator('#capture').click();await page.waitForFunction(n=>document.querySelectorAll('.saved-record').length===n,count);await page.waitForFunction(()=>!document.querySelector('#capture').disabled);assert.equal(await page.locator('#draft-dialog').isVisible(),false);};
 await page.goto((process.env.TEST_URL||'http://127.0.0.1:4181/')+'?area=iidabashi');await ready();await page.waitForFunction(()=>navigator.serviceWorker.controller!==null);
 await start();await capture(1);await capture(2);
 let saved=await rows();assert.equal(payloads.length,0);assert.ok(saved.every(r=>r.photoBytes>100&&r.draft.observation_type==='addition'));assert.ok(saved[0].draft.target_evidence.candidates.length>0);assert.equal(saved[0].draft.target_evidence.dimension_status,'unresolved');assert.equal(saved[0].draft.feature_id,null);
 await page.locator('#session-controls summary').click();await page.locator('#submission-token').fill('test-only-not-real');await page.locator('#submission-consent').check();await page.locator('#enable-upload').click();await capture(3);
 await page.waitForFunction(()=>[...document.querySelectorAll('.saved-record')].some(b=>b.textContent.includes('受付を確認できません')));
 assert.equal(payloads.length,1);saved=await rows();assert.equal(saved.filter(r=>r.autoUpload).length,1);
 await page.reload();await ready();await page.locator('#session-controls summary').click();assert.equal(await page.locator('#submission-token').inputValue(),'');fail=false;
 await page.locator('#submission-token').fill('test-only-not-real');await page.locator('#submission-consent').check();await page.locator('#enable-upload').click();await page.waitForFunction(()=>[...document.querySelectorAll('.saved-record')].some(b=>b.textContent.includes('送信済み')));
 assert.equal(payloads.length,2);assert.equal(payloads[0],payloads[1]);
 await context.setOffline(true);await page.reload();await ready();await start();await capture(4);saved=await rows();assert.equal(saved.length,4);assert.ok(saved.every(r=>!JSON.stringify(r).includes('test-only-not-real')));
 await context.setOffline(false);await page.locator('#stop').click();await page.locator('.saved-record').first().click();await page.locator('#draft-dialog').waitFor();
 const download=page.waitForEvent('download');await page.locator('#save-draft').click();assert.ok(await(await download).path());
 await page.locator('#next-photo').click();await start();
 await page.evaluate(()=>{window.originalPut=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(){this.transaction.abort();throw new DOMException('Full disk','QuotaExceededError');};});
 await page.locator('#capture').click();await page.locator('#draft-dialog').waitFor();assert.match(await page.locator('#draft-status').innerText(),/失敗/);
 const fallback=page.waitForEvent('download');await page.locator('#save-draft').click();assert.ok(await(await fallback).path());
 await page.evaluate(()=>{IDBObjectStore.prototype.put=window.originalPut;});await page.locator('#next-photo').click();await page.waitForFunction(()=>!document.querySelector('#draft-dialog').open);assert.equal((await rows()).length,5);
 assert.deepEqual(errors,[]);if(process.env.SCREENSHOT_PATH)await page.screenshot({path:process.env.SCREENSHOT_PATH,fullPage:true});
 console.log('PASS: shutter-only repeated capture, consent boundaries, automatic upload, identical retry after reload, no persisted credentials, offline capture/catalogue, ZIP, storage-failure recovery');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
