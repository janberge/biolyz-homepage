# Biolyz homepage redesign

A rebuild of biolyz.com on the [Atira design system](https://github.com/janberge/biolyz-squad-monitoring) —
the same token layer the squad-monitoring dashboard is built from. 21 hash
routes plus a 404, assembled into one self-contained HTML file.

Published preview: https://claude.ai/code/artifact/07f9858d-6147-4000-a55b-19835786de18

```bash
python3 build.py            # → biolyz-site.html + serve/index.html
python3 -m http.server 3000 --directory serve
```

`site.html` is the **source of truth**. Never edit `biolyz-site.html` — it is
generated, gitignored, and overwritten on the next build.

## How the build works

`site.html` carries two kinds of placeholder, and `build.py` substitutes both:

- **`__IMG_<name>__`** → a dashboard screenshot from `web/<name>.jpg`. These
  do *not* become inline `src` data URIs. The biomarker overview alone appears
  four times, so inlining at each use embedded the same megabyte repeatedly;
  instead each image ships **once** in a `window.__IMG` map and a small loader
  assigns them at runtime. `width`/`height` are already on the markup, so
  nothing shifts while they resolve.
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

## Before this goes live

Carried over from the build, unresolved, and all content rather than code:

- The four protocol step descriptions.
- The science comparison table's Collection row — the live site's own copy
  there is garbled, so there was nothing correct to copy from.
- Changelog wording and dates.
- Every page carrying a `.stub` note: Privacy, Impressum, ERDF, Careers
  vacancies, and Literature's remaining 72 studies.
- **No legal text was drafted.** The Privacy and Impressum pages are
  placeholders, not drafts.

## Two bugs worth not reintroducing

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
