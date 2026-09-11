const PORT = 9336, sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const t = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl); let id = 0; const p = new Map();
  ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && p.has(m.id)) { p.get(m.id)(m.result); p.delete(m.id); } });
  const send = (me, pa = {}) => new Promise(r => { const i = ++id; p.set(i, r); ws.send(JSON.stringify({ id: i, method: me, params: pa })); });
  await new Promise(r => ws.addEventListener('open', r));
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 2, mobile: false });
  await send('Page.navigate', { url: 'http://localhost:3000/#/' });
  await sleep(2800);
  await send('Runtime.evaluate', { expression: `document.querySelector('.clubs').scrollIntoView({block:'center',behavior:'instant'})` });
  await sleep(400);

  const info = (await send('Runtime.evaluate', { returnByValue: true, expression: `
    JSON.stringify([...document.querySelectorAll('.club')].map(a=>{
      const svg=a.querySelector('svg'), r=svg.getBoundingClientRect();
      return { href:a.href, name:a.querySelector('.cn').textContent.trim(),
               w:Math.round(r.width), h:Math.round(r.height),
               filter:getComputedStyle(svg).filter,
               viewBox:svg.getAttribute('viewBox') };
    }).concat([{ dupIds: (()=>{const seen={},dup=[];document.querySelectorAll('[id]').forEach(e=>{if(seen[e.id])dup.push(e.id);seen[e.id]=1});return dup.join(',')||'none'})(),
                 styleTags: document.querySelectorAll('svg style').length,
                 sw: document.documentElement.scrollWidth, vw: document.documentElement.clientWidth }]))`})).result.value;
  console.log(info);

  // rest state
  let shot = await send('Page.captureScreenshot', { format: 'png' });
  require('fs').writeFileSync(process.argv[2], Buffer.from(shot.data, 'base64'));
  // hover the first mark
  const box = JSON.parse((await send('Runtime.evaluate', { returnByValue: true, expression:
    `(()=>{const r=document.querySelector('.club svg').getBoundingClientRect();
      return JSON.stringify({x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)})})()` })).result.value);
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: box.x, y: box.y });

  ws.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
