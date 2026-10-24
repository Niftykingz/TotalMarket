"""Publishing queue: the only path from job files to the live site.

Research runs (anywhere) commit job files to pipeline/inbox/ and data-file updates.
GitHub Actions (.github/workflows/publish-queue.yml) then runs this module, where the
remote source audit can reach publisher pages:

  1. every inbox job is run through stages 1–5 (resuming safely; a failed job never
     blocks the others);
  2. the gated publisher builds and pushes the site once (all READY jobs + data files);
  3. if the push is rejected because main moved, the checkout is reset to the new main
     and the whole step is repeated (idempotent: same jobs → same posts);
  4. published jobs move to pipeline/archive/; failed jobs stay in the inbox for retry;
  5. the live site is checked for every newly published article.
Exit code is non-zero when any job failed or the deployment check failed, so GitHub's
failure e-mail is the alert; the step summary lists what happened to each job.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from . import core

ROOT = core.ROOT
SITE = "https://totalmarket.co.in"


def sh(args, cwd=ROOT):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)[-3000:]


def inbox(root=ROOT):
    return sorted((Path(root) / "pipeline" / "inbox").glob("*.json"))


def run_jobs(root=ROOT):
    """{slug: status} after running stages 1–5 for every inbox job."""
    out = {}
    for p in inbox(root):
        try:
            slug = json.loads(p.read_text(encoding="utf-8"))["slug"]
            run = core.run_job(p.resolve(), root)
            out[slug] = core.status(run)
        except Exception as ex:  # a broken job file must not stop the queue
            out[p.stem] = f"FAILED: unreadable job ({type(ex).__name__}: {ex})"
            core.log("queue_job_error", job=p.name, error=str(ex))
    return out


def archive_published(root=ROOT):
    moved = []
    arc = Path(root) / "pipeline" / "archive"
    for p in inbox(root):
        slug = json.loads(p.read_text(encoding="utf-8"))["slug"]
        run = core.Run(slug, root)
        st = run.m.get("stages", {}).get("PUBLISH", {})
        if st.get("status") == "PASS":
            arc.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(arc / p.name))
            moved.append(slug)
    return moved


def live_check(slugs, timeout_s=600, opener=None):
    """Wait until each published article is served by the live site."""
    opener = opener or urllib.request.urlopen
    pending = {s: f"{SITE}/news/{s}/" for s in slugs}
    deadline = time.time() + timeout_s
    while pending and time.time() < deadline:
        for s, url in list(pending.items()):
            try:
                with opener(urllib.request.Request(url + f"?v={int(time.time())}", headers={"User-Agent": "TotalMarketDeployCheck/1.0"}), timeout=15) as r:
                    if r.status == 200 and s.encode() in r.read(400_000):
                        pending.pop(s)
            except Exception:
                pass
        if pending:
            time.sleep(20)
    return sorted(pending)


def main(publish=True, root=ROOT):
    from .__main__ import cmd_publish
    summary = []
    for attempt in range(1, 4):
        statuses = run_jobs(root)
        for slug, st in statuses.items():
            print(f"{slug}: {st}")
        if not publish:
            return 0 if all(s == "READY" for s in statuses.values()) else 1
        n = sum(1 for s in statuses.values() if s == "READY")
        rc = cmd_publish(False, root, message=f"Publish queue: {n} verified articles")
        if rc == 0:
            break
        if rc == 3 and attempt < 3:  # main moved under us: start again from the new main
            print(f"push rejected (attempt {attempt}); resetting to origin/main and retrying")
            sh(["git", "fetch", "-q", "origin", "main"], root)
            sh(["git", "reset", "-q", "--hard", "origin/main"], root)
            continue
        summary.append(f"PUBLISH FAILED (code {rc})")
        _summary(statuses, [], [], summary)
        return 2
    moved = archive_published(root)
    if moved:
        git = ["git", "-c", "user.name=TotalMarket Bot", "-c", "user.email=noreply@anthropic.com"]
        sh(["git", "add", "-A", "pipeline"], root)
        if sh(git + ["commit", "-q", "-m", f"Publish queue: archive {len(moved)} published jobs"], root)[0] == 0:
            for _ in range(3):
                if sh(["git", "push", "-q", "origin", "HEAD"], root)[0] == 0:
                    break
                sh(["git", "pull", "-q", "--rebase", "origin", "main"], root)
    missing = live_check(moved) if moved and os.environ.get("TM_SKIP_LIVE_CHECK") != "1" else []
    try:  # read by the workflow's Telegram step (not committed)
        Path(root, "pipeline", "last_queue.json").write_text(json.dumps({"published": [s for s in moved if s not in missing]}), encoding="utf-8")
    except OSError:
        pass
    _summary(statuses, moved, missing, summary)
    failed = [s for s, st in statuses.items() if st != "READY"]
    core.log("queue", published=moved, failed=failed, not_live=missing)
    return 1 if failed or missing else 0


def _summary(statuses, moved, missing, extra):
    lines = ["## TotalMarket publish queue", ""]
    for slug, st in statuses.items():
        mark = "✅ published" if slug in moved and slug not in missing else ("⚠️ published, not yet live" if slug in missing else ("✅ ready" if st == "READY" else "❌ " + st))
        lines.append(f"- `{slug}`: {mark}")
    lines += [""] + extra
    text = "\n".join(lines)
    print(text)
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    sys.exit(main())
