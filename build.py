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
import base64,json,os,re,sys,subprocess
sp=os.path.abspath(sys.argv[1] if len(sys.argv)>1 else os.path.dirname(__file__) or ".")
BRAND=os.path.join(sp,"brand")
src=open(os.path.join(sp,"site.html"),encoding="utf-8").read()
# Screenshots are shared across pages — the biomarker overview alone appears
# four times. Inlining the data URI at each use embedded the same megabyte
# repeatedly, so each one ships ONCE in a map and the images take their src
# from it at load. src="__IMG_x__" in the source becomes data-img="x" here.
used = sorted(set(re.findall(r'__IMG_([a-z0-9]+)__', src)))
imgmap = {}
for name in used:
    b = base64.b64encode(open(os.path.join(sp, "web", name + ".jpg"), "rb").read()).decode()
    imgmap[name] = "data:image/jpeg;base64," + b
src = re.sub(r'src="__IMG_([a-z0-9]+)__"', r'data-img="\1"', src)
assert "__IMG_" not in src, "an __IMG_ token was used outside a src attribute"
loader = ("<script>window.__IMG=" + json.dumps(imgmap) + ";\n"
          "/* Set every screenshot from the shared map. width/height are on the\n"
          "   markup already, so nothing shifts while these resolve. */\n"
          "document.querySelectorAll('img[data-img]').forEach(function(i){\n"
          "  var d=window.__IMG[i.dataset.img]; if(d) i.src=d; });\n</script>")
# Append, do not anchor on "</footer>" — the first one in the document is a
# blockquote's attribution footer, which put the loader before every image.
src = src.rstrip() + "\n" + loader + "\n"
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
src = src.replace("__SVG_sportico__", _clean(
    os.path.join(TP, "sportico.svg"), "sportico", viewbox="0 0 491.1 126.76"))

logo=os.path.join(BRAND,"biolyz")
src=src.replace("__SVG_signet__",svg(logo+"/biolyz-signet.svg","mark"))
h=svg(logo+"/biolyz-horizontal.svg","mark")
src=src.replace("__SVG_horizontal__",h,1).replace("__SVG_horizontal2__",h,1)
assert not re.findall(r'__[A-Z_a-z0-9]+__',src), "unsubstituted tokens"
open(os.path.join(sp,"biolyz-site.html"),"w",encoding="utf-8").write(src)
head='<!doctype html><html><head><meta charset="utf-8">'\
     '<meta name="viewport" content="width=device-width, initial-scale=1">'\
     '<style>:root{color-scheme:light}body{margin:0}img{max-width:100%}'\
     '[hidden]{display:none!important}</style></head><body>'
os.makedirs(os.path.join(sp,"serve"),exist_ok=True)
open(os.path.join(sp,"serve","index.html"),"w",encoding="utf-8").write(head+src+"</body></html>")
i=src.rindex("<script>"); j=src.rindex("</script>")
open(sp+"/check.js","w",encoding="utf-8").write(src[i+8:j])
r=subprocess.run(["node","--check",sp+"/check.js"],capture_output=True,text=True)
print("assembled", round(len(src.encode())/1048576,2),"MB | node --check:", r.returncode, r.stderr[:300] or "clean")
