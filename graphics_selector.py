"""Story understanding + deterministic graphic selection for TotalMarket covers.

`analyze(story, meta, ipos)` reads a story's headline, summary, category, companies,
session and structured data, and returns what the cover should show:

    {"event": ..., "instruments": [...], "companies": [...], "direction": "up|down|flat",
     "template": "index_chart|earnings_card|ipo_card|illustration", "object": <art object>,
     "figures": [...verified figures with labels...], "series": [...], "reason": "..."}

Rules:
* Numbers only come from structured, verified data: the site's recorded index closes
  (data/meta.json history, with source), the story's own `figures` list, or the IPO
  register (data/ipos.json). Headline wording is never parsed into figures.
* If the figures a template needs are missing, the cover falls back to a number-free
  (or story-field) illustration.
* Selection is deterministic: the same story always gets the same graphic.
"""
import re

# ------------------------------------------------------------------ vocabulary
INSTRUMENTS = [
    ("Bank Nifty", r"\b(bank nifty|nifty bank)\b"),
    ("GIFT Nifty", r"\bgift nifty\b"),
    ("Nifty 50", r"\bnifty(\s*50)?\b(?!\s*(bank|midcap|smallcap|it|pharma|fmcg|auto|metal|media))"),
    ("Sensex", r"\bsensex\b"),
    ("India VIX", r"\b(india vix|vix)\b"),
    ("Nasdaq", r"\bnasdaq\b"),
    ("Dow Jones", r"\bdow\b"),
    ("S&P 500", r"\bs&p\s*500\b"),
    ("Kospi", r"\bkospi\b"),
    ("Brent", r"\bbrent\b"),
    ("WTI", r"\bwti\b"),
    ("Gold", r"\bgold\b"),
    ("Silver", r"\bsilver\b"),
    ("USD/INR", r"\b(rupee|usd/inr)\b"),
    ("US 10Y", r"\b(10-year|10y) (yield|treasury)\b"),
    ("Bitcoin", r"\bbitcoin\b"),
]
WRAP_EDITIONS = ("closing wrap", "daily market report", "midday check")
R_EARN = re.compile(r"\b(q[1-4]|results?|net profit|profit|earnings|revenue)\b", re.I)
R_LIST = re.compile(r"\b(lists?|listing|debut)\b", re.I)
R_IPO = re.compile(r"\bipos?\b", re.I)
R_POLICY = re.compile(r"\b(rbi|repo rate|monetary policy|inflation|cpi|gdp|sebi|budget|gst)\b", re.I)
R_EXPLAIN = re.compile(r"\b(lessons?|explained|what is|how to|guide|fact-check(ed)?)\b", re.I)
R_DOWN = re.compile(r"\b(drops?|falls?|fell|slides?|slips?|plunges?|crash(es)?|tumbles?|sinks?|loses?|sheds?|loss)\b", re.I)
R_UP = re.compile(r"\b(jumps?|rises?|rose|gains?|surges?|rall(y|ies)|climbs?|soars?|record high|bounces?)\b", re.I)

# Title keywords -> original illustration (art objects already in covers.py).
OBJECT_RULES = (
    (r"\b(cybersecurity|hack(er|ed)?|breach|vulnerabilit\w*|flaws?|security)\b", "shield"),
    (r"\b(chips?|semiconductors?|gpu|nvidia)\b", "chip"),
    (r"\b(cloud|data cent(er|re)s?|servers?)\b", "servers"),
    (r"\b(ai|artificial intelligence|model|agents?|openai|anthropic|gemini|deepseek)\b", "neural"),
    (r"\b(rbi|repo rate|central bank|monetary policy|sebi|regulators?)\b", "bank"),
    (r"\b(fed|yields?|treasury|bond)\b", "yield"),
    (r"\b(rupee|usd.?inr|forex|currency)\b", "forex"),
    (r"\b(gold|bullion)\b", "gold"),
    (r"\bsilver\b", "silver"),
    (r"\b(crude|brent|oil)\b", "oil"),
    (r"\b(ipo|listing|funding|raises|startups?|unicorn)\b", "growth"),
    (r"\b(results?|q[1-4]|earnings|profit|revenue|dividend)\b", "coins"),
    (r"\b(wall street|nasdaq|dow|global|overnight|kospi|europe)\b", "globe"),
)
CATEGORY_OBJECT = {"tech": "neural", "startups": "growth", "policy": "bank", "global": "globe", "commodities": "gold", "markets": "candles"}


def _text(p):
    return " ".join(str(p.get(k) or "") for k in ("title", "dek")).strip()


def _session(p):
    return str(p.get("editionLabel") or "").split("·")[-1].strip().lower()


def instruments_in(text):
    """Instruments named in the text, in a fixed order (Bank Nifty is never counted as Nifty 50)."""
    found, t = [], text.lower()
    for name, pat in INSTRUMENTS:
        if re.search(pat, t, re.I):
            found.append(name)
            t = re.sub(pat, " ", t, flags=re.I)  # avoid double-matching 'nifty' inside 'bank nifty'
    return found


def story_date(p):
    rep = p.get("report") or {}
    if rep.get("date"):
        return str(rep["date"])[:10]
    return str(p.get("publishedAt") or "")[:10]


# ------------------------------------------------------------------ events
def classify(p):
    t = _text(p)
    title = str(p.get("title") or "")
    cat = p.get("category")
    sess = _session(p)
    inst = instruments_in(title)
    if p.get("palette") == "festive" or R_EXPLAIN.search(title):
        return "explainer"
    if p.get("report") or (cat == "markets" and ({"Sensex", "Nifty 50"} & set(inst)) and sess in WRAP_EDITIONS):
        return "index_move"
    if re.match(r"\s*stock market today\b", title, re.I) or sess in ("pre-market brief",) and cat == "markets":
        return "market_preview"
    if re.match(r"\s*ipo today\b", title, re.I):
        return "ipo"  # daily IPO roundup covers several issues: no single-company card
    if R_IPO.search(t) or cat == "startups" and R_LIST.search(title):
        lead = re.split(r"[;:,]", title)[0]
        if R_LIST.search(lead) and not re.search(r"\bsubscri", lead, re.I):
            return "ipo_listing"
        return "ipo"
    if p.get("companies") and R_EARN.search(title) and cat != "global":
        return "earnings"
    if R_POLICY.search(title) or cat == "policy":
        return "policy"
    if cat == "commodities":
        return "forex" if "USD/INR" in inst and not ({"Gold", "Silver", "Brent", "WTI"} & set(inst)) else "commodity"
    if cat == "global":
        return "global_markets"
    if cat == "tech":
        return "tech"
    if cat == "startups":
        return "funding"
    if {"Sensex", "Nifty 50", "GIFT Nifty"} & set(inst):
        return "market_preview"
    return "generic"


def direction(p, figures=()):
    for f in figures:
        ch = str(f.get("change") or f.get("pct") or "").strip()
        if ch[:1] in "-−":
            return "down"
        if ch[:1] == "+" or (ch[:1].isdigit() and float(re.sub(r"[^\d.]", "", ch) or 0) > 0):
            return "up"
    stat = str(p.get("stat") or "").strip()
    if stat[:1] in "-−":
        return "down"
    if stat[:1] == "+":
        return "up"
    t = str(p.get("title") or "")
    if R_DOWN.search(t) and not R_UP.search(t):
        return "down"
    if R_UP.search(t) and not R_DOWN.search(t):
        return "up"
    return "flat"


# ------------------------------------------------------------------ verified figures
def index_figures(p, meta):
    """Sensex / Nifty 50 / Bank Nifty closes for the story's date from recorded history (never from the headline).
    Only for closing stories: a midday or pre-market story is not illustrated with a close."""
    if not meta:
        return [], []
    sess = _session(p)
    if not (p.get("report") or sess in ("closing wrap", "daily market report")):
        return [], []
    day = story_date(p)
    hist = meta.get("history") or {}
    figs, series = [], []
    for name in ("Sensex", "Nifty 50", "Bank Nifty"):
        pts = [x for x in (hist.get(name) or []) if str(x.get("d")) <= day]
        if not pts or str(pts[-1].get("d")) != day or len(pts) < 2:
            continue
        last, prev = float(pts[-1]["v"]), float(pts[-2]["v"])
        ch = last - prev
        figs.append({"label": name, "value": f"{last:,.2f}", "change": f"{ch:+,.2f}", "pct": f"{ch / prev * 100:+.2f}%",
                     "date": day, "prevDate": str(pts[-2]["d"]), "source": pts[-1].get("s") or "", "kind": "close"})
        if name == "Nifty 50":
            series = [{"d": str(x["d"]), "v": float(x["v"])} for x in pts[-10:]]
    return figs, series


def story_figures(p):
    """Structured figures written into the story itself (`figures`: [{label, value, change, period, unit}])."""
    out = []
    for f in p.get("figures") or []:
        if isinstance(f, dict) and f.get("label") and f.get("value"):
            out.append({k: (v if k == "series" else str(v)) for k, v in f.items() if v is not None})
    return out


def ipo_record(p, ipos):
    t = _text(p).lower()
    for x in ipos or []:
        n = str(x.get("name") or "").lower()
        if n and n in t:
            return x
    return None


def ipo_figures(p, ipos):
    x = ipo_record(p, ipos)
    if not x or not x.get("listingPrice"):
        return []
    issue = x.get("issuePrice")
    try:
        iss = float(re.sub(r"[^\d.]", "", str(issue)))
        lst = float(re.sub(r"[^\d.]", "", str(x["listingPrice"]).split("(")[0]))
    except ValueError:
        return []
    pct = (lst - iss) / iss * 100
    ps = x.get("priceSeries") or {}
    return [{"label": x["name"], "issue": f"₹{iss:,.0f}", "listing": f"₹{lst:,.2f}".replace(".00", ""), "pct": f"{pct:+.2f}%",
             "exchange": "NSE", "date": str(x.get("listing") or ""),
             "series": ps.get("points") or [], "seriesLabel": ps.get("label") or "", "seriesSource": ps.get("source") or ""}]


# ------------------------------------------------------------------ main entry
def choose_object(p, event, fallback="candles"):
    if event in ("index_move", "market_preview"):
        return "candles"
    if event in ("ipo", "ipo_listing", "funding"):
        return "growth"
    if event == "earnings":
        return "coins"
    if event == "global_markets":
        t = str(p.get("title") or "")
        if re.match(r"\s*(fed|us 10-year|yields?)\b", t, re.I):
            return "yield"
        return "globe"
    if event == "explainer" and p.get("palette") == "festive":
        return "diya"
    title = str(p.get("title") or "")
    for pat, obj in OBJECT_RULES:
        if re.search(pat, title, re.I):
            return obj
    return CATEGORY_OBJECT.get(p.get("category"), fallback)


def analyze(p, meta=None, ipos=None):
    event = classify(p)
    inst = instruments_in(str(p.get("title") or ""))
    figures, series, template, reason = [], [], "illustration", "no verified figures for a data card"
    if event == "index_move":
        figures, series = index_figures(p, meta)
        if len(figures) >= 1 and len(series) >= 2:
            template, reason = "index_chart", "closing story with recorded index closes"
    elif event == "earnings":
        figures = story_figures(p)
        if figures:
            template, reason = "earnings_card", "earnings story with structured figures"
    elif event == "ipo_listing":
        figures = ipo_figures(p, ipos)
        if figures:
            template, reason = "ipo_card", "listing with issue and listing price in the IPO register"
    chart = p.get("chart") if isinstance(p.get("chart"), dict) else None
    missing = ""
    if chart:  # v2: a verified chart spec chooses a layout that fits the story type
        import cover_templates_v2 as v2
        ctype = chart.get("type")
        if event in ("generic", "market_preview", "funding") and ctype == "stock_move":
            event = "stock_move"
        allowed = EVENT_LAYOUTS.get(event, set())
        gap = v2.ok(chart)
        if ctype not in allowed:
            missing = f"chart layout {ctype!r} does not fit a {event} story (allowed: {sorted(allowed) or 'none'})"
        elif gap:
            missing = f"{ctype} needs {gap}"
        else:
            template, reason = ctype, f"{event} story with a verified {ctype} chart"
            figures = [dict(i) for i in chart.get("items") or []]
    need = data_required(p, event)
    if need and template == "illustration" and not missing:
        missing = f"{event} story needs a data graphic: add a verified `chart` ({' or '.join(sorted(EVENT_LAYOUTS.get(event, ())) or ['data'])})"
    out = {"event": event, "instruments": inst, "companies": [c.get("name") for c in p.get("companies") or []],
           "direction": direction(p, figures), "template": template, "object": choose_object(p, event),
           "figures": figures, "series": series, "reason": reason}
    if chart or need:  # extra keys only for v2 stories, so older covers keep their file names
        out.update(data_required=need, missing=missing if template == "illustration" else "", chart=chart if template in V2_LAYOUTS else None)
    return out


# ------------------------------------------------------------------ v2 layout rules
V2_LAYOUTS = {"index_board", "global_bars", "commodity_card", "forex_card", "policy_rate", "stock_move", "ipo_subscription", "earnings_v2"}
EVENT_LAYOUTS = {
    "index_move": {"index_board"}, "market_preview": {"index_board"}, "global_markets": {"global_bars"},
    "commodity": {"commodity_card"}, "forex": {"forex_card"}, "policy": {"policy_rate"}, "earnings": {"earnings_v2", "stock_move"},
    "ipo": {"ipo_subscription"}, "stock_move": {"stock_move"}, "ipo_listing": set(),
}
R_RATE = re.compile(r"\b(repo|policy rate|rate (cut|hike)|cuts? rates?|hikes? rates?|crr|slr|basis points|bps)\b", re.I)
DATA_EVENTS = {"index_move", "market_preview", "global_markets", "commodity", "forex", "earnings", "ipo", "ipo_listing", "stock_move"}


def data_required(p, event):
    """Financial-news stories must carry a data graphic. Explainers, festivals, tech, funding
    and non-rate policy news may use an original illustration."""
    if event in DATA_EVENTS:
        return True
    if event == "policy":
        return bool(R_RATE.search(str(p.get("title") or "")))
    return False


def choose_cover_object(story, fallback="candles"):
    """Backward-compatible helper used by covers.pick(): the illustration object for a story."""
    return choose_object(story, classify(story), fallback)
