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

Two things follow from that, and neither is a code question:

1. **They make claims.** A club mark in this layout reads as "customer" and a
   press mark reads as "covered us". Both need to be true, and permitted,
   before the page goes anywhere public.
2. **This repository must stay private while they are in it.** Storing
   someone else's mark for an internal build is ordinary; redistributing it
   from a public repository is not.

If the repo ever needs to go public, delete this directory, replace the six
`_clean(...)` calls in `build.py` with a local placeholder, and keep the marks
wherever the brand assets actually live.
