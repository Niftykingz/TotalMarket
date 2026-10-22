"""Orchestration engine: persistent task queue + bounded worker pool.

* Tasks live in SQLite with dependencies, priority, attempts and an idempotency key, so a
  crashed run can be resumed and a finished task is never redone.
* Independent tasks (e.g. Writer and Designer for the same story, or tasks of different
  stories) run in parallel, never more than `settings.concurrency` at once.
* Agent errors are retried up to `retry_limit` times, then the task fails and the Boss
  blocks the story. A budget cap suspends the task instead (no retry, no spend).
* The Boss reacts to every result on the coordinating thread, one at a time.
"""
import json
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

from . import config
from .agents.base import Agent
from .agents.designer import Designer
from .agents.fact_checker import FactChecker
from .agents.researcher import Researcher, mock as research_mock
from .agents.writer import Writer, mock as write_mock
from .boss import Boss
from .database import DB, now
from .models import ValidationError
from .providers import BudgetExceeded, MockProvider, get_provider

KIND_AGENT = {"research": Researcher, "write": Writer, "design": Designer, "check": FactChecker}
MockProvider.handlers.update({"researcher": research_mock, "writer": write_mock})


class Newsroom:
    def __init__(self, settings=None, root=None, out_dir=None, provider=None):
        self.settings = settings or config.load()
        self.root = Path(root or config.ROOT)
        self.out_dir = Path(out_dir or config.VAR)
        self.db = DB(self.settings.db())
        self.provider = provider or get_provider(self.settings, self.db)
        self.boss = Boss(self)
        self.agents = {k: cls(self) for k, cls in KIND_AGENT.items()}
        self.max_running = 0

    # ------------------------------------------------------------------ queue
    def enqueue(self, story_id, kind, inp, deps=(), rank=2, round_no=1):
        key = f"{story_id}:{kind}:{round_no}"
        self.db.x("INSERT OR IGNORE INTO tasks(story_id, agent, kind, status, depends_on, priority_rank, idem_key, input, created_at) "
                  "VALUES (?,?,?,?,?,?,?,?,?)", (story_id, KIND_AGENT[kind].name, kind, "queued", json.dumps(list(deps)),
                                                 rank, key, json.dumps(inp, ensure_ascii=False, default=str), now()))
        return self.db.one("SELECT id FROM tasks WHERE idem_key=?", (key,))["id"]

    def task(self, tid):
        t = self.db.one("SELECT * FROM tasks WHERE id=?", (tid,))
        t["input"] = json.loads(t["input"])
        t["depends_on"] = json.loads(t["depends_on"])
        t["output"] = json.loads(t["output"]) if t["output"] else None
        return t

    def dep_tasks(self, t):
        """Dependencies by kind, following the chain (check → write/design → research)."""
        out = {}
        stack = list(t["depends_on"])
        while stack:
            d = self.task(stack.pop())
            out.setdefault(d["kind"], d)
            stack += d["depends_on"]
        return out

    def _prepare(self, t):
        deps = self.dep_tasks(t)
        if t["kind"] == "write":
            t["input"]["quotes"] = (deps.get("research") or {}).get("output", {}).get("quotes", [])
        if t["kind"] == "check":
            t["input"]["draft"] = deps["write"]["output"]
            t["input"]["graphic"] = deps["design"]["output"]
        return t

    def ready(self):
        rows = self.db.all("SELECT id, depends_on FROM tasks WHERE status='queued' ORDER BY priority_rank, id")
        out = []
        for r in rows:
            deps = json.loads(r["depends_on"])
            st = [self.db.one("SELECT status FROM tasks WHERE id=?", (d,))["status"] for d in deps]
            if any(s in ("failed", "cancelled", "suspended") for s in st):
                self.db.x("UPDATE tasks SET status='cancelled', finished_at=? WHERE id=?", (now(), r["id"]))
                continue
            if all(s == "done" for s in st):
                out.append(r["id"])
        return out

    # ------------------------------------------------------------------ execution
    def _execute(self, tid):
        t = self._prepare(self.task(tid))
        agent: Agent = self.agents[t["kind"]]
        return agent.run(t)

    def run(self, max_seconds=300):
        """Run until the queue is empty. Returns the number of tasks completed."""
        done = 0
        running = {}
        deadline = time.monotonic() + max_seconds
        with ThreadPoolExecutor(max_workers=self.settings.concurrency, thread_name_prefix="agent") as pool:
            while time.monotonic() < deadline:
                for tid in self.ready():
                    if len(running) >= self.settings.concurrency:
                        break
                    if tid in running.values():
                        continue
                    self.db.x("UPDATE tasks SET status='running', attempts=attempts+1, started_at=? WHERE id=?", (now(), tid))
                    running[pool.submit(self._execute, tid)] = tid
                    self.max_running = max(self.max_running, len(running))
                if not running:
                    break
                finished, _ = wait(list(running), return_when=FIRST_COMPLETED)
                for fut in finished:
                    tid = running.pop(fut)
                    t = self.task(tid)
                    started = t["started_at"]
                    try:
                        out = fut.result()
                    except BudgetExceeded as ex:
                        self.db.x("UPDATE tasks SET status='suspended', error=?, attempts=attempts-1, finished_at=? WHERE id=?", (str(ex), now(), tid))
                        self.db.error(ex, tid, t["story_id"], t["agent"], t["attempts"])
                        self.boss.on_suspended(t, ex)
                        continue
                    except Exception as ex:  # agent failure: retry, then block
                        self.db.error(f"{type(ex).__name__}: {ex}", tid, t["story_id"], t["agent"], t["attempts"])
                        limit = self.settings.retry_limit
                        no_retry = type(ex).__name__ in ("MissingSource", "ToolNotPermitted", "ProviderNotApproved")
                        if t["attempts"] <= limit and not no_retry:
                            self.db.x("UPDATE tasks SET status='queued', error=? WHERE id=?", (str(ex), tid))
                            self.db.audit("orchestrator", "retry", t["story_id"], task=tid, attempt=t["attempts"], error=str(ex))
                        else:
                            self.db.x("UPDATE tasks SET status='failed', error=?, finished_at=? WHERE id=?", (str(ex), now(), tid))
                            self.boss.on_failed(self.task(tid), ex)
                        continue
                    ms = _ms(started)
                    self.db.x("UPDATE tasks SET status='done', output=?, error=NULL, finished_at=?, duration_ms=? WHERE id=?",
                              (json.dumps(out, ensure_ascii=False, default=str), now(), ms, tid))
                    done += 1
                    self.boss.on_done(self.task(tid), json.loads(json.dumps(out, default=str)))
        return done

    # ------------------------------------------------------------------ helpers
    def resume_suspended(self, story_id):
        """After the owner raises the budget: re-queue suspended tasks (and their cancelled dependants)."""
        from . import workflow
        from .models import Stage
        self.db.x("UPDATE tasks SET status='queued', error=NULL WHERE story_id=? AND status IN ('suspended','cancelled')", (story_id,))
        last = self.db.one("SELECT detail FROM audit_log WHERE story_id=? AND action='stage' AND detail LIKE '%\"to\": \"SUSPENDED\"%' "
                           "ORDER BY id DESC LIMIT 1", (story_id,))
        prev = json.loads(last["detail"])["frm"] if last else Stage.ASSIGNED.value
        workflow.move(self.db, story_id, prev, "owner", "budget raised; resumed")


def _ms(started):
    from datetime import datetime, timezone
    try:
        return int((datetime.now(timezone.utc) - datetime.fromisoformat(started)).total_seconds() * 1000)
    except Exception:
        return None
