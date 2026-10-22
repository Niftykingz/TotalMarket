"""SQLite store: the newsroom's single source of truth.

* Original evidence (source_documents) is stored separately from AI interpretations
  (facts, revisions, graphics).
* Evidence, revisions, fact checks, approvals, publications and the audit log are
  append-only: SQLite triggers abort any UPDATE or DELETE on them.
* One connection per thread (WAL mode) so the bounded worker pool can write safely.
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS stories (
  id INTEGER PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  category TEXT NOT NULL,
  priority TEXT,
  score REAL,
  reason TEXT,
  stage TEXT NOT NULL,
  demo INTEGER NOT NULL DEFAULT 0,
  source_url TEXT,
  dedupe_key TEXT NOT NULL,
  duplicate_of TEXT,
  current_revision TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_documents (
  id INTEGER PRIMARY KEY,
  story_id INTEGER REFERENCES stories(id),
  url TEXT NOT NULL,
  org TEXT NOT NULL,
  reliability TEXT NOT NULL,
  published_at TEXT,
  fetched_at TEXT NOT NULL,
  content TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  injection_flags TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS facts (
  id INTEGER PRIMARY KEY,
  story_id INTEGER NOT NULL REFERENCES stories(id),
  key TEXT NOT NULL,
  label TEXT NOT NULL,
  value TEXT NOT NULL,
  unit TEXT NOT NULL,
  as_of TEXT NOT NULL,
  doc_id INTEGER NOT NULL REFERENCES source_documents(id),
  excerpt TEXT NOT NULL,
  derivation TEXT,
  grp TEXT,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(story_id, key)
);

CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY,
  story_id INTEGER NOT NULL REFERENCES stories(id),
  agent TEXT NOT NULL,
  kind TEXT NOT NULL,
  status TEXT NOT NULL,             -- queued | running | done | failed | suspended | cancelled
  depends_on TEXT NOT NULL DEFAULT '[]',
  priority_rank INTEGER NOT NULL DEFAULT 2,
  attempts INTEGER NOT NULL DEFAULT 0,
  idem_key TEXT NOT NULL UNIQUE,
  input TEXT NOT NULL DEFAULT '{}',
  output TEXT,
  error TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  duration_ms INTEGER
);

CREATE TABLE IF NOT EXISTS revisions (
  id INTEGER PRIMARY KEY,
  story_id INTEGER NOT NULL REFERENCES stories(id),
  number INTEGER NOT NULL,
  content TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(story_id, number)
);

CREATE TABLE IF NOT EXISTS graphics (
  id INTEGER PRIMARY KEY,
  story_id INTEGER NOT NULL REFERENCES stories(id),
  attempt INTEGER NOT NULL,
  spec TEXT NOT NULL,
  file TEXT,
  sha256 TEXT,
  status TEXT NOT NULL,              -- draft | verified | rejected
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_checks (
  id INTEGER PRIMARY KEY,
  story_id INTEGER NOT NULL REFERENCES stories(id),
  target TEXT NOT NULL,              -- article | graphic
  subject_sha TEXT NOT NULL,         -- hash of the exact draft/graphic that was checked
  status TEXT NOT NULL,
  findings TEXT NOT NULL,
  checker TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS qa_reports (
  id INTEGER PRIMARY KEY,
  story_id INTEGER NOT NULL REFERENCES stories(id),
  revision_sha TEXT NOT NULL,
  outcome TEXT NOT NULL,
  findings TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
  id INTEGER PRIMARY KEY,
  story_id INTEGER NOT NULL REFERENCES stories(id),
  revision_sha TEXT NOT NULL,
  decision TEXT NOT NULL,            -- approve | reject | request_changes | invalidated
  actor TEXT NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS publications (
  id INTEGER PRIMARY KEY,
  story_id INTEGER NOT NULL REFERENCES stories(id),
  revision_sha TEXT NOT NULL UNIQUE,
  url TEXT NOT NULL,
  commit_sha TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS api_usage (
  id INTEGER PRIMARY KEY,
  task_id INTEGER,
  agent TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  prompt_tokens INTEGER NOT NULL,
  completion_tokens INTEGER NOT NULL,
  cost_inr REAL NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS errors (
  id INTEGER PRIMARY KEY,
  task_id INTEGER,
  story_id INTEGER,
  agent TEXT,
  attempt INTEGER,
  message TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS budget_changes (
  id INTEGER PRIMARY KEY,
  actor TEXT NOT NULL,
  daily_inr REAL NOT NULL,
  monthly_inr REAL NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  story_id INTEGER,
  detail TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks(status, priority_rank, id);
CREATE INDEX IF NOT EXISTS ix_audit_story ON audit_log(story_id, id);
"""

APPEND_ONLY = ("source_documents", "revisions", "fact_checks", "qa_reports", "approvals",
               "publications", "audit_log", "budget_changes")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class DB:
    def __init__(self, path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._write_lock = threading.RLock()
        c = self.conn()
        c.executescript(SCHEMA)
        for t in APPEND_ONLY:
            c.execute(f"CREATE TRIGGER IF NOT EXISTS {t}_no_update BEFORE UPDATE ON {t} "
                      f"BEGIN SELECT RAISE(ABORT, '{t} is append-only'); END;")
            c.execute(f"CREATE TRIGGER IF NOT EXISTS {t}_no_delete BEFORE DELETE ON {t} "
                      f"BEGIN SELECT RAISE(ABORT, '{t} is append-only'); END;")

    def conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "c", None)
        if c is None:
            c = sqlite3.connect(self.path, timeout=30, isolation_level=None, check_same_thread=False)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA foreign_keys = ON")
            c.execute("PRAGMA busy_timeout = 30000")
            if self.path != ":memory:":
                c.execute("PRAGMA journal_mode = WAL")
            self._local.c = c
        return c

    # small helpers --------------------------------------------------
    def x(self, sql, args=()):
        with self._write_lock:
            cur = self.conn().execute(sql, args)
            return cur.lastrowid

    def one(self, sql, args=()):
        r = self.conn().execute(sql, args).fetchone()
        return dict(r) if r else None

    def all(self, sql, args=()):
        return [dict(r) for r in self.conn().execute(sql, args).fetchall()]

    def tx(self):
        """`with db.tx():` runs statements atomically under the write lock."""
        db = self

        class _Tx:
            def __enter__(self):
                db._write_lock.acquire()
                db.conn().execute("BEGIN IMMEDIATE")
                return db

            def __exit__(self, et, ev, tb):
                try:
                    db.conn().execute("ROLLBACK" if et else "COMMIT")
                finally:
                    db._write_lock.release()
                return False
        return _Tx()

    def audit(self, actor, action, story_id=None, **detail):
        return self.x("INSERT INTO audit_log(ts, actor, action, story_id, detail) VALUES (?,?,?,?,?)",
                      (now(), actor, action, story_id, json.dumps(detail, ensure_ascii=False, default=str)))

    def error(self, message, task_id=None, story_id=None, agent=None, attempt=None):
        return self.x("INSERT INTO errors(task_id, story_id, agent, attempt, message, created_at) VALUES (?,?,?,?,?,?)",
                      (task_id, story_id, agent, attempt, str(message)[:2000], now()))

    def backup(self, dest):
        """Online backup to another file (safe while the newsroom runs)."""
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        out = sqlite3.connect(str(dest))
        with out:
            self.conn().backup(out)
        out.close()
        return str(dest)
