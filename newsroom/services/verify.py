"""Deterministic verification engine used by the Independent Fact Checker.

The checker does NOT trust the writer's or designer's own claim mapping. It re-reads the
finished text / graphic, extracts every number, date and quotation itself, and matches
each one against facts that are traceable to stored source documents:

* a fact is traceable only if its excerpt occurs verbatim in its source document and the
  fact's value occurs in that excerpt;
* a number is VERIFIED if it equals a traceable fact (same unit, at the precision written)
  or a value the checker recomputes itself from facts (percentage change, absolute change,
  basis points), recording the formula, numerator and denominator;
* quotations must occur verbatim in a source document;
* agreement between two AI agents is never evidence.
"""
import itertools
import re
from datetime import date

from ..models import FactStatus

MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
R_DATE = re.compile(r"\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?,?\s+(\d{4})\b", re.I)
R_NUM = re.compile(r"(?<![\w.])([+\-−]?)(₹\s?)?(\d{1,3}(?:,\d{2,3})+|\d+)(\.\d+)?\s*(%|percentage\s+points?|per\s*cent|percent|bps\b|basis\s+points?|pp\b|crore|cr\b|lakh)?", re.I)
R_QUOTE = re.compile(r"[“\"]([^”\"]{12,400})[”\"]")


def to_float(s):
    return float(str(s).replace(",", "").replace("₹", "").replace("−", "-").replace("%", "").strip())


def unit_of(u):
    u = (u or "").lower().replace(" ", "")
    if u in ("%", "percent"):
        return "%"
    if u.startswith("bps") or u.startswith("basispoint"):
        return "bps"
    if u.startswith("percentagepoint") or u == "pp":
        return "pp"
    if u in ("crore", "cr"):
        return "crore"
    if u == "lakh":
        return "lakh"
    return ""


def dates_in(text):
    out = []
    for m in R_DATE.finditer(text):
        try:
            out.append((m.group(0), date(int(m.group(3)), MONTHS[m.group(2).lower()[:3]], int(m.group(1))).isoformat()))
        except ValueError:
            out.append((m.group(0), "invalid"))
    return out


def numbers_in(text):
    """Every numeric mention: dict(raw, value, decimals, unit, sign, currency)."""
    masked = R_DATE.sub(lambda m: "§" * len(m.group(0)), text)
    out = []
    for m in R_NUM.finditer(masked):
        sign, cur, whole, frac, unit = m.groups()
        raw = m.group(0).strip()
        value = to_float(whole + (frac or ""))
        out.append({"raw": raw, "value": value, "decimals": len(frac) - 1 if frac else 0, "unit": unit_of(unit),
                    "sign": "-" if sign in ("-", "−") else ("+" if sign == "+" else ""), "currency": bool(cur)})
    return out


def quotes_in(text):
    return [q.strip() for q in R_QUOTE.findall(text)]


def traceable(fact, docs):
    """(ok, reason). A fact must be backed by a stored source document."""
    doc = docs.get(fact["doc_id"])
    if not doc:
        return False, "source document missing"
    if fact.get("derivation"):
        return True, "derived"
    if fact["excerpt"] not in doc["content"]:
        return False, "excerpt not found in source document"
    if fact["unit"] == "date":
        if fact["value"] not in [iso for _, iso in dates_in(fact["excerpt"])] and fact["value"] not in fact["excerpt"]:
            return False, "date not found in excerpt"
        return True, "ok"
    vals = [n["value"] for n in numbers_in(fact["excerpt"])]
    try:
        fv = to_float(fact["value"])
    except ValueError:
        return (str(fact["value"]) in fact["excerpt"]), "text value"
    if not any(abs(v - fv) < 1e-9 for v in vals):
        return False, f"value {fact['value']} not found in excerpt"
    return True, "ok"


def candidates(facts):
    """Values the checker may accept: facts themselves plus its own recomputed derivations."""
    out = []
    nums = []
    for f in facts:
        if f["unit"] == "date":
            continue
        try:
            v = to_float(f["value"])
        except ValueError:
            continue
        nums.append((f, v))
        out.append({"value": v, "unit": f["unit"], "evidence": f"{f['label']} = {f['value']}{f['unit'] if f['unit'] != 'count' else ''} "
                    f"(source doc #{f['doc_id']}, as of {f['as_of']})", "key": f["key"], "label": f["label"]})
    for (fa, a), (fb, b) in itertools.permutations(nums, 2):
        if fa["unit"] != fb["unit"] or a == 0 or not fa.get("grp") or fa.get("grp") != fb.get("grp"):
            continue
        rel = (b - a) / a * 100
        out.append({"value": rel, "unit": "%", "key": f"derived:rel_change:{fa['key']}:{fb['key']}",
                    "label": f"% change {fa['label']} → {fb['label']}",
                    "evidence": f"({b} − {a}) / {a} × 100 = {rel:.4f}% [numerator {b - a:+g}, denominator {a}, {fa['key']} → {fb['key']}]"})
        d = b - a
        out.append({"value": d, "unit": "pp" if fa["unit"] == "%" else fa["unit"], "key": f"derived:abs_change:{fa['key']}:{fb['key']}",
                    "label": f"change {fa['label']} → {fb['label']}", "evidence": f"{b} − {a} = {d:+g}"})
        if fa["unit"] == "%":
            out.append({"value": d * 100, "unit": "bps", "key": f"derived:bps_change:{fa['key']}:{fb['key']}",
                        "label": f"change in bps {fa['label']} → {fb['label']}", "evidence": f"({b} − {a}) × 100 = {d * 100:+g} bps"})
    return out


def _compatible(mention_unit, cand_unit):
    if mention_unit == cand_unit:
        return True
    if mention_unit == "" and cand_unit in ("count", "inr", "points", "", "index"):
        return True
    if mention_unit == "%" and cand_unit == "pp":   # "fell 0.25%" vs "0.25 percentage points" are not the same claim
        return False
    return False


def match(n, cands):
    tol = 0.5 * 10 ** (-n["decimals"]) + 1e-9
    hits = [c for c in cands if _compatible(n["unit"], c["unit"]) and abs(abs(n["value"]) - abs(c["value"])) <= tol]
    if n["sign"]:
        hits = [c for c in hits if (c["value"] < 0) == (n["sign"] == "-") or c["value"] == 0]
    return hits


def near_miss(n, cands):
    """Same unit, close but wrong value → NEEDS_CORRECTION rather than UNVERIFIED."""
    best = None
    for c in cands:
        if not _compatible(n["unit"], c["unit"]) or c["value"] == 0:
            continue
        err = abs(abs(n["value"]) - abs(c["value"])) / abs(c["value"])
        if err <= 0.5 and (best is None or err < best[0]):
            best = (err, c)
    return best[1] if best else None


def worst(statuses):
    order = [FactStatus.REJECTED, FactStatus.NEEDS_CORRECTION, FactStatus.UNVERIFIED, FactStatus.VERIFIED]
    s = {FactStatus(x) for x in statuses} or {FactStatus.VERIFIED}
    return next(o for o in order if o in s)


def finding(claim, status, evidence, issue, target):
    return {"claim": claim, "status": FactStatus(status).value, "evidence": evidence, "issue": issue, "target": target}


def check_text(text, facts, docs, owner="writer"):
    """Findings for every number, date and quotation in `text`."""
    good = []
    out = []
    for f in facts:
        ok, why = traceable(f, docs)
        if ok:
            good.append(f)
        else:
            out.append(finding(f"fact {f['key']}", FactStatus.UNVERIFIED, f"doc #{f['doc_id']}", why, "researcher"))
    cands = candidates(good)
    date_vals = {f["value"] for f in good if f["unit"] == "date"}
    for raw, iso in dates_in(text):
        if iso in date_vals:
            out.append(finding(raw, FactStatus.VERIFIED, f"date fact {iso}", "", owner))
        else:
            out.append(finding(raw, FactStatus.UNVERIFIED, "", "date not supported by any source fact", owner))
    for n in numbers_in(text):
        hits = match(n, cands)
        if hits:
            out.append(finding(n["raw"], FactStatus.VERIFIED, hits[0]["evidence"], "", owner))
            continue
        nm = near_miss(n, cands)
        if nm:
            out.append(finding(n["raw"], FactStatus.NEEDS_CORRECTION, nm["evidence"],
                               f"stated {n['raw']} but evidence gives {nm['value']:.4g}{nm['unit'] if nm['unit'] not in ('count', '') else ''}", owner))
        else:
            out.append(finding(n["raw"], FactStatus.UNVERIFIED, "", "no source fact or derivation supports this number", owner))
    for q in quotes_in(text):
        if any(q in d["content"] for d in docs.values()):
            out.append(finding(f"“{q}”", FactStatus.VERIFIED, "verbatim in source document", "", owner))
        else:
            out.append(finding(f"“{q}”", FactStatus.REJECTED, "", "quotation not found verbatim in any source (possible invented quote)", owner))
    return out
