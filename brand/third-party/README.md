# Third-party marks

These are **other organisations' trademarks**, vendored here only so
`build.py` runs on a fresh clone without hunting through `~/Downloads`.

| File | Owner | Used on the page as |
|---|---|---|
| `borussia-dortmund.svg` | BV Borussia 09 Dortmund | a club mark |
| `bayer-leverkusen.svg` | Bayer 04 Leverkusen | a club mark |
| `new-york-times.svg` | The New York Times Company | a press mark |
| `kicker.svg` | kicker (Olympia-Verlag) | a press mark |
| `sportico.svg` | Sportico Media | a press mark |
| `whoop.svg` | WHOOP, Inc. | an integration mark |
| `garmin.svg` | Garmin Ltd. | an integration mark |
| `trainingpeaks.svg` | TrainingPeaks (PeaksWare, LLC) | an integration mark |
| `catapult.svg` | Catapult Group International | an integration mark |

(Kinexon, STATSports, and Oura's marks live as raster images in `web/` instead
— sourced as PNG/WEBP/JPG, not SVG — but the same rules below apply to them.)

Two things follow from that, and neither is a code question:

1. **They make claims.** A club mark in this layout reads as "customer", a
   press mark reads as "covered us", and an integration mark reads as "we
   connect with this platform". All of that needs to be true, and permitted,
   before the page goes anywhere public.
2. **This repository must stay private while they are in it.** Storing
   someone else's mark for an internal build is ordinary; redistributing it
   from a public repository is not.

If the repo ever needs to go public, delete this directory (and the
integration-mark files under `web/`), replace the `_clean(...)` calls and
`__IMG_` references for all of them in `build.py` with a local placeholder,
and keep the marks wherever the brand assets actually live.
