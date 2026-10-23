"""Number extraction and matching used by verification, graphics checks and QA.

A number written anywhere in an article or graphic must be one of:
  * a verified figure (at the precision written; Indian/Western digit grouping ignored),
  * a unit-scaled verified figure (×/÷ 10, 100, 1,000, 1 lakh, 1 crore: per-gram vs per-10 g, lakh vs crore),
  * a difference or % change between two verified figures, recomputed here,
  * a declared worked-example value (article body only, never a graphic),
  * or harmless text furniture: years, dates, clock times, Q2/FY27-style labels, small counts (0–12).
"""
import itertools
import re

MONTHS = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
R_DATE = re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTHS}(?:\s+\d{{4}})?\b|\b{MONTHS}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b|\b\d{{4}}-\d{{2}}-\d{{2}}\b", re.I)
R_TIME = re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)|\b\d{1,2}:\d{2}\b", re.I)
R_LABEL = re.compile(r"\b(?:q[1-4]|h[12]|fy\s?\d{2,4}|\d{1,2}[- ]?(?:week|day|month|year|session|member|lakh-share)s?)\b|\b\d{2,3}[kK]\b|\b(?:nifty|sensex|midcap|smallcap|next|bse|s&p)\s?(?:50|30|100|150|250|500)\b(?![,.]\d)|\b\d{1,3}(?:st|nd|rd|th)\b|\b(?:24|22|18|14)\s?(?:k|carat|ct)\b|\b(?:10|2)\s?(?:-year|y)\b|\b\d+-for-\d+\b|\((?:999|995|916|750|585)\)|\b(?:999|995|916|750|585)\s+(?:gold|purity|fine)", re.I)
R_URL = re.compile(r"https?://\S+|/[a-z0-9\-/]+/", re.I)
R_NUM = re.compile(r"(?<![\w.])[+\-−]?₹?\$?\s?(\d{1,3}(?:,\d{2,3})+|\d+)(\.\d+)?")
R_UNIT = re.compile(r"\s*(?:%|per\s?cent|bps\b|basis points?|percentage points?|x\b|times\b|crore|cr\b|lakh|paise|pts?\b|points?\b|bn\b|billion|million)", re.I)
SCALES = (1, 10, 100, 1000, 100000, 10000000)


def to_float(s):
    return float(re.sub(r"[^\d.\-]", "", str(s).replace("−", "-")) or "nan")


def mentions(text):
    """Numeric mentions in text that need support: [(raw, value, decimals)]."""
    t = str(text or "")
    for rx in (R_URL, R_DATE, R_TIME, R_LABEL):
        t = rx.sub(" ", t)
    out = []
    for m in R_NUM.finditer(t):
        whole, frac = m.group(1), m.group(2) or ""
        v = float(whole.replace(",", "") + frac)
        dec = len(frac) - 1 if frac else 0
        money_or_rate = bool(re.search(r"[₹$]", m.group(0))) or bool(R_UNIT.match(t, m.end()))
        if dec == 0 and v <= 12 and "," not in whole and not money_or_rate:
            continue  # small counts ("three of five", "4 members") are low risk
        if dec == 0 and 1990 <= v <= 2100 and "," not in whole:
            continue  # years
        out.append((m.group(0).strip(), v, dec))
    return out


def figure_values(figs):
    vals = []
    for f in figs:
        try:
            v = to_float(f["value"])
        except Exception:
            continue
        if v == v:  # not NaN
            vals.append((f["id"], v))
        for k in ("change", "pct"):
            if f.get(k) not in (None, ""):
                try:
                    vals.append((f"{f['id']}.{k}", to_float(f[k])))
                except Exception:
                    pass
    return vals


def candidates(figs):
    """(value, why) pairs the checker accepts, computed only from verified figures."""
    base = figure_values(figs)
    out = []
    for fid, v in base:
        for s in SCALES:
            out.append((v * s, fid if s == 1 else f"{fid}×{s}"))
            if s != 1:
                out.append((v / s, f"{fid}÷{s}"))
    for (ia, a), (ib, b) in itertools.permutations(base, 2):
        out.append((b - a, f"{ib}−{ia}"))
        out.append(((b - a) * 100, f"({ib}−{ia})×100 (paise / basis points)"))
        if a:
            out.append(((b - a) / a * 100, f"%change {ia}→{ib}"))
            out.append((b / a * 100, f"{ib}/{ia}×100"))
    return out


def supported(value, decimals, cands):
    tol = 0.5 * 10 ** (-decimals) + 1e-9
    for v, why in cands:
        if abs(abs(value) - abs(v)) <= max(tol, abs(v) * 1e-9):
            return why
    return None


def unsupported(text, cands):
    return [(raw, v) for raw, v, d in mentions(text) if not supported(v, d, cands)]


def in_evidence(value, evidence):
    """True if the figure's value appears in its evidence quote (digit grouping ignored)."""
    want = to_float(value)
    for raw, v, d in mentions_all(evidence):
        if abs(v - want) < 1e-9 or abs(abs(v) - abs(want)) < 1e-9:
            return True
    return False


def mentions_all(text):
    out = []
    for m in R_NUM.finditer(str(text or "")):
        whole, frac = m.group(1), m.group(2) or ""
        out.append((m.group(0), float(whole.replace(",", "") + frac), len(frac) - 1 if frac else 0))
    return out
