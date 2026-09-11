const PORT = 9338, sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const t = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl); let id = 0; const p = new Map();
  ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && p.has(m.id)) { p.get(m.id)(m.result); p.delete(m.id); } });
  const send = (me, pa = {}) => new Promise(r => { const i = ++id; p.set(i, r); ws.send(JSON.stringify({ id: i, method: me, params: pa })); });
  await new Promise(r => ws.addEventListener('open', r));
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: 'http://localhost:3000/#/solution/football' });
  await sleep(2500);

  const state = async () => (await send('Runtime.evaluate', { returnByValue: true, expression: `
    JSON.stringify({
      panel: [...document.querySelectorAll('#p-solution [data-panel]')].filter(x=>!x.hidden).map(x=>x.dataset.panel)[0],
      sel:   [...document.querySelectorAll('#p-solution .step4')].map(b=>b.getAttribute('aria-selected')).join(','),
      bars:  [...document.querySelectorAll('#p-solution .step4-bar i')].map(b=>Math.round(parseFloat(b.style.width||0))).join(','),
      live:  [...document.querySelectorAll('#p-solution .step4-bar i')].map(b=>b.classList.contains('is-live')?1:0).join(','),
      img:   (document.querySelector('#p-solution [data-panel]:not([hidden]) figcaption span')||{}).textContent
    })`})).result.value;

  console.log('initial      ', await state());
  await sleep(2200);
  console.log('after 2.2s   ', await state());

  // scroll the flow into view first — a CDP mouse event outside the viewport hits nothing
  await send('Runtime.evaluate', { expression:
    `document.querySelector('#p-solution .steps4').scrollIntoView({block:'center',behavior:'instant'})` });
  await sleep(500);

  // a real click, on the DESCRIPTION text of step 3 — the part that used to be dead
  const box = (await send('Runtime.evaluate', { returnByValue: true, expression:
    `(()=>{const r=document.querySelectorAll('#p-solution .step4')[2].querySelector('.d').getBoundingClientRect();
      return JSON.stringify({x:Math.round(r.left+r.width/2), y:Math.round(r.top+r.height/2)})})()` })).result.value;
  const { x, y } = JSON.parse(box);
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
  await sleep(400);
  console.log('click desc 03', await state());

  // move the cursor away, then let it run past the segment boundary
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 20, y: 20 });
  await sleep(7400);
  console.log('after advance', await state());
  ws.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
