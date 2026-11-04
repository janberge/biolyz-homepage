"""Copy Biolyz's open jobs from Needle into content/jobs.json.

    python3 tools/jobs_sync.py              # updates the file if Needle changed
    python3 tools/jobs_sync.py --dry-run    # only prints what it would change

Runs daily from .github/workflows/jobs-sync.yml. build.py turns the file into
the Careers list, one page per job and one apply page per job, so adding,
editing or closing a job in Needle reaches the site with the next run.

Needle's public API, the same one jobs.needle.so reads:
  /public/organizations/biolyz/jobs   the published jobs
  /public/jobs/<uuid>                 one job: text and application form
Standard library only, so the workflow needs no install step.
"""
import argparse, json, os, re, sys, unicodedata, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "content", "jobs.json")
API = "https://api.needle.so/public"
ORG = "biolyz"


def get(path):
    req = urllib.request.Request(API + path, headers={"User-Agent": "biolyz-site-jobs-sync"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def slugify(title):
    s = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    old = json.load(open(DATA, encoding="utf-8")) if os.path.exists(DATA) else {"jobs": []}
    # A job keeps its address once it has one, even if the title changes later.
    slugs = {j["uuid"]: j["slug"] for j in old["jobs"]}

    jobs = []
    for item in get("/organizations/%s/jobs" % ORG)["jobs"]:
        d = get("/jobs/%s" % item["job_uuid"])
        if not d.get("is_published", True):
            continue
        title = d["title"].strip()
        slug = slugs.get(d["job_uuid"]) or slugify(title)
        taken = {j["slug"] for j in jobs}
        while slug in taken:
            slug += "-2"
        jobs.append({
            "uuid": d["job_uuid"],
            "slug": slug,
            "title": title,
            "location": (d.get("location") or "").strip(),
            "employment_type": (d.get("employment_type") or "").strip(),
            "start_date": (d.get("start_date") or "").strip(),
            "description_html": d.get("description_html") or "",
            "fields": [{k: f.get(k) for k in ("id", "label", "type", "required", "options")}
                       for f in d.get("application_form_fields") or []],
        })

    new = {"jobs": jobs}
    if new == {"jobs": old["jobs"]}:
        print("No change: %d job(s)" % len(jobs))
        changed = False
    else:
        before = {j["uuid"]: j.get("title", j["slug"]) for j in old["jobs"]}
        after = {j["uuid"]: j["title"] for j in jobs}
        for u in after.keys() - before.keys():
            print("ADDED    %s" % after[u])
        for u in before.keys() - after.keys():
            print("REMOVED  %s" % before[u])
        for u in after.keys() & before.keys():
            if next(j for j in jobs if j["uuid"] == u) != next(j for j in old["jobs"] if j["uuid"] == u):
                print("UPDATED  %s" % after[u])
        changed = True
        if not args.dry_run:
            with open(DATA, "w", encoding="utf-8") as f:
                json.dump(new, f, ensure_ascii=False, indent=2)
                f.write("\n")

    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write("changed=%s\n" % ("true" if changed else "false"))


if __name__ == "__main__":
    main()
