// 真实鼠标点击回归检查：node check_click.cjs <页面.html> [额外按钮选择器]
// 用 CDP Input.dispatchMouseEvent 逐个点击 .seg 分段按钮、button.preset 预设按钮（及额外选择器），检查：
//   1. 页面没有抛出未捕获异常（rAF 回调里抛错会让动画永久停止）
//   2. 页面一开始在动的，点击后仍在动
//   3. 点过的预设 / 分段按钮带 .on 高亮
// 脚本里的 el.click() 不经过浏览器"帧开头处理输入"的时序，复现不了 rAF 时间戳早于 t0 的问题，所以必须用真实输入事件。
// 不依赖 npm 包（Node 18+）。浏览器：Windows 用 Edge，其他系统用 google-chrome / chromium，或设置环境变量 CHROME。
const { spawn } = require('node:child_process');
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const { pathToFileURL } = require('node:url');

const page = process.argv[2], extra = process.argv[3];
if (!page) { console.error('用法: node check_click.cjs <页面.html> [额外按钮选择器]'); process.exit(2); }
const exe = process.env.CHROME || ['C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', 'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'].find(fs.existsSync);
if (!exe) { console.error('找不到 Chromium 内核浏览器，请设置环境变量 CHROME'); process.exit(2); }
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'avclick-'));
const br = spawn(exe, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-pipe',
  '--window-size=1600,1000', '--user-data-dir=' + profile, 'about:blank'], { stdio: ['ignore', 'ignore', 'ignore', 'pipe', 'pipe'] });
let seq = 0, buf = '', sid = null;
const pend = new Map(), events = [];
br.stdio[4].on('data', ch => {
  buf += ch; let e;
  while ((e = buf.indexOf('\0')) !== -1) {
    const raw = buf.slice(0, e); buf = buf.slice(e + 1); if (!raw) continue;
    const m = JSON.parse(raw);
    if (m.id && pend.has(m.id)) { const p = pend.get(m.id); pend.delete(m.id); clearTimeout(p.timer); m.error ? p.rej(Error(JSON.stringify(m.error))) : p.res(m.result); }
    else if (m.method) events.push(m);
  }
});
const call = (method, params = {}, s = sid) => new Promise((res, rej) => {
  const id = ++seq, timer = setTimeout(() => { pend.delete(id); rej(Error('超时: ' + method)); }, 30000);
  pend.set(id, { res, rej, timer });
  br.stdio[3].write(JSON.stringify({ id, method, params, ...(s ? { sessionId: s } : {}) }) + '\0');
});
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ev = async expr => {
  const r = await call('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw Error(JSON.stringify(r.exceptionDetails));
  return r.result.value;
};
// SVG / canvas 的几何属性快照；前后两次不同即视为"在动"
const SNAP = `(() => [...document.querySelectorAll('svg polygon, svg path, svg circle, svg line, svg rect, svg g[transform]')]
  .map(e => ['points','d','transform','cx','cy','x1','y1','x','y'].map(a => e.getAttribute(a) || '').join(',')).join('|')
  + [...document.querySelectorAll('canvas')].map(c => { try { return c.toDataURL().length; } catch (e) { return 0; } }).join(','))()`;
const moving = async () => { const a = await ev(SNAP); await sleep(450); return a !== await ev(SNAP); };

(async () => {
  const { targetId } = await call('Target.createTarget', { url: 'about:blank' }, null);
  sid = (await call('Target.attachToTarget', { targetId, flatten: true }, null)).sessionId;
  await call('Runtime.enable'); await call('Page.enable');
  await call('Page.navigate', { url: pathToFileURL(path.resolve(page)).href });
  await sleep(1500);
  const animated = await moving();
  const sel = ['.seg button', 'button.preset', extra].filter(Boolean).join(', ');
  const btns = await ev(`[...document.querySelectorAll(${JSON.stringify(sel)})].map((b, i) => { b.dataset.avci = i;
    return [i, b.textContent.trim(), b.classList.contains('preset') || !!b.closest('.seg')]; })`);
  const fails = [];
  for (const [i, label, needOn] of btns) {
    const pos = await ev(`(() => { const b = document.querySelector('[data-avci="${i}"]'); if (!b || b.offsetParent === null) return null;
      b.scrollIntoView({ block: 'center' }); const r = b.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()`);
    if (!pos) continue;
    await sleep(80);
    for (const type of ['mousePressed', 'mouseReleased']) await call('Input.dispatchMouseEvent', { type, x: pos[0], y: pos[1], button: 'left', clickCount: 1 });
    await sleep(250);
    const on = await ev(`document.querySelector('[data-avci="${i}"]').classList.contains('on')`);
    const mv = animated ? await moving() : null;
    if (needOn && !on) fails.push(`「${label}」点击后没有高亮（缺 .on）`);
    if (animated && !mv) fails.push(`点击「${label}」后动画停止`);
    console.log(`${needOn ? (on ? '✓ 高亮' : '✗ 未高亮') : '  —    '}  ${animated ? (mv ? '✓ 在动' : '✗ 停止') : '（静态页）'}  ${label}`);
  }
  const errs = events.filter(e => e.method === 'Runtime.exceptionThrown')
    .map(e => (e.params.exceptionDetails.exception?.description || e.params.exceptionDetails.text || '').split('\n').slice(0, 2).join(' / '));
  errs.forEach(e => fails.push('未捕获异常：' + e));
  console.log(fails.length ? `FAIL（${fails.length} 项）\n  ` + [...new Set(fails)].join('\n  ') : `OK  共点击 ${btns.length} 个按钮`);
  br.kill();
  process.exit(fails.length ? 1 : 0);
})().catch(e => { console.error(e); br.kill(); process.exit(2); });
