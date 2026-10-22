"""Command line for the newsroom.

  py -m newsroom demo                         run the fictional RBI demo (fresh database)
  py -m newsroom status [--db PATH]           stories, stages and tasks
  py -m newsroom approve ID --revision SHA    owner approval (needs TM_NEWSROOM_OWNER_KEY)
  py -m newsroom reject  ID --revision SHA [--note TEXT]
  py -m newsroom changes ID --revision SHA --note TEXT
  py -m newsroom publish ID                   shows why publishing is refused (always, in Phase 1)
  py -m newsroom backup DEST                  online copy of the database
"""
import argparse
import getpass
import os
import sys
from pathlib import Path

from . import approvals, config, demo
from .database import DB


def _db(args):
    p = args.db or str(config.VAR / "demo" / "newsroom-demo.db")
    if not Path(p).is_file():
        sys.exit(f"no database at {p}; run `py -m newsroom demo` first")
    return DB(p)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles
    ap = argparse.ArgumentParser(prog="newsroom")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo")
    for name in ("status", "publish", "backup", "approve", "reject", "changes"):
        sp = sub.add_parser(name)
        sp.add_argument("--db")
        if name in ("publish", "approve", "reject", "changes"):
            sp.add_argument("story", type=int)
        if name in ("approve", "reject", "changes"):
            sp.add_argument("--revision", required=True)
            sp.add_argument("--note", default="")
        if name == "backup":
            sp.add_argument("dest")
    a = ap.parse_args(argv)
    if a.cmd == "demo":
        demo.run()
        return 0
    db = _db(a)
    if a.cmd == "status":
        for r in db.all("SELECT id, stage, priority, title, current_revision FROM stories ORDER BY id"):
            print(f"#{r['id']:<3} {r['stage']:<15} {str(r['priority'] or ''):<9} {r['title']}  rev={str(r['current_revision'] or '')[:12]}")
        for t in db.all("SELECT id, story_id, kind, status, attempts, duration_ms FROM tasks ORDER BY id"):
            print(f"   task {t['id']:<3} story #{t['story_id']} {t['kind']:<8} {t['status']:<9} attempts={t['attempts']} {t['duration_ms'] or 0} ms")
        return 0
    if a.cmd == "backup":
        print(db.backup(a.dest))
        return 0
    if a.cmd == "publish":
        try:
            approvals.publish(db, a.story)
        except approvals.PublishRefused as ex:
            print("Publishing refused:", ex)
            return 2
    key = os.environ.get("TM_NEWSROOM_OWNER_KEY_INPUT") or getpass.getpass("Owner key: ")
    decision = {"approve": "approve", "reject": "reject", "changes": "request_changes"}[a.cmd]
    try:
        stage = approvals.decide(db, a.story, decision, key, a.revision, a.note)
    except PermissionError as ex:
        print("Refused:", ex)
        return 2
    print(f"Recorded {decision} for story #{a.story} revision {a.revision[:12]}… → {stage.value}")
    print("Publishing still blocked:", "; ".join(approvals.publish_gate(db, a.story)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
