  /* =====================================================================
     HERO: THE MARKER NETWORK
     The panel is not a list, it is a set of markers that group into
     indicators — so the hero draws that, with the real analyte names on the
     nodes and the real indicator names on the groups. Six clusters, springs
     that hold each node near its own place so the composition never
     degenerates, and one attractor that follows the cursor.

     Neon is the cursor's own colour here: it appears only within the radius
     of attention and fades out behind it, which keeps the accent rationed to
     one earned moment per page rather than painted across the hero.

     Where a pointer never arrives — a phone, a laptop with the cursor
     parked — the attractor walks a slow Lissajous path instead, so the
     interplay is visible without one. The handover is a lerp, so it glides
     rather than jumps.
     ===================================================================== */
  var GROUPS = [
    { g: 'Psychological stress', m: ['Cortisol', 'Cortisol morning', 'Cortisone', 'DHEAS', 'Cortisol/Cortisone'] },
    { g: 'Metabolic stress',     m: ['Hypoxanthine', 'Xanthine/Hypoxanthine', 'Alanine', 'Glutamine', 'Leucine', 'Proline', 'cAMP'] },
    { g: 'Hydration',            m: ['Creatinine', 'Protein concentration', 'Creatine', 'Creatinine/Creatine', 'Citrulline'] },
    { g: 'Hormonal status',      m: ['Estradiol', 'Progesterone', 'Androstenedione', 'Estrone', 'Testosterone'] },
    { g: 'Inflammation',         m: ['Arachidonic acid', 'Eicosapentaenoic acid', 'AA/EPA ratio', 'Histamine', 'Nitrotyrosine', '8-OHdG', 'Prostaglandin F2-alpha'] },
    { g: 'Sleep',                m: ['Melatonin', 'Kynurenine', 'Kynurenic acid', 'Nicotinuric acid'] }
  ];

  var vz = document.getElementById('viz');
  var vctx = vz && vz.getContext ? vz.getContext('2d') : null;
  var hero = document.querySelector('#p-home .hero');
  var vzW = 0, vzH = 0, nodes = null, link = 120, running = false, raf = 0;
  var ptrX = null, ptrY = null, ptrAt = -1e9;      // last real pointer position
  var atX = 0, atY = 0, atInit = false;            // the attractor, lerped
  var t0 = 0, intro = 0;

  /* Deterministic layout: the same web every load, which matters because a
     hero that reshuffles on refresh reads as noise rather than as data. */
  function lcg(seed) {
    var s = seed;
    return function () { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
  }

  function layout() {
    if (!vctx) return false;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    vzW = vz.clientWidth; vzH = vz.clientHeight;
    if (!vzW || !vzH) return false;
    vz.width = Math.round(vzW * dpr); vz.height = Math.round(vzH * dpr);
    vctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    link = Math.max(84, Math.min(155, Math.min(vzW, vzH) * 0.36));

    var rnd = lcg(20260907);
    /* Cluster centroids on a jittered ring, so the groups read as separate
       without falling into a diagram's tidy grid. */
    var cx = vzW * 0.52, cy = vzH * 0.5;
    var rx = vzW * 0.34, ry = vzH * 0.33;
    var keep = nodes;                       // reuse velocities across a resize
    nodes = [];
    GROUPS.forEach(function (grp, gi) {
      var a = (gi / GROUPS.length) * Math.PI * 2 + 0.6 + (rnd() - 0.5) * 0.45;
      var pull = 0.62 + rnd() * 0.38;
      var gx = cx + Math.cos(a) * rx * pull;
      var gy = cy + Math.sin(a) * ry * pull;
      grp.m.forEach(function (name, mi) {
        var b = rnd() * Math.PI * 2, r = Math.pow(rnd(), 0.62) * Math.min(vzW, vzH) * 0.15;
        var hx = Math.max(10, Math.min(vzW - 10, gx + Math.cos(b) * r));
        var hy = Math.max(10, Math.min(vzH - 10, gy + Math.sin(b) * r * 0.9));
        var old = keep && keep[nodes.length];
        nodes.push({
          hx: hx, hy: hy,
          x: old ? old.x : hx, y: old ? old.y : hy,
          vx: old ? old.vx : (rnd() - 0.5) * 0.12,
          vy: old ? old.vy : (rnd() - 0.5) * 0.12,
          g: gi, name: name, phase: rnd() * Math.PI * 2,
          i: mi
        });
      });
    });
    return true;
  }

  /* A soft mask at the left and bottom edges. Without it the network reads as
     a rectangle pasted onto the hero; with it, it dissolves into the ground. */
  function mask(x, y) {
    var u = x / vzW, v = y / vzH;
    var mx = u < 0.30 ? Math.max(0, u / 0.30) : 1;
    var my = v > 0.80 ? Math.max(0, (1 - v) / 0.20) : 1;
    return Math.pow(mx, 1.4) * Math.pow(my, 1.2);
  }

  function step(dt, now) {
    /* The attractor: the cursor when there is one, otherwise a slow walk. */
    var live = now - ptrAt < 2400 && ptrX !== null;
    var tx, ty;
    if (live) { tx = ptrX; ty = ptrY; }
    else {
      var k = now / 1000;
      tx = vzW * (0.52 + 0.30 * Math.sin(k * 0.21));
      ty = vzH * (0.48 + 0.26 * Math.sin(k * 0.147 + 1.1));
    }
    if (!atInit) { atX = tx; atY = ty; atInit = true; }
    atX += (tx - atX) * Math.min(1, dt * 0.005);
    atY += (ty - atY) * Math.min(1, dt * 0.005);

    var R = Math.min(vzW, vzH) * 0.42;
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      /* Spring home, gentle lean toward attention, light damping. Three
         forces, no collision handling — the clusters do that themselves. */
      n.vx += (n.hx - n.x) * 0.0011 * dt * 0.06;
      n.vy += (n.hy - n.y) * 0.0011 * dt * 0.06;
      var dx = atX - n.x, dy = atY - n.y;
      var d = Math.sqrt(dx * dx + dy * dy) || 1;
      if (d < R) {
        var f = (1 - d / R) * 0.055;
        n.vx += (dx / d) * f * dt * 0.06;
        n.vy += (dy / d) * f * dt * 0.06;
        n.infl = 1 - d / R;
      } else n.infl = 0;
      n.vx *= 0.972; n.vy *= 0.972;
      /* A breath of independent drift so a resting network is never frozen. */
      n.x += n.vx * dt * 0.06 + Math.sin(now / 2600 + n.phase) * 0.045;
      n.y += n.vy * dt * 0.06 + Math.cos(now / 3100 + n.phase) * 0.045;
      if (n.x < 6) { n.x = 6; n.vx = Math.abs(n.vx); }
      if (n.x > vzW - 6) { n.x = vzW - 6; n.vx = -Math.abs(n.vx); }
      if (n.y < 6) { n.y = 6; n.vy = Math.abs(n.vy); }
      if (n.y > vzH - 6) { n.y = vzH - 6; n.vy = -Math.abs(n.vy); }
    }
  }

  function render(now) {
    vctx.clearRect(0, 0, vzW, vzH);
    var i, j, n, m, a;

    /* Edges first, so nodes always sit on top of their own connections. */
    vctx.lineWidth = 1;
    for (i = 0; i < nodes.length; i++) {
      n = nodes[i];
      for (j = i + 1; j < nodes.length; j++) {
        m = nodes[j];
        var dx = m.x - n.x, dy = m.y - n.y;
        var d2 = dx * dx + dy * dy;
        if (d2 > link * link) continue;
        var d = Math.sqrt(d2);
        var same = n.g === m.g;
        /* Within an indicator the markers are wired more tightly than across
           one. That is the only thing the edge weight encodes. */
        var base = (same ? 0.20 : 0.075) * (1 - d / link);
        var hot = Math.max(n.infl, m.infl);
        var mk = Math.min(mask(n.x, n.y), mask(m.x, m.y));
        a = base * mk * intro;
        if (a < 0.004) continue;
        vctx.beginPath();
        vctx.moveTo(n.x, n.y); vctx.lineTo(m.x, m.y);
        vctx.strokeStyle = hot > 0.02
          ? 'rgba(' + Math.round(253 - 55 * hot) + ',' + Math.round(253 + 2 * hot) + ',' +
            Math.round(253 - 253 * hot) + ',' + (a * (1 + hot * 2.6)).toFixed(3) + ')'
          : 'rgba(253,253,253,' + a.toFixed(3) + ')';
        vctx.stroke();
      }
    }

    /* Nodes. */
    var near = null, nearD = 1e9;
    for (i = 0; i < nodes.length; i++) {
      n = nodes[i];
      var mk = mask(n.x, n.y);
      if (mk < 0.02) continue;
      var r = (1.7 + n.infl * 1.9) * (0.6 + 0.4 * intro);
      a = (0.30 + n.infl * 0.62) * mk * intro;
      vctx.beginPath();
      vctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      vctx.fillStyle = n.infl > 0.02
        ? 'rgba(' + Math.round(253 - 55 * n.infl) + ',' + Math.round(253 + 2 * n.infl) + ',' +
          Math.round(253 - 253 * n.infl) + ',' + Math.min(1, a * 1.5).toFixed(3) + ')'
        : 'rgba(253,253,253,' + a.toFixed(3) + ')';
      vctx.fill();
      if (mk > 0.6) {
        var dd = Math.hypot(atX - n.x, atY - n.y);
        if (dd < nearD) { nearD = dd; near = n; }
      }
    }

    /* One label at a time: the marker nearest the cursor, and the indicator
       it belongs to. Any more than one and the hero becomes a chart. */
    if (near && nearD < link * 0.9 && intro > 0.85) {
      var fade = Math.min(1, (1 - nearD / (link * 0.9)) * 2.2);
      var flip = near.x > vzW * 0.72;
      var lx = near.x + (flip ? -10 : 10);
      vctx.textAlign = flip ? 'right' : 'left';
      vctx.textBaseline = 'alphabetic';
      vctx.font = '11px "JetBrains Mono", ui-monospace, monospace';
      vctx.fillStyle = 'rgba(198,255,0,' + (0.92 * fade).toFixed(3) + ')';
      vctx.fillText(near.name, lx, near.y - 5);
      vctx.fillStyle = 'rgba(253,253,253,' + (0.42 * fade).toFixed(3) + ')';
      vctx.fillText(GROUPS[near.g].g, lx, near.y + 9);
    }
  }

  var last = 0;
  function loop(now) {
    if (!running) return;
    var dt = last ? Math.min(48, now - last) : 16;
    last = now;
    if (!t0) t0 = now;
    intro = Math.min(1, (now - t0) / 900);
    step(dt, now);
    render(now);
    raf = requestAnimationFrame(loop);
  }

  function startViz() {
    if (!vctx) return;
    if (!layout()) return;
    if (reduce) {
      /* Static, but still the real composition rather than an empty box. */
      intro = 1; atX = vzW * 0.55; atY = vzH * 0.45; atInit = true;
      for (var i = 0; i < nodes.length; i++) nodes[i].infl = 0;
      render(0);
      return;
    }
    if (running) return;
    running = true; last = 0; t0 = 0;
    raf = requestAnimationFrame(loop);
  }
  function stopViz() {
    running = false;
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
  }

  if (vz && !reduce) {
    /* Read the pointer from the hero, not the canvas: the canvas is
       pointer-events:none so the buttons under it stay clickable. */
    hero.addEventListener('pointermove', function (e) {
      var r = vz.getBoundingClientRect();
      ptrX = e.clientX - r.left; ptrY = e.clientY - r.top;
      ptrAt = performance.now();
      hero.classList.add('is-touched');
    }, { passive: true });
    hero.addEventListener('pointerleave', function () { ptrAt = -1e9; });
    /* Off-screen or on another route, stop burning frames. */
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) stopViz();
      else if (!document.getElementById('p-home').hidden) startViz();
    });
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (es) {
        if (es[0].isIntersecting) startViz(); else stopViz();
      }, { threshold: 0 }).observe(vz);
    }
  }

  var vzT;
  window.addEventListener('resize', function () {
    clearTimeout(vzT);
    vzT = setTimeout(function () {
      if (!layout()) return;
      atInit = false;
      if (reduce) { intro = 1; render(0); }
    }, 150);
  });

