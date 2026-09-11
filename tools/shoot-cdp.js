// Drive a real headless Chrome over CDP: real frames, real mouse events.
// node shoot-cdp.js <url> <out.png> <mouseXfrac> <mouseYfrac> [width] [height]
const fs = require('fs');
const [url, out, mx = '0.55', my = '0.45', W = '1440', H = '620'] = process.argv.slice(2);
const PORT = 9338;
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json/new?${encodeURIComponent('about:blank')}`, { method: 'PUT' })).json();
  const ws = new WebSocket(list.webSocketDebuggerUrl);
  let id = 0; const pend = new Map();
  ws.addEventListener('message', e => {
    const m = JSON.parse(e.data);
    if (m.id && pend.has(m.id)) { pend.get(m.id)(m.result); pend.delete(m.id); }
  });
  const send = (method, params = {}) => new Promise(res => {
    const i = ++id; pend.set(i, res);
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  await new Promise(r => ws.addEventListener('open', r));

  await send('Emulation.setDeviceMetricsOverride',
    { width: +W, height: +H, deviceScaleFactor: 2, mobile: false });
  await send('Page.enable');
  await send('Page.navigate', { url });
  await sleep(3500);                              // fonts, layout, entrance

  // A real cursor, moved in real steps, so the pointer path is exercised.
  const bx = +W * +mx, by = +H * +my;
  for (let k = 0; k < 14; k++) {
    await send('Input.dispatchMouseEvent', {
      type: 'mouseMoved',
      x: bx + Math.sin(k / 3) * 14,
      y: by + Math.cos(k / 3) * 10
    });
    await sleep(70);
  }
  await sleep(600);

  const shot = await send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(out, Buffer.from(shot.data, 'base64'));
  const probe = await send('Runtime.evaluate', {
    expression: `(() => { const t = document.getElementById('vizTag');
      return JSON.stringify({ hidden: t.hidden, text: t.textContent,
        tf: t.style.transform, op: t.style.opacity,
        canvas: document.getElementById('viz').width }); })()`,
    returnByValue: true
  });
  console.log(probe.result.value);
  ws.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
