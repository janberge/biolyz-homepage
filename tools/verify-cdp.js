const PORT = 9343;
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const t = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  let id = 0; const pend = new Map(); const errs = [];
  ws.addEventListener('message', e => {
    const m = JSON.parse(e.data);
    if (m.id && pend.has(m.id)) { pend.get(m.id)(m.result); pend.delete(m.id); }
    if (m.method === 'Runtime.exceptionThrown') errs.push(m.params.exceptionDetails.text + ' ' + (m.params.exceptionDetails.exception||{}).description);
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') errs.push(JSON.stringify(m.params.args.map(a=>a.value)));
  });
  const send = (method, params = {}) => new Promise(res => { const i = ++id; pend.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  await new Promise(r => ws.addEventListener('open', r));
  await send('Runtime.enable'); await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: 'http://localhost:3000/#/' });
  await sleep(3000);
  const r = await send('Runtime.evaluate', { awaitPromise: true, returnByValue: true, expression: `(async () => {
    const routes = ['/','/product','/solution/football','/solution/cycling','/science','/biomarkers','/about','/about/founder','/use-cases','/literature','/changelog','/demo','/waitlist','/careers','/contact','/press','/privacy','/data-security','/impressum','/erdf','/cookies','/zzz'];
    const bad = [];
    for (const rt of routes) {
      location.hash = '#' + rt;
      await new Promise(x => setTimeout(x, 90));
      const vis = [...document.querySelectorAll('.page')].filter(p => !p.hidden);
      if (vis.length !== 1) bad.push(rt + ' pages=' + vis.length);
      if (document.documentElement.scrollWidth > document.documentElement.clientWidth + 1) bad.push(rt + ' overflow');
    }
    location.hash = '#/';
    await new Promise(x => setTimeout(x, 300));
    const imgs = [...document.querySelectorAll('img')];
    return JSON.stringify({ routes: routes.length, bad,
      imgs: imgs.length, broken: imgs.filter(i => i.complete && i.naturalWidth === 0).length,
      canvas: document.getElementById('viz').width });
  })()` });
  await sleep(200);
  console.log(r.result.value);
  console.log('jsErrors:', errs.length ? errs : 'none');
  ws.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
