// Local-only visual/interaction check. Supply the existing private export in
// data/local/web-exports/data221-af7335da; no model is bundled with this test.
const assert=require('node:assert/strict');
const fs=require('node:fs/promises'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const {createHash}=require('node:crypto');
const {chromium}=require('playwright');
const web=path.resolve(__dirname,'..');
const output=path.resolve(process.env.LOCAL_VIEWS_OUTPUT||path.join(web,'../../data/local/view-presets'));
const before=process.env.LOCAL_VIEWS_BEFORE==='1';
const baseline=process.env.LOCAL_VIEWS_BASELINE?path.resolve(process.env.LOCAL_VIEWS_BASELINE):null;
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const report={phase:before?'before':'after',cases:[],errors:[],external_requests:[],screenshots:[]};

(async()=>{
  let vite,browser;
  await fs.mkdir(output,{recursive:true});
  try{
    const {createServer}=await import(pathToFileURL(path.join(web,'node_modules/vite/dist/node/index.js')));
    vite=await createServer({root:web,configFile:path.join(web,'vite.config.js'),configLoader:'native',
      server:{host:'127.0.0.1',port:0,strictPort:true}});
    await vite.listen();const url=`http://127.0.0.1:${vite.httpServer.address().port}/`;
    browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'msedge',headless:true});
    report.browser=browser.version();
    const context=await browser.newContext({viewport:{width:960,height:900},deviceScaleFactor:1,serviceWorkers:'block'});
    await context.route('**/*',route=>{
      if(new URL(route.request().url()).origin===new URL(url).origin)return route.continue();
      report.external_requests.push(route.request().url());return route.abort();
    });
    await context.addInitScript(()=>{
      window.__draws=0;window.__cameraRequests=0;
      for(const prototype of [WebGLRenderingContext.prototype,WebGL2RenderingContext.prototype]){
        const clear=prototype.clear;prototype.clear=function(...args){if(this.canvas.parentElement?.id==='canvas-host')window.__draws++;return clear.apply(this,args);};
      }
      const getUserMedia=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      navigator.mediaDevices.getUserMedia=(...args)=>{window.__cameraRequests++;return getUserMedia(...args);};
    });
    const page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.message));
    // Camera inspection exists only in the intercepted QA response, never in the app.
    await page.route('**/src/main.js',async route=>{
      const response=await route.fetch();await route.fulfill({response,body:await response.text()+`
        window.__localViewCheck=()=>{
          camera.updateMatrixWorld(true);const bounds=manifest.assets[0].bounds_render_m;
          return {position:camera.position.toArray(),target:controls.target.toArray(),quaternion:camera.quaternion.toArray(),
            preset:typeof localPreset==='undefined'?null:localPreset,aspect:camera.aspect,
            corners:Array.from({length:8},(_,mask)=>new THREE.Vector3(...[0,1,2].map(i=>bounds[i+((mask>>i)&1)*3])).project(camera).toArray())};
        };`});
    });
    const ready=()=>page.waitForFunction(()=>{try{return document.getElementById('loading').hidden&&JSON.parse(document.getElementById('diagnostics').textContent).local_model?.triangles===466;}catch{return false;}});
    const idle=async()=>{
      await page.evaluate(()=>window.__idle={last:-1,stable:0});
      await page.waitForFunction(()=>{const p=window.__idle;if(p.last===window.__draws)p.stable++;else{p.last=window.__draws;p.stable=0;}return p.stable>=5;},null,{polling:100});
    };
    const view=()=>page.evaluate(()=>window.__localViewCheck());
    const fits=v=>assert.ok(v.corners.every(p=>p.every(n=>Number.isFinite(n)&&Math.abs(n)<1)),'all model bounds must fit');
    const screenshot=async(name,canvas=false)=>{
      const file=`${report.phase}-${name}.png`,bytes=canvas?await page.locator('#canvas-host').screenshot({path:path.join(output,file)}):await page.screenshot({path:path.join(output,file),fullPage:true});
      report.screenshots.push({file,sha256:hash(bytes)});return bytes;
    };
    const passed=name=>report.cases.push({name,passed:true});
    await page.goto(url+'?local_model=data221-af7335da');await ready();await idle();fits(await view());
    report.model=JSON.parse(await page.locator('#diagnostics').textContent()).local_model;
    await screenshot('desktop');const home=await screenshot('overview-canvas',true);
    await page.setViewportSize({width:390,height:900});await idle();fits(await view());await screenshot('mobile');
    await page.setViewportSize({width:960,height:900});await idle();
    passed('actual local GLB loads and fits desktop/mobile');
    if(!before){
      if(baseline)assert.equal(hash(home),hash(await fs.readFile(path.join(baseline,'before-overview-canvas.png'))),'overview geometry/render must remain unchanged');
      const button=id=>page.locator(`[data-local-view="${id}"]`);
      const selection=async id=>{
        assert.equal((await view()).preset,id);
        for(const name of ['overview','north','east'])assert.equal(await button(name).getAttribute('aria-pressed'),String(name===id));
      };
      const direction=async id=>{
        const v=await view();fits(v);const d=v.position.map((n,i)=>n-v.target[i]);
        if(id==='north'){assert.ok(Math.abs(d[0])<1e-8);assert.ok(d[2]<0);}
        if(id==='east'){assert.ok(d[0]>0);assert.ok(Math.abs(d[2])<1e-8);}
        await selection(id);
      };
      await page.locator('#reset-view').focus();await page.keyboard.press('Tab');
      assert.equal(await button('overview').evaluate(e=>e===document.activeElement),true);
      await page.keyboard.press('Tab');assert.equal(await button('north').evaluate(e=>e===document.activeElement),true);
      await page.keyboard.press('Enter');await idle();await direction('north');await screenshot('north-desktop');
      const north=await view();await page.keyboard.press('Tab');await page.keyboard.press('Space');await idle();await direction('east');
      assert.equal(await button('east').evaluate(e=>e===document.activeElement),true);await screenshot('east-desktop');
      assert.notDeepEqual((await view()).position,north.position);
      passed('desktop Tab / Enter / Space select visible north/east presets');
      for(const id of ['overview','north','east']){
        await button(id).click();await idle();await direction(id);
        for(const size of [{width:390,height:900},{width:900,height:390},{width:320,height:740},{width:960,height:900}]){
          await page.setViewportSize(size);await idle();await direction(id);
          assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'no horizontal overflow');
        }
      }
      passed('all presets retain direction and fit through portrait / landscape / 320px resize');
      await page.setViewportSize({width:390,height:900});await idle();
      await page.locator('#reset-view').focus();await page.keyboard.press('Tab');await page.keyboard.press('Tab');await page.keyboard.press('Enter');await idle();await direction('north');
      await page.keyboard.press('Tab');await page.keyboard.press('Space');await idle();await direction('east');await screenshot('east-mobile');
      passed('mobile viewport Tab / Enter / Space retain focus and select views');
      await page.setViewportSize({width:960,height:900});await idle();
      const box=await page.locator('#canvas-host').boundingBox();
      await page.mouse.move(box.x+box.width*.65,box.y+box.height*.45);await page.mouse.down();await page.mouse.move(box.x+box.width*.35,box.y+box.height*.5,{steps:8});
      const during=await page.evaluate(()=>{
        const pre=window.__localViewCheck(),stage=document.getElementById('stage'),height=stage.style.height;
        stage.style.height=(stage.clientHeight+70)+'px';window.dispatchEvent(new Event('resize'));
        const post=window.__localViewCheck();stage.style.height=height;window.dispatchEvent(new Event('resize'));return {pre,post};
      });
      assert.equal(during.pre.preset,null);assert.notEqual(during.pre.aspect,during.post.aspect);
      for(const key of ['position','target','quaternion'])assert.deepEqual(during.pre[key],during.post[key]);
      await page.mouse.up();
      // Switch while the previous orbit is still damping; there must be no residual drift.
      await button('north').click();await idle();await direction('north');
      const settled=await view();await button('north').click();await idle();assert.deepEqual((await view()).position,settled.position);
      passed('preset cancels orbit inertia; repeated selection is deterministic');
      await page.mouse.move(box.x+box.width*.65,box.y+box.height*.5);await page.mouse.down({button:'right'});await page.mouse.move(box.x+box.width*.48,box.y+box.height*.55,{steps:8});await page.mouse.up({button:'right'});await idle();await selection(null);
      const manual=await view();await page.setViewportSize({width:390,height:900});await idle();
      const resized=await view();
      // Resuming a settled OrbitControls frame can consume its sub-micrometre damping tail.
      report.manual_resize_max_delta=Math.max(...['position','target','quaternion'].flatMap(key=>resized[key].map((n,i)=>Math.abs(n-manual[key][i]))));
      assert.ok(report.manual_resize_max_delta<1e-6,'manual camera must not be reframed');
      assert.match(await page.locator('#local-view-status').innerText(),/自由視点/);
      await page.locator('#reset-view').click();await idle();await direction('overview');
      await page.setViewportSize({width:960,height:900});await idle();await direction('overview');
      passed('drag/pan become manual; resize preserves manual pose; reset restores overview auto-fit');
      assert.equal(await page.locator('#start').isVisible(),false);assert.equal(await page.locator('#capture').isVisible(),false);
      assert.equal(await page.evaluate(()=>window.__cameraRequests),0);
      const draws=await page.evaluate(()=>window.__draws);await page.waitForTimeout(500);assert.equal(await page.evaluate(()=>window.__draws),draws);
      passed('local review stays camera-free and settled renderer stays idle');
      for(const failure of ['missing','corrupt']){
        const failed=await context.newPage();failed.on('pageerror',e=>report.errors.push(e.message));
        await failed.route('**/__otw_local__/data221-af7335da/model.glb',route=>route.fulfill({status:failure==='missing'?404:200,body:'not a model'}));
        await failed.goto(url+'?local_model=data221-af7335da');
        await failed.waitForFunction(()=>document.getElementById('loading').textContent.includes('再読み込み'));
        assert.equal(await failed.locator('#local-view-controls').isVisible(),false);assert.equal(await failed.locator('#start').isDisabled(),true);await failed.close();
      }
      passed('failed load/hash validation never reveals usable preset controls');
    }
    await page.goto(url);await page.waitForFunction(()=>!document.getElementById('start').disabled);await idle();
    await page.locator('#opacity').evaluate(e=>{e.value='100';e.dispatchEvent(new Event('input',{bubbles:true}));});await idle();
    const fixture=await screenshot('fixture-canvas',true);
    if(!before){
      assert.equal(await page.locator('#local-view-controls').isVisible(),false);
      if(baseline)assert.equal(hash(fixture),hash(await fs.readFile(path.join(baseline,'before-fixture-canvas.png'))));
      passed(baseline?'public fixture UI/opaque render unchanged':'public fixture loads without local view controls');
    }
    report.compared_baseline=baseline;
    assert.deepEqual(report.errors,[]);assert.deepEqual(report.external_requests,[]);report.ok=true;
  }catch(error){report.ok=false;report.failure=error.stack;throw error;}
  finally{
    await browser?.close();await vite?.close();
    await fs.writeFile(path.join(output,`${report.phase}-browser.json`),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify({ok:report.ok,phase:report.phase,cases:report.cases.length,errors:report.errors.length,external_requests:report.external_requests.length}));
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
