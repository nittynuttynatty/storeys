// Phone/desktop smoke test with mocked map tiles, data and Supabase (never touches the live community).
// Needs playwright + maplibre-gl + @fontsource/fraunces,figtree in ../node_modules; run from the folder above the repo:
//   node topalready.github.io/tests/ui.smoke.js
const {chromium}=require('playwright');const fs=require('fs');
const R='topalready.github.io/';
const shots='/tmp/claude-0/ui/';fs.mkdirSync(shots,{recursive:true});
const ago=d=>new Date(Date.now()-d*864e5).toISOString();
async function page(b,{w=390,h=844,reduce=false,dataFail=false,sbFail=false,geo=true}={}){
  const ctx=await b.newContext({viewport:{width:w,height:h},deviceScaleFactor:1.5,colorScheme:'light',reducedMotion:reduce?'reduce':'no-preference',...(geo?{geolocation:{latitude:1.3778,longitude:103.7625},permissions:['geolocation']}:{})});
  await ctx.addInitScript(()=>{window.__geo=0;const g=navigator.geolocation;if(g){const o=g.getCurrentPosition.bind(g);g.getCurrentPosition=(...a)=>{window.__geo++;return o(...a)}}});
  const pg=await ctx.newPage();const errs=[];pg.on('pageerror',e=>errs.push(e.message));
  await pg.route('**/*',async r=>{const u=r.request().url();
    if(u.includes('maplibre-gl.min.js'))return r.fulfill({body:fs.readFileSync('node_modules/maplibre-gl/dist/maplibre-gl.js'),contentType:'application/javascript'});
    if(u.includes('maplibre-gl.min.css'))return r.fulfill({body:fs.readFileSync('node_modules/maplibre-gl/dist/maplibre-gl.css'),contentType:'text/css'});
    if(u.includes('openfreemap'))return r.fulfill({status:404,body:''});
    if(u.startsWith('https://fonts.googleapis.com/css2')){let css='';for(const [f,ws] of [['Fraunces',[400,500,600]],['Figtree',[400,500,600]]])for(const w2 of ws)css+=`@font-face{font-family:'${f}';font-weight:${w2};src:url(https://fontfile.test/${f.toLowerCase()}-latin-${w2}-normal.woff2) format('woff2')}`;return r.fulfill({body:css,contentType:'text/css'})}
    if(u.startsWith('https://fontfile.test/')){const n=u.split('/').pop();return r.fulfill({body:fs.readFileSync(`node_modules/@fontsource/${n.split('-')[0]}/files/${n}`),contentType:'font/woff2'})}
    if(u.startsWith('https://x.test/data.json'))return dataFail?r.fulfill({status:500,body:''}):r.fulfill({body:fs.readFileSync(R+'data.json'),contentType:'application/json'});
    if(u.match(/x\.test\/icon/))return r.fulfill({body:fs.readFileSync(R+u.split('/').pop().split('?')[0]),contentType:'image/png'});
    if(u.startsWith('https://x.test/manifest'))return r.fulfill({body:fs.readFileSync(R+'manifest.webmanifest'),contentType:'application/manifest+json'});
    if(u.startsWith('https://x.test/'))return r.fulfill({body:fs.readFileSync(R+'index.html'),contentType:'text/html'});
    if(u.includes('supabase.co')){
      if(sbFail)return r.fulfill({status:500,body:'{}'});
      if(r.request().method()==='POST')return r.fulfill({status:201,body:''});
      if(u.includes('storage/v1/object/public'))return r.fulfill({body:fs.readFileSync(R+'icon-512.png'),contentType:'image/png'});
      if(u.includes('project_status'))return r.fulfill({body:JSON.stringify([{project_key:'BTO:Bangkit Breeze:2025-07',last_photo:ago(1),photos_30d:1,photos:1,storeys:null,storeys_at:null,total_storeys:null}]),contentType:'application/json'});
      if(u.includes('rest/v1/photos')&&u.includes('project_key=eq')&&u.includes('Bangkit'))return r.fulfill({body:JSON.stringify([{id:'a',path:'x/1.jpg',taken_at:ago(1),distance_m:140,storeys:null,total_storeys:null}]),contentType:'application/json'});
      if(u.includes('rest/v1/photos')&&!u.includes('project_key=eq'))return r.fulfill({body:JSON.stringify([{id:'a',path:'x/1.jpg',taken_at:ago(1),project_key:'BTO:Bangkit Breeze:2025-07'},{id:'b',path:'x/2.jpg',taken_at:ago(9),project_key:'Condo:Hillhaven:2024-01'}]),contentType:'application/json'});
      return r.fulfill({body:'[]',contentType:'application/json'});
    }
    return r.fulfill({status:404,body:''});
  });
  return {ctx,pg,errs};
}
const log=(...a)=>console.log(...a);
(async()=>{const b=await chromium.launch({args:['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist']});
 const fails=[];const check=(c,msg)=>{log((c?'PASS ':'FAIL ')+msg);if(!c)fails.push(msg)};
 for(const w of [320,390]){
  const {ctx,pg,errs}=await page(b,{w});
  await pg.goto('https://x.test/');await pg.waitForTimeout(2500);
  await pg.screenshot({path:shots+`first-${w}.png`});
  const st=await pg.evaluate(()=>({welcome:!$('#welcome').hidden,geo:window.__geo,centre:MAP?MAP.getCenter().toArray():null,label:$('#nearlabel').textContent,card:$('.ncard')?.textContent.replace(/\s+/g,' ')}));
  check(st.welcome,`[${w}] welcome shown on first visit`);check(st.geo===0,`[${w}] no location prompt on load`);
  check(st.centre&&!(Math.abs(st.centre[1]-1.3521)<.01&&Math.abs(st.centre[0]-103.8198)<.01),`[${w}] map doesn't start over the reservoir (${st.centre&&st.centre.map(v=>v.toFixed(3))})`);
  check(/map centre/.test(st.label)&&/from map centre|at map centre/.test(st.card),`[${w}] nearby distances say "from map centre": "${st.card}"`);
  check(/% of timeline|Not launched/.test(st.card),`[${w}] nearby card labels % as timeline`);
  await pg.click('#welcomesearch');check(await pg.evaluate(()=>document.activeElement.id==='q'),`[${w}] "Find my project" focuses search`);
  await pg.fill('#q','zzzzqq');await pg.waitForTimeout(200);check(/No match/.test(await pg.textContent('#sugg')),`[${w}] no-result search state`);
  await pg.fill('#q','bangkit');await pg.waitForTimeout(200);await pg.click('#sugg .pick');await pg.waitForFunction(()=>!$('#sheet').hidden,null,{timeout:12000}).catch(()=>{});await pg.waitForTimeout(400);
  const s1=await pg.evaluate(()=>({open:!$('#sheet').hidden,url:location.search,txt:$('#sheetbody').innerText}));
  check(s1.open&&s1.url.includes('bangkit-breeze'),`[${w}] search result opens project (${s1.url})`);
  check(/of estimated timeline elapsed/.test(s1.txt)&&/doesn't measure work on site/.test(s1.txt),`[${w}] sheet explains timeline %`);
  check(!/Pace|wait to keys/.test(s1.txt),`[${w}] no "Pace"/"wait to keys" wording`);
  check(/Where these numbers come from/.test(s1.txt),`[${w}] sources box present`);
  await pg.evaluate(()=>{$('.sources').open=true;$('.sources').scrollIntoView()});await pg.waitForTimeout(200);await pg.screenshot({path:shots+`sources-${w}.png`});
  await pg.evaluate(()=>$('.photos').scrollIntoView());await pg.waitForTimeout(200);await pg.screenshot({path:shots+`photos-${w}.png`});
  // watch + back button
  await pg.click('[data-watch-toggle]');await pg.goBack();await pg.waitForTimeout(400);
  const s2=await pg.evaluate(()=>({open:!$('#sheet').hidden,url:location.href}));
  check(!s2.open&&s2.url.startsWith('https://x.test/'),`[${w}] back button closes the panel and stays in the app`);
  await pg.reload();await pg.waitForTimeout(2000);
  check(await pg.evaluate(()=>tracked.length===1&&$('#list').textContent.includes('Bangkit')),`[${w}] watchlist persists after reload`);
  check(await pg.evaluate(()=>$('#welcome').hidden),`[${w}] welcome not repeated`);
  await pg.evaluate(()=>setTab('watch'));await pg.waitForTimeout(300);await pg.screenshot({path:shots+`watch-${w}.png`});
  check(/of estimated timeline elapsed/.test(await pg.textContent('#list')),`[${w}] watchlist labels % as timeline`);
  // community
  await pg.evaluate(()=>setTab('disc'));await pg.waitForTimeout(800);await pg.screenshot({path:shots+`community-${w}.png`,fullPage:false});
  const order=await pg.evaluate(()=>[...document.querySelectorAll('#v-disc .sect')].map(h=>h.textContent));
  check(order[0]==='Latest from the sites',`[${w}] photos come first: ${order.join(' > ')}`);
  check(/Taken .* · /.test(await pg.textContent('#feed')),`[${w}] feed shows names + photo dates`);
  // snap a site: no location prompt until tapped
  const g0=await pg.evaluate(()=>window.__geo);await pg.click('#snapbtn');await pg.waitForTimeout(500);
  check(await pg.evaluate(g=>window.__geo===g,g0),`[${w}] Snap a site doesn't ask for location on open`);
  await pg.screenshot({path:shots+`snap-${w}.png`});
  await pg.click('#snapnear');await pg.waitForTimeout(800);
  check(await pg.evaluate(g=>window.__geo===g+1,g0)&&/Closest to you/.test(await pg.textContent('#snaplist')),`[${w}] location used only after "Show sites near me"`);
  await pg.keyboard.press('Escape');await pg.waitForTimeout(300);
  // upload without GPS: explains before asking
  await pg.evaluate(()=>{const i=P.findIndex(p=>p.name==='Hillhaven');openSheet(i);window.readExif=()=>({date:new Date()});
    const c=document.createElement('canvas');c.width=40;c.height=30;c.toBlob(bl=>uploadFile(P[i].key,new File([bl],'x.jpg',{type:'image/jpeg'})),'image/jpeg')});
  await pg.waitForTimeout(600);const g1=await pg.evaluate(()=>window.__geo);
  const stt=await pg.textContent('#sheet .status');
  check(/no location saved/.test(stt),`[${w}] no-GPS photo explains first: "${stt.slice(0,60)}"`);
  await pg.evaluate(()=>$('#sheet .status').scrollIntoView({block:'center'}));await pg.screenshot({path:shots+`nogps-${w}.png`});
  await pg.click('#sheet .status button.ghost');await pg.waitForTimeout(2500);
  check(await pg.evaluate(g=>window.__geo===g+1,g1),`[${w}] location asked only after tapping "Use my current location"`);
  const after=await pg.evaluate(()=>({st:$('#sheet .status')?.textContent||'',cheer:!$('#cheer').hidden}));
  check(after.cheer||/km from|Photos need/.test(after.st),`[${w}] upload result shown (${after.cheer?'celebration':after.st.slice(0,60)})`);
  check(errs.length===0,`[${w}] no page errors ${JSON.stringify(errs)}`);
  await ctx.close();
 }
 // desktop
 {const {ctx,pg,errs}=await page(b,{w:1280,h:800,reduce:true});await pg.goto('https://x.test/?p=hillhaven');await pg.waitForTimeout(2500);
  await pg.screenshot({path:shots+'desktop-sheet.png'});
  const s=await pg.evaluate(()=>({open:!$('#sheet').hidden,focus:document.activeElement.className}));
  check(s.open,'[desktop] deep link opens project (reduced motion)');check(/xbtn/.test(s.focus),'[desktop] focus moves to close button');
  await pg.keyboard.press('Escape');await pg.waitForTimeout(300);check(await pg.evaluate(()=>$('#sheet').hidden),'[desktop] Escape closes panel');
  await pg.screenshot({path:shots+'desktop-map.png'});check(errs.length===0,'[desktop] no page errors '+JSON.stringify(errs));await ctx.close()}
 // failures
 {const {ctx,pg,errs}=await page(b,{dataFail:true});await pg.goto('https://x.test/');await pg.waitForTimeout(1500);
  check(/Couldn't load the project data/.test(await pg.evaluate(()=>$('#list').textContent))&&/Couldn't load/.test(await pg.textContent('#toast')),'[fail] data outage explained');await ctx.close()}
 {const {ctx,pg,errs}=await page(b,{sbFail:true});await pg.goto('https://x.test/');await pg.waitForTimeout(2000);await pg.evaluate(()=>{hideWelcome();setTab('disc')});await pg.waitForTimeout(700);
  check(/couldn't load/i.test(await pg.textContent('#feed')),'[fail] photo service outage explained');check(errs.length===0,'[fail] no page errors '+JSON.stringify(errs));await ctx.close()}
 log(`\n${fails.length?fails.length+' FAILED':'ALL PASSED'}`);await b.close()})();
