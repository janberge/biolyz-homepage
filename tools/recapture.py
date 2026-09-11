#!/usr/bin/env python3
"""Re-capture every dashboard screenshot the homepage uses.

    python3 tools/recapture.py [path-to-biolyz-atira] [--only name,name]

WHY THIS EXISTS. The screenshots in web/ are of a different application, and
they go stale every time that application changes. Before this script the
capture was a set of hand-edits to a scratch copy of the dashboard, made once,
in a session that no longer exists — so the images could not be regenerated at
all. Now they can.

THE DASHBOARD IS NOT MODIFIED. It keeps route / playerId / playerTab in React
state rather than in the URL, which is correct for the product and useless for
a capture tool, so this script copies it and patches the COPY:

  · a harness injected after the data files and before js/imagery.js, which
    parses the query string into `window.__SHOT` and sets `window.__READY`
    once React has painted;
  · the six `aState(...)` initialisers in App(), which then seed from it.

Nothing is written back. Do not "simplify" this by committing the patch to the
dashboard: a capture hack in the product is how the product grows a feature
nobody asked for.

?shots=1 NULLS EVERY PLAYER PHOTO. The avatars in this dashboard are press
photographs of identifiable professional footballers. Real faces must not ship
on a public marketing page beside biomarker data, so the harness empties
`p.photo` before imagery.js reads it and every avatar falls back to a
generated silhouette. The script asserts, per capture, that no photo rendered,
and refuses to write an image if one did.
"""
import os, re, shutil, signal, subprocess, sys, time, json, http.client

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
WEB  = os.path.join(REPO, "web")
SRC  = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") \
       else os.path.expanduser("~/Downloads/biolyz-atira")
WORK = "/tmp/biolyz-shots"
# Its own port: the dashboard's own dev server usually holds 8920/8921.
PORT, CDP = 8971, 9351
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

only = None
for a in sys.argv[1:]:
    if a.startswith("--only"):
        only = set((a.split("=", 1)[1] if "=" in a else sys.argv[sys.argv.index(a) + 1]).split(","))

# name -> (query string, width, height, scroll-to selector or None)
# Sizes match what site.html declares for each image; a capture at the wrong
# aspect gets letterboxed by the page and looks soft.
SHOTS = {
  # `full` also fills the two slots that used to hold `brief` — the dashboard's
  # Brief view was removed on 2026-09-11 and there is nothing left to shoot.
  "full":       ("view=overview",                        1920, 1080, None),
  "markers":    ("view=markers",                         1920, 1080, None),
  "indicators": ("view=status&matrix=1",                 1920, 1080, None),
  "hydration":  ("view=status&ind=hydration",            1920, 1080, None),
  "knowledge":  ("view=knowledge",                       1920, 1080, None),
  "digest":     ("view=digest",                          1920, 1080, None),
  "samples":    ("view=samples",                         1920, 1080, None),
  "player":     ("player=p04&tab=p_overview",            1920, 1080, None),
  "playerind":  ("player=p04&tab=p_indicators",          1920, 1080, None),
  "playermk":   ("player=p04&tab=p_markers",             1920, 1080, None),
  "athlete":    ("athlete=p04",                          1920, 1382, None),
}

HARNESS = """
<!-- ===================================================================
     CAPTURE HARNESS — injected by tools/recapture.py in the homepage
     repository. Not part of the dashboard; never commit this.
     =================================================================== -->
<script>
(function () {
  var q = new URLSearchParams(location.search);
  window.__SHOT = {
    view:   q.get('view'),
    player: q.get('player'),
    tab:    q.get('tab'),
    marker: q.get('marker'),
    athlete:q.get('athlete'),
    ind:    q.get('ind'),
    matrix: q.get('matrix') === '1',
    on:     q.has('view') || q.has('player') || q.has('athlete')
  };
  window.__ERRS = [];
  window.addEventListener('error', function (e) { window.__ERRS.push(e.message); });

  /* REAL FACES DO NOT LEAVE THIS APP. The portraits are press photographs of
     identifiable footballers; on a marketing page beside biomarker data they
     would identify someone the scrambled names are there to protect. Emptied
     before js/imagery.js reads them, so Art.photo falls back to the drawn
     silhouette. */
  if (q.get('shots') === '1') {
    (window.SQUAD_REAL || []).forEach(function (p) { p.photo = null; });
    (window.ROSTER || []).forEach(function (p) { p.photo = null; });
    window.PHOTO_DATA = {};
  }

  /* React has painted when the first h1 is in the DOM. Two frames after that
     the entrance transitions have started, which is close enough to settled
     that dashshot.js only needs a short fixed wait on top. */
  var t = setInterval(function () {
    /* `main h1` covers every routed view. The athlete view is not routed —
       it replaces the whole shell and has no <main> — so its own heading
       has to count too, or that one capture waits forever. */
    if (document.querySelector('main h1, .ath__name')) {
      clearInterval(t);
      requestAnimationFrame(function () {
        requestAnimationFrame(function () { window.__READY = true; });
      });
    }
  }, 100);
})();
</script>
"""

# (regex, replacement) against js/app.jsx — each seeds one piece of state.
PATCHES = [
 (r"const \[route, setRoute\] = aState\('overview'\);",
  "const [route, setRoute] = aState((window.__SHOT && window.__SHOT.view) || 'overview');"),
 (r"const \[playerId, setPlayerId\] = aState\(null\);",
  "const [playerId, setPlayerId] = aState((window.__SHOT && window.__SHOT.player) || null);"),
 (r"const \[playerTab, setPlayerTab\] = aState\('p_overview'\);",
  "const [playerTab, setPlayerTab] = aState((window.__SHOT && window.__SHOT.tab) || 'p_overview');"),
 (r"const \[marker, setMarker\] = aState\(null\);",
  "const [marker, setMarker] = aState((window.__SHOT && window.__SHOT.marker) || null);"),
 (r"const \[athlete, setAthlete\] = aState\(null\);",
  "const [athlete, setAthlete] = aState((window.__SHOT && window.__SHOT.athlete) || null);"),
 (r"const \[indPage, setIndPage\] = aState\(null\);",
  "const [indPage, setIndPage] = aState((window.__SHOT && window.__SHOT.ind) || null);"),
 # The squad matrix is StatusView's own state, not App's. It defaults to false
 # because the product wants one indicator at a time; the site shows the matrix.
 (r"const \[matrix, setMatrix\] = useState\(false\);",
  "const [matrix, setMatrix] = useState(!!(window.__SHOT && window.__SHOT.matrix));"),
]


def build_work_copy():
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    shutil.copytree(SRC, WORK, ignore=shutil.ignore_patterns(".git", "build"))

    hit = {}
    idx = os.path.join(WORK, "index.html")
    s = open(idx, encoding="utf-8").read()
    # After the data files, before js/theme.js and js/imagery.js: the harness
    # needs SQUAD_REAL to exist and imagery.js not to have read it yet.
    anchor = '<script src="js/theme.js"></script>'
    assert anchor in s, "index.html script order changed — re-check the injection point"
    s = s.replace(anchor, HARNESS + anchor, 1)
    open(idx, "w", encoding="utf-8").write(s)

    for rel in ("js/app.jsx", "js/team.jsx"):
        f = os.path.join(WORK, *rel.split("/"))
        a = open(f, encoding="utf-8").read()
        for pat, rep in PATCHES:
            a, n = re.subn(pat, rep, a, count=1)
            hit[pat] = hit.get(pat, 0) + n
            if n:
                open(f, "w", encoding="utf-8").write(a)
    missing = [p for p, _ in PATCHES if not hit.get(p)]
    assert not missing, "state initialiser not found: " + "; ".join(missing)
    print("work copy patched at", WORK)


def wait_for(port, path="/", tries=60):
    for _ in range(tries):
        try:
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
            c.request("GET", path); c.getresponse().read(1); c.close()
            return True
        except Exception:
            time.sleep(0.25)
    return False


def main():
    if not os.path.isdir(SRC):
        sys.exit("dashboard not found at " + SRC)
    build_work_copy()

    srv = subprocess.Popen([sys.executable, "serve.py", str(PORT)], cwd=WORK,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    chrome = subprocess.Popen(
        [CHROME, "--headless=new", f"--remote-debugging-port={CDP}",
         "--force-device-scale-factor=2", "--hide-scrollbars",
         "--disable-gpu", "--no-first-run", "--user-data-dir=/tmp/biolyz-shots-chrome",
         "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_for(PORT):
            sys.exit("dashboard server did not come up")
        if not wait_for(CDP, "/json/version"):
            sys.exit("headless Chrome did not come up")

        os.makedirs("/tmp/biolyz-shots-png", exist_ok=True)
        wrote, failed = [], []
        for name, (query, w, h, sel) in SHOTS.items():
            if only and name not in only:
                continue
            png = f"/tmp/biolyz-shots-png/{name}.png"
            url = f"http://localhost:{PORT}/?shots=1&{query}"
            r = subprocess.run(["node", os.path.join(HERE, "dashshot.js"),
                                str(CDP), url, png, str(w), str(h), sel or "-"],
                               capture_output=True, text=True)
            sys.stdout.write(r.stdout)
            if r.returncode != 0 or not os.path.exists(png):
                print("  FAILED", name, r.stderr.strip()[:200]); failed.append(name); continue
            # THE FACE CHECK. dashshot.js reports how many .avatar__photo
            # elements rendered; anything but zero means the nulling did not
            # take and the image must not be written.
            m = re.search(r'"photos":\s*(\d+)', r.stdout)
            if m and int(m.group(1)) != 0:
                print("  REFUSED", name, "— real photos rendered"); failed.append(name); continue
            jpg = os.path.join(WEB, name + ".jpg")
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "78",
                            "-z", str(h), str(w), png, "--out", jpg],
                           capture_output=True)
            wrote.append((name, os.path.getsize(jpg) // 1024))

        print("\nwrote", len(wrote), "screenshots")
        for n, kb in wrote:
            print(f"  web/{n}.jpg".ljust(24), f"{kb}KB")
        if failed:
            print("FAILED:", ", ".join(failed))
            sys.exit(1)
    finally:
        for p in (chrome, srv):
            try: p.send_signal(signal.SIGTERM); p.wait(timeout=5)
            except Exception:
                try: p.kill()
                except Exception: pass


if __name__ == "__main__":
    main()
