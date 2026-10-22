"""Boss Agent: editor-in-chief.

Ranks and de-duplicates candidate stories, explains why each deserves coverage, assigns
specialist tasks with dependencies, reacts to results (including correction loops), and
prepares finished packages for the owner. It cannot bypass fact checking, budgets, the
logo policy, owner approval or the publish gate: those live in code it does not control.
"""
import html
import json
from datetime import datetime, timezone
from pathlib import Path

from . import approvals, workflow
from .database import now
from .models import PRIORITY_RANK, FactStatus, Priority, Stage, digest, slugify, validate, CANDIDATE
from .services import dedupe, sources

CATEGORY_IMPACT = {"policy": 25, "markets": 20, "commodities": 12, "global": 12, "startups": 10, "tech": 10}
KEYWORDS = {"rbi": 15, "repo": 10, "monetary policy": 10, "sebi": 12, "gdp": 10, "inflation": 10, "cpi": 8,
            "results": 8, "q2": 5, "ipo": 8, "listing": 6, "fii": 6, "sensex": 6, "nifty": 6, "budget": 10}
RELIABILITY = {"official": 30, "secondary": 15, "unknown": 0}
MAX_CORRECTIONS = 2


def _age_hours(published_at):
    try:
        t = datetime.fromisoformat(str(published_at).replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - t).total_seconds() / 3600)
    except ValueError:
        return 48.0


def score(c, now_override=None):
    """(score, priority, reasons[]) — deterministic and explainable."""
    why = []
    rel = RELIABILITY.get(c.get("reliability"), 0)
    why.append(f"{c.get('reliability')} source {c.get('source_org')} (+{rel})")
    cat = CATEGORY_IMPACT.get(c["category"], 5)
    why.append(f"{c['category']} impact (+{cat})")
    text = c["headline"].lower()
    kw = min(25, sum(v for k, v in KEYWORDS.items() if k in text))
    if kw:
        why.append(f"market-moving keywords (+{kw})")
    age = _age_hours(c.get("published_at")) if now_override is None else now_override
    fresh = max(0.0, 25 - age * 2)
    why.append(f"{age:.1f} h old (+{fresh:.0f} freshness)")
    val = 5 if c.get("instrument") else 0
    s = round(rel + cat + kw + fresh + val + float(c.get("importance") or 0), 1)
    if s >= 85 and c.get("reliability") == "official" and age < 2:
        pr = Priority.BREAKING
    elif s >= 65:
        pr = Priority.HIGH
    elif s >= 40:
        pr = Priority.NORMAL
    else:
        pr = Priority.LOW
    return s, pr, why


class Boss:
    name = "boss"

    def __init__(self, nr):
        self.nr, self.db = nr, nr.db

    # ------------------------------------------------------------------ intake
    def intake(self, candidates):
        """De-duplicate, rank and register candidates. Returns story ids in priority order."""
        made = []
        for c in candidates:
            validate(c, CANDIDATE, "candidate")
            rel = sources.reliability(c["source_url"], self.nr.settings.allowlist)
            c = dict(c, reliability=rel or "unknown")
            dup = dedupe.find_duplicate(c, self.db, self.nr.root)
            slug = slugify(("demo-" if c.get("demo") else "") + c["headline"])
            if self.db.one("SELECT 1 FROM stories WHERE slug=?", (slug,)):
                slug = f"{slug}-{digest(c)[:6]}"
            sid = self.db.x("INSERT INTO stories(slug, title, category, stage, demo, source_url, dedupe_key, created_at, updated_at) "
                            "VALUES (?,?,?,?,?,?,?,?,?)", (slug, c["headline"], c["category"], Stage.DISCOVERED.value,
                                                           int(bool(c.get("demo"))), dedupe.canonical_url(c["source_url"]),
                                                           dedupe.key(c["headline"]), now(), now()))
            self.db.audit(self.name, "discovered", sid, url=c["source_url"], org=c["source_org"],
                          published_at=c["published_at"], discovered_at=c["discovered_at"])
            if dup:
                self.db.x("UPDATE stories SET duplicate_of=? WHERE id=?", (dup[1], sid))
                workflow.move(self.db, sid, Stage.DUPLICATE, self.name, f"duplicate of {dup[1]} ({dup[0]}, similarity {dup[2]})")
                continue
            workflow.move(self.db, sid, Stage.DEDUPLICATED, self.name, "no duplicate in newsroom or on the site")
            s, pr, why = score(c)
            related = dedupe.related(c["headline"], self.nr.root)
            reason = "; ".join(why) + (f". Related site stories: {', '.join(related)}" if related else "")
            self.db.x("UPDATE stories SET score=?, priority=?, reason=? WHERE id=?", (s, pr.value, reason, sid))
            workflow.move(self.db, sid, Stage.PRIORITIZED, self.name, f"{pr.value} (score {s}): {reason}")
            made.append((PRIORITY_RANK[pr], -s, sid))
        made.sort()
        out = []
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        active = self.db.one("SELECT COUNT(*) n FROM stories WHERE substr(created_at,1,10)=? AND stage NOT IN "
                             "('DUPLICATE','SKIPPED','DISCOVERED','DEDUPLICATED','PRIORITIZED')", (today,))["n"]
        for _, _, sid in made:
            if active >= self.nr.settings.daily_story_limit:
                workflow.move(self.db, sid, Stage.SKIPPED, self.name, "daily story limit reached")
                continue
            active += 1
            out.append(sid)
        return out

    # ------------------------------------------------------------------ assignment
    def plan(self, sid, brief):
        """Assign specialists. brief: {event, org, documents, inject_error?}."""
        st = self.db.one("SELECT * FROM stories WHERE id=?", (sid,))
        rank = PRIORITY_RANK[Priority(st["priority"])]
        enabled = set(self.nr.settings.enabled_agents)
        nr = self.nr
        r = nr.enqueue(sid, "research", {"documents": brief.get("documents", []), "category": st["category"]}, rank=rank)
        w = nr.enqueue(sid, "write", {"event": brief.get("event", "generic"), "inject_error": brief.get("writer_error")}, deps=[r], rank=rank)
        g = nr.enqueue(sid, "design", {"event": brief.get("event", "generic"), "org": brief.get("org", ""),
                                       "inject_error": brief.get("inject_error")}, deps=[r], rank=rank)
        nr.enqueue(sid, "check", {}, deps=[w, g], rank=rank)
        plan = (f"Assign Researcher to verify the source documents; Writer to draft from the verified facts; "
                f"Designer to prepare an original graphic from the same facts (in parallel with the Writer); "
                f"Independent Fact Checker to verify the article and graphic.")
        skipped = [a for a in ("analyst", "seo", "developer", "qa") if a not in enabled]
        if skipped:
            plan += f" Not enabled in this phase: {', '.join(skipped)}."
        workflow.move(self.db, sid, Stage.ASSIGNED, self.name, plan)
        self.db.x("UPDATE stories SET reason=reason||? WHERE id=?", (" | Plan: " + plan, sid))
        return plan

    # ------------------------------------------------------------------ reactions
    def rounds(self, sid, kind):
        return self.db.one("SELECT COUNT(*) n FROM tasks WHERE story_id=? AND kind=?", (sid, kind))["n"]

    def on_done(self, task, out):
        sid, kind = task["story_id"], task["kind"]
        stage = self.db.one("SELECT stage FROM stories WHERE id=?", (sid,))["stage"]
        if kind == "research" and stage == Stage.ASSIGNED.value:
            workflow.move(self.db, sid, Stage.RESEARCHED, self.name, f"{len(out['facts'])} facts from {len(out['source_refs'])} documents")
        elif kind == "write" and stage == Stage.RESEARCHED.value:
            workflow.move(self.db, sid, Stage.DRAFTED, self.name, f"draft {out['word_count']} words")
        elif kind == "check":
            self._after_check(task, out)

    def _after_check(self, task, out):
        sid, db = task["story_id"], self.db
        a, g = FactStatus(out["article"]["status"]), FactStatus(out["graphic"]["status"])
        st = db.one("SELECT stage FROM stories WHERE id=?", (sid,))["stage"]
        deps = self.nr.dep_tasks(task)
        if a != FactStatus.VERIFIED:
            bad = [f for f in out["article"]["findings"] if f["status"] != "VERIFIED"]
            to_research = any(f["target"] == "researcher" for f in bad)
            if self.rounds(sid, "write") > MAX_CORRECTIONS:
                return workflow.move(db, sid, Stage.BLOCKED, self.name, f"article failed fact check {self.rounds(sid, 'write')} times: {bad[:3]}")
            if to_research:
                return workflow.move(db, sid, Stage.BLOCKED, self.name, f"missing or untraceable source; returned to Researcher: {bad[:3]}")
            w = self.nr.enqueue(sid, "write", dict(deps["write"]["input"], corrections=bad), deps=[deps["research"]["id"]],
                                rank=task["priority_rank"], round_no=self.rounds(sid, "write") + 1)
            self.nr.enqueue(sid, "check", {}, deps=[w, deps["design"]["id"]], rank=task["priority_rank"], round_no=self.rounds(sid, "check") + 1)
            return db.audit(self.name, "returned_to_writer", sid, findings=bad)
        if st == Stage.DRAFTED.value:
            workflow.move(db, sid, Stage.FACT_CHECKED, self.name, f"article VERIFIED ({out['article']['checked_numbers']} numbers)")
        if g != FactStatus.VERIFIED:
            bad = [f for f in out["graphic"]["findings"] if f["status"] != "VERIFIED"]
            if self.rounds(sid, "design") > MAX_CORRECTIONS:
                return workflow.move(db, sid, Stage.BLOCKED, self.name, f"graphic failed verification {self.rounds(sid, 'design')} times: {bad[:3]}")
            gd = self.nr.enqueue(sid, "design", dict(deps["design"]["input"], corrections=bad), deps=[deps["research"]["id"]],
                                 rank=task["priority_rank"], round_no=self.rounds(sid, "design") + 1)
            self.nr.enqueue(sid, "check", {}, deps=[deps["write"]["id"], gd], rank=task["priority_rank"], round_no=self.rounds(sid, "check") + 1)
            return db.audit(self.name, "returned_to_designer", sid, findings=bad)
        workflow.move(db, sid, Stage.GRAPHICS_READY, self.name, "graphic VERIFIED: numbers match evidence, no unapproved logos")
        draft, spec = deps["write"]["output"], deps["design"]["output"]
        content = {"draft": draft, "graphic": spec, "article_sha": digest(draft), "graphic_sha": digest(spec),
                   "graphic_file_sha256": spec.get("sha256"), "demo": bool(spec.get("demo"))}
        sha, num = approvals.create_revision(db, sid, content, self.name)
        workflow.move(db, sid, Stage.OWNER_REVIEW, self.name,
                      "Phase 1 preview: SEO, Developer and QA agents are not enabled, so this cannot be published")
        self.prepare_review(sid)

    def on_failed(self, task, err):
        from .agents.researcher import MissingSource
        why = f"{task['kind']} failed after {task['attempts']} attempts: {err}"
        if isinstance(err, MissingSource):
            why = f"missing source → Researcher: {err}"
        st = self.db.one("SELECT stage FROM stories WHERE id=?", (task["story_id"],))["stage"]
        if Stage.BLOCKED.value in {s.value for s in workflow.TRANSITIONS.get(Stage(st), set())}:
            workflow.move(self.db, task["story_id"], Stage.BLOCKED, self.name, why)
        else:
            self.db.audit(self.name, "task_failed", task["story_id"], reason=why)

    def on_suspended(self, task, err):
        st = self.db.one("SELECT stage FROM stories WHERE id=?", (task["story_id"],))["stage"]
        if Stage.SUSPENDED.value in {s.value for s in workflow.TRANSITIONS.get(Stage(st), set())}:
            workflow.move(self.db, task["story_id"], Stage.SUSPENDED, self.name, str(err))

    # ------------------------------------------------------------------ owner review package
    def prepare_review(self, sid):
        db = self.db
        st = db.one("SELECT * FROM stories WHERE id=?", (sid,))
        rev = approvals.current_revision(db, sid)
        c = rev["content"]
        d, g = c["draft"], c["graphic"]
        checks = db.all("SELECT target, status, findings, created_at FROM fact_checks WHERE story_id=? ORDER BY id", (sid,))
        docs = db.all("SELECT id, org, url, reliability, sha256, injection_flags FROM source_documents WHERE story_id=?", (sid,))
        gate = approvals.publish_gate(db, sid)
        out = Path(self.nr.out_dir) / "review"
        out.mkdir(parents=True, exist_ok=True)
        e = html.escape
        img = Path(g["file"])
        rel_img = Path("..") / img.relative_to(Path(self.nr.out_dir)) if img.is_relative_to(Path(self.nr.out_dir)) else img
        rows = "".join(
            f"<tr><td>{e(ch['target'])}</td><td class='s-{e(ch['status'])}'>{e(ch['status'])}</td><td><ul>"
            + "".join(f"<li><b class='s-{e(f['status'])}'>{e(f['status'])}</b> {e(f['claim'])}"
                      f"{' — ' + e(f['evidence']) if f['evidence'] else ''}{' — <i>' + e(f['issue']) + '</i>' if f['issue'] else ''}</li>"
                      for f in json.loads(ch["findings"]))
            + f"</ul></td><td>{e(ch['created_at'])}</td></tr>" for ch in checks)
        page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>Owner review · {e(st['title'])}</title>
<style>body{{font:16px/1.55 Inter,system-ui,sans-serif;background:#F8FAFC;color:#0F172A;margin:0;padding:16px}}main{{max-width:980px;margin:auto}}
.card{{background:#fff;border:1px solid #E2E8F0;border-radius:14px;padding:20px;margin:14px 0}}h1{{font-size:28px;line-height:1.2}}
img{{max-width:100%;height:auto;border-radius:10px;border:1px solid #E2E8F0}}table{{width:100%;border-collapse:collapse;font-size:14px}}
td,th{{border-top:1px solid #E2E8F0;padding:8px;vertical-align:top;text-align:left}}.s-VERIFIED{{color:#15803D}}.s-NEEDS_CORRECTION,.s-UNVERIFIED{{color:#B45309}}.s-REJECTED{{color:#DC2626}}
.demo{{background:#FEE2E2;color:#991B1B;padding:10px 14px;border-radius:10px;font-weight:600}}code{{background:#EEF2FF;padding:2px 6px;border-radius:6px;word-break:break-all}}
.gate li{{color:#B45309}}</style></head><body><main>
{"<p class='demo'>DEMONSTRATION — fictional test data. Not a real RBI decision. Never publishable.</p>" if st['demo'] else ""}
<p>Stage <b>{e(st['stage'])}</b> · Priority <b>{e(st['priority'] or '')}</b> · Revision {rev['number']} <code>{e(rev['sha256'])}</code></p>
<div class="card"><h1>{e(d['headline'])}</h1><p><b>{e(d['summary'])}</b></p>{''.join(f'<p>{e(p)}</p>' for p in d['body'])}
<h3>Key takeaways</h3><ul>{''.join(f'<li>{e(t)}</li>' for t in d['takeaways'])}</ul></div>
<div class="card"><h2>Graphic</h2><img src="{e(str(rel_img).replace(chr(92), '/'))}" alt="{e(d['short_headline'])}" width="1200" height="675">
<p>Template <b>{e(g['template'])}</b> · {e(g['method'])}{' · ' + e(g['logo_note']) if g.get('logo_note') else ''}</p></div>
<div class="card"><h2>Source evidence</h2><ul>{''.join(f"<li>#{x['id']} {e(x['org'])} ({e(x['reliability'])}) — {e(x['url'])} · sha256 <code>{e(x['sha256'][:16])}…</code>{' · ⚠ instruction-like text flagged' if json.loads(x['injection_flags']) else ''}</li>" for x in docs)}</ul></div>
<div class="card"><h2>Fact checks (newest last)</h2><table><tr><th>Target</th><th>Result</th><th>Findings</th><th>When (UTC)</th></tr>{rows}</table></div>
<div class="card"><h2>Why the Boss covered it</h2><p>{e(st['reason'] or '')}</p></div>
<div class="card gate"><h2>Publishing</h2><p>Approving records your decision for this exact revision. It cannot publish. Reasons publishing is blocked:</p><ul>{''.join(f'<li>{e(r)}</li>' for r in gate)}</ul>
<p>To decide: <code>py -m newsroom approve {sid} --revision {e(rev['sha256'])}</code> (or <code>reject</code> / <code>changes</code>), with <code>TM_NEWSROOM_OWNER_KEY</code> set.</p></div>
</main></body></html>"""
        f = out / f"{st['slug']}.html"
        f.write_text(page, encoding="utf-8")
        db.audit(self.name, "owner_review_ready", sid, page=str(f), revision=rev["sha256"])
        return f
