"""TotalMarket strict pipeline CLI.

  python3 -m pipeline run pipeline/inbox/<slug>.json     stages 1–5 for one article (resumes safely)
  python3 -m pipeline retry                              re-run every inbox job that is not READY
  python3 -m pipeline status                             stage status of every inbox job
  python3 -m pipeline publish --dry-run                  gate + build into a temp folder; no git
  python3 -m pipeline publish                            gate + build + tests + commit + push (the ONLY publish entry point)
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import core, gate  # noqa: E402

ROOT = core.ROOT
sys.path.insert(0, str(ROOT))


def jobs(root=ROOT):
    return sorted((Path(root) / "pipeline" / "inbox").glob("*.json"))


def cmd_run(paths, root=ROOT):
    bad = 0
    for p in paths:
        run = core.run_job(Path(p).resolve(), root)
        s = core.status(run)
        print(f"{run.slug}: {s}")
        bad += s != "READY"
    return 1 if bad else 0


def cmd_check(paths, root=ROOT):
    """Offline pre-check for research runs that cannot reach publisher pages: stages 1–5 in a
    throw-away copy of the site data. The remote source audit is skipped HERE ONLY; nothing is
    written to the repository and nothing can be published. The publish queue on GitHub runs
    every stage again with the remote audit before anything goes live."""
    tmp = Path(tempfile.mkdtemp(prefix="tm-check-"))
    for d in ("data", "logos"):
        if (root / d).is_dir():
            shutil.copytree(root / d, tmp / d)
    (tmp / "pipeline").mkdir()
    cfg = json.loads((root / "pipeline" / "config.json").read_text(encoding="utf-8"))
    cfg["require_live_evidence"] = False
    (tmp / "pipeline" / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    log, core.LOG = core.LOG, tmp / "pipeline" / "log.jsonl"
    bad = 0
    try:
        for p in paths:
            run = core.run_job(Path(p).resolve(), tmp)
            s = core.status(run)
            print(f"{run.slug}: {s} (offline pre-check; remote source audit runs in the publish queue)")
            if s == "READY":
                print(f"  cover preview: {run.dir / 'cover.jpg'}")
            bad += s != "READY"
    finally:
        core.LOG = log
    return 1 if bad else 0


def cmd_status(root=ROOT):
    for p in jobs(root):
        slug = json.loads(p.read_text(encoding="utf-8"))["slug"]
        print(f"{slug}: {core.status(core.Run(slug, root))}")
    return 0


def sh(args, cwd, env=None):
    r = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)[-4000:]


def built_checks(out_dir, results):
    """After the build: allowed posts have a page and a cover; blocked ones have no page."""
    errs = []
    for slug, ok, why in results:
        page = Path(out_dir) / "news" / slug / "index.html"
        if ok and not page.is_file():
            errs.append(f"{slug}: passed the gate but no page was built")
        if not ok and page.exists():
            errs.append(f"{slug}: BLOCKED but a page was built")
        if ok and page.is_file():
            html = page.read_text(encoding="utf-8")
            import re
            m = re.search(r'/covers/([^"\s]+?\.webp)', html)
            if not m or not (Path(out_dir) / "covers" / m.group(1)).is_file():
                errs.append(f"{slug}: cover image missing from the built page")
    return errs


def cmd_publish(dry_run, root=ROOT, message=None, run_tests=True):
    root = Path(root)
    results = gate.check_all(root)
    blocked = [(s, w) for s, ok, w in results if not ok]
    ready = [s for s, ok, w in results if ok and w == "pipeline PASS"]
    for s, w in blocked:
        print(f"BLOCKED {s}: {w}")
    core.log("publish_gate", dry_run=dry_run, ready=ready, blocked=blocked)
    env = dict(os.environ)
    if dry_run:
        tmp = Path(tempfile.mkdtemp(prefix="tm-dryrun-"))
        if (root / "docs" / "covers").is_dir():
            shutil.copytree(root / "docs" / "covers", tmp / "covers")
        env["TM_BUILD_OUT"] = str(tmp)
        out_dir = tmp
    else:
        out_dir = root / "docs"
    rc, out = sh([sys.executable, "build.py"], root, env)
    print(out.strip().splitlines()[-1] if out.strip() else "")
    if rc != 0:
        core.log("publish", ok=False, stage="build", output=out[-1500:])
        print("PUBLISH FAILED: build error\n" + out[-1500:])
        return 2
    errs = built_checks(out_dir, results)
    if errs:
        core.log("publish", ok=False, stage="built_checks", errors=errs)
        print("PUBLISH FAILED:\n  " + "\n  ".join(errs))
        return 2
    if run_tests and not dry_run:
        rc, out = sh([sys.executable, "-W", "ignore", "-m", "unittest", "discover", "-s", "tests"], root)
        if rc != 0:
            core.log("publish", ok=False, stage="tests", output=out[-1500:])
            print("PUBLISH FAILED: tests\n" + out[-1500:])
            return 2
    if dry_run:
        core.log("publish", ok=True, dry_run=True, ready=ready, blocked=[b[0] for b in blocked], out=str(out_dir))
        print(f"DRY RUN OK: {len(ready)} pipeline articles would publish, {len(blocked)} blocked; output in {out_dir}")
        return 0
    msg = message or f"Publish via pipeline: {len(ready)} verified articles"
    trailer = "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01EepqV255MWYbzjUN28a3RF"
    git = ["git", "-c", "user.name=TotalMarket Bot", "-c", "user.email=noreply@anthropic.com"]
    sh(["git", "checkout", "--", "__pycache__", "tests/__pycache__"], root)
    sh(["git", "add", "-A", "data", "docs", "pipeline"], root)
    rc, out = sh(git + ["commit", "-q", "-m", msg + trailer], root)
    if rc != 0 and "nothing to commit" not in out:
        core.log("publish", ok=False, stage="commit", output=out)
        print("PUBLISH FAILED: commit\n" + out)
        return 2
    # A different workflow or editor may advance main while this run builds.
    # Rebase our verified output commit onto the current remote before pushing.
    # Never force-push; fail safely on conflicting edits.
    rc, out = sh(["git", "fetch", "origin", "main"], root)
    if rc == 0:
        rc, out = sh(["git", "-c", "user.name=TotalMarket Bot",
                      "-c", "user.email=bot@totalmarket.co.in",
                      "rebase", "origin/main"], root)
        if rc != 0:
            sh(["git", "rebase", "--abort"], root)
            core.log("publish", ok=False, stage="rebase", output=out)
            print("PUBLISH FAILED: concurrent edits conflict with verified output; manual review required\n" + out)
            return 3
    else:
        core.log("publish", ok=False, stage="fetch", output=out)
        print("PUBLISH FAILED: cannot fetch latest main\n" + out)
        return 3
    rc, out = sh(["git", "push", "-q", "origin", "HEAD:main"], root)
    if rc != 0:
        core.log("publish", ok=False, stage="push", output=out)
        print("PUBLISH FAILED: main advanced again; retry publishing from latest main\n" + out)
        return 3
    _, commit = sh(["git", "rev-parse", "HEAD"], root)
    commit = commit.strip()
    for slug in ready:
        run = core.Run(slug, root)
        if run.m["stages"].get("PUBLISH", {}).get("status") == "PASS" and run.load(6).get("post_sha256") == run.load(4).get("post_sha256"):
            continue
        sha = run.save(6, {"commit": commit, "url": f"https://totalmarket.co.in/news/{slug}/", "post_sha256": run.load(4).get("post_sha256")})
        run.record(6, "PASS", sha=sha)
    core.log("publish", ok=True, commit=commit, ready=ready, blocked=[b[0] for b in blocked])
    sh(["git", "add", "-A", "pipeline"], root)
    if sh(git + ["commit", "-q", "-m", "Pipeline publish log" + trailer], root)[0] == 0:
        sh(["git", "push", "-q", "origin", "HEAD"], root)
    print(f"PUBLISHED {commit[:7]}: {len(ready)} pipeline articles; {len(blocked)} blocked")
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("jobs", nargs="+")
    sub.add_parser("retry")
    sub.add_parser("status")
    pb = sub.add_parser("publish"); pb.add_argument("--dry-run", action="store_true"); pb.add_argument("-m", "--message")
    ck = sub.add_parser("check"); ck.add_argument("jobs", nargs="+")
    sub.add_parser("queue")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        return cmd_run(a.jobs)
    if a.cmd == "retry":
        todo = [p for p in jobs() if core.status(core.Run(json.loads(p.read_text(encoding="utf-8"))["slug"])) != "READY"]
        return cmd_run(todo) if todo else 0
    if a.cmd == "status":
        return cmd_status()
    if a.cmd == "check":
        return cmd_check(a.jobs)
    if a.cmd == "queue":
        from pipeline import queue
        return queue.main()
    if os.environ.get("TM_PIPELINE_OFFLINE") == "1":
        print("REFUSED: publishing is disabled in offline mode")
        return 4
    return cmd_publish(a.dry_run, message=a.message)


if __name__ == "__main__":
    sys.exit(main())
