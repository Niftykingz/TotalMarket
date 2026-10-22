"""Graphic Designer Agent: original covers with verified numbers only and no invented logos.

The designer builds a *spec* (every text and number with the fact it comes from), checks the
logo registry, then renders the spec with the Pillow templates in services/graphics.py.
It never asks an image model to draw an official logo; if no approved logo exists the
organization name appears as plain text.
"""
from pathlib import Path

import tmdate

from ..models import GRAPHIC
from ..services import graphics, logos
from .base import Agent

ORG_LOGO_KEYS = {"Reserve Bank of India": "rbi", "SEBI": "sebi", "NSE": "nse", "BSE": "bse"}


class Designer(Agent):
    name = "designer"
    title = "Graphic Designer Agent"
    role = "Produce original, accurate news graphics on the TotalMarket blue-and-white brand."
    tools = frozenset({"db_read", "render", "logo_registry"})
    output_schema = GRAPHIC

    def execute(self, task):
        db, sid = self.ctx.db, task["story_id"]
        self.use("db_read")
        st = db.one("SELECT * FROM stories WHERE id=?", (sid,))
        facts = {f["key"]: f for f in db.all("SELECT * FROM facts WHERE story_id=?", (sid,))}
        inp = task["input"]
        attempt = db.one("SELECT COUNT(*) n FROM graphics WHERE story_id=?", (sid,))["n"] + 1
        spec = build_spec(st, facts, inp.get("event", "generic"), inp.get("org", ""),
                          inject_error=inp.get("inject_error") if attempt == 1 else None)
        self.use("logo_registry")
        key = ORG_LOGO_KEYS.get(inp.get("org", ""))
        if key:
            entry, why = logos.approved(key, self.ctx.root)
            if entry:  # approved original file only, composited as its own layer (Phase 3 compositor)
                spec["items"].append({"kind": "logo", "text": inp["org"], "logo_key": key, "role": "logo"})
            else:
                spec["logo_note"] = f"{inp['org']}: {why}; name shown as plain text"
        self.use("render")
        out_base = Path(self.ctx.out_dir) / "graphics" / f"{st['slug']}-g{attempt}"
        png, sha = graphics.render(spec, out_base)
        spec.update(file=str(png), sha256=sha)
        db.x("INSERT INTO graphics(story_id, attempt, spec, file, sha256, status, created_at) VALUES (?,?,?,?,?,?,datetime('now'))",
             (sid, attempt, __import__("json").dumps(spec, ensure_ascii=False), str(png), sha, "draft"))
        return spec


def _num(v):
    return float(str(v))


def build_spec(st, facts, event, org, inject_error=None):
    demo = bool(st["demo"])
    items = [{"kind": "text", "role": "kicker", "text": "RBI policy" if event == "policy_rate" else st["category"].title()}]
    if demo:
        items.append({"kind": "text", "role": "badge", "text": "DEMO · FICTIONAL DATA"})
    used = []
    if event == "policy_rate" and "repo_old" in facts and "repo_new" in facts:
        old, new = facts["repo_old"], facts["repo_new"]
        o, n = _num(old["value"]), _num(new["value"])
        bps = round((n - o) * 100)
        rel = (n - o) / o * 100
        if inject_error == "wrong_pct":
            rel = -3.58                       # deliberate designer mistake for the failure demo
        items += [
            {"kind": "text", "role": "title", "text": "Repo rate cut" if bps < 0 else "Repo rate hike"},
            {"kind": "text", "role": "org", "text": org or "Reserve Bank of India"},
            {"kind": "figure", "role": "old", "text": f"{old['value']}%", "label": "Repo rate (before)", "fact_key": "repo_old"},
            {"kind": "figure", "role": "new", "text": f"{new['value']}%", "label": "Repo rate (after)", "fact_key": "repo_new"},
            {"kind": "figure", "role": "change", "text": f"{'−' if bps < 0 else '+'}{abs(bps)} bps", "label": "Change",
             "fact_key": "derived:bps_change:repo_old:repo_new"},
            {"kind": "figure", "role": "rel_change", "text": f"{'−' if rel < 0 else '+'}{abs(rel):.2f}%",
             "label": "Relative change in the rate", "fact_key": "derived:rel_change:repo_old:repo_new"},
        ]
        used = ["repo_old", "repo_new"]
        if "decision_date" in facts:
            items.append({"kind": "figure", "role": "date", "text": tmdate.fmt(facts["decision_date"]["value"], "%-d %b %Y"),
                          "label": "Decision date", "fact_key": "decision_date"})
            used.append("decision_date")
        template = "policy_rate"
    else:
        items += [{"kind": "text", "role": "title", "text": "".join(c for c in st["title"] if not c.isdigit())[:60].strip()},
                  {"kind": "text", "role": "org", "text": org or ""}]
        items = [i for i in items if i["text"]]
        template = "number_free"
    return {"template": template, "method": "deterministic-pillow (cover_templates helpers); no generative model",
            "width": 1200, "height": 675, "items": items, "source_fact_keys": used,
            "review_status": "pending_fact_check", "demo": demo}
