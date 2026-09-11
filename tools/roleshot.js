const PORT = 9343, sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const t = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl); let id = 0; const p = new Map();
  ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && p.has(m.id)) { p.get(m.id)(m.result); p.delete(m.id); } });
  const send = (me, pa = {}) => new Promise(r => { const i = ++id; p.set(i, r); ws.send(JSON.stringify({ id: i, method: me, params: pa })); });
  await new Promise(r => ws.addEventListener('open', r));
  const [out, route, idx] = process.argv.slice(2);
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1150, deviceScaleFactor: 2, mobile: false });
  await send('Page.navigate', { url: 'http://localhost:3000/#' + route });
  await sleep(3200);
  await send('Runtime.evaluate', { expression: `
    const ds=[...document.querySelectorAll(".page:not([hidden]) details")];
    ds.forEach(d=>d.open=false); ds[${idx}].open=true;
    ds[${idx}].scrollIntoView({block:"start",behavior:"instant"}); scrollBy(0,-110);` });
  await sleep(1200);
  const shot = await send('Page.captureScreenshot', { format: 'png' });
  require('fs').writeFileSync(out, Buffer.from(shot.data, 'base64'));
  ws.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
