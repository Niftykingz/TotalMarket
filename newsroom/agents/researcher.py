"""News Research Agent: stores original evidence and extracts candidate facts.

Evidence is written to `source_documents` (append-only) exactly as received; facts are a
separate interpretation layer pointing back to a document and an excerpt.
"""
import json

from ..database import now
from ..models import EVIDENCE
from ..services import sources
from .base import Agent


class MissingSource(RuntimeError):
    pass


class Researcher(Agent):
    name = "researcher"
    title = "News Research Agent"
    role = "Discover accurate, timely news from authoritative sources and record traceable evidence."
    tools = frozenset({"llm", "source_fixtures", "source_fetch", "db_evidence"})
    output_schema = EVIDENCE

    def execute(self, task):
        db, s = self.ctx.db, self.ctx.settings
        sid = task["story_id"]
        docs_in = task["input"].get("documents") or []
        stored, refs, flags_all = [], [], []
        for d in docs_in:
            try:
                rel = sources.check_url(d["url"], s.allowlist)
            except sources.SourceRefused as ex:
                db.error(f"source refused: {ex}", task["id"], sid, self.name)
                continue
            content = sources.clean(d["content"])
            flags = sources.injection_flags(content)
            if flags:
                rel = "unknown"   # instructions inside a source make it untrustworthy
                flags_all += flags
                db.audit(self.name, "injection_flagged", sid, url=d["url"], patterns=flags)
            self.use("db_evidence")
            # append-only evidence; re-runs of the same task reuse the identical document
            sha = sources.sha(content)
            have = db.one("SELECT id FROM source_documents WHERE story_id=? AND sha256=?", (sid, sha))
            doc_id = have["id"] if have else db.x(
                "INSERT INTO source_documents(story_id, url, org, reliability, published_at, fetched_at, content, sha256, injection_flags) "
                "VALUES (?,?,?,?,?,?,?,?,?)", (sid, d["url"], d["org"], rel, d.get("published_at"), now(), content, sha, json.dumps(flags)))
            stored.append({"doc_id": doc_id, "org": d["org"], "url": d["url"], "reliability": rel, "content": content,
                           "mock_extraction": d.get("mock_extraction")})
            refs.append({"doc_id": doc_id, "org": d["org"], "url": d["url"]})
        if not stored:
            raise MissingSource("no usable source documents (none supplied or all refused)")
        if task["input"].get("category") == "policy" and not any(x["reliability"] == "official" for x in stored):
            raise MissingSource("policy story without an official primary source")

        out = self.ask_model({"documents": stored, "category": task["input"].get("category")}, task_id=task["id"])
        facts, quotes = [], []
        contents = {x["doc_id"]: x["content"] for x in stored}
        for f in out.get("facts", []):
            # self-check: keep only facts whose excerpt really is in the document
            if f.get("excerpt") and f["excerpt"] in contents.get(f.get("doc_id"), ""):
                facts.append(f)
                db.x("INSERT OR IGNORE INTO facts(story_id, key, label, value, unit, as_of, doc_id, excerpt, derivation, grp, created_by, created_at) "
                     "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                     (sid, f["key"], f["label"], str(f["value"]), f["unit"], f["as_of"], f["doc_id"], f["excerpt"], None, f.get("grp"), self.name, now()))
            else:
                db.error(f"dropped fact {f.get('key')}: excerpt not in source", task["id"], sid, self.name)
        for q in out.get("quotes", []):
            if q.get("text") and q["text"] in contents.get(q.get("doc_id"), ""):
                quotes.append(q)
        return {"facts": facts, "quotes": quotes, "source_refs": refs, "injection_flags": flags_all}


def mock(payload):
    """Deterministic stand-in for an LLM extraction: returns the fixture's extraction,
    attached to the doc ids the database assigned."""
    facts, quotes = [], []
    for d in payload["documents"]:
        ex = d.get("mock_extraction") or {}
        for f in ex.get("facts", []):
            facts.append(dict(f, doc_id=d["doc_id"]))
        for q in ex.get("quotes", []):
            quotes.append(dict(q, doc_id=d["doc_id"]))
    return {"facts": facts, "quotes": quotes}
