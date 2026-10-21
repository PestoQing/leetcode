// Real-browser interaction regression check. No npm packages required (Node 18+).
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const assert = require('node:assert/strict');
const page = process.argv[2];
if (!page) { console.error('Usage: node check_drag.cjs <page.html>'); process.exit(2); }
const browserPath = process.env.CHROME || ['/usr/bin/google-chrome','/usr/bin/chromium','C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'].find(fs.existsSync);
if (!browserPath) throw Error('Set CHROME to an installed Chromium browser');
const profile = fs.mkdtempSync(path.join(os.tmpdir(),'av-drag-'));
const browser = spawn(browserPath, ['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-pipe','--window-size=1920,1080','--force-device-scale-factor=1','--user-data-dir='+profile,'about:blank'], {stdio:['ignore','ignore','ignore','pipe','pipe']});
let sequence=0, buffer='', session, closed=false;
const pending=new Map();
browser.on('exit',()=>{closed=true;for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Browser exited'));}pending.clear();});
browser.stdio[4].on('data',chunk=>{buffer+=chunk;let end;while((end=buffer.indexOf('\0'))!==-1){const raw=buffer.slice(0,end);buffer=buffer.slice(end+1);if(!raw)continue;const m=JSON.parse(raw),p=pending.get(m.id);if(p){pending.delete(m.id);clearTimeout(p.timer);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}}});
function call(method,params={},sid=session){return new Promise((resolve,reject)=>{const id=++sequence;const timer=setTimeout(()=>{pending.delete(id);reject(Error('Timed out: '+method));},30000);pending.set(id,{resolve,reject,timer});browser.stdio[3].write(JSON.stringify({id,method,params,...(sid?{sessionId:sid}:{})})+'\0');});}
async function evaluate(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
const frames=()=>evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');
const bounds=id=>evaluate(`(()=>{const r=document.getElementById(${JSON.stringify(id)}).getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};})()`);
async function mouse(type,x,y){if(type==='mousePressed')await call('Input.dispatchMouseEvent',{type:'mouseMoved',x,y,buttons:0});await call('Input.dispatchMouseEvent',{type,x,y,button:'left',buttons:type==='mouseReleased'?0:1,clickCount:1});}
const state=()=>evaluate(`({step:document.getElementById('stepNo').textContent,instant:AV.isInstant(),dragging:!!document.querySelector('.dragging')})`);
(async()=>{try{
 const targets=await call('Target.getTargets',{},null);const target=targets.targetInfos.find(t=>t.type==='page');
 session=(await call('Target.attachToTarget',{targetId:target.targetId,flatten:true},null)).sessionId;
 await call('Page.navigate',{url:pathToFileURL(path.resolve(page)).href});
 for(let i=0;i<100;i++){if(await evaluate('typeof AV!=="undefined" && !!document.getElementById("stepNo")?.textContent'))break;await new Promise(r=>setTimeout(r,50));}
 await frames();
 const bar=await bounds('progress'), y=bar.y+bar.height/2;
 await mouse('mousePressed',bar.x+1,y);await frames();
 const burst=await evaluate(`(async()=>{
  const bar=document.getElementById('progress'),r=bar.getBoundingClientRect();let renders=0;
  const obs=new MutationObserver(records=>renders+=records.length);obs.observe(document.getElementById('stepNo'),{childList:true});
  for(let i=1;i<=100;i++)bar.dispatchEvent(new PointerEvent('pointermove',{pointerId:1,isPrimary:true,clientX:r.left+r.width*i/100,clientY:r.top,buttons:1}));
  await Promise.resolve();const synchronous=renders;
  await new Promise(done=>requestAnimationFrame(()=>requestAnimationFrame(done)));
  obs.disconnect();return {synchronous,renders,step:document.getElementById('stepNo').textContent,instant:AV.isInstant()};
 })()`);
 assert.equal(burst.synchronous,0,'pointermove should not synchronously render');
 assert.equal(burst.renders,1,'100 pointer moves should render the latest snapshot once');
 assert.equal(burst.instant,true);
 let [step,total]=burst.step.split('/').map(Number);assert.equal(step,total);
 await mouse('mouseReleased',bar.x+bar.width*.37,y);await frames();
 let s=await state();[step,total]=s.step.split('/').map(Number);assert.equal(step,Math.round(.37*(total-1))+1);assert.equal(s.instant,false);assert.equal(s.dragging,false);
 for(const type of ['pointercancel','lostpointercapture']){
  await mouse('mousePressed',bar.x+bar.width*.5,y);
  await evaluate(`document.getElementById('progress').dispatchEvent(new PointerEvent('${type}',{pointerId:1,isPrimary:true}))`);
  await mouse('mouseReleased',bar.x+bar.width*.5,y);await frames();s=await state();assert.equal(s.instant,false);assert.equal(s.dragging,false);
 }
 // A new preset interrupts an unpainted seek: no stale callback may overwrite its first step.
 await mouse('mousePressed',bar.x+1,y);
 await evaluate(`(()=>{const bar=document.getElementById('progress'),r=bar.getBoundingClientRect();bar.dispatchEvent(new PointerEvent('pointermove',{pointerId:1,isPrimary:true,clientX:r.right,buttons:1}));document.querySelector('button.preset, #inputs button.primary').click();})()`);
 await mouse('mouseReleased',bar.x+1,y);await frames();s=await state();assert.equal(Number(s.step.split('/')[0]),1);assert.equal(s.instant,false);
 // Splitter ends at release coordinate and writes the clamped width to storage.
 const initialWidth=await evaluate(`parseInt(document.getElementById('app').style.getPropertyValue('--code-w'))`);
 const splitter=await bounds('splitter'), sx=splitter.x+splitter.width/2, sy=splitter.y+40;
 await mouse('mousePressed',sx,sy);await mouse('mouseMoved',sx-60,sy);await mouse('mouseReleased',sx-80,sy);await frames();
 const width=await evaluate(`({style:parseInt(document.getElementById('app').style.getPropertyValue('--code-w')),saved:+localStorage.getItem('algoviz.codeW')})`);assert.equal(width.style,width.saved);assert.equal(width.style,initialWidth+80);s=await state();assert.equal(s.dragging,false);assert.equal(s.instant,false);
 await evaluate(`document.getElementById('btnFirst').click();document.getElementById('btnPlay').click()`);
 await new Promise(r=>setTimeout(r,220));s=await state();assert.ok(Number(s.step.split('/')[0])>1,'playback must still advance');assert.equal(s.instant,false);
 await evaluate(`document.getElementById('btnPlay').click()`);
 console.log(JSON.stringify({ok:true,burst,releaseStep:'verified',cancel:'verified',preset:'verified',splitter:width,playback:'verified'},null,2));
 }catch(e){console.error(e);process.exitCode=1;}finally{
  if(!closed){try{await call('Browser.close',{},null);}catch{}}
  if(!closed)await Promise.race([new Promise(r=>browser.once('exit',r)),new Promise(r=>setTimeout(r,2000))]);
  if(!closed)browser.kill('SIGTERM');
  for(const p of pending.values())clearTimeout(p.timer);
  fs.rmSync(profile,{recursive:true,force:true});
 }
})();
