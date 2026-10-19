"""Emit the two comparison pages from the Word source.

The copy is Jan's, written for SEO, and retyping it by hand is how a claim
quietly changes. This reads `content/compare-source.json` — paragraphs
extracted verbatim from 261005-BiolyzWebsite(POC+BL)-v2.docx — and prints the
two <div class="page"> blocks to paste into site.html.

The document is one shared explainer followed by two individual parts, so the
explainer is emitted on BOTH pages: each comparison has to stand alone for
someone arriving cold from search.

    python3 tools/gen_compare.py > /tmp/compare.html
"""
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = [r["t"] for r in json.load(open(os.path.join(HERE, "content", "compare-source.json"),
                                   encoding="utf-8"))]


# Typos in the Word source. Spelling and grammar only — nothing here changes a
# claim, a number or a tone. Listed explicitly so every change is auditable
# against the original, and so a corrected .docx makes this list shrink.
FIXES = {
    7:   [("biolyz tells", "Biolyz tells")],
    10:  [("for very test", "for every test")],
    11:  [("Spoint of care wins", "Point of care wins"), ("reutrns", "returns")],
    14:  [("Whats the", "What&rsquo;s the")],
    52:  [("test strips of cartridges", "test strips or cartridges")],
    122: [("your athletes blood", "your athletes&rsquo; blood")],
    124: [("Bloodlabs needs a trained", "Blood labs need a trained")],
}


def e(i):
    """One source paragraph, escaped, with the typographic marks the site uses."""
    t = html.escape(P[i], quote=False)
    for a, b in FIXES.get(i, []):
        assert a in t, f"correction for paragraph {i} no longer matches: {a!r}"
        t = t.replace(a, b)
    return (t.replace("'", "&rsquo;").replace('"', "&rdquo;")
             .replace(" - ", " &mdash; ").replace("–", "&ndash;"))


def para(i, cls="copy"):
    return f'      <p class="{cls}">{e(i)}</p>\n'


def bullets(idxs):
    out = '      <ul class="ticks">\n'
    for i in idxs:
        out += f'        <li>{e(i)}</li>\n'
    out += "      </ul>\n"
    return out


def split_bullets(idxs):
    """Lines shaped 'Label: sentence' become a label + the rest."""
    out = '      <ul class="splits">\n'
    for i in idxs:
        t = e(i)
        if ":" in t:
            head, rest = t.split(":", 1)
            out += f'        <li><b>{head.strip()}</b>{rest.strip()}</li>\n'
        else:
            out += f'        <li>{t}</li>\n'
    out += "      </ul>\n"
    return out


def table(head, start, end, rival):
    out = '    <div class="tbl">\n      <table>\n        <thead>\n          <tr>'
    out += f'<th scope="col">{html.escape(P[head])}</th>'
    out += f'<th scope="col">{html.escape(P[head+1])}</th>'
    out += f'<th scope="col">{html.escape(P[head+2])}</th></tr>\n'
    out += "        </thead>\n        <tbody>\n"
    i = start
    while i + 2 <= end:
        out += (f'          <tr><th scope="row">{e(i)}</th>'
                f'<td class="us">{e(i+1)}</td>'
                f'<td class="them">{e(i+2)}</td></tr>\n')
        i += 3
    out += "        </tbody>\n      </table>\n    </div>\n"
    return out


def faqs(pairs):
    out = '    <div class="faqs">\n'
    for q, a in pairs:
        out += (f'      <details class="faq"><summary>{e(q)}</summary>\n'
                f'        <p>{e(a)}</p></details>\n')
    out += "    </div>\n"
    return out


def explainer():
    """Shared across both pages — the doc's opening block."""
    return (
        '<section class="sec">\n  <div class="wrap">\n'
        '    <div class="split">\n'
        '      <div class="hd" style="margin:0">\n'
        '        <span class="eyebrow">What Biolyz is</span>\n'
        f'        <h2 class="h3">{e(2)}</h2>\n'
        "      </div>\n      <div>\n"
        + para(1) + para(3)
        + f'        <h3 class="h5" style="margin-top:var(--sp-xl)">{e(4)}</h3>\n'
        + para(5)
        + "      </div>\n    </div>\n  </div>\n</section>\n\n")


def page(pid, title, route, other_route, other_label, idx):
    """idx: the paragraph indices for this comparison, named for readability."""
    s = f'<div class="page" id="{pid}" data-title="{title}" '
    s += f'data-desc="{idx["desc"]}" hidden>\n\n'
    s += ('<header class="pagehead">\n  <div class="wrap inner">\n'
          '    <span class="eyebrow">Comparison</span>\n'
          f'    <h1 class="h1">{e(idx["h1"])}</h1>\n'
          f'    <p class="lead">{e(idx["lede"])}</p>\n'
          '  </div>\n</header>\n\n')

    # the claim pair and the four operational differences
    s += ('<section class="sec--md">\n  <div class="wrap">\n'
          '    <div class="claimpair">\n'
          f'      <p class="h4 claim-them">{e(idx["claimThem"])}</p>\n'
          f'      <p class="h4 claim-us">{e(idx["claimUs"])}</p>\n'
          "    </div>\n"
          + split_bullets(idx["four"]) +
          "  </div>\n</section>\n\n")

    s += explainer()

    # what's the difference
    s += ('<section class="sec band-grey">\n  <div class="wrap">\n'
          '    <div class="hd">\n      <span class="eyebrow">The difference</span>\n'
          f'      <h2 class="h2">{e(idx["diffH"])}</h2>\n    </div>\n'
          '    <div class="cols">\n')
    for i in idx["diff"]:
        s += f'      <div class="col"><p>{e(i)}</p></div>\n'
    s += "    </div>\n"
    if idx.get("nonInvasive"):
        s += ('    <div class="callout" style="margin-top:var(--sp-2xl)">\n'
              f'      <b style="font-weight:400;color:var(--text)">{e(idx["nonInvasive"][0])}</b> '
              f'{e(idx["nonInvasive"][1])}\n    </div>\n')
    s += "  </div>\n</section>\n\n"

    # what the rival is, and what it does well
    s += ('<section class="sec">\n  <div class="wrap">\n'
          '    <div class="hd">\n      <span class="eyebrow">The alternative</span>\n'
          f'      <h2 class="h2">{e(idx["whatH"])}</h2>\n'
          + para(idx["whatP"]) + "    </div>\n"
          '    <div class="cols">\n')
    for h, p in idx["whatCols"]:
        s += (f'      <div class="col"><h3>{e(h)}</h3><p>{e(p)}</p></div>\n')
    s += ("    </div>\n"
          f'    <p class="eyebrow" style="margin-top:var(--sp-2xl)">{e(idx["egH"])}</p>\n'
          + bullets(idx["eg"]) +
          "  </div>\n</section>\n\n")

    # the table
    s += ('<section class="sec band-grey">\n  <div class="wrap">\n'
          '    <div class="hd">\n      <span class="eyebrow">Side by side</span>\n'
          f'      <h2 class="h2">{e(idx["tableH"])}</h2>\n    </div>\n'
          + table(idx["tHead"], idx["tStart"], idx["tEnd"], other_label) +
          "  </div>\n</section>\n\n")

    # limits, both ways
    s += ('<section class="sec">\n  <div class="wrap">\n'
          '    <div class="hd">\n      <span class="eyebrow">Honest limits</span>\n'
          f'      <h2 class="h2">{e(idx["limH"])}</h2>\n    </div>\n'
          '    <div class="split split--even">\n'
          f'      <div><h3 class="h5">{e(idx["limThemH"])}</h3>\n'
          + para(idx["limThemP"]) + bullets(idx["limThem"]) + "      </div>\n"
          f'      <div><h3 class="h5">{e(idx["limUsH"])}</h3>\n'
          + bullets(idx["limUs"]) + "      </div>\n"
          "    </div>\n  </div>\n</section>\n\n")

    # a testing day, then cost
    s += ('<section class="sec band-grey">\n  <div class="wrap">\n'
          '    <div class="split">\n'
          '      <div class="hd" style="margin:0">\n'
          '        <span class="eyebrow">In practice</span>\n'
          f'        <h2 class="h3">{e(idx["dayH"])}</h2>\n      </div>\n'
          f'      <div>{para(idx["dayP"])}      </div>\n    </div>\n'
          '    <hr class="rule" style="margin-block:var(--sp-3xl)">\n'
          '    <div class="split">\n'
          '      <div class="hd" style="margin:0">\n'
          '        <span class="eyebrow">Economics</span>\n'
          f'        <h2 class="h3">{e(idx["costH"])}</h2>\n      </div>\n'
          f'      <div>{para(idx["costP"])}'
          f'        <p class="copy" style="margin-top:var(--sp-md)">{e(idx["costLead"])}</p>\n'
          + split_bullets(idx["cost"]) + "      </div>\n    </div>\n  </div>\n</section>\n\n")

    # which fits
    s += ('<section class="sec">\n  <div class="wrap">\n'
          '    <div class="hd">\n      <span class="eyebrow">Which to choose</span>\n'
          f'      <h2 class="h2">{e(idx["fitH"])}</h2>\n'
          + para(idx["fitP"]) + "    </div>\n"
          '    <div class="cols">\n'
          f'      <div class="col"><h3>{e(idx["getThemH"])}</h3>\n'
          + bullets(idx["getThem"]) + "      </div>\n"
          f'      <div class="col"><h3>{e(idx["getUsH"])}</h3>\n'
          + bullets(idx["getUs"]) + "      </div>\n"
          "    </div>\n"
          f'    <h3 class="h5" style="margin-top:var(--sp-3xl)">{e(idx["chooseH"])}</h3>\n'
          + bullets(idx["choose"]) + "  </div>\n</section>\n\n")

    # the quote — the doc leaves this heading empty
    s += ('<section class="sec inv">\n  <div class="wrap">\n'
          f'    <span class="eyebrow">{e(idx["sayH"])}</span>\n'
          '    <blockquote style="margin-top:var(--sp-xl)">\n'
          '      <p>&ldquo;I was skeptical at first, but when you experience the power of\n'
          '        looking inside a player on a daily basis, that can really change how you\n'
          '        work and compete.&rdquo;</p>\n'
          '      <footer><b>Dr. Markus Braun</b><span>Head Team Physician, Borussia Dortmund (BVB)</span></footer>\n'
          "    </blockquote>\n  </div>\n</section>\n\n")

    # faqs
    s += ('<section class="sec">\n  <div class="wrap">\n'
          '    <div class="hd">\n      <span class="eyebrow">FAQ</span>\n'
          f'      <h2 class="h2">{e(idx["faqH"])}</h2>\n    </div>\n'
          + faqs(idx["faq"]) +
          '    <p class="copy" style="margin-top:var(--sp-2xl)">Also worth reading: '
          f'<a href="#{other_route}" data-link class="inline-link">{other_label}</a>.</p>\n'
          "  </div>\n</section>\n\n")

    s += ('<section class="sec--xl">\n  <div class="wrap close-cta">\n'
          '    <span class="eyebrow">See it on your own squad</span>\n'
          '    <h2 class="h2">The fastest way to judge this is your own data.</h2>\n'
          '    <a class="btn" href="#/demo" data-link>Book a demo &#8599;</a>\n'
          "  </div>\n</section>\n</div>\n")
    return s


POC = dict(
    desc=("Point of care gives one number in seconds; Biolyz reads 60+ biomarkers from a "
          "saliva swab in 24 to 48 hours. Panel size, needles, staff time and cost compared."),
    h1=6, lede=7, claimThem=8, claimUs=9, four=[10, 11, 12, 13],
    diffH=14, diff=[15, 16],
    whatH=17, whatP=18, whatCols=[(19, 20), (21, 22), (23, 24)], egH=25, eg=[26, 27, 28, 29],
    tableH=31, tHead=32, tStart=35, tEnd=70,
    limH=71, limThemH=72, limThemP=73, limThem=[74, 75, 76, 77, 78], limUsH=79, limUs=[80, 81],
    dayH=82, dayP=83, costH=85, costP=86, costLead=87, cost=[88, 89, 90],
    fitH=91, fitP=92, getThemH=93, getThem=[94, 95, 96], getUsH=97, getUs=[98, 99, 100, 101],
    chooseH=102, choose=[103, 104, 105], sayH=106,
    faqH=107, faq=[(108, 109), (110, 111), (112, 113), (114, 115), (116, 117), (118, 119)],
)

BL = dict(
    desc=("A sports blood lab gives a clinical snapshot a few times a season; Biolyz reads "
          "60+ biomarkers from saliva, daily, with no needle. Panels, turnaround and cost compared."),
    h1=120, lede=121, claimThem=122, claimUs=123, four=[124, 125, 126, 127],
    diffH=128, diff=[129, 130], nonInvasive=(131, 132),
    whatH=133, whatP=134, whatCols=[(135, 136), (137, 138), (139, 140)],
    egH=141, eg=[142, 143, 144],
    tableH=145, tHead=146, tStart=149, tEnd=184,
    limH=185, limThemH=186, limThemP=187, limThem=[188, 189, 190, 191, 192],
    limUsH=193, limUs=[194, 195, 196],
    dayH=197, dayP=198, costH=200, costP=201, costLead=202, cost=[203, 204, 205],
    fitH=206, fitP=207, getThemH=208, getThem=[209, 210, 211], getUsH=212,
    getUs=[213, 214, 215, 216],
    chooseH=217, choose=[218, 219, 220], sayH=221,
    faqH=222, faq=[(224, 225), (226, 227), (228, 229), (230, 231), (232, 233), (234, 235)],
)

sys.stdout.write(page("p-vs-poc", "Biolyz vs Point of Care", "/compare/point-of-care",
                      "/compare/blood-labs", "Biolyz vs sports blood labs", POC))
sys.stdout.write("\n")
sys.stdout.write(page("p-vs-bloodlab", "Biolyz vs Sports Blood Labs", "/compare/blood-labs",
                      "/compare/point-of-care", "Biolyz vs point of care", BL))
