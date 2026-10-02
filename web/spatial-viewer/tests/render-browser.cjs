const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const {mkdir, writeFile, readFile} = require('node:fs/promises');
const path = require('node:path');
const {createHash} = require('node:crypto');

const url = process.env.TEST_URL || 'http://127.0.0.1:4181/';
const output = path.resolve(process.env.PERF_OUTPUT || '../../data/local/viewer-performance/after');
const expectIdle = process.env.EXPECT_IDLE !== '0';
const sampleMs = Number(process.env.PERF_SAMPLE_MS || 2500);
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const median = values => [...values].sort((a,b) => a-b)[Math.floor(values.length/2)];

(async () => {
  await mkdir(output, {recursive:true});
  const browser = await chromium.launch({
    ...(process.env.BROWSER_CHANNEL ? {channel:process.env.BROWSER_CHANNEL} : {}),
    headless:true,
    args:['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream'],
  });
  try {
    const context = await browser.newContext({viewport:{width:960,height:900}, deviceScaleFactor:1,
      permissions:['camera','geolocation'], geolocation:{latitude:35.65858,longitude:139.74543},
      serviceWorkers:'block'});
    const page = await context.newPage(), errors = [];
    page.on('pageerror', error => errors.push(error.message));
    // No consent or upload is exercised here. Block external traffic as a guard.
    await context.route('**/*', route => new URL(route.request().url()).origin === new URL(url).origin ? route.continue() : route.abort());
    await page.addInitScript(() => {
      window.__viewerWork = {frames:0,drawCalls:0,triangles:0};
      for (const prototype of [WebGLRenderingContext.prototype,WebGL2RenderingContext.prototype]) {
        for (const method of ['clear','drawElements','drawArrays']) {
          const original = prototype[method];
          prototype[method] = function(...args) {
            if (this.canvas.parentElement?.id === 'canvas-host') {
              const work = window.__viewerWork;
              if (method === 'clear') work.frames++;
              else {work.drawCalls++; if (args[0] === this.TRIANGLES) work.triangles += args[method==='drawElements'?1:2]/3;}
            }
            return original.apply(this,args);
          };
        }
      }
    });
    const cdp = await context.newCDPSession(page);
    await cdp.send('Performance.enable');
    const metrics = async () => Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(({name,value}) => [name,value]));
    const work = () => page.evaluate(() => ({...window.__viewerWork, time:performance.now()}));
    const sample = async (duration = sampleMs) => {
      const cpuStart = await metrics(), start = await work();
      await page.waitForTimeout(duration);
      const end = await work(), cpuEnd = await metrics(), elapsedMs = end.time - start.time;
      return {elapsed_ms:elapsedMs, frames:end.frames-start.frames, draw_calls:end.drawCalls-start.drawCalls,
        rendered_triangles:end.triangles-start.triangles, task_ms:(cpuEnd.TaskDuration-cpuStart.TaskDuration)*1000,
        script_ms:(cpuEnd.ScriptDuration-cpuStart.ScriptDuration)*1000};
    };
    const snapshots = {};
    const snapshot = async name => {
      const bytes = await page.locator('#canvas-host').screenshot({path:path.join(output,name+'.png')});
      snapshots[name] = {file:name+'.png',sha256:digest(bytes)};
    };
    const diagnostics = () => page.locator('#diagnostics').textContent().then(JSON.parse);
    const idleCheck = result => {if(expectIdle)assert.equal(result.frames,0,'settled viewer must stop drawing');};
    const settle = async () => {
      if(!expectIdle) {await page.waitForTimeout(3000);return;}
      await page.waitForFunction(() => {
        const previous=window.__settleFrames,frames=window.__viewerWork.frames;
        window.__settleFrames=frames;return previous===frames;
      },undefined,{polling:200,timeout:15000});
    };
    await page.goto(url);
    await page.waitForFunction(() => !document.querySelector('#start').disabled);
    await page.waitForTimeout(1000);
    await snapshot('initial');
    const initialDiagnostics = await diagnostics();
    assert.equal(initialDiagnostics.triangles,144);
    const idle = [];
    for(let i=0;i<3;i++) {const result=await sample();idleCheck(result);idle.push(result);}

    const beforeOpacity = await work();
    await page.locator('#opacity').evaluate(element => {element.value='100';element.dispatchEvent(new Event('input',{bubbles:true}));});
    await page.waitForTimeout(200);
    assert.ok((await work()).frames>beforeOpacity.frames,'opacity must redraw the model');
    await snapshot('opaque');
    const opaqueIdle = await sample(500);idleCheck(opaqueIdle);
    await page.locator('#opacity').evaluate(element => {element.value='75';element.dispatchEvent(new Event('input',{bubbles:true}));});

    const beforeResize = await work();
    await page.setViewportSize({width:390,height:844});await page.waitForTimeout(250);
    assert.ok((await work()).frames>beforeResize.frames,'resize must redraw the model');
    await snapshot('mobile');
    const mobileIdle = await sample(500);idleCheck(mobileIdle);
    await page.setViewportSize({width:960,height:900});await page.waitForTimeout(250);
    const rectangle = await page.locator('#canvas-host').boundingBox(), beforeDrag = await work();
    await page.mouse.move(rectangle.x+rectangle.width/2,rectangle.y+rectangle.height/2);
    await page.mouse.down();await page.mouse.move(rectangle.x+rectangle.width/2+70,rectangle.y+rectangle.height/2+20);await page.mouse.up();
    const interaction = await sample(3000);
    assert.ok(interaction.frames>1,'OrbitControls damping must continue after a drag');
    assert.ok((await work()).frames>beforeDrag.frames);
    await settle();
    await snapshot('orbit');
    const orbitIdle = await sample(500);idleCheck(orbitIdle);
    const beforeReset = await work();await page.locator('#reset-view').click();await page.waitForTimeout(1000);
    await settle();
    assert.ok((await work()).frames>beforeReset.frames,'reset view must redraw');
    await snapshot('reset');

    await page.locator('#start').click();await page.waitForFunction(() => document.querySelector('#camera').readyState>=2);
    const cameraWork = await sample(1000);
    assert.ok(cameraWork.frames>=10,'camera overlay must keep drawing');
    assert.equal((await diagnostics()).mode,'camera');
    await page.locator('#stop').click();await page.waitForTimeout(1000);
    const stoppedWork = await sample(500);idleCheck(stoppedWork);
    assert.equal((await diagnostics()).mode,'viewer');
    // Visibility suspension uses a dedicated document; it never switches a user's tab.
    await page.evaluate(() => {Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'));});
    const hiddenWork = await sample(500);assert.equal(hiddenWork.frames,0);
    await page.evaluate(() => {Object.defineProperty(document,'hidden',{configurable:true,value:false});document.dispatchEvent(new Event('visibilitychange'));});
    await page.waitForTimeout(300);
    const visibleWork = await sample(500);idleCheck(visibleWork);

    await page.evaluate(() => window.dispatchEvent(new PageTransitionEvent('pagehide')));
    const pageHideWork = await sample(500);idleCheck(pageHideWork);
    const beforePageShow = await work();
    await page.evaluate(() => window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true})));
    await page.waitForTimeout(250);
    assert.ok((await work()).frames>beforePageShow.frames,'pageshow must redraw a restored page');
    const pageShowWork = await sample(500);idleCheck(pageShowWork);
    const supportsContextLoss = await page.evaluate(() => {
      const canvas=document.querySelector('#canvas-host canvas'),gl=canvas.getContext('webgl2');
      window.__contextLoss=gl.getExtension('WEBGL_lose_context');
      if(!window.__contextLoss)return false;
      window.__contextLost=false;window.__contextRestored=false;
      canvas.addEventListener('webglcontextlost',()=>window.__contextLost=true,{once:true});
      canvas.addEventListener('webglcontextrestored',()=>window.__contextRestored=true,{once:true});
      window.__contextLoss.loseContext();return true;
    });
    let contextLostWork=null,contextRestoredWork=null;
    if(supportsContextLoss) {
      await page.waitForFunction(()=>window.__contextLost);
      contextLostWork=await sample(500);assert.equal(contextLostWork.frames,0);
      const beforeRestore=await work();await page.evaluate(()=>window.__contextLoss.restoreContext());
      await page.waitForFunction(()=>window.__contextRestored);await page.waitForTimeout(300);
      assert.ok((await work()).frames>beforeRestore.frames,'restored WebGL context must redraw');
      assert.equal((await diagnostics()).triangles,144);
      contextRestoredWork=await sample(500);idleCheck(contextRestoredWork);
    }

    const report = {browser:browser.version(),platform:process.platform,node:process.version,url,
      viewport:{width:960,height:900,deviceScaleFactor:1},sample_ms:sampleMs,
      model:{bytes:initialDiagnostics.model_bytes,triangles:initialDiagnostics.triangles},idle,
      idle_median:{frames:median(idle.map(x=>x.frames)),draw_calls:median(idle.map(x=>x.draw_calls)),task_ms:median(idle.map(x=>x.task_ms)),script_ms:median(idle.map(x=>x.script_ms))},
      checks:{opaqueIdle,mobileIdle,interaction,orbitIdle,cameraWork,stoppedWork,hiddenWork,visibleWork,pageHideWork,pageShowWork,supportsContextLoss,contextLostWork,contextRestoredWork},snapshots,errors,
      limits:['Desktop headless Chromium only; fake camera, no Safari/device thermal or battery measurements.','Performance counters cover this document; no whole-machine CPU or GPU power claim.']};
    assert.deepEqual(errors,[]);
    if(process.env.BASELINE_REPORT) {
      const baselinePath = path.resolve(process.env.BASELINE_REPORT), baseline = JSON.parse(await readFile(baselinePath,'utf8'));
      report.pixel_comparisons = {};
      for(const [name,entry] of Object.entries(snapshots)) {
        const previous = await readFile(path.resolve(path.dirname(baselinePath),baseline.snapshots[name].file)), current = await readFile(path.join(output,entry.file));
        const diff = await page.evaluate(async ([a,b]) => {
          const pixels = async uri => {const image=new Image();image.src=uri;await image.decode();const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0);return {width:image.width,height:image.height,data:ctx.getImageData(0,0,image.width,image.height).data};};
          const left=await pixels(a),right=await pixels(b);
          if(left.width!==right.width||left.height!==right.height)return {dimensions_equal:false};
          let changed=0,max=0,total=0;
          for(let i=0;i<left.data.length;i+=4) {let different=false;for(let j=0;j<4;j++){const delta=Math.abs(left.data[i+j]-right.data[i+j]);if(delta)different=true;max=Math.max(max,delta);total+=delta;}if(different)changed++;}
          return {dimensions_equal:true,width:left.width,height:left.height,differing_pixels:changed,total_pixels:left.width*left.height,max_channel_delta:max,mean_absolute_channel_delta:total/left.data.length};
        }, [previous,current].map(bytes=>'data:image/png;base64,'+bytes.toString('base64')));
        report.pixel_comparisons[name] = diff;
      }
    }
    await writeFile(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n');
    for(const [name,diff] of Object.entries(report.pixel_comparisons||{})) {
      assert.equal(diff.dimensions_equal,true);
      assert.ok(diff.differing_pixels/diff.total_pixels<0.001,name+' must remain within 0.1% pixel differences');
      assert.ok(diff.max_channel_delta<=2,name+' may differ by at most two 8-bit channel levels');
    }
    console.log(JSON.stringify({output,idle_median:report.idle_median,camera_frames:cameraWork.frames,pixel_comparisons:report.pixel_comparisons,errors}));
    await context.close();
  } finally {await browser.close();}
})().catch(error => {console.error(error);process.exitCode=1;});
