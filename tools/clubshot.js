const PORT = 9338, sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const t = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl); let id = 0; const p = new Map();
  ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && p.has(m.id)) { p.get(m.id)(m.result); p.delete(m.id); } });
  const send = (me, pa = {}) => new Promise(r => { const i = ++id; p.set(i, r); ws.send(JSON.stringify({ id: i, method: me, params: pa })); });
  await new Promise(r => ws.addEventListener('open', r));
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 620, deviceScaleFactor: 2, mobile: false });
  await send('Page.navigate', { url: 'http://localhost:3000/#/' });
  await sleep(2800);
  await send('Runtime.evaluate', { expression: `document.querySelector('.clubs').scrollIntoView({block:'center',behavior:'instant'})` });
  await sleep(500);
  const fs = require('fs');
  let s = await send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(process.argv[2], Buffer.from(s.data, 'base64'));
  const b = JSON.parse((await send('Runtime.evaluate', { returnByValue: true, expression:
    `(()=>{const r=document.querySelectorAll('.club')[1].querySelector('svg').getBoundingClientRect();
      return JSON.stringify({x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)})})()` })).result.value);
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: b.x, y: b.y });
  await sleep(700);
  s = await send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(process.argv[3], Buffer.from(s.data, 'base64'));
  ws.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
