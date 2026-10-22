"""Local demonstration with FICTIONAL data: "RBI cuts repo rate by 25 basis points".

Shows the full Phase 1 pipeline, including a designer mistake (wrong percentage) that the
Fact Checker rejects and returns for correction, a duplicate candidate being caught, and
the system stopping at owner review. Free: mock provider, no network, no publishing.
"""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import approvals, config
from .orchestrator import Newsroom

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "demo_rbi.json"


def load_fixture():
    fx = json.loads(FIXTURE.read_text(encoding="utf-8"))
    t = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for c in fx["candidates"]:
        for k in ("published_at", "discovered_at"):
            if c.get(k) == "NOW":
                c[k] = t
    return fx


def run(out_dir=None, fresh=True, echo=print):
    out = Path(out_dir or (config.VAR / "demo"))
    if fresh and out.exists():
        shutil.rmtree(out)
    settings = config.load(path=out / "none.json", db_path=str(out / "newsroom-demo.db"))
    nr = Newsroom(settings=settings, out_dir=out)
    fx = load_fixture()
    echo("TotalMarket newsroom · Phase 1 demo · FICTIONAL DATA · mock AI provider (₹0)")
    echo("-" * 78)
    ids = nr.boss.intake(fx["candidates"])
    for r in nr.db.all("SELECT id, title, stage, priority, score, duplicate_of FROM stories ORDER BY id"):
        extra = f"duplicate of {r['duplicate_of']}" if r["duplicate_of"] else f"{r['priority']} · score {r['score']}"
        echo(f"[Boss] #{r['id']} {r['title']!r}: {r['stage']} ({extra})")
    for sid in ids:
        st = nr.db.one("SELECT title, reason FROM stories WHERE id=?", (sid,))
        echo(f"[Boss] Why cover #{sid}: {st['reason']}")
        echo(f"[Boss] {nr.boss.plan(sid, fx['briefs'][st['title']])}")
    nr.run()
    for a in nr.db.all("SELECT ts, actor, action, story_id, detail FROM audit_log WHERE action IN "
                       "('stage','returned_to_designer','returned_to_writer','revision','owner_review_ready') ORDER BY id"):
        d = json.loads(a["detail"])
        if a["action"] == "stage" and d["to"] in ("DUPLICATE", "DEDUPLICATED", "PRIORITIZED", "ASSIGNED"):
            continue
        if a["action"] == "stage":
            echo(f"[{a['actor']}] #{a['story_id']} {d['frm']} → {d['to']}: {d['reason']}")
        elif a["action"] == "returned_to_designer":
            for f in d["findings"]:
                echo(f"[Fact Checker] #{a['story_id']} graphic {f['status']}: {f['claim']} — {f['issue']}")
            echo(f"[Boss] #{a['story_id']} graphic returned to Designer for correction")
        elif a["action"] == "returned_to_writer":
            echo(f"[Boss] #{a['story_id']} article returned to Writer: {len(d['findings'])} findings")
        elif a["action"] == "revision":
            echo(f"[Boss] #{a['story_id']} revision {d['number']} sealed: {d['sha']}")
        elif a["action"] == "owner_review_ready":
            echo(f"[Boss] #{a['story_id']} owner review page: {d['page']}")
    echo("-" * 78)
    for sid in ids:
        rev = approvals.current_revision(nr.db, sid)
        st = nr.db.one("SELECT stage FROM stories WHERE id=?", (sid,))
        echo(f"Story #{sid} stage: {st['stage']}")
        if rev:
            g = rev["content"]["graphic"]
            echo(f"  Graphic: {g['file']}")
            echo(f"  Logo: {g.get('logo_note') or 'none'}")
            gate = approvals.publish_gate(nr.db, sid)
            echo("  Publishing blocked because: " + "; ".join(gate))
    tasks = nr.db.all("SELECT kind, status, attempts FROM tasks ORDER BY id")
    echo(f"Tasks: {len(tasks)} ({', '.join(t['kind'] + ':' + t['status'] for t in tasks)}) · max parallel {nr.max_running}")
    cost = nr.db.one("SELECT COUNT(*) n, COALESCE(SUM(cost_inr),0) c FROM api_usage")
    echo(f"AI calls: {cost['n']} · cost ₹{cost['c']:.2f} (mock)")
    echo("Stopped before publishing. Nothing was deployed, merged or committed.")
    return nr, ids
