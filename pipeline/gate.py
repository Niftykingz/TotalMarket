"""Publishing gate. build.py calls `allowed()` for every post; publish calls `check_all()`.

An enforced post (published or updated at/after `enforce_from` in pipeline/config.json) is
rendered only if its run manifest shows stages 1–5 PASS in order, every saved artifact is
intact (SHA-256), the post file is byte-identical to what ARTICLE_WRITING saved, and the
saved artifacts still pass re-validation (verification and QA are re-run here from the
saved files, so a hand-edited manifest cannot unlock publishing).
"""
import json
from pathlib import Path

from . import core

CONFIG = core.PIPE / "config.json"


def config(root=core.ROOT):
    p = Path(root) / "pipeline" / "config.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {"enforce_from": None}


def enforced(p, cfg):
    start = cfg.get("enforce_from")
    if not start:
        return False
    t0 = core.parse_dt(start)
    for k in ("publishedAt", "updatedAt"):
        if p.get(k):
            try:
                if core.parse_dt(p[k]) >= t0:
                    return True
            except core.StageError:
                return True  # unparseable dates are treated as new and must pass
    return False


def verify_post(slug, root=core.ROOT):
    """'' if the post may be published, else the reason it is blocked."""
    root = Path(root)
    try:
        run = core.Run(slug, root)
    except core.StageError as ex:
        return str(ex)
    if not run.mpath.is_file():
        return "no pipeline run for this article"
    try:
        run.require(5)
        art = run.load(4)
        post_file = root / art["post_path"]
        if core.sha_file(post_file) != art.get("post_sha256"):
            return "post file differs from the version that passed ARTICLE_WRITING"
        collected = run.load(1)
        ver, errs = core.stage2_verify(collected)            # re-run verification on the saved dataset
        if errs or core.canon(ver["verified"]) != core.canon(run.load(2)["verified"]):
            return "saved verification no longer reproduces"
        errs = core.qa_checks(slug, ver, run.load(3), art, root, compare_render=False)   # re-run final QA on the saved artifacts
        if errs:
            return "QA re-check failed: " + "; ".join(errs[:3])
    except core.StageError as ex:
        return str(ex)
    except Exception as ex:
        return f"{type(ex).__name__}: {ex}"
    return ""


def allowed(p, root=core.ROOT):
    """(ok, reason). For a passing enforced post, pins the verified graphic analysis onto the
    post (p["_analysis"]) so the site renders exactly the graphic that passed, even if
    market data files change later."""
    cfg = config(root)
    if not enforced(p, cfg):
        return True, "legacy (before enforcement)"
    why = verify_post(p["id"], root)
    if not why:
        a = core.Run(p["id"], root).load(3)["analysis"]
        p["_analysis"] = a
    return (not why), why or "pipeline PASS"


def check_all(root=core.ROOT):
    """[(slug, ok, reason)] for every post file."""
    out = []
    for f in sorted((Path(root) / "data" / "posts").glob("*.json")):
        p = json.loads(f.read_text(encoding="utf-8"))
        p["id"] = f.stem
        ok, why = allowed(p, root)
        out.append((f.stem, ok, why))
    return out
