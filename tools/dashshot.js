/* Capture one dashboard view over the Chrome DevTools Protocol.
 *
 *   node dashshot.js <port> <url> <out.png> <width> <height> [selector]
 *
 * Why CDP and not the Browser pane: the pane caps a capture at roughly its
 * own 800x450, and these ship at 1920 wide on a 2x scale factor. Why a real
 * Chrome and not a screenshot API: the dashboard compiles its JSX in the
 * browser, so the page needs a genuine JS runtime and a moment to settle.
 *
 * Waits on `window.__READY` — set by the injected shot harness once React has
 * painted — rather than a fixed sleep, then adds a short settle for fonts and
 * the entrance transitions. A fixed sleep is how you get a screenshot of a
 * half-drawn chart.
 */
const fs = require('fs');
const [port, url, out, W, H, sel] = process.argv.slice(2);
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const t = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,
                               { method: 'PUT' })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  let id = 0; const pend = new Map();
  ws.addEventListener('message', e => {
    const m = JSON.parse(e.data);
    if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
  });
  const send = (method, params = {}) => new Promise(res => {
    const i = ++id; pend.set(i, res);
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  const evalJs = async expr => {
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    return r.result && r.result.result ? r.result.result.value : undefined;
  };
  await new Promise(r => ws.addEventListener('open', r));

  await send('Emulation.setDeviceMetricsOverride',
             { width: +W, height: +H, deviceScaleFactor: 2, mobile: false });
  await send('Page.enable');
  await send('Page.navigate', { url });

  // Babel compiles 22 JSX files in the page, so first paint is slow and the
  // wait has to be generous. Poll rather than guess.
  let ready = false;
  for (let i = 0; i < 60; i++) {
    await sleep(500);
    if (await evalJs('!!window.__READY')) { ready = true; break; }
  }
  if (!ready) { console.error('NOT READY', out); process.exit(2); }
  await sleep(1400);                                   // fonts + entrance

  if (sel && sel !== '-') {
    const found = await evalJs(
      `(()=>{const e=document.querySelector(${JSON.stringify(sel)});
        if(!e) return false; e.scrollIntoView({block:'start',behavior:'instant'});
        return true;})()`);
    if (!found) console.error('  ! selector not found:', sel);
    await sleep(700);
  }

  // Report what is actually on screen, so a wrong-view capture fails loudly
  // rather than shipping.
  const probe = await evalJs(`JSON.stringify({
    h1: (document.querySelector('main h1')||{}).textContent||'',
    photos: document.querySelectorAll('.avatar__photo').length,
    errs: (window.__ERRS||[]).length })`);
  console.log('  ' + out.split('/').pop().padEnd(16) + probe);

  const shot = await send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(out, Buffer.from(shot.result.data, 'base64'));
  ws.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
