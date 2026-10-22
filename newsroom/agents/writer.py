"""Content Writer Agent: original, attributed article built only from stored evidence."""
import re

import tmdate

from ..models import DRAFT
from .base import Agent


class Writer(Agent):
    name = "writer"
    title = "Content Writer Agent"
    role = "Write accurate, original, attributed financial journalism from verified evidence only."
    tools = frozenset({"llm", "db_read"})
    output_schema = DRAFT

    def execute(self, task):
        db, sid = self.ctx.db, task["story_id"]
        self.use("db_read")
        st = db.one("SELECT * FROM stories WHERE id=?", (sid,))
        facts = db.all("SELECT key, label, value, unit, as_of, doc_id, excerpt FROM facts WHERE story_id=? ORDER BY id", (sid,))
        docs = db.all("SELECT id, org, url, reliability FROM source_documents WHERE story_id=? ORDER BY id", (sid,))
        quotes = task["input"].get("quotes") or []
        payload = {"title_hint": st["title"], "category": st["category"], "demo": bool(st["demo"]),
                   "event": task["input"].get("event", "generic"), "facts": facts, "quotes": quotes,
                   "sources": docs, "corrections": task["input"].get("corrections") or [],
                   "inject_error": task["input"].get("inject_error")}
        return self.ask_model(payload, task_id=task["id"])


# ------------------------------------------------------------------ deterministic mock
def _f(facts, key):
    for f in facts:
        if f["key"] == key:
            return f
    return None


def _pct(f):
    return f"{f['value']}%"


def _words(paras):
    return sum(len(p.split()) for p in paras)


def mock(p):
    facts, quotes, src = p["facts"], p["quotes"], p["sources"]
    org = src[0]["org"] if src else "the source"
    refs = [d["id"] for d in src]
    if p["event"] == "policy_rate" and _f(facts, "repo_old") and _f(facts, "repo_new"):
        old, new = _f(facts, "repo_old"), _f(facts, "repo_new")
        bps = round((float(new["value"]) - float(old["value"])) * 100)
        rel = (float(new["value"]) - float(old["value"])) / float(old["value"]) * 100
        if p.get("inject_error") == "writer_pct":
            rel = rel * 1.2
        verb = "cuts" if bps < 0 else "raises"
        day = _f(facts, "decision_date")
        when = f" on {tmdate.fmt(day['value'], '%-d %B %Y')}" if day else ""
        vf, va = _f(facts, "votes_for"), _f(facts, "votes_against")
        headline = f"RBI {verb} repo rate by {abs(bps)} basis points to {_pct(new)}"
        body = []
        if p["demo"]:
            body.append("DEMONSTRATION ONLY: this article is fictional test data produced by the TotalMarket newsroom "
                        "system. It does not describe a real Reserve Bank of India decision.")
        body.append(f"The Reserve Bank of India's Monetary Policy Committee {'cut' if bps < 0 else 'raised'} the repo rate by "
                    f"{abs(bps)} basis points to {_pct(new)} from {_pct(old)}{when}, according to {org}.")
        if vf and va:
            body.append(f"The decision was taken by a majority, with {vf['value']} members voting in favour and "
                        f"{va['value']} against, the statement said.")
        body.append(f"The change lowers the policy rate by {abs(rel):.2f}% in relative terms. The repo rate is the rate at "
                    "which the central bank lends short-term funds to banks, so it acts as a reference point for "
                    "borrowing costs across the economy." if bps < 0 else
                    f"The change raises the policy rate by {abs(rel):.2f}% in relative terms.")
        if quotes:
            q = quotes[0]
            body.append(f"“{q['text']}”, {q['speaker']} said in the statement.")
        body.append("How quickly a policy rate change reaches loan and deposit rates depends on individual banks and on "
                    "liquidity conditions; the statement does not say when lenders will adjust their rates.")
        body.append(f"Source: {org} policy statement. TotalMarket will update this story if the official text is revised.")
        takeaways = [f"Repo rate {_pct(old)} → {_pct(new)} ({'-' if bps < 0 else '+'}{abs(bps)} bps)",
                     "Decision by majority vote of the MPC" if vf else "MPC decision",
                     "Effect on loan rates depends on banks' transmission"]
        claims = [{"text": f"repo rate {_pct(old)} to {_pct(new)}", "fact_keys": ["repo_old", "repo_new"]},
                  {"text": f"{abs(bps)} basis points", "fact_keys": ["repo_old", "repo_new"]}]
        brief = "Original rate-step graphic: old vs new repo rate, change in bps, institution name as text, no logo."
        short = f"RBI {verb} repo rate to {_pct(new)}"
        summary = (f"The RBI's MPC {'cut' if bps < 0 else 'raised'} the repo rate by {abs(bps)} basis points to {_pct(new)}."
                   + (" Fictional demonstration story." if p["demo"] else ""))
        entities = ["Reserve Bank of India", "Monetary Policy Committee", "repo rate"]
    else:
        headline = re.sub(r"\s+", " ", p["title_hint"]).strip()
        short = headline[:60]
        body = [f"According to {org}, {f['label'].lower()} was {f['value']}{'%' if f['unit'] == '%' else ''} "
                f"as of {f['as_of']}." for f in facts if f["unit"] != "date"] or [f"{org} published an update."]
        if p["demo"]:
            body.insert(0, "DEMONSTRATION ONLY: fictional test data.")
        summary, takeaways, claims, brief, entities = body[0], body[:3], [], "Number-free illustration.", [org]
    return {"headline": headline, "short_headline": short, "summary": summary, "body": body,
            "takeaways": takeaways, "entities": entities, "source_refs": refs, "claims": claims,
            "graphic_brief": brief, "word_count": _words(body), "language": "en"}
