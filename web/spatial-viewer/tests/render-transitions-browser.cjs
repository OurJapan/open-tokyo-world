const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const url=process.env.TEST_URL||'http://127.0.0.1:4181/';
const output=path.resolve(process.env.PERF_OUTPUT||'../../data/local/viewer-integration/transitions');
const api='https://otw-observation-api.open-tokyo-world-observation-api.workers.dev';

(async()=>{
  await fs.mkdir(output,{recursive:true});
  const browser=await chromium.launch({...(process.env.BROWSER_CHANNEL?{channel:process.env.BROWSER_CHANNEL}:{}),headless:true,
    args:['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream']});
  const report={browser:browser.version(),url,cases:[],errors:[],limits:[
    'Original public fixture and fake camera only. External API responses are mocked locally.',
    'Visibility events are controlled in a dedicated document; real CDP freeze/resume is also checked. Headless tabs do not report hidden on tab switching.',
    'These assertions verify rendering state transitions, not FPS, battery or thermal improvement.',
  ]};
  let context;
  try{
    context=await browser.newContext({viewport:{width:960,height:900},permissions:['camera','geolocation'],
      geolocation:{latitude:35.65858,longitude:139.74543},serviceWorkers:'block'});
    let failSubmission=true;const payloads=[];
    await context.route('**/*',async route=>{
      const request=route.request(),requestURL=new URL(request.url());
      if(requestURL.origin===new URL(url).origin)return route.continue();
      if(requestURL.origin!==api)return route.abort();
      const headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'authorization','Access-Control-Allow-Methods':'POST,OPTIONS'};
      const body=request.postData();if(!body)return route.fulfill({status:204,headers});
      const raw=body.split('name="observation"\r\n\r\n')[1].split('\r\n--')[0];payloads.push(raw);
      return route.fulfill({status:failSubmission?503:201,headers,contentType:'application/json',
        body:JSON.stringify(failSubmission?{error:'temporarily_unavailable'}:{observation_id:JSON.parse(raw).client_submission_id})});
    });
    await context.addInitScript(()=>{
      window.__draws=0;
      for(const prototype of [WebGLRenderingContext.prototype,WebGL2RenderingContext.prototype]){
        const original=prototype.clear;prototype.clear=function(...args){if(this.canvas.parentElement?.id==='canvas-host')window.__draws++;return original.apply(this,args);};
      }
      const original=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      window.__cameraMode='live';
      navigator.mediaDevices.getUserMedia=async(...args)=>{
        const mode=window.__cameraMode;window.__cameraMode='live';
        if(mode==='deny')throw new DOMException('Test permission denial','NotAllowedError');
        const stream=await original(...args);window.__lastCameraStream=stream;
        if(mode==='pending'){window.__pendingCameraStream=stream;await new Promise(resolve=>window.__releasePermission=resolve);}
        return stream;
      };
    });
    const page=await context.newPage();page.on('pageerror',error=>report.errors.push(error.message));
    const draws=()=>page.evaluate(()=>window.__draws);
    const diagnostics=async()=>JSON.parse(await page.locator('#diagnostics').textContent());
    const visible=async hidden=>page.evaluate(value=>{Object.defineProperty(document,'hidden',{configurable:true,value});document.dispatchEvent(new Event('visibilitychange'));},hidden);
    const settle=async()=>{
      await page.evaluate(()=>window.__quietDraws=undefined);
      await page.waitForFunction(()=>{const before=window.__quietDraws;window.__quietDraws=window.__draws;return before===window.__draws;},undefined,{polling:200,timeout:15000});
    };
    const idle=async name=>{await settle();const before=await draws();await page.waitForTimeout(300);assert.equal(await draws(),before,name+' must remain idle');report.cases.push({name,passed:true,idle_draws:0});};
    const ready=()=>page.waitForFunction(()=>!document.querySelector('#start').disabled);
    const camera=async()=>{await page.locator('#start').click();await page.waitForFunction(()=>document.querySelector('#camera').readyState>=2&&!document.querySelector('#camera').hidden);const before=await draws();await page.waitForTimeout(250);assert.ok(await draws()>before+1,'camera must keep drawing');};
    const fixture=async name=>{
      assert.equal((await diagnostics()).triangles,144);
      const bytes=await page.locator('#canvas-host').screenshot({path:path.join(output,name+'.png')});
      const orange=await page.evaluate(async data=>{const image=new Image();image.src=data;await image.decode();const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0);const pixels=ctx.getImageData(0,0,canvas.width,canvas.height).data;let count=0;for(let i=0;i<pixels.length;i+=4)if(pixels[i]-pixels[i+1]>30&&pixels[i+1]-pixels[i+2]>15)count++;return count;},'data:image/png;base64,'+bytes.toString('base64'));
      assert.ok(orange>100,'fixture must be visibly rendered');return orange;
    };
    let releaseAsset,assetRequested=false;const assetGate=new Promise(resolve=>releaseAsset=resolve);
    await page.route('**/device-test.glb',async route=>{assetRequested=true;await assetGate;await route.continue();});
    await page.goto(url,{waitUntil:'domcontentloaded'});
    await page.waitForFunction(()=>document.querySelector('#canvas-host canvas'));
    await page.waitForTimeout(350);assert.ok(assetRequested);assert.equal(await page.locator('#start').isDisabled(),true);
    await idle('waiting_for_delayed_asset');
    const beforeResize=await draws();await page.setViewportSize({width:390,height:844});await settle();assert.ok(await draws()>beforeResize);
    await page.locator('#opacity').evaluate(element=>{element.value='50';element.dispatchEvent(new Event('input',{bubbles:true}));});await idle('resize_and_opacity_before_asset');
    const beforeLoad=await draws();releaseAsset();await ready();await idle('delayed_asset_complete');assert.ok(await draws()>beforeLoad);
    const delayedOrange=await fixture('delayed-load');assert.equal(await page.locator('#opacity-label').textContent(),'50%');
    report.cases.push({name:'late_model_is_visible_at_latest_opacity_and_size',passed:true,orange_pixels:delayedOrange});
    await page.unroute('**/device-test.glb');

    // No animation frame is required while a hidden document finishes loading.
    await page.addInitScript(()=>Object.defineProperty(document,'hidden',{configurable:true,value:true}));
    const beforeReload=await draws();assert.ok(beforeReload>0);await page.reload();await ready();assert.equal(await draws(),0);
    const hiddenBefore=await draws();await page.setViewportSize({width:960,height:900});
    await page.locator('#opacity').evaluate(element=>{element.value='100';element.dispatchEvent(new Event('input',{bubbles:true}));});
    await page.waitForTimeout(250);assert.equal(await draws(),hiddenBefore);
    await visible(false);await idle('initially_hidden_load_and_edits_resume');await fixture('hidden-load-resume');
    await page.locator('#opacity').evaluate(element=>{element.value='75';element.dispatchEvent(new Event('input',{bubbles:true}));});await idle('opacity_after_resume');

    const box=await page.locator('#canvas-host').boundingBox();
    await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+60,box.y+box.height/2+10);await page.mouse.up();
    const duringDamping=await draws();await page.waitForTimeout(200);assert.ok(await draws()>duringDamping+1);
    await visible(true);const hiddenDamping=await draws();await page.waitForTimeout(250);assert.equal(await draws(),hiddenDamping);
    await visible(false);await idle('damping_interrupted_by_visibility_resumes');await fixture('damping-resume');
    await page.locator('#reset-view').click();await idle('reset_after_resumed_damping');

    const cdp=await context.newCDPSession(page);
    await cdp.send('Page.setWebLifecycleState',{state:'frozen'});await page.waitForTimeout(300);await cdp.send('Page.setWebLifecycleState',{state:'active'});
    const beforeLifecycleEdit=await draws();
    await page.locator('#opacity').evaluate(element=>{element.value='100';element.dispatchEvent(new Event('input',{bubbles:true}));});await idle('real_browser_freeze_resume');assert.ok(await draws()>beforeLifecycleEdit);

    await page.evaluate(()=>window.__cameraMode='deny');await page.locator('#start').click();
    await page.waitForFunction(()=>!document.querySelector('#start').disabled);assert.equal(await page.locator('#camera').isHidden(),true);await idle('camera_denial_returns_to_viewer');
    await camera();
    await cdp.send('Page.setWebLifecycleState',{state:'frozen'});await page.waitForTimeout(300);await cdp.send('Page.setWebLifecycleState',{state:'active'});
    const resumedCamera=await draws();await page.waitForTimeout(250);assert.ok(await draws()>resumedCamera+1,'pending camera animation must continue after real browser resume');
    report.cases.push({name:'active_camera_real_browser_freeze_resume',passed:true});
    await visible(true);assert.equal(await page.locator('#camera').isHidden(),true);await visible(false);await idle('camera_background_stop_and_viewer_resume');await fixture('camera-background-resume');

    await page.evaluate(()=>window.__cameraMode='pending');await page.locator('#start').click();await page.waitForFunction(()=>typeof window.__releasePermission==='function');
    await page.locator('#stop').click();await page.evaluate(()=>window.__releasePermission());
    await page.waitForFunction(()=>window.__pendingCameraStream.getTracks().every(track=>track.readyState==='ended'));
    assert.equal(await page.locator('#camera').isHidden(),true);await idle('pending_camera_cancel_does_not_restart');
    await camera();await page.evaluate(()=>window.__lastCameraStream.getTracks().forEach(track=>track.stop()));
    await page.waitForFunction(()=>document.querySelector('#camera').hidden);await idle('camera_track_end_returns_to_idle_viewer');
    await camera();await page.evaluate(()=>window.dispatchEvent(new PageTransitionEvent('pagehide')));
    const pageHidden=await draws();await page.waitForTimeout(250);assert.equal(await draws(),pageHidden);
    await page.evaluate(()=>window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true})));
    await page.waitForFunction(()=>document.querySelector('#camera').hidden);await idle('camera_pagehide_pageshow_stops_dead_stream');

    await page.locator('#session-controls summary').click();await page.locator('#submission-token').fill('test-only-not-real');await page.locator('#submission-consent').check();
    await camera();await page.locator('#capture').click();await page.waitForFunction(()=>document.querySelectorAll('.saved-record').length===1);await page.waitForFunction(()=>!document.querySelector('#capture').disabled);
    const afterCapture=await draws();await page.waitForTimeout(250);assert.ok(await draws()>afterCapture+1,'capture must not stop camera rendering');
    await page.locator('#stop').click();await idle('capture_then_stop_returns_to_viewer');
    await page.locator('.saved-record').first().click();await page.locator('#draft-dialog').waitFor();await idle('saved_draft_dialog_viewer_stays_idle');
    await page.keyboard.press('Escape');await page.waitForFunction(()=>!document.querySelector('#draft-dialog').open);await idle('draft_escape_cancel_keeps_viewer_idle');
    const beforeReset=await draws();await page.locator('#reset-view').click();await idle('reset_after_draft_cancel_redraws');assert.ok(await draws()>beforeReset);
    await page.locator('.saved-record').first().click();await page.locator('#draft-dialog').waitFor();
    await page.locator('#send-observation').click();await page.waitForFunction(()=>!document.querySelector('#send-observation').disabled);assert.equal(payloads.length,1);await idle('submission_failure_keeps_viewer_idle');
    failSubmission=false;await page.locator('#send-observation').click();await page.waitForFunction(()=>document.querySelector('#draft-status').textContent.includes('受付番号'));assert.equal(payloads.length,2);assert.equal(payloads[0],payloads[1]);await idle('identical_submission_retry_keeps_viewer_idle');
    await page.locator('#next-photo').click();await page.waitForFunction(()=>!document.querySelector('#draft-dialog').open);await idle('next_photo_returns_to_viewer');
    await camera();await page.locator('#stop').click();await idle('camera_retry_after_submission');await fixture('final-viewer');
    assert.deepEqual(report.errors,[]);
    report.passed=true;await fs.writeFile(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify({output,cases:report.cases.length,passed:true,errors:report.errors}));
  }catch(error){report.passed=false;report.failure=error.stack;await fs.writeFile(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n');throw error;}
  finally{await context?.close();await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
