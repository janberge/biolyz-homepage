const PORT = 9343, sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const t = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl); let id = 0; const p = new Map();
  ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && p.has(m.id)) { p.get(m.id)(m.result); p.delete(m.id); } });
  const send = (me, pa = {}) => new Promise(r => { const i = ++id; p.set(i, r); ws.send(JSON.stringify({ id: i, method: me, params: pa })); });
  await new Promise(r => ws.addEventListener('open', r));
  const W = +(process.argv[3] || 1440), H = +(process.argv[4] || 1000);
  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 2, mobile: false });
  await send('Page.navigate', { url: 'http://localhost:3000/#/' });
  await sleep(3200);
  const sel = process.argv[5];
  if (sel) { await send('Runtime.evaluate', { expression: `document.querySelector('${sel}').scrollIntoView({block:'center',behavior:'instant'})` }); await sleep(500); }
  const r = await send('Runtime.evaluate', { returnByValue: true, expression: `JSON.stringify({
    sw:document.documentElement.scrollWidth, vw:document.documentElement.clientWidth,
    heroH:Math.round(document.querySelector('.hero').getBoundingClientRect().height),
    marks:[...document.querySelectorAll('.marks .logo-svg')].map(s=>{const b=s.getBoundingClientRect();
      return Math.round(b.width)+'x'+Math.round(b.height)}).join(' '),
    proofTop:[...document.querySelectorAll('.proof-group .marks')].map(m=>Math.round(m.getBoundingClientRect().top)).join(','),
    ctaR:getComputedStyle(document.querySelector('.cta-box')).borderRadius,
    ctaBg:getComputedStyle(document.querySelector('.cta-box')).backgroundColor
  })`});
  console.log(r.result.value);
  const shot = await send('Page.captureScreenshot', { format: 'png' });
  require('fs').writeFileSync(process.argv[2], Buffer.from(shot.data, 'base64'));
  ws.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
