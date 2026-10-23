"""TotalMarket strict publishing pipeline: six stages, each saving a hashed artifact.

    1 DATA_COLLECTION    sources + figures with evidence, saved as-is (normalized)
    2 DATA_VERIFICATION  every figure checked against its own evidence; failures rejected
    3 GRAPHICS_GENERATION cover rendered from verified figures only; logo registry enforced
    4 ARTICLE_WRITING    post file written; every number must be a verified figure
    5 FINAL_QA           figures, labels and dates consistent across dataset, article, graphic
    6 PUBLISH            only via `python3 -m pipeline publish` after the gate passes

A stage runs only if every earlier stage's saved artifact still exists, matches its
recorded SHA-256 and has status PASS. A FAILED or INCOMPLETE stage blocks the article.
The gate (gate.py) re-validates the saved artifacts at build time, so build.py will not
render an enforced article without them — whatever starts the build.
"""
import hashlib
import json
import os
import re
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import numbers as N

ROOT = Path(__file__).resolve().parent.parent
PIPE = Path(__file__).resolve().parent
RUNS = PIPE / "runs"
LOG = PIPE / "log.jsonl"
IST = timezone(timedelta(hours=5, minutes=30))
STAGES = ["DATA_COLLECTION", "DATA_VERIFICATION", "GRAPHICS_GENERATION", "ARTICLE_WRITING", "FINAL_QA", "PUBLISH"]
GRAPHIC_FIELDS = ("coverHeadline", "stat", "statLabel", "coverContext", "coverDate", "symbol", "coverLabel", "palette", "flags", "companies", "figures", "chart")
TEXT_FIELDS = ("title", "dek", "why", "indiaImpact", "globalImpact", "seoTitle", "seoDescription", "coverAlt", "changeNote")
PLACEHOLDER = re.compile(r"lorem ipsum|placeholder|\bTBD\b|\bTODO\b|\bXX+\b|\bdemo(nstration)?\b|fictional|test data|\[insert|\{\{", re.I)
MAX_SOURCE_AGE_DAYS = 3


class StageError(Exception):
    pass


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    return sha_bytes(Path(p).read_bytes())


def canon(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def now():
    return datetime.now(IST).isoformat(timespec="seconds")


def log(event, **kw):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(canon(dict(ts=now(), event=event, **kw)) + "\n")


def parse_dt(s):
    if isinstance(s, datetime):
        return s if s.tzinfo else s.replace(tzinfo=IST)
    if isinstance(s, date):
        return datetime(s.year, s.month, s.day, tzinfo=IST)
    s = str(s or "").strip()
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=IST)
    except ValueError:
        raise StageError(f"not an ISO date/time: {s!r}")


# ------------------------------------------------------------------ run directory / manifest
class Run:
    def __init__(self, slug, root=ROOT):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,120}", slug or ""):
            raise StageError(f"bad slug {slug!r}")
        self.slug, self.root = slug, Path(root)
        self.dir = self.root / "pipeline" / "runs" / slug
        self.mpath = self.dir / "manifest.json"
        self.m = json.loads(self.mpath.read_text(encoding="utf-8")) if self.mpath.is_file() else {"slug": slug, "stages": {}}

    def save_manifest(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        self.mpath.write_text(json.dumps(self.m, ensure_ascii=False, indent=1), encoding="utf-8")

    def artifact(self, n, name):
        return self.dir / f"{n:02d}_{name.lower()}.json"

    def save(self, n, data):
        """Save a stage artifact; returns its sha256. Saved BEFORE the next stage may start."""
        self.dir.mkdir(parents=True, exist_ok=True)
        p = self.artifact(n, STAGES[n - 1])
        p.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        return sha_file(p)

    def load(self, n):
        p = self.artifact(n, STAGES[n - 1])
        return json.loads(p.read_text(encoding="utf-8"))

    def require(self, upto):
        """Every stage 1..upto must be PASS with an intact artifact, in order."""
        last = ""
        for i in range(1, upto + 1):
            st = self.m["stages"].get(STAGES[i - 1])
            if not st:
                raise StageError(f"{STAGES[i - 1]} has not run (INCOMPLETE)")
            if st["status"] != "PASS":
                raise StageError(f"{STAGES[i - 1]} is {st['status']}")
            p = self.artifact(i, STAGES[i - 1])
            if not p.is_file() or sha_file(p) != st["sha256"]:
                raise StageError(f"{STAGES[i - 1]} artifact missing or modified after it was saved")
            if st["finished"] < last:
                raise StageError(f"{STAGES[i - 1]} finished before an earlier stage (order violated)")
            last = st["finished"]

    def record(self, n, status, sha=None, errors=(), started=None):
        self.m["stages"][STAGES[n - 1]] = {"status": status, "sha256": sha, "errors": list(errors), "started": started or now(), "finished": now()}
        for later in STAGES[n:]:          # anything after a re-run stage is stale
            self.m["stages"].pop(later, None)
        self.save_manifest()
        log("stage", slug=self.slug, stage=STAGES[n - 1], status=status, errors=list(errors)[:5])


# ------------------------------------------------------------------ stage 1
def stage1_collect(job, edition_date):
    errs = []
    col = job.get("collection") or {}
    srcs = {s.get("id"): s for s in col.get("sources") or []}
    if not srcs:
        errs.append("no sources")
    today = parse_dt(edition_date)
    for sid, s in srcs.items():
        if not sid or not s.get("name"):
            errs.append(f"source {sid!r}: missing id/name")
        if not re.match(r"https://[^\s/]+\.[^\s/]+", str(s.get("url") or "")):
            errs.append(f"source {sid}: url must be https")
        try:
            pub = parse_dt(s.get("published"))
            if pub > today + timedelta(days=1):
                errs.append(f"source {sid}: published date is in the future")
        except StageError as ex:
            errs.append(f"source {sid}: {ex}")
    figs = col.get("figures") or []
    ids = set()
    for f in figs:
        fid = f.get("id")
        if not fid or fid in ids:
            errs.append(f"figure {fid!r}: missing or duplicate id")
        ids.add(fid)
        for k in ("label", "value", "as_of", "source", "evidence"):
            if f.get(k) in (None, ""):
                errs.append(f"figure {fid}: missing {k}")
        if f.get("source") and f["source"] not in srcs:
            errs.append(f"figure {fid}: unknown source {f['source']}")
    for ex in col.get("examples") or []:
        if not ex.get("id") or ex.get("value") in (None, "") or not ex.get("note"):
            errs.append(f"example {ex.get('id')!r}: needs id, value, note")
    if not figs:
        errs.append("no figures collected")
    return {"edition_date": str(edition_date)[:10], "sources": list(srcs.values()), "figures": figs, "examples": col.get("examples") or []}, errs


# ------------------------------------------------------------------ stage 2
def stage2_verify(collected):
    srcs = {s["id"]: s for s in collected["sources"]}
    ed = parse_dt(collected["edition_date"])
    verified, rejected = [], []
    by_label = {}
    for f in collected["figures"]:
        why = []
        if not N.in_evidence(f["value"], f["evidence"]):
            why.append("value does not appear in its evidence quote")
        for k in ("change", "pct"):
            if f.get(k) not in (None, "") and not N.in_evidence(f[k], f["evidence"]):
                why.append(f"{k} {f[k]} does not appear in its evidence quote")
        try:
            asof = parse_dt(f["as_of"])
            pub = parse_dt(srcs[f["source"]]["published"])
            if not f.get("historical") and (ed - asof).days > MAX_SOURCE_AGE_DAYS:
                why.append(f"as_of {f['as_of']} is more than {MAX_SOURCE_AGE_DAYS} days old (mark historical if intended)")
            if pub + timedelta(days=1) < asof:
                why.append("source was published before the figure's as-of date")
        except (StageError, KeyError) as ex:
            why.append(str(ex))
        by_label.setdefault((f["label"].strip().lower(), str(f["as_of"])[:10]), []).append(f)
        (rejected if why else verified).append(dict(f, reasons=why) if why else f)
    # two sources reporting different values for the same thing on the same date: reject both
    for key, fs in by_label.items():
        vals = {round(N.to_float(x["value"]), 6) for x in fs}
        if len(vals) > 1:
            for x in fs:
                if x in verified:
                    verified.remove(x)
                    rejected.append(dict(x, reasons=["conflicting values for the same label and date"]))
    key_rejected = [r["id"] for r in rejected if r.get("key")]
    errs = []
    if not verified:
        errs.append("no figure could be verified")
    if key_rejected:
        errs.append(f"key figures rejected: {key_rejected}")
    return {"verified": verified, "rejected": rejected, "examples": collected["examples"]}, errs


def stage1_source_first(job, edition_date, root=ROOT):
    """Refresh stale quotations from publisher text before verification."""
    collected, errors = stage1_collect(job, edition_date)
    cfg_path = Path(root) / "pipeline" / "config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.is_file() else {}
    if cfg.get("source_recovery", False) and not errors:
        from .source_audit import recover_evidence
        collected, unresolved = recover_evidence(collected)
        # No unsupported values may reach a graphic or article.
        errors.extend("SOURCE_RECOVERY: " + e for e in unresolved)
    return collected, errors


def stage2_with_remote_evidence(collected, root=ROOT):
    """Require original-source evidence BEFORE creating graphics or articles."""
    from . import source_audit
    cfg_path = Path(root) / "pipeline" / "config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.is_file() else {}
    verified, errors = stage2_verify(collected)
    if cfg.get("require_live_evidence", True):
        ok, source_errors = source_audit.audit(collected)
        if not ok:
            errors.extend("REMOTE_EVIDENCE: " + e for e in source_errors)
    return verified, errors


def _cands(ver, with_examples=False):
    figs = list(ver["verified"]) + (list(ver["examples"]) if with_examples else [])
    return N.candidates(figs)


# ------------------------------------------------------------------ stage 3
def logo_problems(companies, root):
    reg_path = Path(root) / "data" / "company-logos.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8")).get("companies", []) if reg_path.is_file() else []
    by_sym = {str(e.get("symbol", "")).lower(): e for e in reg}
    out = []
    for c in companies or []:
        t = str(c.get("ticker") or "").lower()
        for ext in ("png", "webp", "jpg", "jpeg", "svg"):
            f = Path(root) / "logos" / f"{t}.{ext}"
            if f.is_file():
                e = by_sym.get(t)
                if not e or e.get("status") != "verified" or e.get("rights_reviewed") is not True or not e.get("source_url"):
                    out.append(f"logo {f.name} is not an approved, rights-reviewed registry entry")
                elif e.get("sha256") != sha_file(f):
                    out.append(f"logo {f.name} bytes do not match the approved sha256")
    return out


def graphic_numbers(post, analysis):
    """Every number that will appear on the cover."""
    texts = [str(post.get(k) or "") for k in ("coverHeadline", "stat", "statLabel", "coverContext")]
    for f in analysis.get("figures") or []:
        for k in ("value", "change", "pct", "issue", "listing", "prev", "note", "label"):
            if f.get(k):
                texts.append(str(f[k]))
    ch = analysis.get("chart") or {}
    texts += [str(ch.get(k) or "") for k in ("title", "asOf", "period")]
    return " | ".join(texts)


def headline_matches_chart(post, analysis):
    """Numbers in the cover headline and stat must be figures shown in the chart itself."""
    figs = []
    for k, f in enumerate(analysis.get("figures") or []):
        for key in ("value", "change", "pct", "issue", "listing", "prev"):
            if f.get(key) not in (None, ""):
                figs.append({"id": f"c{k}{key}", "value": f[key]})
    cands = N.candidates(figs)
    bad = N.unsupported(" ".join(str(post.get(k) or "") for k in ("coverHeadline", "stat")), cands)
    return [b[0] for b in bad]


def stage3_graphic(job, ver, run, root, render=True):
    import covers, graphics_selector
    g = dict(job.get("graphic") or {})
    errs = []
    if not g.get("headline") and not g.get("coverHeadline"):
        errs.append("graphic needs a headline")
    post = {k: g[k] for k in GRAPHIC_FIELDS if k in g}
    post.update(id=job["slug"], title=g.get("headline") or g.get("coverHeadline"), category=job["article"].get("category", "markets"),
                publishedAt=job["article"].get("publishedAt") or now(), editionLabel=job["article"].get("editionLabel", ""),
                dek=job["article"].get("dek", ""))
    meta = json.loads((Path(root) / "data" / "meta.json").read_text(encoding="utf-8"))
    ipos = json.loads((Path(root) / "data" / "ipos.json").read_text(encoding="utf-8")).get("ipos", [])
    a = graphics_selector.analyze(post, meta, ipos)
    bad = N.unsupported(graphic_numbers(post, a), _cands(ver))   # examples never allowed on a graphic
    if bad:
        errs.append(f"graphic shows unverified numbers: {[b[0] for b in bad]}")
    errs += logo_problems(post.get("companies"), root)
    if a.get("data_required") and a["template"] == "illustration":
        errs.append("MISSING_DATA: " + (a.get("missing") or f"{a['event']} story needs a data-driven graphic") +
                    ". Collect the figures and retry; never publish this story with a generic illustration.")
    if a["template"] != "illustration":
        off = headline_matches_chart(post, a)
        if off:
            errs.append(f"cover headline/stat numbers not shown in the chart: {off}")
    out = {"fields": {k: post[k] for k in GRAPHIC_FIELDS if k in post}, "analysis": a,
           "headline": post["title"], "files": {}}
    if not errs and render:
        run.dir.mkdir(parents=True, exist_ok=True)
        wp, jp = run.dir / "cover.webp", run.dir / "cover.jpg"
        post["_analysis"] = a
        covers.render(post, str(wp), str(jp))
        from PIL import Image
        for p, size in ((wp, (1600, 900)), (jp, (1200, 675))):
            with Image.open(p) as im:
                im.verify()
            with Image.open(p) as im:
                if im.size != size:
                    errs.append(f"{p.name} is {im.size}, expected {size}")
        wp.unlink()  # keep the 1200×675 JPEG as the logged graphic; build renders the site copy
        out["files"] = {"cover.jpg": sha_file(jp)}
    return out, errs


# ------------------------------------------------------------------ stage 4
def article_text(post, body_only=False):
    parts = [] if body_only else [str(post.get(k) or "") for k in TEXT_FIELDS]
    parts += [str(x) for x in post.get("body") or []]
    hi = post.get("hi") or {}
    if hi:  # the Hindi edition must carry exactly the same verified numbers
        parts += [str(x) for x in hi.get("body") or []] if body_only else []
        if not body_only:
            parts += [str(hi.get(k) or "") for k in TEXT_FIELDS + ("tableTitle",)]
            hp = hi.get("piggy") or {}
            parts += [hp.get("happened", ""), hp.get("matters", "")] + list(hp.get("watch") or [])
    if not body_only:
        t = post.get("table") or {}
        for r in t.get("rows") or []:
            parts += [str(r.get(k) or "") for k in ("label", "value", "change", "note")]
        pg = post.get("piggy") or {}
        parts += [pg.get("happened", ""), pg.get("matters", "")] + list(pg.get("watch") or [])
    return "\n".join(parts)


def number_problems(post, ver):
    probs = []
    head = dict(post, body=[])
    bad = N.unsupported(article_text(head), _cands(ver))                     # headline, dek, SEO, table: verified only
    bad += N.unsupported(article_text(post, body_only=True), _cands(ver, True))  # body may use declared worked examples
    if bad:
        probs.append(f"unverified numbers in article: {sorted({b[0] for b in bad})}")
    for f in post.get("figures") or []:  # earnings-card figures must be verified, never examples
        bad = N.unsupported(" ".join(str(f.get(k) or "") for k in ("value", "change")), _cands(ver))
        if bad:
            probs.append(f"figures entry {f.get('label')}: unverified {[b[0] for b in bad]}")
    return probs


def stage4_article(job, ver, gfx, root, write=True):
    art = dict(job.get("article") or {})
    errs = []
    for k in ("title", "dek", "category", "body", "indiaImpact", "seoTitle", "seoDescription", "sources", "publishedAt", "edition", "editionLabel"):
        if not art.get(k):
            errs.append(f"article missing {k}")
    post = dict(art)
    post.update(gfx["fields"])                   # graphic fields come from the verified graphic stage, unchanged
    src_urls = {s["url"] for s in job["collection"]["sources"]}
    for s in post.get("sources") or []:
        if s.get("url") not in src_urls:
            errs.append(f"article cites a source not in the collected dataset: {s.get('url')}")
    errs += number_problems(post, ver)
    if len(str(post.get("seoTitle", ""))) > 70:
        errs.append("seoTitle longer than 70 characters")
    p = Path(root) / "data" / "posts" / f"{job['slug']}.json"
    out = {"post_path": str(p.relative_to(root)), "post": post}
    if not errs and write:
        p.write_text(json.dumps(post, ensure_ascii=False, indent=1), encoding="utf-8")
        out["post_sha256"] = sha_file(p)
    return out, errs


# ------------------------------------------------------------------ stage 5
def qa_checks(slug, ver, gfx, art_out, root, compare_render=True):
    errs = []
    p = Path(root) / art_out["post_path"]
    if not p.is_file():
        return ["post file missing"]
    if sha_file(p) != art_out.get("post_sha256"):
        errs.append("post file changed after ARTICLE_WRITING")
    post = json.loads(p.read_text(encoding="utf-8"))
    for k, v in gfx["fields"].items():
        if post.get(k) != v:
            errs.append(f"graphic field {k} in article differs from the verified graphic")
    errs += number_problems(post, ver)
    blob = article_text(post) + " " + " ".join(str(post.get(k) or "") for k in GRAPHIC_FIELDS if isinstance(post.get(k), str))
    if PLACEHOLDER.search(blob):
        errs.append(f"placeholder/demonstration text found: {PLACEHOLDER.search(blob).group(0)!r}")
    if post.get("demo"):
        errs.append("demo flag set")
    try:
        if str(parse_dt(post["publishedAt"]).date()) != str(post.get("edition", ""))[:10]:
            errs.append("publishedAt date does not match the edition date")
        if post.get("coverDate"):
            asofs = {str(f["as_of"])[:10] for f in ver["verified"]}
            if str(post["coverDate"])[:10] not in asofs and str(post["coverDate"])[:10] != str(post["edition"])[:10]:
                errs.append("coverDate is neither the edition date nor a verified as-of date")
    except (StageError, KeyError) as ex:
        errs.append(str(ex))
    run_dir = Path(root) / "pipeline" / "runs" / slug
    for name, h in (gfx.get("files") or {}).items():
        f = run_dir / name
        if not f.is_file() or sha_file(f) != h:
            errs.append(f"graphic {name} missing or changed")
        else:
            from PIL import Image
            try:
                with Image.open(f) as im:
                    im.verify()
            except Exception as ex:
                errs.append(f"graphic {name} is not a valid image: {ex}")
    if not gfx.get("files"):
        errs.append("no rendered graphic recorded")
    a0 = gfx.get("analysis") or {}
    if a0.get("template") not in (None, "illustration") and a0.get("figures"):
        figs = [{"id": f"g{k}{key}", "value": f[key]} for k, f in enumerate(a0["figures"]) for key in ("value", "change", "pct", "issue", "listing", "prev") if f.get(key) not in (None, "")]
        shown = {round(abs(N.to_float(f["value"])), 6) for f in figs if N.to_float(f["value"]) == N.to_float(f["value"])}
        said = {round(abs(v), 6) for _, v, _ in N.mentions(f'{post.get("title", "")} {post.get("dek", "")}')}
        if said and not (said & shown) and not any(N.supported(v, 2, N.candidates(figs)) for v in said):
            errs.append("headline/dek numbers do not match any figure in the graphic")
    if a0.get("data_required") and a0.get("template") == "illustration":
        errs.append("financial story without its data-driven graphic")
    if not compare_render:  # gate re-checks: the build pins the verified analysis instead (see gate.allowed)
        return errs
    # the cover the site will build must show the same verified analysis
    import graphics_selector
    meta = json.loads((Path(root) / "data" / "meta.json").read_text(encoding="utf-8"))
    ipos = json.loads((Path(root) / "data" / "ipos.json").read_text(encoding="utf-8")).get("ipos", [])
    a = graphics_selector.analyze(dict(post, id=slug), meta, ipos)
    if canon([a["template"], a["figures"]]) != canon([gfx["analysis"]["template"], gfx["analysis"]["figures"]]):
        bad = N.unsupported(graphic_numbers(post, a), _cands(ver))
        if bad or a["template"] != gfx["analysis"]["template"]:
            errs.append("final article would render a different graphic than the verified one")
    return errs


# ------------------------------------------------------------------ driver
def run_job(job_path, root=ROOT, render=True):
    """Run stages 1–5 for one article job file, resuming after the last PASS stage.
    If the job file changed since DATA_COLLECTION, everything restarts from stage 1."""
    job_path = Path(job_path)
    raw = job_path.read_bytes()
    job = json.loads(raw)
    run = Run(job["slug"], root)
    if run.m.get("job_sha256") != sha_bytes(raw):
        run.m = {"slug": job["slug"], "job": str(job_path.relative_to(root)) if job_path.is_relative_to(root) else str(job_path),
                 "job_sha256": sha_bytes(raw), "stages": {}}
        run.save_manifest()
    edition_date = str(job["article"].get("edition") or job["article"].get("publishedAt"))[:10]
    steps = [
        lambda: stage1_source_first(job, edition_date, root),
        lambda: stage2_with_remote_evidence(run.load(1), root),
        lambda: stage3_graphic(job, run.load(2), run, root, render=render),
        lambda: stage4_article(job, run.load(2), run.load(3), root),
        lambda: (None, qa_checks(job["slug"], run.load(2), run.load(3), run.load(4), root)),
    ]
    for i, step in enumerate(steps, 1):
        st = run.m["stages"].get(STAGES[i - 1])
        if st and st["status"] == "PASS":
            try:
                run.require(i)
                continue
            except StageError:
                pass
        started = now()
        try:
            run.require(i - 1)
            out, errs = step()
            if i == 5:
                out = {"checked": [STAGES[0], STAGES[1], STAGES[2], STAGES[3]], "errors": errs,
                       "post_sha256": run.load(4).get("post_sha256"), "graphic": run.load(3).get("files")}
        except StageError as ex:
            run.record(i, "FAILED", errors=[str(ex)], started=started)
            return run
        except Exception as ex:  # unexpected: record and stop; safe to retry later
            run.record(i, "FAILED", errors=[f"{type(ex).__name__}: {ex}", traceback.format_exc(limit=3)], started=started)
            return run
        sha = run.save(i, out)            # saved before the next stage begins
        run.record(i, "PASS" if not errs else "FAILED", sha=sha, errors=errs, started=started)
        if any(str(e).startswith("MISSING_DATA") for e in errs):
            run.m["retry"] = {"reason": "missing figures for the data graphic", "after": "collect the figures, update the job, run `python3 -m pipeline retry`"}
            run.save_manifest()
        if errs:
            if i == 4:  # never leave an unchecked article in data/posts
                pass
            return run
    return run


def status(run):
    st = run.m.get("stages", {})
    for s in STAGES[:5]:
        if s not in st:
            return f"INCOMPLETE at {s}"
        if st[s]["status"] != "PASS":
            return f"FAILED at {s}: {'; '.join(st[s]['errors'][:2])}"
    return "READY"
