"""Assemble site.html into the shippable single file.

    python3 build.py            # everything resolves relative to this repo
    python3 build.py <dir>      # or point it somewhere else

`site.html` is the source of truth. It carries __IMG_*__ and __SVG_*__ tokens
which this script substitutes with base64 screenshots from web/ and cleaned
inline SVG from brand/. Output: biolyz-site.html (artifact-shaped, no doctype)
and serve/index.html (wrapped, openable from disk).

Every input used to be an absolute path into ~/Downloads and a sibling
checkout of the dashboard. They are vendored under brand/ now, so a clone
builds without anything else on the machine.
"""
import base64,hashlib,hmac,json,os,re,struct,sys,subprocess
sp=os.path.abspath(sys.argv[1] if len(sys.argv)>1 else os.path.dirname(__file__) or ".")
BRAND=os.path.join(sp,"brand")
src=open(os.path.join(sp,"site.html"),encoding="utf-8").read()
# Screenshots are shared across pages — the biomarker overview alone appears
# four times. Inlining the data URI at each use embedded the same megabyte
# repeatedly, so each one ships ONCE in a map and the images take their src
# from it at load. src="__IMG_x__" in the source becomes data-img="x" here.
used = sorted(set(re.findall(r'__IMG_([a-z0-9]+)__', src)))
src = re.sub(r'src="__IMG_([a-z0-9]+)__"', r'data-img="\1"', src)
# A video's poster resolves from the same map: one still, shown instantly,
# so the hero is never a black rectangle while 4 MB of video arrives.
src = re.sub(r'poster="__IMG_([a-z0-9]+)__"', r'data-poster="\1"', src)
assert "__IMG_" not in src, "an __IMG_ token was used outside src= or poster="
# Same trick for video (the hero background), one map even though there is
# only one entry today — src="__VIDEO_x__" becomes data-video="x".
usedv = sorted(set(re.findall(r'__VIDEO_([a-z0-9]+)__', src)))
src = re.sub(r'src="__VIDEO_([a-z0-9]+)__"', r'data-video="\1"', src)
assert "__VIDEO_" not in src, "a __VIDEO_ token was used outside a src attribute"

# ---- two loaders, one markup --------------------------------------------
# The deployable build writes assets as real files and references them by
# URL. Inlining them as data: URIs cost +37% on every byte AND forced the
# browser to download 21 MB before it could paint anything — the whole page
# was one blocking request. Separate files are cacheable, range-requestable,
# and let the hero video arrive after the text rather than before it.
#
# The artifact-shaped copy still inlines, because it has nowhere to put a
# sibling file.
LOADER_JS = """
/* Screenshots resolve immediately; width/height are already on the markup so
   nothing shifts. Videos do NOT: each one waits until its page is actually
   on screen, so visiting the home page never downloads the product and
   science heroes. A video inside a hidden page has no box and so never
   intersects, which is what makes the observer the right trigger here. */
(function(){
  /* Posters are small and resolve straight away, so a hero that has not
     started yet still shows its still frame the moment you reach it. */
  document.querySelectorAll('video[data-poster]').forEach(function(v){
    var d = window.__IMG[v.dataset.poster]; if (d) v.poster = d; });

  /* Everything heavy waits until it is actually on screen. An element inside
     a hidden page has no box and never intersects, so visiting the home page
     downloads neither the product hero video nor the twenty-odd dashboard
     screenshots that live on other routes. loading="lazy" alone does not do
     this: the src is set, and the browser decides. */
  function img(i){
    var d = window.__IMG[i.dataset.img];
    if (d && !i.src) i.src = d;
  }
  function vid(v){
    if (v.dataset.started) return;
    var d = window.__VIDEO[v.dataset.video];
    if (!d) return;
    v.dataset.started = '1';
    v.src = d;
    var play = v.play();
    if (play && play.catch) play.catch(function(){ /* autoplay refused */ });
  }
  var imgs = [].slice.call(document.querySelectorAll('img[data-img]'));
  var vids = [].slice.call(document.querySelectorAll('video[data-video]'));
  if (!('IntersectionObserver' in window)) { imgs.forEach(img); vids.forEach(vid); return; }
  var io = new IntersectionObserver(function(es){
    es.forEach(function(e){
      if (!e.isIntersecting) return;
      var t = e.target;
      if (t.tagName === 'IMG') img(t); else vid(t);
      io.unobserve(t);
    });
  }, { rootMargin: '300px' });
  imgs.concat(vids).forEach(function(el){ io.observe(el); });
})();
"""


def loader(imgs, vids):
    return ("<script>window.__IMG=" + json.dumps(imgs) +
            ";window.__VIDEO=" + json.dumps(vids) + ";" + LOADER_JS + "</script>")


def data_uri(path, mime):
    return "data:%s;base64,%s" % (
        mime, base64.b64encode(open(path, "rb").read()).decode())


IMG_SRC = {n: os.path.join(sp, "web", n + ".jpg") for n in used}
VID_SRC = {n: os.path.join(sp, "web", n + ".mp4") for n in usedv}

# The artifact copy carries no video. Inlined, the three heroes are ~14 MB of
# base64 on their own and put the file over the 16 MB artifact ceiling, so the
# preview could not be published at all. Without them it fits, and each hero
# shows its poster still instead — a preview that exists beats a video that
# nobody can open. BIOLYZ_ARTIFACT_VIDEO=1 puts them back.
ARTIFACT_VIDEO = os.environ.get("BIOLYZ_ARTIFACT_VIDEO") == "1"
inline_loader = loader(
    {n: data_uri(p_, "image/jpeg") for n, p_ in IMG_SRC.items()},
    {n: data_uri(p_, "video/mp4") for n, p_ in VID_SRC.items()} if ARTIFACT_VIDEO else {})
# Root-based, not relative: from a nested route such as /compare/point-of-care
# a bare "assets/x.jpg" resolves to /compare/assets/x.jpg and 404s.
_ASSET_ROOT = os.environ.get("BIOLYZ_BASE", "").rstrip("/") + "/assets/"
file_loader = loader(
    {n: _ASSET_ROOT + n + ".jpg" for n in used},
    {n: _ASSET_ROOT + n + ".mp4" for n in usedv})
def svg(path,cls):
    s=open(path,encoding="utf-8").read()
    s=re.sub(r'<defs>.*?</defs>','',s,flags=re.S).replace(' class="cls-1"','')
    return re.sub(r'\s+',' ',s.replace('<svg ','<svg fill="currentColor" class="%s" aria-hidden="true" '%cls,1)).strip()
# Club marks: Illustrator exports whose <style> classes are folded inline, so
# two of them can share one document without fighting over .st0/.st1/.st2.
sys.path.insert(0, sp)
from svgclean import clean as _clean
TP = os.path.join(BRAND, "third-party")
src = src.replace("__SVG_bvb__", _clean(os.path.join(TP, "borussia-dortmund.svg"), "bvb"))
src = src.replace("__SVG_b04__", _clean(os.path.join(TP, "bayer-leverkusen.svg"), "b04"))
# Press marks. Tight viewBoxes measured with getBBox in a real browser, so
# three wordmarks of very different proportions can be sized against one
# another rather than against whatever whitespace their exporter left in.
# The Biolyz wordmark ships white-only; recoloured to currentColor so one file
# serves the transparent nav over the dark hero and the light bar everywhere else.
src = src.replace("__SVG_biolyz__", _clean(
    os.path.join(BRAND, "biolyz", "wordmark-white.svg"), "bz", recolor=True))
src = src.replace("__SVG_nyt__", _clean(
    os.path.join(TP, "new-york-times.svg"), "nyt", viewbox="0 0.4 184.1 24.2"))
src = src.replace("__SVG_kicker__", _clean(
    os.path.join(TP, "kicker.svg"), "kicker", viewbox="13.89 70.38 168.98 48",
    drop='<path fill="#fff" d="M0 0h192.756v192.756H0V0z"/>'))
# The only press mark that is not already black: it ships navy (#1f3265), and
# the featured-in row reads as one ink.
src = src.replace("__SVG_scienceforsport__", _clean(
    os.path.join(TP, "scienceforsport.svg"), "sfs",
    viewbox="53.49 26.47 1814.65 286.01", recolor=True))
src = src.replace("__SVG_sportico__", _clean(
    os.path.join(TP, "sportico.svg"), "sportico", viewbox="0 0 491.1 126.76"))
# Integration marks for the marquee. Own colours kept (no recolor) — these
# are read on a plain white card, not over a variable background.
src = src.replace("__SVG_whoop__", _clean(os.path.join(TP, "whoop.svg"), "whoop"))
src = src.replace("__SVG_garmin__", _clean(os.path.join(TP, "garmin.svg"), "garmin"))
src = src.replace("__SVG_trainingpeaks__", _clean(os.path.join(TP, "trainingpeaks.svg"), "trainingpeaks"))
src = src.replace("__SVG_catapult__", _clean(os.path.join(TP, "catapult.svg"), "catapult"))

logo=os.path.join(BRAND,"biolyz")
src=src.replace("__SVG_signet__",svg(logo+"/biolyz-signet.svg","mark"))
h=svg(logo+"/biolyz-horizontal.svg","mark")
src=src.replace("__SVG_horizontal__",h,1).replace("__SVG_horizontal2__",h,1)
# Only the build's own token shapes — the app has legitimate runtime globals
# of its own (__BASE__, __FORCE_HASH__) that this must not mistake for one.
_left = re.findall(r'__(?:IMG|SVG|VIDEO)_[A-Za-z0-9]+__', src)
assert not _left, "unsubstituted tokens: %s" % sorted(set(_left))
# ---- the gated US readiness section --------------------------------------
# The repository is PUBLIC, so the draft does not live in site.html: it sits in
# us/, which is gitignored, and site.html carries four markers where it goes.
# Encrypting the built file was never going to protect prose that the source
# published in the clear.
#
# No us/ directory -> the markers resolve to nothing and the build is the
# public site: no /us routes, no footer entry, no gate. That is the build
# anyone who clones this repo gets, and it is a complete, working site.
US_DIR = os.path.join(sp, "us")


def _us_read(name):
    p = os.path.join(US_DIR, name)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


US_ON = os.path.isdir(US_DIR) and os.path.exists(os.path.join(US_DIR, "section.html"))
src = src.replace("<!--US:SECTION-->", _us_read("section.html"))
src = src.replace("<!--US:GATE-->", _us_read("gate.html"))
src = src.replace("<!--US:ROUTES-->", _us_read("routes.js").strip())
src = src.replace("<!--US:FOOTER-->", _us_read("footer.html").strip())
assert "<!--US:" not in src, "a US marker was not resolved"


# /us and its six subpages are a working draft: unconfirmed claims, and API
# endpoints the source document itself warns must not be published as fact.
# Hiding them behind a CSS class would still ship every word in the markup,
# where View Source and any crawler that ignores the gate would find it, so
# the bodies are encrypted here and decrypted in the browser from a
# passphrase. See the long comment on the gate script in site.html for what
# this does and does not protect.
#
# Only hashlib and hmac, so the build needs no third party package:
#   key    = PBKDF2-HMAC-SHA256(passphrase, salt, ITER) -> 32 bytes
#   stream = HMAC(key, label || 0x01 || uint64be(block))
#   cipher = plaintext XOR stream
#   tag    = HMAC(key, label || 0x02 || cipher)          (encrypt then MAC)
US_PASS = os.environ.get("BIOLYZ_US_PASS") or _us_read("pass.txt").strip()
# 200k derived in ~35 ms on this machine, which is also ~30,000 guesses a
# second for anyone attacking the verifier offline. 600k costs the reader a
# tenth of a second and triples that cost. Neither makes a guessable phrase
# safe — only the phrase itself does.
US_ITER = 600000
# A fixed salt, not a random one: a fresh salt every build would change the
# whole ciphertext on every run for no benefit, and the passphrase is the
# only secret here either way.
US_SALT = bytes.fromhex("5b1f9c4a2e7d6038a14c8be5f2097d31")
_us_key = hashlib.pbkdf2_hmac("sha256", US_PASS.encode(), US_SALT, US_ITER, 32)


def _us_stream(label, n):
    out, i = bytearray(), 0
    while len(out) < n:
        out += hmac.new(_us_key, label + b"\x01" + struct.pack(">Q", i),
                        hashlib.sha256).digest()
        i += 1
    return bytes(out[:n])


def _us_seal(label, plaintext):
    ct = bytes(a ^ b for a, b in zip(plaintext, _us_stream(label, len(plaintext))))
    return {"c": base64.b64encode(ct).decode(),
            "t": hmac.new(_us_key, label + b"\x02" + ct, hashlib.sha256).hexdigest()}


_us_pages = {}
for _m in (re.finditer(r"<!--us:([a-z]+)\n(.*?)\n-->(.*?)<!--/us:\1-->", src, re.S)
           if US_ON else []):
    _name, _meta, _html = _m.group(1), _m.group(2), _m.group(3)
    _hdr = dict(l.split(": ", 1) for l in _meta.strip().splitlines())
    _us_pages[_name] = _us_seal(_name.encode(), json.dumps(
        {"t": _hdr["title"], "d": _hdr["desc"], "h": _html.strip()}).encode())
    src = src.replace(_m.group(0), "")
assert len(_us_pages) == (7 if US_ON else 0), \
    "expected %d gated pages, sealed %d" % (7 if US_ON else 0, len(_us_pages))
assert "players\u2019 associations" not in src and "HIPAA" not in src, \
    "gated prose survived into the shipped markup"
if US_ON:
  src = src.replace(
    '<script id="usx">window.__USX=null;</script>',
    '<script id="usx">window.__USX=' + json.dumps({
        "salt": US_SALT.hex(), "iter": US_ITER,
        "verify": hmac.new(_us_key, b"biolyz-us-verify", hashlib.sha256).hexdigest(),
        "pages": _us_pages,
    }) + ';</script>')
  assert "window.__USX=null" not in src, "the __USX marker script moved or changed"
print("us section: %s"
      % ("%d pages sealed, %.0f KB ciphertext"
         % (len(_us_pages), sum(len(p["c"]) for p in _us_pages.values()) / 1024)
         if US_ON else "not present (public build)"))

# ---- routing shims -------------------------------------------------------
# The app routes on real paths. BASE lets one bundle serve a domain root or a
# subdirectory without guessing; BIOLYZ_BASE=/sub sets it at build time.
BASE = os.environ.get("BIOLYZ_BASE", "").rstrip("/")
base_js = '<script>window.__BASE__=%s;</script>' % json.dumps(BASE)

# The artifact-shaped output is served from a deep, opaque URL where no host
# will answer /compare/... with the app, so that copy routes on hashes.
open(os.path.join(sp, "biolyz-site.html"), "w", encoding="utf-8").write(
    '<script>window.__FORCE_HASH__=true;</script>\n' + src + "\n" + inline_loader + "\n")
head='<!doctype html><html><head><meta charset="utf-8">'\
     '<meta name="viewport" content="width=device-width, initial-scale=1">'\
     '<style>:root{color-scheme:light}body{margin:0}img{max-width:100%}'\
     '[hidden]{display:none!important}</style></head><body>'
os.makedirs(os.path.join(sp,"serve"),exist_ok=True)
open(os.path.join(sp, "serve", "index.html"), "w", encoding="utf-8").write(
    head + base_js + src + "\n" + file_loader + "\n</body></html>")

# Assets as real files beside the page.
assets = os.path.join(sp, "serve", "assets")
os.makedirs(assets, exist_ok=True)
for cur in os.listdir(assets):
    os.remove(os.path.join(assets, cur))
_bytes = 0
for name, src_path in list(IMG_SRC.items()) + list(VID_SRC.items()):
    dst = os.path.join(assets, os.path.basename(src_path))
    with open(src_path, "rb") as a, open(dst, "wb") as b:
        data = a.read(); b.write(data); _bytes += len(data)
print("assets: %d files, %.2f MB" % (len(IMG_SRC) + len(VID_SRC), _bytes / 1048576))

# Host rewrite rules so a deep path serves the app instead of a 404. Netlify,
# Cloudflare Pages and friends all read this file; other hosts need the
# equivalent rule, which the README spells out.
open(os.path.join(sp, "serve", "_redirects"), "w", encoding="utf-8").write(
    "/*    /index.html   200\n")

# A preview deploy must not be indexed. This build still carries visible
# "TO CONFIRM" placeholders, API endpoints engineering has not signed off,
# and a gated section nobody outside Biolyz should find in a search result.
# DELETE THIS FILE when the site actually goes live.
open(os.path.join(sp, "serve", "robots.txt"), "w", encoding="utf-8").write(
    "# Preview build. Delete this file when the site goes live.\n"
    "User-agent: *\nDisallow: /\n")
_withloader = src + "\n" + file_loader
i=_withloader.rindex("<script>"); j=_withloader.rindex("</script>")
open(sp+"/check.js","w",encoding="utf-8").write(_withloader[i+8:j])
r=subprocess.run(["node","--check",sp+"/check.js"],capture_output=True,text=True)
_page = len((head + base_js + src + file_loader).encode())
print("page %.0f KB  |  artifact %.2f MB  |  node --check: %s %s"
      % (_page / 1024,
         len(open(os.path.join(sp, "biolyz-site.html"), "rb").read()) / 1048576,
         r.returncode, r.stderr[:300] or "clean"))


def mirror_dir():
    """Where to drop a servable copy, or None.

    macOS TCC denies a dev server spawned by the editor ANY read access to
    ~/Downloads. Point such a server at this repo's serve/ and every request
    404s, with the right --directory on the process and the file plainly on
    disk — which is what makes it look impossible. Serving a copy out of the
    session scratchpad is the only thing that works.

    The scratchpad path contains a session id, so it is discovered rather
    than hardcoded: a hardcoded one is wrong in every later session and
    meaningless on anyone else's machine.
    """
    env = os.environ.get("BIOLYZ_SERVE_MIRROR")
    if env in ("0", "none", "off"):
        return None
    if env:
        return env
    import glob
    # /private/tmp/claude-<uid>/<project>/<session>/scratchpad
    pads = [d for d in glob.glob("/private/tmp/claude-*/*/*/scratchpad")
            if os.path.isdir(d)]
    if not pads:
        return None
    # Prefer a scratchpad that ALREADY holds a mirror: that is the one a dev
    # server is pointed at. Plain "most recently modified" picks whichever
    # session last touched its scratchpad for any reason, which silently
    # writes 21 MB somewhere nobody is serving.
    served = [d for d in pads if os.path.exists(os.path.join(d, "serve", "index.html"))]
    return os.path.join(max(served or pads, key=os.path.getmtime), "serve")


dest = mirror_dir()
if dest:
    os.makedirs(dest, exist_ok=True)
    out = os.path.join(dest, "index.html")
    # The assets live beside the page now, so the mirror has to carry them or
    # the preview serves a page with no images and no video.
    adst = os.path.join(dest, "assets")
    os.makedirs(adst, exist_ok=True)
    asrc = os.path.join(sp, "serve", "assets")
    keep = set(os.listdir(asrc)) if os.path.isdir(asrc) else set()
    for stale in set(os.listdir(adst)) - keep:
        os.remove(os.path.join(adst, stale))
    for f in keep:
        s_, d_ = os.path.join(asrc, f), os.path.join(adst, f)
        if not os.path.exists(d_) or os.path.getsize(d_) != os.path.getsize(s_):
            with open(s_, "rb") as a, open(d_, "wb") as b:
                b.write(a.read())
    for rel, dst in (("serve/index.html", out),
                     ("serve/_redirects", os.path.join(dest, "_redirects")),
                     # The dev server has to live beside what it serves: TCC
                     # denies the spawned process ~/Downloads entirely, the
                     # script included, so running it from the repo fails with
                     # "Operation not permitted" before it reads a single file.
                     ("tools/serve.py", os.path.join(dest, "serve.py"))):
        src_path = os.path.join(sp, *rel.split("/"))
        if os.path.exists(src_path):
            with open(src_path, "rb") as a, open(dst, "wb") as b:
                b.write(a.read())
    print("mirrored to", out)
else:
    print("no serve mirror (set BIOLYZ_SERVE_MIRROR to choose one)")
