"""Find new press articles about Biolyz and add them to content/blog.json.

    python3 tools/press_check.py                    # adds new articles to the file
    python3 tools/press_check.py --dry-run          # only lists what it would add
    python3 tools/press_check.py --summary pr.md    # also writes a pull-request body

Runs daily from .github/workflows/press-check.yml, which turns the change into a
pull request. Nothing reaches /blog until that pull request is merged, so every
suggestion is reviewed first.

Searches Google News (English and German) for "Biolyz". Google News links are
redirects, so each one is resolved to the publisher's own URL; an article is new
when that URL is not on the blog yet. Every Google link checked is remembered in
"seen", so an article is suggested once, and one marked "hidden" never returns.
Standard library only, so the workflow needs no install step.
"""
import argparse, datetime, email.utils, html, json, os, re, sys
import urllib.parse, urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "content", "blog.json")
QUERY = "Biolyz"
# Only recent coverage counts as "new"; older articles found by the search
# (2020-2024 pitch prizes, the seed round) are left for a person to add.
MAX_AGE_DAYS = 60
# (language label on the card, Google News edition)
FEEDS = [("EN", "hl=en-US&gl=US&ceid=US:en"),
         ("EN", "hl=en-GB&gl=GB&ceid=GB:en"),
         ("DE", "hl=de&gl=DE&ceid=DE:de"),
         ("DE", "hl=de&gl=AT&ceid=AT:de")]
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124 Safari/537.36"}


def fetch(url, data=None, headers=None):
    h = dict(UA); h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def resolve(link):
    """Google News article link -> the publisher's URL (None if Google refuses)."""
    aid = urllib.parse.urlparse(link).path.rsplit("/", 1)[-1]
    try:
        page = fetch("https://news.google.com/rss/articles/" + aid)
        sg = re.search(r'data-n-a-sg="([^"]+)"', page).group(1)
        ts = re.search(r'data-n-a-ts="([^"]+)"', page).group(1)
        inner = json.dumps(["garturlreq", [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1,
                                            None, None, None, None, None, 0, 1], "X", "X", 1, [1, 1, 1],
                                           1, 1, None, 0, 0, None, 0], aid, int(ts), sg])
        body = "f.req=" + urllib.parse.quote(json.dumps([[["Fbv4je", inner, None, "generic"]]]))
        r = fetch("https://news.google.com/_/DotsSplashUi/data/batchexecute", body.encode(),
                  {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
        url = json.loads(json.loads(r.split("\n\n")[1])[0][2])[1]
        return url if url.startswith("http") else None
    except Exception as e:  # Google changes this endpoint now and then
        print("  could not resolve %s: %s" % (link[:80], e), file=sys.stderr)
        return None


def norm(url):
    """Compare URLs without scheme, www., query, fragment or trailing slash."""
    p = urllib.parse.urlparse(url)
    return (p.netloc.lower().removeprefix("www.") + p.path.rstrip("/")).lower()


def key(title):
    """Headline reduced to letters and digits, to catch the same article at a second URL."""
    return re.sub(r"[^0-9a-zäöüß]+", "", title.casefold())


def on_page_urls():
    """Article links that are written into site.html directly (the featured one)."""
    s = open(os.path.join(ROOT, "site.html"), encoding="utf-8").read()
    a = s.index('id="p-blog"'); b = s.index('<div class="page"', a + 10)
    return re.findall(r'class="bl-(?:feat|card)" href="([^"]+)"', s[a:b])


def search():
    """Every Google News hit for the query, de-duplicated by Google link."""
    hits = {}
    for lang, edition in FEEDS:
        url = "https://news.google.com/rss/search?q=%s&%s" % (urllib.parse.quote(QUERY), edition)
        try:
            root = ET.fromstring(fetch(url))
        except Exception as e:
            print("feed failed (%s): %s" % (edition, e), file=sys.stderr)
            continue
        for it in root.iter("item"):
            link = it.findtext("link") or ""
            src = it.find("source")
            outlet = (src.text if src is not None else "") or ""
            title = it.findtext("title") or ""
            if outlet and title.endswith(" - " + outlet):
                title = title[: -len(" - " + outlet)]
            when = email.utils.parsedate_to_datetime(it.findtext("pubDate")).date().isoformat() \
                if it.findtext("pubDate") else ""
            outlet = re.sub(r"^www\.", "", outlet.strip())
            hits.setdefault(link, {"lang": lang, "outlet": outlet,
                                   "title": html.unescape(title).strip(), "date": when})
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--summary")
    args = ap.parse_args()

    data = json.load(open(DATA, encoding="utf-8"))
    seen = set(data.setdefault("seen", []))
    known = {norm(a["url"]) for a in data["articles"]} | {norm(u) for u in on_page_urls()}
    titles = {key(a["title"]) for a in data["articles"]}
    cutoff = (datetime.date.today() - datetime.timedelta(days=MAX_AGE_DAYS)).isoformat()

    new = []
    for link, h in sorted(search().items(), key=lambda kv: kv[1]["date"], reverse=True):
        if link in seen or (h["date"] and h["date"] < cutoff) or key(h["title"]) in titles:
            continue
        url = resolve(link)
        if url is None:
            continue  # try again tomorrow rather than publish a Google redirect
        seen.add(link)
        if norm(url) in known:
            continue
        known.add(norm(url)); titles.add(key(h["title"]))
        new.append({"url": url, "outlet": h["outlet"], "date": h["date"], "lang": h["lang"],
                    "title": h["title"], "blurb": "",
                    "suggested": datetime.date.today().isoformat()})

    for a in new:
        print("NEW  %s  %-22s %s\n     %s" % (a["date"], a["outlet"][:22], a["title"], a["url"]))
    print("%d new article(s)" % len(new))

    if args.summary:
        lines = ["The daily press check found **%d new article(s)** about Biolyz.\n" % len(new)]
        for a in new:
            lines.append("- **%s** · %s · %s  \n  [%s](%s)" % (a["outlet"], a["date"], a["lang"], a["title"], a["url"]))
        lines += ["",
                  "### How to review",
                  "- **Publish:** merge this pull request. The articles appear on /blog, newest first.",
                  "- **Leave one out:** in `content/blog.json`, add `\"hidden\": true` to that article, then merge. "
                  "Please don't just close the pull request: closed suggestions are found again the next day.",
                  "- **Description:** each new card shows only the headline. To add the short line under it, "
                  "fill in `\"blurb\"` for that article.",
                  "- New outlets show their name as text on a grey tile until someone adds a logo.",
                  "",
                  "If more articles turn up before you merge, they are added to this same pull request."]
        open(args.summary, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write("new=%d\n" % len(new))
    if args.dry_run or not new:
        return  # nothing new: leave the file alone so no empty pull request opens
    data["articles"] = new + data["articles"]
    data["seen"] = sorted(seen)
    write(data)


def write(data):
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2); f.write("\n")


if __name__ == "__main__":
    main()
