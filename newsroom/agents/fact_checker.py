"""Independent Fact Checker Agent.

Works only from the stored evidence and the finished draft/graphic. It ignores the writer's
and designer's own claim mappings, re-extracts every number, date and quotation, and checks
each against traceable facts (services/verify.py). It also enforces the logo authenticity
policy and graphic-number consistency. Its verdict is deterministic code, not a model's
opinion, so two AI agents agreeing can never pass a story.
"""
import hashlib
import json
from pathlib import Path

from ..database import now
from ..models import FACTCHECK, FactStatus, digest
from ..services import logos, verify
from .base import Agent


def _fmt(c):
    u = c["unit"]
    return f"{c['value']:+.2f}".replace("-", "−") + ("%" if u == "%" else "" if u in ("count", "") else f" {u}")


def article_text(d):
    return "\n".join([d["headline"], d["short_headline"], d["summary"], *d["body"], *d["takeaways"]])


class FactChecker(Agent):
    name = "fact_checker"
    title = "Independent Fact Checker Agent"
    role = "Independently verify every material claim against primary evidence."
    tools = frozenset({"db_read", "verify", "logo_registry"})
    output_schema = {"article": FACTCHECK, "graphic": FACTCHECK}

    def execute(self, task):
        db, sid = self.ctx.db, task["story_id"]
        self.use("db_read")
        facts = db.all("SELECT * FROM facts WHERE story_id=?", (sid,))
        docs = {d["id"]: d for d in db.all("SELECT * FROM source_documents WHERE story_id=?", (sid,))}
        draft, spec = task["input"].get("draft"), task["input"].get("graphic")
        res = {}
        if draft is not None:
            res["article"] = self.check_article(draft, facts, docs)
            self._record(sid, "article", digest(draft), res["article"])
        else:
            res["article"] = {"status": "VERIFIED", "findings": [], "checked_numbers": 0, "skipped": True}
        if spec is not None:
            res["graphic"] = self.check_graphic(spec, facts, docs)
            self._record(sid, "graphic", digest(spec), res["graphic"])
            db.x("UPDATE graphics SET status=? WHERE story_id=? AND sha256=?",
                 ("verified" if res["graphic"]["status"] == "VERIFIED" else "rejected", sid, spec.get("sha256")))
        else:
            res["graphic"] = {"status": "VERIFIED", "findings": [], "checked_numbers": 0, "skipped": True}
        return res

    def _record(self, sid, target, sha, result):
        self.ctx.db.x("INSERT INTO fact_checks(story_id, target, subject_sha, status, findings, checker, created_at) VALUES (?,?,?,?,?,?,?)",
                      (sid, target, sha, result["status"], json.dumps(result["findings"], ensure_ascii=False), self.name, now()))

    # ------------------------------------------------------------------ article
    def check_article(self, d, facts, docs):
        self.use("verify")
        text = article_text(d)
        F = verify.check_text(text, facts, docs, owner="writer")
        refs = [r for r in d.get("source_refs", []) if r in docs]
        if not refs:
            F.append(verify.finding("source attribution", FactStatus.UNVERIFIED, "", "article cites no stored source document", "researcher"))
        elif not any(docs[r]["org"].lower() in text.lower() for r in refs):
            F.append(verify.finding("source attribution", FactStatus.NEEDS_CORRECTION, "", "article does not name its source in the text", "writer"))
        if any(json.loads(docs[r]["injection_flags"] or "[]") for r in refs):
            F.append(verify.finding("source integrity", FactStatus.UNVERIFIED, "", "a source contains instruction-like text; needs human review", "researcher"))
        nums = sum(1 for f in F if f["claim"][:1].isdigit() or f["claim"][:1] in "+-−₹")
        return {"status": verify.worst([f["status"] for f in F]).value, "findings": F, "checked_numbers": nums}

    # ------------------------------------------------------------------ graphic
    def check_graphic(self, spec, facts, docs):
        self.use("verify"); self.use("logo_registry")
        F = []
        good = [f for f in facts if verify.traceable(f, docs)[0]]
        by_key = {f["key"]: f for f in good}
        cands = {c["key"]: c for c in verify.candidates(good)}
        n_checked = 0
        for it in spec["items"]:
            txt = it.get("text", "")
            if it["kind"] == "text":
                if any(ch.isdigit() for ch in txt):
                    F.append(verify.finding(txt, FactStatus.REJECTED, "", "number in a non-figure text element (unverifiable)", "designer"))
                continue
            if it["kind"] != "figure":
                continue
            n_checked += 1
            key = it.get("fact_key") or ""
            fact = by_key.get(key)
            if fact and fact["unit"] == "date":
                iso = [i for _, i in verify.dates_in(txt)]
                ok = fact["value"] in iso
                F.append(verify.finding(txt, FactStatus.VERIFIED if ok else FactStatus.NEEDS_CORRECTION,
                                        f"{fact['label']} = {fact['value']}", "" if ok else "date differs from evidence", "designer"))
                continue
            nums = verify.numbers_in(txt)
            if not nums:
                F.append(verify.finding(txt, FactStatus.UNVERIFIED, "", "figure has no number", "designer"))
                continue
            n = nums[0]
            if key.startswith("derived:"):
                c = cands.get(key)
                if not c:
                    F.append(verify.finding(txt, FactStatus.UNVERIFIED, "", f"cannot recompute {key} from traceable facts", "designer"))
                    continue
            elif fact:
                if it.get("label") and it["label"].strip().lower() != fact["label"].strip().lower():
                    F.append(verify.finding(txt, FactStatus.REJECTED, f"{fact['label']} = {fact['value']}",
                                            f"label '{it['label']}' does not match the instrument/measure of the fact ('{fact['label']}')", "designer"))
                    continue
                c = cands.get(key)
            else:
                F.append(verify.finding(txt, FactStatus.UNVERIFIED, "", f"figure cites unknown or untraceable fact '{key}'", "designer"))
                continue
            hit = verify.match(n, [c])
            if hit:
                F.append(verify.finding(txt, FactStatus.VERIFIED, c["evidence"], "", "designer"))
            else:
                F.append(verify.finding(txt, FactStatus.NEEDS_CORRECTION, c["evidence"],
                                        f"graphic shows {txt} but evidence gives {_fmt(c)}", "designer"))
        for status, what, why in logos.check_items(spec["items"], self.ctx.root):
            F.append(verify.finding(what, status, why if status == "VERIFIED" else "", "" if status == "VERIFIED" else why, "designer"))
        f = spec.get("file")
        if f:
            p = Path(f)
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != spec.get("sha256"):
                F.append(verify.finding("graphic file", FactStatus.REJECTED, "", "image file missing or changed after rendering", "designer"))
        return {"status": verify.worst([x["status"] for x in F]).value, "findings": F, "checked_numbers": n_checked}
