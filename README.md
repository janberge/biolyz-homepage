# Biolyz homepage redesign

A rebuild of biolyz.com on the [Atira design system](https://github.com/janberge/biolyz-squad-monitoring) —
the same token layer the squad-monitoring dashboard is built from. 30 routes
plus a 404, assembled into one self-contained HTML file.

Published preview: https://claude.ai/artifact/1z7hPfYiPFh9fA74bNMgmu

```bash
python3 build.py            # → biolyz-site.html + serve/index.html
python3 tools/serve.py 3000 # NOT http.server — see Routing below
```

`site.html` is the **source of truth**. Never edit `biolyz-site.html` — it is
generated, gitignored, and overwritten on the next build.

### Routing

The app routes on **real paths** (`/compare/point-of-care`), not fragments. A
`#/route` is the same document to a crawler, so page-specific titles,
descriptions and FAQ markup count for nothing on hash URLs — which defeats the
comparison pages entirely.

That means any host serving this must **fall back to `index.html` for unknown
paths**. `serve/_redirects` carries the rule for Netlify and Cloudflare Pages;
other hosts need their own equivalent (nginx `try_files`, Apache rewrite, S3
error-document). `python3 -m http.server` does **not** do this and will 404
every deep link — use `tools/serve.py`, which applies the same rule locally.

`tools/serve.py` falls back **only for paths with no extension**. A route has
none; an asset does. Falling back for both means a missing `/assets/hero.mp4`
is answered with `index.html` at 200 and `text/html`, so the video silently
does not play instead of failing where you can see it — which is exactly how an
emptied scratchpad went unnoticed for two days. The scratchpad lives under
`/private/tmp` and is cleaned between sessions, so **re-run `python3 build.py`
before trusting a local preview**; the mirror copy is rebuilt from `serve/`
every time.

`serve/robots.txt` blocks all crawlers. This build still carries visible
"TO CONFIRM" placeholders, API endpoints engineering has not signed off and the
gated US section, none of which should appear in a search result. **Delete that
file when the site goes live.**

Two fallbacks keep it from breaking elsewhere. Opened from disk, or anywhere
`history.pushState` is unavailable, it switches to hash mode and rewrites its
own links to match. The artifact-shaped `biolyz-site.html` is served from a
deep opaque URL where no host will answer `/compare/...`, so that copy is
built with hash mode forced on. Set `BIOLYZ_BASE=/sub` at build time to serve
from a subdirectory.

Legacy `#/route` links still circulate; they are rewritten to the real path on
load, without adding a history entry.

**Linking to a section of another page** uses `data-anchor` on the link rather
than a route of its own: `<a href="/science" data-link
data-anchor="research-pipeline">`. A second route for the same page would mean
two URLs sharing one title and one description, which is the SEO problem the
real-paths work existed to solve. `ANCHOR_OF` is still there for a route that
should *always* open at a section; `data-anchor` is for the case where only one
link wants it. The recorder listener is registered before either mode's own
click handler, so it also covers hash mode, which has no click handler at all.

### The gated US readiness section

`/us` and its six subpages (`/us/player-consent`, `/us/security`,
`/us/lab-quality`, `/us/result-to-action`, `/us/league-systems`,
`/us/integrations`) are an internal working draft of
`biolyz_us_readiness_content.md`. They are reachable from one footer entry,
marked with a padlock, and are the only routes the app sets
`<meta name="robots" content="noindex, nofollow">` on.

**This repository is public, so the draft is not in it.** It lives in `us/`,
which is gitignored, and `site.html` carries four markers where it goes:
`<!--US:SECTION-->`, `<!--US:GATE-->`, `<!--US:ROUTES-->`, `<!--US:FOOTER-->`.
With no `us/` directory the markers resolve to nothing and you get the public
site — 24 pages, no `/us` routes, no footer entry, no gate — which is a
complete, working build and the one a fresh clone produces. With `us/` present
the markers fill and the build seals the seven pages as before.

Encrypting the built file was never going to protect prose that the source
published in the clear, and the passphrase sat in this file until the same
realisation. **The access code is in `us/pass.txt`, not here.** Override it for
a build with `BIOLYZ_US_PASS='...' python3 build.py`; only a verifier derived
from it reaches the output, so changing it means rebuilding.

#### How the gate works, and what it does not do

The six page bodies are **encrypted in the shipped file** and decrypted in the
browser. That is a step beyond the usual "hide it with CSS, compare a hash",
and it is there for one reason: this draft states things nobody has confirmed
yet, including API endpoints the source document itself warns must not be
published as fact. A gate that still ships the prose would put all of it one
View Source away, and a crawler reads markup without ever running the gate.
`build.py` asserts that none of the gated prose survives into either output.

    key    = PBKDF2-HMAC-SHA256(passphrase, salt, 600000) -> 32 bytes
    stream = HMAC(key, label || 0x01 || uint64be(block))
    cipher = plaintext XOR stream
    tag    = HMAC(key, label || 0x02 || cipher)        encrypt then MAC

Only primitives that both WebCrypto and Python's `hashlib` ship with, so the
build needs no third party package and there is no hand written cipher in it.
Unlock measured at 172 ms. An unlock is cached in `sessionStorage` for that
tab only, and "Lock this section" clears it and reloads.

**This is not access control.** Anyone with the passphrase reads everything,
forever, offline, and can pass the file on. The passphrase is the only secret,
so a weak one can be attacked offline against the verifier — 600k iterations
make each guess cost something, they do not make a guessable phrase safe.
Treat the link as confidential, not as protected.

#### Editing the content

In `us/section.html` each page body sits between `<!--us:name ... -->` and
`<!--/us:name-->`; the title and description for that page live in the opening
marker and are encrypted with it. Opened straight from `site.html` the pages
are plain and the gate unlocks itself, so the source stays editable without a
code. `build.py` asserts every marker resolved, so a half applied edit fails
the build rather than shipping a stray `<!--US:` into the page. `build.py` asserts it sealed exactly seven.

Rules carried from the source document, all enforced by hand, not by the
build: no block titled "Internal notes" is published; no hyphens joining words
("long term", "third party", "opt in"); never *predicts*, *diagnoses* or
*prevents*; only Borussia Dortmund and Bayer 04 Leverkusen may be named.

Every `[CONFIRM]` in the source became an inline `.cf` flag on the exact claim
it belongs to — 29 of them — rather than a list at the foot of the page that
loses what it refers to. The preview bar counts them per page and switches
them off, which renders the copy as it would actually ship. The per page
checklist is built from the flags themselves at unlock, so the count can never
drift from what is marked. **Switching the flags off does not remove the
claims.** The source document's rule is that an unconfirmed sentence is
deleted, not softened; nothing here has been deleted yet.

The seventh Mermaid block — the CLIA decision tree — is inside an "Internal
notes" section and is deliberately not on any page.

### Analytical performance explorer (`/biomarkers`)

The precision study from `Biolyz_Saliva_Panel_Performance_Summary` (release
1.2.1, October 2026) as an interactive section at `#precision`, directly under
the page head and above the panel it is the evidence for. 29 analytes,
three measures, a sticky axis and the ICH M10 limit drawn through the chart.

**It is labelled precision, not accuracy, and that is deliberate.** The source
document says in its own scope note that it covers precision and that agreement
with an external reference method was not part of it. Accuracy is closeness to a
true value; this study measures whether the same sample gives the same answer.
Calling it accuracy on a public page would be a claim the data does not support,
so the section says what the study does not cover as well as what it does.

The data is one array at the top of the script, joined from the PDF's three
tables and checked against the document's own claims before it went in: 27
classified markers, 26 at or under 15 % on both measures, adenosine the single
exception at 20.5 % between runs, median between runs 2.7 % in the final
configuration. The two analytes still in optimisation (uric acid,
3-hydroxyglutaric acid) are drawn as open rows with an em dash rather than left
out, which would quietly turn 29 markers into 27. LOQ carries its own display
string (`ls`) so 0.10 and 0.20 keep the significant figures the study reports.

Three measurements drive the whole chart — `--ap-name`, `--ap-val`, `--ap-gap`
on `.ap-chart`. The axis margins and the limit rule are both expressed in them,
so the phone layout only has to zero all three to move the name above its own
bar and give the track the full width.

### The panel, grouped (`/biomarkers`)

The 62 analytes are sorted into the ten groups from **slide 2 of
`Schwarz_biomarker_deep_dive.pptx`** ("Saliva biomarker menu"), in the deck's
own order, rather than alphabetically — the lab's menu of what saliva yields,
which is how the people who built the panel think about it. The old
`.analyte-tag` strings were no use for this: 54 distinct tags across 62
analytes, almost all unique.

Every analyte the deck names keeps the deck's own assignment, including
`2'-deoxyguanosine`, which the deck files under purines where the site's tag
calls it a DNA turnover nucleoside. **Four analytes are on the site but not on
the slide, and those four assignments are mine, not the deck's:** estradiol →
steroid hormones, arachidonoyl glycine and prostaglandin E2 ethanolamide →
fatty acids and lipid mediators, nicotinuric acid → sleep, vitamins and
lifestyle. The build asserts all 62 land in exactly one group with none left
over.

Group chips and the search box are two ways into one filter: a heading with
nothing left under it hides rather than standing over an empty list, and each
heading's count follows what is actually showing.

Two groups on the slide have no quantified entries and are written up
underneath the list instead: proteins (~70, by proteomics, a separate platform)
and in development (lactate, vitamin D, IgA, IgG, insulin, T4). The slide's
"Not in your current panel" is specific to the client the deck was written for
and is not reproduced.

### In motion (homepage) and the case rail (`/so-what`)

A scroll-snap rail of short current items — the "conversation currency" strip at
`#in-motion`, directly under the logos. **To add one, copy an `<article class="cc-card">` and fill it in.**
The cards are plain markup, not a JS array: the section reads with the script
disabled, and the controls count the cards themselves.

Auto-advances every 7 s, but only while the section is on screen, and stops for
good the first time anyone touches the rail. Off entirely under
`prefers-reduced-motion`. The precision card is also the home page's only route
into the analytical performance data, since that section lives on
`/biomarkers`.

### So what (`/so-what`, `/use-cases`, `/use-cases/alpha-actin`)

Built from `261008-SoWhatWebsite-v1.md`, then reshaped on Jan's direction: a
four step product flow, the readiness checklist as seven expandable cards, a
filterable case rail, and a reusable case detail template whose first instance
is the alpha-actin case.

**The four step flow** takes its shape from themarquee.ai/product: a spine with
numbered steps hanging off it, each a badge, a headline, a paragraph and its own
node diagram. Each step is **two columns — words left, diagram right** — rather
than text and boxes alternating down the page, so the four steps read as four
rows instead of eight blocks.

**The diagrams are one connected spine** (`.tree`), from Jan's sketch: a single
line running the whole flow with each node hanging off it to the left or the
right, and only the genuine branch points splitting into a pair. The spine
belongs to `.fw`, not to each tree, so it is continuous across all four steps
instead of restarting under every heading.

Its x position is derived: with two 1fr columns and a column gap `g`, the
diagram column's centre is at `75% + g/4` **of the step** — but the step is
inset from `.fw` by the rail padding `p`, and an absolutely positioned
percentage resolves against `.fw`'s padding box, which includes `p`. So the
same 75% lands `0.25p` short and the rule carries that correction:
`0.75(W - p) + p = 0.75W + p/4`. Measured at 1512px it was 17px out before that
term and within 1px after, across all ten single sided arms and all three split
bars. A node reaches the spine with one arm from its own vertical centre; a
split is a bar crossing the spine with a stub down into each side.

Below 980px the layout stacks, the diagram goes full width, and the spine moves
onto `.tree` at its own 50% (verified exact at 900px). Below 620px every node
goes full width on a left rail, which is the chain this degrades to.

Two deliberate departures from the reference. The spine is on the **left**, not
down the middle, because this system is left aligned everywhere and a centred
tree would be the one thing on the site that is not. And the nodes are hairlines
rather than glowing cards, because Atira has no shadow to glow with — the same
reason the screenshot frame is a hairline on a grey mat. The per step diagrams
reuse the `.fl` vocabulary already on the site, so the whole component is a rail
and a badge and nothing else. Step 02 carries the integration marks from the
product page's marquee, standing still, in a node of their own so they sit on
the tree rather than floating under it.

**Removed on Jan's direction, October 2026:** the three step "What we do"
(replaced by the four step flow), the "From signal to action" loop (the flow
covers it), and the cost of absence calculator with its ROI section. The case
detail page's "Calculate your cost of absence" button, which pointed at the
calculator, now points at the seven questions. Two brief placeholders went with
the ROI section — the calculator's default "weeks earlier" and days out for the
alpha-actin example — and are no longer open items for the site.

**Two places the brief and the site disagreed, resolved in the site's favour**
as the brief itself instructs: "Request a demo" is "Book a demo" at `/demo`,
the label and route every other CTA uses; and the brief joins words with
hyphens ("high-intensity", "starting-XI") where nothing else on this site does,
so those were unjoined. Biomarker names keep their hyphens — the brief says to
reproduce those exactly.

Every open item in the brief that touches published copy is rendered as a
visible `.ph` marker on the page rather than hidden in a comment, because the
page can go live before the answers arrive and an invented default is worse
than a blank: the calculator's default "weeks earlier", days out for the
alpha-actin ROI example, the missing hydration case for row 7, and club
approval. One open item does **not** surface anywhere in published copy and so
is recorded only here: the "cracks" case uses kynurenic acid and glutamine,
while checklist row 1 lists kynurenine and does not include glutamine.

### Page weight

There are **two outputs and they are not the same shape**:

| | what it is | size |
| --- | --- | --- |
| `serve/` | the deployable site: a small page plus `assets/` | **439 KB** page |
| `biolyz-site.html` | the artifact preview: everything inlined, hash routing | 7.9 MB |

The deployable build used to inline every screenshot and all three hero videos
as `data:` URIs in one 21 MB file. That cost +37% on every byte *and* made the
whole page one blocking request — nothing could paint until all 21 MB arrived.
Assets are now real files beside the page: cacheable, range-requestable, and
fetched only when needed.

Nothing heavy loads until it is on screen. An element inside a hidden page has
no box and so never intersects the viewport, which is what the loader keys
off. `loading="lazy"` alone does **not** do this — the `src` is set and the
browser decides. Measured: the home page fetches its own hero video and
nothing else; the product and science heroes and all 30-odd dashboard
screenshots stay unfetched until you visit those routes.

Each hero carries a **poster still** extracted from its own first frame, so
the video arrives after the text rather than before it and the hero is never a
black rectangle.

The artifact copy ships **no video at all** — inlined they are ~14 MB of
base64 and put the file over the 16 MB artifact ceiling, so the preview could
not be published. Posters stand in. `BIOLYZ_ARTIFACT_VIDEO=1` puts them back
and breaks publishing again.

### Serving it from the editor

The command above works from a terminal. A dev server **spawned by the editor**
is a different matter: macOS TCC denies those processes any read access to
`~/Downloads`, so pointing one at this repo's `serve/` returns 404 for every
request — with the correct `--directory` on the process and the file plainly on
disk. Nothing in the error says "permissions", which is what makes it waste an
afternoon.

So `build.py` also mirrors `serve/index.html` into the session scratchpad,
which such a server *can* read, and prints where it put it. The scratchpad
path carries a session id, so it is discovered at build time rather than
hardcoded — a hardcoded one is wrong in the next session and meaningless on
another machine.

```bash
BIOLYZ_SERVE_MIRROR=/some/dir python3 build.py   # mirror somewhere specific
BIOLYZ_SERVE_MIRROR=0 python3 build.py           # skip the mirror
```

## How the build works

`site.html` carries three kinds of placeholder, and `build.py` substitutes all of them:

- **`__IMG_<name>__`** → a dashboard screenshot from `web/<name>.jpg`. These
  do *not* become inline `src` data URIs. The biomarker overview alone appears
  four times, so inlining at each use embedded the same megabyte repeatedly;
  instead each image ships **once** in a `window.__IMG` map and a small loader
  assigns them at runtime. `width`/`height` are already on the markup, so
  nothing shifts while they resolve.
- **`__VIDEO_<name>__`** → a video from `web/<name>.mp4`, inlined the same
  way through a `window.__VIDEO` map (one entry today: the home hero's
  background). A video is a much bigger asset than a screenshot — the hero
  clip alone is most of the assembled file's size — but the project stays a
  single self-contained file, so it ships the same way rather than as an
  external reference.
- **`__SVG_<name>__`** → cleaned inline SVG from `brand/`. `svgclean.py` folds
  each exporter's `<style>` classes inline, because two Illustrator exports in
  one document otherwise fight over `.st0`/`.st1`.

The script asserts that no token survives substitution, and runs
`node --check` on the extracted script block before writing. A file that does
not parse is worse than one that is merely wrong: it looks fine until someone
opens it.

## Layout

| Path | What it is |
|---|---|
| `site.html` | The whole site: 21 routes, all CSS and JS inline. 191KB. |
| `build.py` | Assembly. Takes no arguments; everything is repo-relative. |
| `svgclean.py` | SVG normaliser — inlines `<style>` classes, retargets fills, retightens viewBoxes. |
| `ctx.html` | Source for the data-flow diagram (dotted paths drawn from live element positions, so they stay attached at every width). |
| `web/*.jpg` | 16 dashboard screenshots, 3.2MB. See below. |
| `web/hero.mp4` | Home hero background video, ~8MB. |
| `brand/biolyz/` | Our own marks — signet, horizontal lockup, white wordmark. |
| `brand/third-party/` | Club and press marks. **Read that folder's README before making this repo public.** |
| `tools/*.js` | Chrome DevTools Protocol scripts for capture and verification. |
| `tools/bbox.html` | How the tight viewBoxes in `build.py` were measured — `getBBox` in a real browser. Keeps those magic numbers explicable. |

## The screenshots

```bash
python3 tools/recapture.py                       # all of them
python3 tools/recapture.py --only full,athlete   # just these
python3 tools/recapture.py ~/src/biolyz-atira    # dashboard somewhere else
```

`tools/recapture.py` copies the dashboard, patches the **copy** so each view
is addressable as a URL, serves it, drives headless Chrome over CDP at
`deviceScaleFactor: 2`, and writes the JPEGs into `web/`. The dashboard itself
is never modified — it keeps `route` / `playerId` / `playerTab` in React state,
which is right for the product and useless for a capture tool, so the patch
lives here instead. `tools/dashshot.js` takes one frame.

The manifest at the top of `recapture.py` maps each name to a view and a size.
Sizes match what `site.html` declares; a capture at the wrong aspect gets
letterboxed and looks soft.

Two rules held when these were taken, and must hold again:

- **`?shots=1` nulls every player photo** before `imagery.js` runs, so
  captures fall back to generated silhouettes. *Real athlete faces must not
  ship on a public marketing page next to biomarker data.* Every image in
  `web/` was verified against this — all avatars are silhouettes.
- The dashboard keeps `route` / `playerId` / `playerTab` in React state rather
  than the URL, so capturing an arbitrary view means patching a **scratch copy
  only** to seed those from `URLSearchParams`. Do not commit that patch to the
  dashboard.

**These screenshots are a snapshot and will drift.** Re-run the script after
any change to the dashboard's chrome. Last captured **2026-09-11**, against a
dashboard with no topbar role chip, no Beta button and no Brief/Full toggle.

That last one cost an image: `brief.jpg` showed "Team Overview in Brief mode",
and the Brief view no longer exists. Both of its slots now use `full`, and the
alt text no longer claims a mode that is gone. `compare.jpg` and
`playerdata.jpg` went too — nothing had referenced them since 7 September.

Four alt texts were also wrong, which is the same staleness in words rather
than pixels: one counted 29 players against a squad of 36, one quoted 89% for
a player now reading 51% and named a "kynurenine pattern" from a surface the
product no longer has, one described a removed recovery score and those same
patterns, and one had the key measure **inverted** — it said the share of
markers *outside* the player's range when every percentage in the app is the
share *inside*, so it read the chart backwards.

The research lanes on `/science` are two, not three: Hyrox moved from "In the
pipeline" to "Ongoing" in October 2026 and the pipeline lane was retired rather
than left as an empty column with a zero in it.

## Before this goes live

Carried over from the build, unresolved, and all content rather than code:

- **The crest strip is centred and the testimonial card lives inside it**, so
  the card inherited `text-align:center` from `.proof--stacked` on a site that
  is left aligned everywhere. The card now opts out for itself; the logo row
  above it is untouched.
- **Four use cases, one detail page.** Three cards in the library carry a
  "detail page to follow" marker instead of a link.
- **`62 published` against `56 reportable markers from 48 measured analytes`.**
  The list toolbar and the derived-ratios callout under it have disagreed on
  the size of the panel since before this work; grouping them has not changed
  that. One of the two numbers is stale.
- **29 `[CONFIRM]` items across the US section**, listed per page behind the
  preview bar. Eleven of them are on `/us/security` alone, and most of those
  are questions for engineering rather than copy decisions.
- The US integrations page publishes endpoint paths and field names that
  engineering has not confirmed. The source document is explicit that these
  must not go out as fact.

- The four protocol step descriptions.
- The science comparison table's Collection row — the live site's own copy
  there is garbled, so there was nothing correct to copy from.
- Changelog wording and dates.
- Every page carrying a `.stub` note: Privacy, Impressum, ERDF, Careers
  vacancies, and Literature's remaining 72 studies.
- **No legal text was drafted.** The Privacy and Impressum pages are
  placeholders, not drafts.

## Nine bugs worth not reintroducing

- **`getElementById` does not care which page is showing.** Every route's
  markup is in the DOM at once, so an anchor lookup happily returns a section
  belonging to a hidden page — which measures zero and would scroll the page
  you *are* on to an arbitrary offset. `show()` now requires the anchor to be
  inside the page it is rendering.
- **An anchored link clicked while already on its own page** took the
  same-route branch, scrolled to the top, and left the anchor pending — so the
  *next* navigation, to an unrelated page, jumped to it. That branch now
  consumes the anchor and scrolls to it, which is what the click meant anyway.

- **A popover anchored to an off-centre element cannot be centred with CSS
  alone.** `.testi-pop` was `left:50%; transform:translateX(-50%)` against a
  club crest that sits near the left of the band, so at 375px one card hung
  3px off the left edge and the other 10px off the right — 10px of sideways
  pan on *every* page, because `body{overflow-x:hidden}` hides the scrollbar
  and not the scroll. It overflowed while **closed** too: `opacity:0` still has
  a box. The card is now placed rather than centred — clamped inside the frame
  with a 12px margin, with `--pop-arrow` moving the arrow by the same amount
  the other way so it stays on its crest. Run for every card at all times, not
  on open, since a hidden box overflows exactly as much as a visible one, and
  measured against `clientWidth` rather than the stylesheet's `100vw`, which on
  a desktop with a classic scrollbar is the wider of the two. At desktop the
  shift computes to exactly `0px`, so the original centred behaviour is intact.
  Note when measuring: the closed card carries `scale(.96)`, so
  `getBoundingClientRect()` returns a box 4% narrower than the layout box that
  `scrollWidth` actually counts.

- **An inline component script only sees the markup parsed before it.** The
  rail's script lives in the home page's own section, so when a second rail was
  added to `/so-what` — the last page in the document — `querySelectorAll`
  found one rail, not two, and the new one had no controls at all. Initialising
  now waits for `DOMContentLoaded`.
- **A rail on a route the router has not shown yet measures zero wide**, which
  makes every scroll position unreachable and collapses the dots to one. Loading
  `/` and then navigating to `/so-what` produced a dead carousel. A
  `ResizeObserver` on the rail covers it: being shown is a resize of that
  element and of nothing else, which a `window` resize listener never hears.


- **One dot per card is not one dot per scroll position.** Four cards on a
  1024px rail scroll to two positions, not four: the other two dots were
  controls that did nothing when clicked, and the active dot could never reach
  them. Dots are now derived from `ceil(scrollable / cardStep) + 1` and rebuilt
  on resize. The same width also broke `scroll-snap-type: x mandatory` — where
  the rail overflows by less than one card, a clamped scroll gets dragged back
  to the previous snap point and the last card is unreachable. `proximity`
  fixes it.


- **A router that rewrites links once, at load, against a page that is no
  longer finished at load.** In hash mode the router rewrites every
  `[data-link]` to `#/route`; the gated pages build themselves *after* the
  passphrase lands, so their six hub links still read `/us/security` and a
  click left the app for a path the artifact host does not serve. The rewrite
  is now `window.__relink(scope)` and the gate calls it on what it injects.
  Path mode hid this — its delegated click handler resolves any href, so the
  bug only existed in the two modes nobody tests by default.

- **`<div class="wrap inner">`.** `.pagehead .inner`'s `max-width` beat
  `.wrap`'s, and `.wrap`'s `margin-inline: auto` then *centred* a design that
  is left-aligned everywhere. Constrain the children, never the element that
  is also the container.
- **A measure in `ch` is not a viewport guarantee.** At the fluid root's 13px
  floor, a `62ch` paragraph is wider than a 390px phone, and
  `body { overflow-x: hidden }` turns that into silently clipped text. Every
  `max-width: <n>ch|rem` is now `min(<n>ch, 100%)`. Headless Chrome does
  **not** reproduce this — it ignored `width=device-width`. Only a real
  browser, checking `document.documentElement.scrollWidth` at 375px, showed
  the truth.
