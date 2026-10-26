#!/usr/bin/env python3
"""Build the TotalMarket static site.

Reads stories from data/posts/*.json and data/meta.json, writes the public
site to docs/ (served by GitHub Pages). No third-party packages needed.

Run:  python3 build.py
"""
from pipeline import gate as pipeline_gate
import hashlib, html, json, os, re, shutil, sys
import covers
import report
import art
import tools
import hubs
import markets
import hindi
import home
import category
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
OUT = os.environ.get("TM_BUILD_OUT") or os.path.join(ROOT, "docs")  # TM_BUILD_OUT: dry-run builds
SITE_URL = "https://totalmarket.co.in"   # no trailing slash
BASE = "/"                                   # site is served at the domain root
SITE_NAME = "TotalMarket"
TAGLINE = "Indian markets, IPOs, tech and AI news, explained"
TAG_SLUGS = []
TOOL_URLS = []
HUB_URLS = []
HOLIDAYS_PATH = "stock-market-holidays-2026/"
COMPANY_SLUGS = set()
IPO_LIST = []
HOME_TITLE = "TotalMarket: Sensex, Nifty, Gold Rate, IPO & Market News Today"
HOME_KEYWORDS = ["Sensex today", "Nifty 50", "stock market news India", "gold rate today", "silver price today", "crude oil price",
                 "rupee vs dollar", "IPO news", "Q2 results", "global market news", "US market today", "AI news"]
IST = ZoneInfo("Asia/Kolkata")
HOME_LIMIT = 60
SECTION_LIMIT = 80

CATS = {
    "markets":  ("Markets", "Sensex and Nifty moves, big stock news, quarterly results and what drove them."),
    "tech":     ("Tech & AI", "AI, big tech and Indian tech companies: launches, deals and regulation."),
    "startups": ("Startups & IPOs", "Indian startup funding, upcoming IPOs, price bands, subscriptions and listings."),
    "policy":   ("Policy & Economy", "RBI, SEBI, budget, tax and government decisions that affect your money."),
    "global":   ("Global Markets", "Overnight US and Asian markets, bond yields, the Fed and world events that move Indian markets."),
    "commodities": ("Commodities & Forex", "Gold, silver, crude oil, metals, the dollar and the rupee, and what each move means for India."),
}

e = lambda s: html.escape(str(s or ""), quote=True)


def parse_dt(s):
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=IST)
    except Exception:
        return None



def portable_strftime(dt, pattern):
    """Support unpadded day/hour on Windows as well as Unix."""
    return (dt.strftime(pattern.replace("%-d", "__TM_DAY__").replace("%-I", "__TM_HOUR__"))
            .replace("__TM_DAY__", str(dt.day))
            .replace("__TM_HOUR__", str(dt.hour % 12 or 12) if "%-I" in pattern else ""))

def fmt_ist(d, with_date=True):
    d = d.astimezone(IST)
    t = portable_strftime(d, "%-I:%M %p").lower()
    return (portable_strftime(d, "%-d %b %Y, ") + t + " IST") if with_date else t + " IST"


def paras(p):
    b = p.get("body")
    if isinstance(b, list):
        return [str(x).strip() for x in b if str(x).strip()]
    return [x.strip() for x in re.split(r"\n\s*\n", str(b or "")) if x.strip()]


SYMBOL_TAGS = {"gold": "Gold price today", "silver": "Silver price today", "oil": "Crude oil price", "rupee": "Rupee vs dollar",
               "dollar": "US dollar", "yield": "US bond yields", "bitcoin": "Bitcoin price", "chip": "Artificial intelligence",
               "rocket": "IPO news", "bank": "RBI", "yen": "Japanese yen", "euro": "Euro"}
KEYWORD_TAGS = [("sensex", "Sensex today"), ("nifty", "Nifty 50"), ("ipo", "IPO news"), ("fed", "US Fed"), ("results", "Q2 results"),
                ("earnings", "Q2 results"), ("sebi", "SEBI"), ("rbi", "RBI"), ("gold", "Gold price today"), ("crude", "Crude oil price"),
                ("rupee", "Rupee vs dollar"), ("nasdaq", "Nasdaq"), ("funding", "Startup funding"), ("ai ", "Artificial intelligence")]


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


CORE_KEYWORDS = ["stock market news", "share market today", "Sensex", "Nifty", "Indian stock market", "market news today", "financial news India", "business news"]
CAT_KEYWORDS = {
    "markets": ["Sensex today", "Nifty today", "Bank Nifty", "stock market today", "share market news", "top gainers and losers", "FII DII data", "sector performance", "stocks to watch", "Q2 results"],
    "tech": ["tech news", "AI news", "artificial intelligence", "tech stocks", "IT stocks", "Nasdaq", "semiconductor", "big tech earnings"],
    "startups": ["IPO news", "upcoming IPO", "IPO GMP", "IPO listing", "IPO subscription status", "startup funding", "unicorn", "venture capital India"],
    "policy": ["RBI policy", "repo rate", "SEBI news", "SEBI rules", "budget", "GST", "income tax", "inflation India", "economy news"],
    "global": ["global market news", "US stock market", "Dow Jones", "S&P 500", "Nasdaq", "US Fed", "Fed rate hike", "US bond yields", "Asian markets", "GIFT Nifty"],
    "commodities": ["gold rate today", "silver rate today", "MCX gold", "crude oil price", "Brent crude", "rupee vs dollar", "USD INR", "dollar index", "commodity market", "forex news"],
}


def page_keywords(p):
    out, seen = [], set()
    for k in list(p["_tags"]) + CAT_KEYWORDS.get(p["category"], []) + CORE_KEYWORDS:
        if k.lower() not in seen:
            seen.add(k.lower()); out.append(k)
    return out[:30]


def make_tags(p):
    tags = [str(t).strip() for t in (p.get("tags") or []) if str(t).strip()]
    if not tags:
        flags, sym, comps = art.detect(p)
        head = " " + (p.get("title", "") + " " + p.get("dek", "")).lower() + " "
        for k, t in KEYWORD_TAGS:
            if k in head: tags.append(t)
        if sym in SYMBOL_TAGS: tags.append(SYMBOL_TAGS[sym])
        for k, t in art.COMPANIES.items():
            if k in head and len(k) > 3: tags.append(k.title())
        for c in flags[:2]:
            if c != "IN": tags.append(art.COUNTRY_NAMES.get(c, c) + " markets")
    tags.append(CATS[p["category"]][0])
    out, seen = [], set()
    for t in tags:
        if slug(t) and slug(t) not in seen:
            seen.add(slug(t)); out.append(t)
    return out[:8]


def load_posts():
    posts, bad = [], []
    pdir = os.path.join(DATA, "posts")
    for fn in sorted(os.listdir(pdir)):
        if not fn.endswith(".json"):
            continue
        try:
            p = json.load(open(os.path.join(pdir, fn), encoding="utf-8"))
        except Exception as ex:
            bad.append(f"{fn}: invalid JSON ({ex})"); continue
        p["id"] = fn[:-5]
        p["_dt"] = parse_dt(p.get("publishedAt"))
        problems = [k for k in ("title", "category") if not p.get(k)]
        if p.get("category") not in CATS: problems.append("category not one of " + ",".join(CATS))
        if not p["_dt"]: problems.append("publishedAt")
        if not paras(p): problems.append("body")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,120}", p["id"]): problems.append("file name must be lowercase-kebab")
        if problems:
            bad.append(f"{fn}: skipped, bad/missing {', '.join(problems)}"); continue
        ok, why = pipeline_gate.allowed(p, ROOT)  # strict pipeline: enforced articles need all stages PASS
        if not ok:
            bad.append(f"{fn}: BLOCKED by publishing pipeline ({why})"); continue
        p["_paras"] = paras(p)
        p["_tags"] = make_tags(p)
        posts.append(p)
    posts.sort(key=lambda p: p["_dt"], reverse=True)
    for b in bad:
        print("WARNING", b, file=sys.stderr)
    return posts


def url(p):
    return f"{BASE}news/{p['id']}/"


def abs_url(path):
    return SITE_URL + path[len(BASE) - 1:] if path.startswith(BASE) else SITE_URL + path


def desc(p):
    d = p.get("dek") or p["_paras"][0]
    if len(d) < 110 and p.get("_paras"):  # too short for a search snippet: add the story's first sentence
        first = re.split(r"(?<=[.!?])\s", p["_paras"][0], maxsplit=1)[0]
        if first and first not in d:
            d = (d.rstrip(". ") + ". " + first).strip()
    return d if len(d) <= 160 else d[:157].rsplit(" ", 1)[0] + "…"


def smart_title(t, limit=65):
    """Shorten an over-long <title> at the last natural break (|, :, ;, –, comma) before the limit, never mid-word."""
    if len(t) <= limit:
        return t
    cut = t[:limit + 1]
    i = max(cut.rfind(sep) for sep in (" | ", ": ", "; ", ". ", " – ", " - ", ", "))  # keep as much as fits
    if i >= 30:
        return t[:i].rstrip(" ,;:–-")
    return cut[:limit].rsplit(" ", 1)[0].rstrip(" ,;:–-")


FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Inter+Tight:wght@700;800&display=swap">')


def page(title, description, path, body, meta, og_type="website", extra_head="", noindex=False, image=None, seo_title=None, keywords=(), news_kw=None, lang="en", alternates=None, switch=None):
    canon = abs_url(path)
    nk = list(news_kw if news_kw else keywords)[:10]
    kw = (f'<meta name="keywords" content="{e(", ".join(keywords))}">' if keywords else "") + (f'<meta name="news_keywords" content="{e(", ".join(nk))}">' if nk else "")
    og = image or f"{SITE_URL}/assets/og.png"
    full_title = seo_title or (title if title.startswith(SITE_NAME) else f"{title} | {SITE_NAME}")
    if len(full_title) > 65 and full_title.endswith(f" | {SITE_NAME}"):
        full_title = full_title[: -len(f" | {SITE_NAME}")]  # keep titles short enough to show fully in search results
    full_title = smart_title(full_title)
    alt_html = "".join(f'<link rel="alternate" hreflang="{h}" href="{e(u)}">' for h, u in (alternates or []))
    if alternates:
        alt_html += f'<link rel="alternate" hreflang="x-default" href="{e(dict(alternates).get("en", canon))}">'
    rss_link = f"{SITE_URL}/hi/rss.xml" if lang == "hi" else f"{SITE_URL}/rss.xml"
    head = f"""<!doctype html>
<html lang="{"hi-IN" if lang == "hi" else "en-IN"}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(description)}">
{kw}
<link rel="canonical" href="{e(canon)}">
{'<meta name="robots" content="noindex,follow">' if noindex else '<meta name="robots" content="index,follow,max-image-preview:large">'}
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(canon)}">
<meta property="og:image" content="{e(og)}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="675">
<meta property="og:locale" content="{"hi_IN" if lang == "hi" else "en_IN"}">{alt_html}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(description)}">
<meta name="twitter:image" content="{e(og)}">
<meta name="theme-color" content="#102A43">
<meta name="google-site-verification" content="R-bU7412W25OlS3wPOdJYbHHIF8P7FdcDqTH9Zd-Xfo">
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag("js",new Date());gtag("config","{GA_ID}");</script>
<link rel="icon" type="image/png" sizes="48x48" href="{BASE}assets/favicon-48.png"><link rel="icon" type="image/png" sizes="96x96" href="{BASE}assets/favicon-96.png"><link rel="icon" type="image/png" sizes="144x144" href="{BASE}assets/favicon-144.png"><link rel="icon" type="image/x-icon" sizes="any" href="{BASE}favicon.ico"><link rel="apple-touch-icon" sizes="180x180" href="{BASE}assets/apple-touch-icon.png"><link rel="manifest" href="{BASE}site.webmanifest">
<link rel="alternate" type="application/rss+xml" title="{SITE_NAME}" href="{rss_link}">
<script>try{{var t=localStorage.getItem("tm-theme");if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
{FONTS}{hindi.FONT if lang == "hi" else ""}
<link rel="stylesheet" href="{BASE}assets/style.css">
{extra_head}
</head>
<body>
{header(meta, path, lang, switch)}
<main class="wrap main" id="main">
{body}
</main>
{footer(lang)}
<script src="{BASE}assets/site.js" defer></script>
</body>
</html>
"""
    return head


def spark(values, w=96, h=30):
    vals = [float(v) for v in values if v is not None]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals); rng = (hi - lo) or 1
    pts = " ".join(f"{i * w / (len(vals) - 1):.1f},{h - 2 - (v - lo) / rng * (h - 4):.1f}" for i, v in enumerate(vals))
    c = "up" if vals[-1] >= vals[0] else "down"
    return f'<svg class="spark {c}" viewBox="0 0 {w} {h}" width="{w}" height="{h}" aria-hidden="true"><polyline points="{pts}" fill="none" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/></svg>'


def hist_vals(meta, label):
    return [x.get("v") for x in (meta.get("history") or {}).get(label, [])]


NAV_MAIN = [("", "Home"), ("markets/", "Markets"), ("tech/", "Tech & AI"), ("startups/", "Startups & IPOs"), ("policy/", "Policy & Economy"),
            ("global/", "Global Markets"), ("commodities/", "Commodities & Forex"), ("nifty-50/", "Nifty 50"), ("gold-rate-today/", "Gold rate")]
NAV_MORE_GROUPS = [
    ("Market data", [("live/", "Today: all updates"), ("market-report/", "Daily market report"), ("global-indices/", "Global indices"),
                     ("top-gainers-losers-today/", "Gainers & losers"), ("fii-dii-data/", "FII / DII data"), ("silver-rate-today/", "Silver rate")]),
    ("Market tools", [("ipo/", "IPO calendar"), ("results/", "Earnings calendar"), ("corporate-events/", "Corporate actions"),
                      ("__HOLIDAYS__", "Market holidays"), ("stock/", "Companies A–Z"), ("calculators/", "SIP & EMI calculators")]),
    ("Learning", [("learn/", "Learn with Boss Piggy"), ("ipo/#learn", "IPO basics")]),
    ("TotalMarket", [("about/", "About TotalMarket"), ("editorial-policy/", "Editorial policy"), ("corrections/", "Corrections"), ("contact/", "Contact"), ("hi/", "हिंदी संस्करण")]),
]
NAV_MORE = [x for _, g in NAV_MORE_GROUPS for x in g]

# Secondary tabs shown under the main navigation for each section (existing pages and filters only).
SUBNAV = {
    "markets": [("markets/", "Overview"), ("markets/#feed", "News"), ("nifty-50/", "Indices"), ("top-gainers-losers-today/", "Top movers"),
                ("market-report/", "Sectors & breadth"), ("fii-dii-data/", "FII / DII"), ("results/", "Earnings"), ("corporate-events/", "Corporate actions")],
    "tech": [("tech/", "Overview"), ("tech/#topic-ai", "AI"), ("tech/#topic-bigtech", "Big Tech"), ("tech/#topic-cyber", "Cybersecurity"),
             ("tech/#topic-chips", "Semiconductors"), ("tech/#topic-aistartups", "AI Startups"), ("tech/#topic-deals", "Deals"), ("tech/#topic-regulation", "Regulation")],
    "startups": [("startups/", "Overview"), ("startups/#topic-funding", "Startup funding"), ("ipo/", "IPO center"), ("startups/#topic-subscription", "Subscription status"),
                 ("startups/#topic-listing", "Listings")],
    "policy": [("policy/", "Overview"), ("policy/#topic-rbi", "RBI"), ("policy/#topic-inflation", "Inflation"), ("policy/#topic-budget", "Union Budget"),
               ("policy/#topic-tax", "Taxation"), ("policy/#topic-govt", "Government & regulators")],
    "global": [("global/", "Overview"), ("global-indices/", "Global indices"), ("global/#topic-us", "US"), ("global/#topic-asia", "Asia"),
               ("global/#topic-europe", "Europe"), ("global/#topic-cb", "Central banks")],
    "commodities": [("commodities/", "Overview"), ("gold-rate-today/", "Gold rate"), ("silver-rate-today/", "Silver rate"), ("commodities/#topic-crude", "Crude oil"),
                    ("commodities/#topic-forex", "Rupee & forex")],
}
SUBNAV_OWNER = {"nifty-50/": "markets", "top-gainers-losers-today/": "markets", "market-report/": "markets", "fii-dii-data/": "markets",
                "results/": "markets", "corporate-events/": "markets", "global-indices/": "global", "gold-rate-today/": "commodities",
                "silver-rate-today/": "commodities", "ipo/": "startups"}


def subnav(path):
    rel = path[len(BASE):] if path.startswith(BASE) else path
    first = rel.split("/")[0] + "/" if rel else ""
    key = rel.split("/")[0] if rel.split("/")[0] in SUBNAV else SUBNAV_OWNER.get(first)
    if not key:
        return ""
    links = "".join(f'<a class="stab{" on" if (BASE + k) == path else ""}" href="{BASE}{k}"{" aria-current=\"page\"" if (BASE + k) == path else ""}>{e(n)}</a>' for k, n in SUBNAV[key])
    return f'<div class="subnav"><nav class="wrap srail" aria-label="{e(CATS[key][0])} sections">{links}</nav></div>'


TICK_STATUS_LABEL = {"EOD": "End-of-day close", "DELAYED": "Delayed figure as reported", "PRELIMINARY": "Preliminary figure",
                     "UNAVAILABLE": "No verified figure", "LIVE": "Live"}


def tick_status(x):
    """Status of a ticker item. TotalMarket has no licensed real-time feed, so LIVE is never produced."""
    if not str(x.get("value") or "").strip():
        return "UNAVAILABLE"
    if "prelim" in str(x.get("asOfText") or "").lower():
        return "PRELIMINARY"
    k = str(x.get("kind") or "").lower()
    if k in ("close", "eod", "settle"):
        return "EOD"
    return "DELAYED"


def tick_kind(x):  # kept for older callers
    return {"EOD": "EOD", "DELAYED": "Delayed", "PRELIMINARY": "Prelim"}.get(tick_status(x), "")


def ticker(meta):
    t = meta.get("ticker") or []
    if not t:
        return ""
    def card(x):
        st = tick_status(x)
        ch = str(x.get("change") or "") if st != "UNAVAILABLE" else ""
        down = ch.lstrip("~≈ ").startswith(("-", "−"))
        arrow = ("▼ " if down else "▲ ") if ch and ch[:1] in "+-−~≈" else ""
        if ch.startswith(("~", "≈")):
            ch = "≈" + ch.lstrip("~≈ ").lstrip("+")
        src = (x.get("source") or {}).get("name") or ""
        when = x.get("asOfText") or ("As-of time not recorded" if st != "UNAVAILABLE" else "")
        title = " · ".join(filter(None, [x.get("label"), TICK_STATUS_LABEL[st], when, ("Source: " + src) if src else "Source not recorded"]))
        val = e(x.get("value")) if st != "UNAVAILABLE" else '<span class="na">Unavailable</span>'
        sp = spark(hist_vals(meta, x.get("label"))) if st != "UNAVAILABLE" else ""
        return (f'<li class="tcard st-{st.lower()}" title="{e(title)}"><span class="tl">{e(x.get("label"))}<em class="tk tk-{st.lower()}">{st}</em></span>'
                f'<span class="tv">{val}</span>'
                f'<span class="tc {"down" if down else "up"}">{arrow}{e(ch.lstrip("+"))}</span>{sp}'
                f'<span class="tw">{e(when)}{(" · " + e(src)) if src else ""}</span></li>')
    srcs = []
    for x in t:
        s_ = (x.get("source") or {}).get("name")
        if s_ and s_ not in srcs: srcs.append(s_)
    note = (f'<div class="wrap tnote"><span><b>Not live.</b> Each card shows its own date and source. EOD = end-of-day close · DELAYED = figure as reported during the session · '
            f'PRELIMINARY = early figure, may change · UNAVAILABLE = no verified figure</span><span>Sources: {e(", ".join(srcs[:6]))}</span></div>')
    arrows = ('<button type="button" class="tnav prev" aria-label="Scroll market snapshot left" disabled>&#8249;</button>'
              '<button type="button" class="tnav next" aria-label="Scroll market snapshot right">&#8250;</button>')
    return (f'<section class="tickers" aria-label="Market snapshot (not live)" data-nosnippet><div class="wrap tbox">{arrows}'
            f'<ul class="trow" tabindex="0" aria-label="Market snapshot cards, use arrow keys to scroll">{"".join(card(x) for x in t)}</ul></div>{note}</section>')


def header(meta, path, lang="en", switch=None):
    if lang == "hi":
        main, more = hindi.NAV_LINKS[:9], hindi.NAV_LINKS[9:] + [("live/", "Today (English)")]
    else:
        main, more = NAV_MAIN, NAV_MORE
    rel = path[len(BASE):] if path.startswith(BASE) else path
    owner = SUBNAV_OWNER.get(rel.split("/")[0] + "/") if rel else None
    on = lambda k: " on" if (path == BASE + k or (k and k == rel.split("/")[0] + "/" and k[:-1] in CATS)) else ""
    nav = "".join(f'<a class="tab{on(k)}" href="{BASE}{k}"{" aria-current=\"page\"" if on(k) else ""}>{e(n)}</a>' for k, n in main)
    # Keep the public Academy visible after Home on every generated page.
    academy_url = "https://niftykingz.github.io/TotalMarket-Academy/courses.html"
    academy_label = "Free Academy" if lang != "hi" else "फ्री अकादमी"
    home_end = nav.find("</a>") + 4
    if home_end >= 4:
        nav = nav[:home_end] + f'<a class="tab" href="{academy_url}">{academy_label}</a>' + nav[home_end:]
    if lang == "hi":
        more_links = "".join(f'<a href="{BASE}{k}">{e(n)}</a>' for k, n in more)
    else:
        more_links = "".join(f'<div class="mgrp"><b>{e(t)}</b>' + "".join(f'<a href="{BASE}{HOLIDAYS_PATH if k == "__HOLIDAYS__" else k}">{e(n)}</a>' for k, n in g) + "</div>"
                             for t, g in NAV_MORE_GROUPS)
    seen_m = set(); allm = []
    for k, n in main + more:
        k = HOLIDAYS_PATH if k == "__HOLIDAYS__" else k
        if k not in seen_m:
            seen_m.add(k); allm.append((k, n))
    all_links = "".join(f'<a class="{on(k).strip()}" href="{BASE}{k}">{e(n)}</a>' for k, n in allm)
    mobile_home_end = all_links.find("</a>") + 4
    if mobile_home_end >= 4:
        all_links = all_links[:mobile_home_end] + f'<a href="{academy_url}">{academy_label} · 20 Courses</a>' + all_links[mobile_home_end:]
    sw_url, sw_label = switch or ((f"{BASE}", "English") if lang == "hi" else (f"{BASE}hi/", "हिंदी"))
    sw = f'<a class="langsw" href="{e(sw_url)}" hreflang="{"en" if lang == "hi" else "hi"}" lang="{"en" if lang == "hi" else "hi"}">{e(sw_label)}</a>'
    ph = "कंपनी, IPO, खबरें खोजें…" if lang == "hi" else "Search companies, IPOs, news, markets…"
    return f"""<a class="skip" href="#main">{"मुख्य सामग्री पर जाएं" if lang == "hi" else "Skip to content"}</a>
<header class="top">
<div class="wrap hbar">
<a class="brand" href="{BASE}{"hi/" if lang == "hi" else ""}" aria-label="TotalMarket home"><img class="brand-pig" src="{BASE}assets/piggy/boss-piggy-head-96.webp" width="48" height="48" alt="" fetchpriority="high"><span class="bm">Total<b>Market</b></span><span class="bt">Markets · Startups · IPOs · Tech · Global</span></a>
<div class="search" role="search"><input id="q" type="search" placeholder="{ph}" aria-label="Search TotalMarket" autocomplete="off"><button type="button" class="sbtn" aria-label="Search" onclick="document.getElementById('q').focus()"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg></button><div id="qres" class="qres" hidden></div></div>
{sw}
<button class="themebtn" id="themebtn" type="button" aria-label="Switch light or dark theme"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M21 13.2A8.5 8.5 0 1 1 10.8 3a6.7 6.7 0 0 0 10.2 10.2Z"/></svg></button>
<details class="mnav"><summary aria-label="Open menu"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg></summary><nav class="mpanel" aria-label="All sections">{all_links}</nav></details>
</div>
<div class="navbar"><nav class="wrap rail" aria-label="Sections">{nav}<details class="more"><summary>{"और" if lang == "hi" else "More"} <span aria-hidden="true">▾</span></summary><div class="mdrop{"" if lang == "hi" else " grouped"}">{more_links}</div></details></nav></div>
{"" if lang == "hi" else subnav(path)}
</header>
{ticker(meta)}"""


def footer(lang="en"):
    if lang == "hi":
        return hindi.footer(BASE, SITE_URL, piggy_img)
    cols = [("Markets", [("markets/", "Market news"), ("nifty-50/", "Nifty 50 today"), ("global-indices/", "Global indices"), ("top-gainers-losers-today/", "Gainers & losers"),
                         ("fii-dii-data/", "FII / DII data"), ("market-report/", "Daily market report")]),
            ("News", [("live/", "Latest updates"), ("tech/", "Tech & AI"), ("startups/", "Startups & IPOs"), ("policy/", "Policy & economy"), ("global/", "Global markets"), ("commodities/", "Commodities & forex")]),
            ("Tools", [("ipo/", "IPO hub"), ("results/", "Results calendar"), ("corporate-events/", "Corporate actions"), (HOLIDAYS_PATH, "Market holidays"),
                       ("gold-rate-today/", "Gold rate"), ("silver-rate-today/", "Silver rate"), ("calculators/", "SIP & EMI calculators"), ("stock/", "Companies A–Z")]),
            ("About", [("about/", "About TotalMarket"), ("editorial-policy/", "Editorial policy"), ("corrections/", "Corrections"), ("contact/", "Contact"),
                       ("learn/", "Learn with Boss Piggy"), ("hi/", "हिंदी संस्करण")])]
    colhtml = "".join(f'<nav aria-label="{e(t)}"><h2>{e(t)}</h2>' + "".join(f'<a href="{BASE}{k}">{e(n)}</a>' for k, n in links) + "</nav>" for t, links in cols)
    return f"""<footer class="foot">
<div class="wrap fgrid">
<div class="fbrand"><a class="brand" href="{BASE}"><img class="brand-pig" src="{BASE}assets/piggy/boss-piggy-head-96.webp" width="48" height="48" alt="" loading="lazy"><span class="bm">Total<b>Market</b></span><span class="bt">Markets · Startups · IPOs · Tech · Global</span></a>
<p>Indian and global market news, IPOs, results and gold rates, explained simply. Written by <b>Boss Piggy AI</b>, TotalMarket's AI market desk; every story lists its sources.</p>
<div class="fsub"><b>Get every update</b><span>Follow with any feed reader.</span><a class="btn sm" href="{SITE_URL}/rss.xml">RSS feed</a> <a class="btn ghost sm" href="{SITE_URL}/hi/rss.xml" lang="hi">हिंदी RSS</a></div></div>
{colhtml}
</div>
<div class="wrap fdisc"><p><b>Not investment advice.</b> TotalMarket reports and explains news. It does not recommend buying, selling or holding any security and is not a SEBI-registered investment adviser or research analyst. Market data on this site is not real-time: figures are end-of-day or delayed, as labelled, with sources. Do your own research or consult a registered adviser before investing.</p>
<p>© {datetime.now(IST).year} TotalMarket · <a href="{BASE}about/">About</a> · <a href="{SITE_URL}/sitemap.xml">Sitemap</a></p></div>
</footer>"""


def chip(p):
    c = p["category"]
    st = STATUS_BADGE.get(str(p.get("status") or "").lower())
    badge = f'<span class="stbadge st-{e(p["status"].lower())}" data-nosnippet>{e(st)}</span>' if st else ""
    return f'<span class="chip" style="--dot:var(--c-{c})">{e(CATS[c][0])}</span>{badge}'


STATUS_BADGE = {"developing": "Developing story", "update": "Updated", "updated": "Updated"}


def meta_row(p):
    src = (p.get("sources") or [{}])[0].get("name")
    bits = [f'<time datetime="{e(p["_dt"].isoformat())}">{e(fmt_ist(p["_dt"]))}</time>']
    up = parse_dt(p.get("updatedAt"))
    if up and up > p["_dt"]:
        bits.append(f'<span class="upd">Updated <time datetime="{e(up.isoformat())}">{e(fmt_ist(up))}</time></span>')
    if p.get("readMins"): bits.append(f'{int(p["readMins"])} min read')
    if src: bits.append(e(src))
    return '<div class="meta">' + "".join(f"<span>{b}</span>" for b in bits) + "</div>"


def cover_url(p, absolute=False):
    rel = f"{BASE}covers/{p['_cover_og'] if absolute else p['_cover']}"
    return abs_url(rel) if absolute else rel


def cover_img(p, cls, eager=False):
    alt = p.get("coverAlt") or f'Cover graphic: {p["title"]}'
    return (f'<img class="{cls}" src="{cover_url(p)}" width="1600" height="900" alt="{e(alt)}" '
            f'{"fetchpriority=\"high\"" if eager else "loading=\"lazy\""} decoding="async">')


def card(p):
    dek = f'<p>{e(p.get("dek"))}</p>' if p.get("dek") else ""
    return (f'<article class="card" style="--dot:var(--c-{p["category"]})">{cover_img(p, "thumb")}<div class="cbody">{chip(p)}'
            f'<h3><a href="{url(p)}">{e(p["title"])}</a></h3>{dek}{meta_row(p)}</div></article>')


LOGO_DIR = os.path.join(ROOT, "logos")


def logo_file(ticker):
    t = str(ticker or "").lower()
    for ext in ("png", "svg", "webp", "jpg", "jpeg"):
        if t and os.path.exists(os.path.join(LOGO_DIR, f"{t}.{ext}")):
            return f"{t}.{ext}"
    return None


def people_strip(p):
    ppl = []
    for x in (p.get("people") or [])[:4]:
        f = str(x.get("commonsFile") or "").replace(" ", "_")
        if not f or "/" in f or not re.fullmatch(r"[^<>\"']+\.(jpg|jpeg|png|webp)", f, re.I):
            continue
        img = f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(f)}?width=240"
        page = f"https://commons.wikimedia.org/wiki/File:{quote(f)}"
        ppl.append(f'<figure class="person"><img src="{img}" width="96" height="96" alt="{e(x.get("name"))}" loading="lazy" decoding="async" referrerpolicy="no-referrer">'
                   f'<figcaption><b>{e(x.get("name"))}</b><span>{e(x.get("role") or "")}</span>'
                   f'<a href="{page}" target="_blank" rel="noopener nofollow">Photo: Wikimedia Commons</a></figcaption></figure>')
    comps = []
    for c in (p.get("companies") or [])[:4]:
        if not isinstance(c, dict):
            continue
        lf = logo_file(c.get("ticker"))
        logo = f'<img src="{BASE}logos/{lf}" alt="" loading="lazy">' if lf else f'<span class="tkb">{e(c.get("ticker") or "")}</span>'
        csl = hubs.company_slug(c.get("name") or "")
        tagname = "a" if csl in COMPANY_SLUGS else "div"
        href = f' href="{BASE}stock/{csl}/"' if tagname == "a" else ""
        comps.append(f'<{tagname} class="company"{href}>{logo}<span><b>{e(c.get("name"))}</b><small>{e(c.get("ticker") or "")}{" · All news →" if href else ""}</small></span></{tagname}>')
    if not ppl and not comps:
        return ""
    out = '<div class="pstrip">'
    if ppl:
        out += f'<div class="pgroup"><h2>People in this story</h2><div class="prow">{"".join(ppl)}</div></div>'
    if comps:
        out += f'<div class="pgroup"><h2>Companies in this story</h2><div class="prow">{"".join(comps)}</div></div>'
    return out + "</div>"


PIGGY_ALT = "Boss Piggy, TotalMarket's market guide: a cartoon pig in black glasses and a navy suit"


def piggy_img(kind="head", cls="pg-av", eager=False):
    src, w, h = {"head": ("boss-piggy-head.webp", 192, 192), "head96": ("boss-piggy-head-96.webp", 96, 96),
                 "full": ("boss-piggy-360.webp", 216, 360)}[kind]
    return (f'<img class="{cls}" src="{BASE}assets/piggy/{src}" width="{w}" height="{h}" alt="{e(PIGGY_ALT)}" '
            f'{"" if eager else "loading=\"lazy\" "}decoding="async">')


def piggy_host(title, text, link=None, kind="full"):
    """Boss Piggy as host of an educational section (IPO hub, Learn page)."""
    more = f'<a class="pg-link" href="{e(link[0])}">{e(link[1])} →</a>' if link else ""
    return (f'<aside class="pg-host" aria-label="Boss Piggy, your market guide">{piggy_img(kind, "pg-full")}'
            f'<div><span class="pg-name">Boss Piggy · your market guide</span><h2>{e(title)}</h2><p>{e(text)}</p>{more}'
            f'<small>Boss Piggy explains news and ideas; he never tells you what to buy or sell.</small></div></aside>')


def piggy_intro():
    return (f'<aside class="pg-intro" aria-label="Boss Piggy, your market guide">{piggy_img("head96", "pg-av", eager=True)}'
            f'<p><b>Namaste, I\'m Boss Piggy.</b> I\'ll help make today\'s market news easier to understand: what happened, why it matters and what to watch. '
            f'<a href="{BASE}learn/">Learn the basics with me →</a></p></aside>')


def piggy_box(p):
    """Compact 'Boss Piggy explains' box: what happened / why it matters / what to watch. Only when the story has a `piggy` field."""
    g = p.get("piggy")
    if not isinstance(g, dict) or not g.get("happened"):
        return ""
    watch = g.get("watch") or []
    if isinstance(watch, str):
        watch = [watch]
    rows = [("What happened", e(g["happened"]))]
    if g.get("matters"):
        rows.append(("Why it matters", e(g["matters"])))
    if watch:
        rows.append(("What to watch next", "<ul>" + "".join(f"<li>{e(w)}</li>" for w in watch) + "</ul>"))
    dev = ' <span class="stbadge st-developing" data-nosnippet>Developing</span>' if str(p.get("status", "")).lower() == "developing" else ""
    asof = fmt_ist(parse_dt(p.get("updatedAt")) or p["_dt"])
    return (f'<aside class="pg-box" aria-label="Boss Piggy explains">'
            f'<div class="pg-head">{piggy_img("head96", "pg-av")}<div><b>Boss Piggy explains</b>{dev}<small>Simple explanation of the facts in this story · as of {e(asof)}</small></div></div>'
            + "".join(f'<div class="pg-row"><h3>{k}</h3><div>{v}</div></div>' for k, v in rows)
            + '<p class="pg-note">Explanation only, based on the sources listed below. Not a recommendation to buy, sell or hold anything.</p></aside>')


def piggy_data(g):
    """Boss Piggy box for evergreen data pages (no story timestamp)."""
    watch = g.get("watch") or []
    rows = [("What this page shows", e(g["happened"]))]
    if g.get("matters"):
        rows.append(("Why it matters", e(g["matters"])))
    if watch:
        rows.append(("What to watch", "<ul>" + "".join(f"<li>{e(w)}</li>" for w in watch) + "</ul>"))
    return (f'<aside class="pg-box" aria-label="Boss Piggy explains">'
            f'<div class="pg-head">{piggy_img("head96", "pg-av")}<div><b>Boss Piggy explains</b><small>A plain-English guide to the numbers on this page</small></div></div>'
            + "".join(f'<div class="pg-row"><h3>{k}</h3><div>{v}</div></div>' for k, v in rows)
            + '<p class="pg-note">Explanation only. Not a recommendation to buy, sell or hold anything.</p></aside>')


def why(p):
    return f'<p class="why"><b>Why it matters</b>{e(p["why"])}</p>' if p.get("why") else ""


def impacts(p):
    boxes = []
    if p.get("globalImpact"):
        boxes.append(f'<div class="impact glob"><b><span class="ico" aria-hidden="true">◍</span>Global impact</b><p>{e(p["globalImpact"])}</p></div>')
    if p.get("indiaImpact"):
        boxes.append(f'<div class="impact ind"><b><span class="ico" aria-hidden="true">▲</span>Impact on India</b><p>{e(p["indiaImpact"])}</p></div>')
    return ('<div class="impacts">' + "".join(boxes) + "</div>") if boxes else ""


def data_table(p):
    t = p.get("table")
    rows = (t or {}).get("rows") if isinstance(t, dict) else None
    if not rows:
        return ""
    cols = [c for c in (t.get("columns") or ["Market", "Level", "Change"]) if c != ""]
    textual = bool(t.get("columns"))
    out = []
    for r in rows:
        sub = f'<span class="sub">{e(r.get("note"))}</span>' if r.get("note") and not textual else ""
        val = f'<td class="{"txt" if textual else "num"}"><b>{e(r.get("value"))}</b>' + (f'<span class="sub">{e(r.get("note"))}</span>' if textual and r.get("note") else "") + "</td>" if textual else f'<td class="num">{e(r.get("value"))}</td>'
        ch = "" if len(cols) < 3 else (f'<td class="num {"down" if str(r.get("change","")).startswith("-") else "up" if str(r.get("change","")).startswith("+") else ""}">{e(r.get("change"))}</td>')
        out.append(f'<tr><th scope="row">{e(r.get("label"))}{sub}</th>{val}{ch}</tr>')
    cap = f'<caption>{e(t.get("title"))}</caption>' if t.get("title") else ""
    return f'<div class="tablewrap"><table class="dt">{cap}<thead><tr>{"".join(f"<th>{e(h)}</th>" for h in cols)}</tr></thead><tbody>{"".join(out)}</tbody></table></div>'


def load_results():
    path = os.path.join(DATA, "results.json")
    if not os.path.exists(path):
        return []
    out = []
    for r in json.load(open(path, encoding="utf-8")):
        try:
            d = datetime.fromisoformat(r["date"]).date()
        except Exception:
            continue
        out.append({"date": d, "company": r.get("company", ""), "note": r.get("note", ""), "big": bool(r.get("big"))})
    return sorted(out, key=lambda r: (r["date"], not r["big"], r["company"]))


def upcoming(results, days=None):
    today = datetime.now(IST).date()
    items = [r for r in results if r["date"] >= today and (days is None or (r["date"] - today).days <= days)]
    by = {}
    for r in items:
        by.setdefault(r["date"], []).append(r)
    return by


def results_widget(results):
    by = upcoming(results, 7)
    if not by:
        return ""
    cols = []
    for d, rs in list(by.items())[:4]:
        names = "".join(f'<li class="{"big" if r["big"] else ""}">{e(r["company"])}</li>' for r in rs[:7])
        more = f'<li class="more">+{len(rs)-7} more</li>' if len(rs) > 7 else ""
        cols.append(f'<div class="rday"><h3>{e(portable_strftime(d, "%a %-d %b"))}</h3><ul>{names}{more}</ul></div>')
    return (f'<section class="rwidget"><div class="rhead"><h2>Upcoming results</h2><a href="{BASE}results/">Full calendar →</a></div>'
            f'<div class="rdays">{"".join(cols)}</div></section>')


def results_page(results, meta):
    path = f"{BASE}results/"
    by = upcoming(results)
    days = []
    for d, rs in by.items():
        rows = "".join(f'<tr class="{"big" if r["big"] else ""}"><th scope="row">{e(r["company"])}</th><td>{e(r["note"])}</td></tr>' for r in rs)
        days.append(f'<section class="rsec"><h2 class="edhead"><b>{e(portable_strftime(d, "%A %-d %B"))}</b><span>{len(rs)} {"company" if len(rs)==1 else "companies"}</span></h2>'
                    f'<div class="tablewrap"><table class="dt rtable"><tbody>{rows}</tbody></table></div></section>')
    body = (f'<div class="sechead"><h1>Upcoming results</h1><p>Quarterly results dates for listed Indian companies. Large companies are in bold. '
            f'Dates come from company announcements and can change, so check the exchange filing on the day.</p></div>'
            + ("".join(days) or '<div class="empty"><p>No upcoming results dates listed right now.</p></div>'))
    return page("Upcoming quarterly results calendar", "Which Indian companies announce quarterly results this week and next, by date.", path, body, meta)


def lead(p):
    dek = f'<p class="dek">{e(p.get("dek"))}</p>' if p.get("dek") else ""
    return (f'<article class="lead" style="--dot:var(--c-{p["category"]})">{cover_img(p, "hero", True)}<div class="lbody"><div>{chip(p)}'
            f'<h2><a href="{url(p)}">{e(p["title"])}</a></h2></div><aside>{(f'<p class="why"><b>Impact on India</b>{e(p["indiaImpact"])}</p>' if p.get("indiaImpact") else why(p)) or dek}{meta_row(p)}</aside></div></article>')


def grouped(posts, show_lead):
    out, groups = [], {}
    for p in posts:
        groups.setdefault(p.get("edition") or p["_dt"].astimezone(IST).date().isoformat(), []).append(p)
    first = True
    for items in groups.values():
        label = items[0].get("editionLabel") or portable_strftime(items[0]["_dt"].astimezone(IST), "%a %-d %b")
        rest = items
        sec = [f'<section class="edition"><h2 class="edhead"><b>{e(label)}</b><span>{len(items)} {"story" if len(items)==1 else "stories"}</span></h2>']
        if first and show_lead:
            li = next((i for i, p in enumerate(items) if p.get("lead")), 0)
            sec.append(lead(items[li])); rest = [p for i, p in enumerate(items) if i != li]
        if rest:
            sec.append('<div class="grid">' + "".join(card(p) for p in rest) + "</div>")
        sec.append("</section>")
        out.append("".join(sec)); first = False
    return "\n".join(out)


ORG_ID = "https://totalmarket.co.in/#organization"


def org_ld():
    """Publisher facts that are true and on the site: name, URL, existing logo, policy pages, contact channel."""
    return {"@context": "https://schema.org", "@type": "NewsMediaOrganization", "@id": ORG_ID, "name": SITE_NAME, "url": SITE_URL + "/",
            "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/assets/logo.png", "width": 512, "height": 512},
            "publishingPrinciples": f"{SITE_URL}/editorial-policy/", "correctionsPolicy": f"{SITE_URL}/corrections/",
            "verificationFactCheckingPolicy": f"{SITE_URL}/editorial-policy/", "actionableFeedbackPolicy": f"{SITE_URL}/contact/",
            "contactPoint": {"@type": "ContactPoint", "contactType": "corrections and feedback", "url": CONTACT_URL}}


CONTACT_URL = "https://github.com/Niftykingz/TotalMarket/issues"
GA_ID = "G-B21DEZHZYT"  # Google Analytics 4 measurement ID (owner's property)

# Likes: free no-login counter (Abacus). Comments: giscus (GitHub Discussions).
# categoryId comes from https://giscus.app after Discussions is enabled; until then a placeholder shows.
GISCUS = {"repo": "Niftykingz/TotalMarket", "repoId": "R_kgDOVQML4Q", "category": "Announcements", "categoryId": ""}


def like_key(p):
    h = hashlib.sha1(p["id"].encode()).hexdigest()[:8]
    return re.sub(r"[^a-z0-9-]", "", p["id"])[:52] + "-" + h


def engage_card(p):
    return f"""<section class="engage" aria-label="React to this story">
<div class="eg-text"><b>Did this story help you?</b><span>Tap like and tell us what you think in the comments.</span></div>
<div class="eg-btns"><button type="button" class="like-btn" data-like-key="{like_key(p)}" aria-pressed="false"><span class="heart" aria-hidden="true">&#9829;</span> <span class="lc">Like</span></button>
<a class="cm-btn" href="#comments"><span aria-hidden="true">&#128172;</span> Comment</a></div>
</section>"""


def comments_block(p):
    g = GISCUS
    if g.get("categoryId"):
        inner = (f'<div class="giscus" data-repo="{e(g["repo"])}" data-repo-id="{e(g["repoId"])}" '
                 f'data-category="{e(g["category"])}" data-category-id="{e(g["categoryId"])}"></div>')
    else:
        inner = '<p class="cm-soon">Comments are opening soon. Meanwhile, share your view on X or Telegram using the buttons above.</p>'
    return f"""<section class="comments" id="comments" aria-label="Comments">
<h2><span aria-hidden="true">&#128172;</span> Comments</h2>
<p class="cm-note">Be respectful and stay on topic. No stock tips or promotions; comments are moderated.</p>
{inner}
</section>"""


def article_page(p, posts, meta):
    path = url(p)
    link = abs_url(path)
    text = quote(p["title"] + " " + link)
    srcs = "".join(
        f'<li><a href="{e(s.get("url"))}" rel="noopener nofollow" target="_blank">{e(s.get("name") or s.get("url"))}</a></li>'
        for s in (p.get("sources") or []) if re.match(r"https?://", str(s.get("url", ""))))
    related = [x for x in posts if x["category"] == p["category"] and x["id"] != p["id"]][:4]
    rel = ('<section class="related"><h2 class="edhead"><b>More in ' + e(CATS[p["category"]][0]) + '</b></h2><div class="grid">'
           + "".join(card(x) for x in related) + "</div></section>") if related else ""
    ld = {
        "@context": "https://schema.org", "@type": "NewsArticle",
        "headline": p["title"][:110], "description": desc(p),
        "datePublished": p["_dt"].isoformat(), "dateModified": (parse_dt(p.get("updatedAt")) or p["_dt"]).isoformat(),
        "mainEntityOfPage": link, "image": [abs_url(cover_url(p)), cover_url(p, True)],
        "articleSection": CATS[p["category"]][0],
        "author": {"@type": "Organization", "name": SITE_NAME, "url": SITE_URL + "/about/"},
        "publisher": {"@type": "Organization", "@id": ORG_ID, "name": SITE_NAME,
                      "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/assets/logo.png", "width": 512, "height": 512}},
        "isAccessibleForFree": True, "inLanguage": "en-IN",
    }
    ld["keywords"] = ", ".join(page_keywords(p))
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
        {"@type": "ListItem", "position": 2, "name": CATS[p["category"]][0], "item": f"{SITE_URL}/{p['category']}/"},
        {"@type": "ListItem", "position": 3, "name": p["title"], "item": link}]}
    extra = ("".join(f'<meta property="article:tag" content="{e(t)}">' for t in p["_tags"])
             + f'<script type="application/ld+json">{json.dumps(crumbs, ensure_ascii=False).replace("</", "<\\/")}</script>'
             f'<meta property="article:published_time" content="{e(p["_dt"].isoformat())}">'
             f'<meta property="article:section" content="{e(CATS[p["category"]][0])}">'
             f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")}</script>')
    # Structured market reports use one data-led dashboard, not duplicated KPI cards.
    # Narrative is concise and follows the verified visual/table report.
    body_html = "".join(f"<p>{e(t)}</p>" for t in p["_paras"])
    if p.get("reportType") == "weekly_market":
        sections = []
        for para in p["_paras"]:
            if " | " in para:
                heading, detail = para.split(" | ", 1)
                sections.append(f'<section class="tm-week-section"><h2>{e(heading.title())}</h2><p>{e(detail)}</p></section>')
            else:
                sections.append(f'<p>{e(para)}</p>')
        body_html = ('<style>.tm-week-section{padding:18px 0;border-bottom:1px solid var(--line,#dce4ec)}'
                     '.tm-week-section h2{font-size:clamp(18px,2.5vw,23px);margin:0 0 9px;font-weight:800}'
                     '.tm-week-section p{margin:0;line-height:1.75}</style>' + "".join(sections))
    dek = f'<p class="dek">{e(p.get("dek"))}</p>' if p.get("dek") else ""
    body = f"""<article class="story" style="--dot:var(--c-{p['category']})">
<nav class="crumbs"><a href="{BASE}">Home</a> / <a href="{BASE}{p['category']}/">{e(CATS[p['category']][0])}</a></nav>
{cover_img(p, "hero", True)}
{chip(p)}
<h1>{e(p['title'])}</h1>
{dek}
{meta_row(p)}
{f'<p class="hi-note" lang="hi"><a href="{hindi.hurl(p, BASE)}">यह खबर हिंदी में पढ़ें →</a></p>' if hindi.has_hi(p) else ""}
<div class="byline">{piggy_img("head96", "by-av")}<span>By <b>Boss Piggy AI</b> · TotalMarket AI market desk</span></div>
{f'<p class="chg"><b>What changed</b>{e(p["changeNote"])}</p>' if p.get("changeNote") else ""}
{people_strip(p)}
{report.render_weekly(p.get("report")) if p.get("reportType") == "weekly_market" else ""}
<div class="body">{body_html}</div>
{report.render_outlook(p.get("report")) if p.get("reportType") == "weekly_market" else ""}
{piggy_box(p)}
{report.render(p.get("report")) if p.get("reportType") != "weekly_market" else ""}
{data_table(p)}
{impacts(p)}
{why(p)}
<div class="share" aria-label="Share this story">
<a href="https://wa.me/?text={text}" target="_blank" rel="noopener">Share on WhatsApp</a>
<a href="https://twitter.com/intent/tweet?text={quote(p['title'])}&url={quote(link)}" target="_blank" rel="noopener">Share on X</a>
<a href="https://t.me/share/url?url={quote(link)}&text={quote(p['title'])}" target="_blank" rel="noopener">Share on Telegram</a>
<button type="button" class="copy" data-url="{e(link)}">Copy link</button>
</div>
<div class="tags" aria-label="Topics">{"".join(f'<a class="tag" href="{BASE}tag/{slug(t)}/">#{e(t)}</a>' for t in p["_tags"])}</div>
{'<div class="sources"><h2>Sources</h2><ul>' + srcs + '</ul></div>' if srcs else ''}
<p class="disc">Written by Boss Piggy AI for TotalMarket. Based on the sources linked in this article; key facts and data should be checked against the original sources. This article is for information only and is not investment advice.</p>
</article>
{rel}"""
    alts = [("en", link), ("hi", abs_url(hindi.hurl(p, BASE)))] if hindi.has_hi(p) else None
    sw = (hindi.hurl(p, BASE), "हिंदी में पढ़ें") if alts else None
    return page(p["title"], p.get("seoDescription") or desc(p), path, body, meta, og_type="article", extra_head=extra, image=cover_url(p, True),
                seo_title=(p.get("seoTitle") + f" | {SITE_NAME}") if p.get("seoTitle") else None, keywords=page_keywords(p), news_kw=p["_tags"][:10],
                alternates=alts, switch=sw)


def about_page(meta):
    path = f"{BASE}about/"
    body = f"""<article class="story">
<h1>About TotalMarket</h1>
<div class="body">
<p>TotalMarket is a free news site for Indian investors and traders who also follow technology. It covers stock market moves and upcoming results, IPOs and startup funding, tech and AI, RBI and SEBI decisions, overnight global markets, and gold, silver, crude oil and currencies, with what each move means globally and for India.</p>
<p><b>How it is made.</b> Every story is researched and written automatically by Boss Piggy AI, TotalMarket's AI market desk, using reporting from the sources linked at the end of each story. The site updates four times on each market day: a pre-market brief around 8:45 am, a midday check around 12:45 pm, a closing wrap around 3:45 pm and an evening tech and startups update around 8:45 pm IST, with one roundup on weekends and market holidays.</p>
<p><b>Analytics.</b> The site uses Google Analytics to count visits and popular stories.</p>
<p><b>Accuracy.</b> Stories state only facts found in their sources and link to them so you can check. AI can still make mistakes, so for anything that affects a decision, open the original source.</p>
<p><b>Not investment advice.</b> TotalMarket reports and explains news. It never recommends buying, selling or holding any security, does not give price targets, and is not registered with SEBI as an investment adviser or research analyst.</p>
<p><b>Policies.</b> Read our <a href="{BASE}editorial-policy/">editorial policy</a> and <a href="{BASE}corrections/">corrections policy</a>, or <a href="{BASE}contact/">contact us</a>.</p>
<p><b>Follow along.</b> Subscribe with any feed reader using the <a href="{SITE_URL}/rss.xml">RSS feed</a>.</p>
</div></article>"""
    return page("About TotalMarket", "How TotalMarket covers Indian markets and tech news, and how its AI-written stories are made, sourced and corrected.", path, body, meta,
                extra_head=f'<script type="application/ld+json">{json.dumps(org_ld(), ensure_ascii=False)}</script>')


def policy_pages(meta):
    """About-the-newsroom pages. Facts only: how stories are actually produced, sourced, corrected and how to reach us."""
    pages = []
    def mk(slug_, title, d, html_):
        path = f"{BASE}{slug_}/"
        body = f'<article class="story"><h1>{e(title)}</h1><div class="body">{html_}</div></article>'
        crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": title, "item": SITE_URL + path}]}
        pages.append((f"{slug_}/index.html", page(title, d, path, body, meta,
                      extra_head=f'<script type="application/ld+json">{json.dumps([org_ld(), crumbs], ensure_ascii=False)}</script>')))
    mk("editorial-policy", "Editorial policy", "How TotalMarket chooses, sources, checks and labels its AI-written market news, and what it never publishes.",
       f"""<p><b>Who writes the stories.</b> Every story on TotalMarket is researched and written by <b>Boss Piggy AI</b>, TotalMarket's AI market desk, and published under the TotalMarket name. We do not present AI-written stories as the work of human reporters, and we do not invent bylines, credentials or quotes.</p>
<p><b>Sources.</b> Each story lists the sources it is based on at the end of the page. For company results we use the company's exchange filing on NSE or BSE where we can read it, and say so when a figure is still "as reported" by a news outlet. Market data is labelled EOD (end-of-day close), DELAYED or PRELIMINARY with its date and source; TotalMarket has no live price feed and never labels data as live.</p>
<p><b>Checks before publishing.</b> A story is published only when its key facts, dates and figures appear in the cited sources. Significant or disputed figures are checked against a second source; when sources disagree we say so or leave the figure out. Numbers shown on cover graphics come only from that verified data.</p>
<p><b>What we never publish.</b> Buy, sell or hold recommendations, price targets or tips. TotalMarket is not registered with SEBI as an investment adviser or research analyst.</p>
<p><b>Updates.</b> When a developing story changes, the page shows an "Updated" time and a "What changed" note. See the <a href="{BASE}corrections/">corrections policy</a>.</p>""")
    mk("corrections", "Corrections policy", "How TotalMarket fixes mistakes: what is corrected, how changes are shown on the page and how to report an error.",
       f"""<p>If a fact, figure, date or name in a TotalMarket story is wrong, we correct it on the same page as soon as we confirm the error.</p>
<p><b>How corrections are shown.</b> The story keeps its original publication time, gains an "Updated" time, and shows a <b>What changed</b> note at the top that says what was corrected (for example, a subscription figure replaced with the final number). Updates to developing stories, such as preliminary closing figures replaced by exact closes, are shown the same way.</p>
<p><b>Report an error.</b> Open an issue on our public GitHub repository at <a href="{CONTACT_URL}" rel="noopener">{CONTACT_URL}</a> with the page link and what is wrong, ideally with a source. Reports are reviewed during the next scheduled update.</p>""")
    mk("contact", "Contact TotalMarket", "How to reach TotalMarket to report an error, suggest a story or give feedback.",
       f"""<p>The best way to reach TotalMarket is through our public GitHub repository: <a href="{CONTACT_URL}" rel="noopener">{CONTACT_URL}</a>. Open an issue to report an error, suggest a story or send feedback.</p>
<p>Please include the link to the page you are writing about. For corrections, see the <a href="{BASE}corrections/">corrections policy</a>; for how stories are made, see the <a href="{BASE}editorial-policy/">editorial policy</a>.</p>
<p>TotalMarket does not give personal investment advice, so we cannot answer questions about what to buy or sell.</p>""")
    return pages


def tag_pages(posts, meta):
    by = {}
    for p in posts:
        for t in p["_tags"]:
            by.setdefault(slug(t), [t, []])[1].append(p)
    for sl, (name, items) in by.items():
        path = f"{BASE}tag/{sl}/"
        body = (f'<div class="sechead"><h1>{e(name)}</h1><p>Latest TotalMarket news and explainers on {e(name)}, with what it means for India.</p></div>'
                + grouped(items[:SECTION_LIMIT], False))
        thin = len(items) < TAG_MIN_STORIES  # thin tag pages stay reachable but are kept out of search results and the sitemap
        write(f"tag/{sl}/index.html", page(f"{name}: latest news and analysis", f"Latest news on {name}: market moves, key numbers and what it means for India.",
                                          path, body, meta, keywords=[name, "India", "market news"], noindex=thin))
    return [sl for sl, (_, items) in by.items() if len(items) >= TAG_MIN_STORIES]


TAG_MIN_STORIES = 3


def report_banner(posts):
    reps = [p for p in posts if p.get("report")]
    if not reps:
        return ""
    p = reps[0]; r = p["report"]
    k = "".join(f'<span class="tk"><span>{e(x.get("label"))}</span>{e(x.get("value"))}<em class="{"down" if str(x.get("change","")).startswith("-") else "up"}">{e(x.get("change"))}</em></span>' for x in (r.get("kpis") or [])[:4])
    return (f'<a class="rbanner" href="{url(p)}"><span class="eyebrow">Daily market report · {e(r.get("dateLabel") or "")}</span>'
            f'<b>{e(p["title"])}</b><span class="rk">{k}</span><span class="go">Full report: indices, sectors, gainers &amp; losers, FII/DII, IPO listings →</span></a>')


def report_page(posts, meta):
    path = f"{BASE}market-report/"
    reps = [p for p in posts if p.get("report")]
    body = (f'<div class="sechead"><h1>Daily stock market report</h1><p>Every market day after 8 pm: Sensex, Nifty and Bank Nifty with day high and low, large vs mid vs small caps, sector heatmap, top gainers and losers, FII/DII data, IPO listings, market breadth and what to watch next.</p></div>'
            + report_banner(reps) + markets.archive_html(reps, meta, {"e": e, "base": BASE, "url": url})
            + ("" if reps else '<div class="empty"><p>The first report is on its way. It publishes after 8 pm on each market day.</p></div>'))
    return page("Daily Stock Market Report", "Daily Indian stock market report: Sensex and Nifty close, day range, FII DII data, top gainers and losers, sectors, IPO listings and breadth.",
                path, body, meta, seo_title="Daily Stock Market Report: Sensex, Nifty, FII DII | TotalMarket",
                keywords=["stock market today", "share market today", "Sensex today", "Nifty today", "FII DII data", "top gainers and losers", "sector performance", "IPO listing today", "market report"])


def status_badge(p):
    st = STATUS_BADGE.get(str(p.get("status") or "").lower())
    return f'<span class="stbadge st-{e(str(p["status"]).lower())}" data-nosnippet>{e(st)}</span>' if st else ""


def section_page(key, posts, meta, results=()):
    name, blurb = CATS[key]
    path = f"{BASE}{key}/"
    cc = {"e": e, "url": url, "base": BASE, "cover_url": cover_url, "ago": ago, "ist": IST, "cats": CATS, "slug": slug,
          "cat_labels": CATS_LABELS, "company_slugs": COMPANY_SLUGS, "status_badge": status_badge, "limit": SECTION_LIMIT,
          "ipo_widget": hubs.ipo_widget(IPO_LIST, e, BASE),
          "rates_card": home.rates_card(meta, {"e": e, "base": BASE})}
    body = category.body(key, posts, meta, results, cc)
    kw = {"markets": ["Sensex today", "Nifty 50", "stock market news India", "share market today"], "tech": ["AI news", "tech news India"],
          "startups": ["IPO news", "upcoming IPO", "startup funding India"], "policy": ["RBI policy", "SEBI news", "budget"],
          "global": ["global market news", "US stock market", "Fed rate"], "commodities": ["gold rate today", "silver price today", "crude oil price", "rupee vs dollar"]}[key]
    items = [p for p in posts if p["category"] == key][:30]
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": f"{name} news", "url": abs_url(path), "description": blurb,
          "mainEntity": {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": abs_url(url(p))} for i, p in enumerate(items)]}}
    return page(f"{name} news today", blurb, path, body, meta, keywords=kw,
                extra_head=f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>')


def ago(p):
    mins = int((datetime.now(IST) - p["_dt"]).total_seconds() // 60)
    if mins < 60: return f"{max(mins,1)} min ago"
    if mins < 60 * 24: return f"{mins // 60} hours ago" if mins >= 120 else "1 hour ago"
    return portable_strftime(p["_dt"].astimezone(IST), "%-d %b")


def mini(p, cls="mini"):
    return (f'<a class="{cls}" href="{url(p)}"><img src="{cover_url(p)}" width="1600" height="900" alt="" loading="lazy" decoding="async">'
            f'<span><b>{e(p["title"])}</b><small>{e(ago(p))}</small></span></a>')


def line_chart(points, w=320, h=150):
    vals = [float(x["v"]) for x in points]
    if len(vals) < 2:
        return '<p class="muted">Chart builds up as daily closes are recorded.</p>'
    lo, hi = min(vals), max(vals); pad = (hi - lo) * .12 or 1; lo -= pad; hi += pad
    X = lambda i: 44 + i * (w - 54) / (len(vals) - 1); Y = lambda v: 8 + (hi - v) / (hi - lo) * (h - 34)
    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
    c = "up" if vals[-1] >= vals[0] else "down"
    grid = "".join(f'<line x1="44" x2="{w-10}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/><text x="40" y="{Y(v)+4:.1f}" text-anchor="end">{v:,.0f}</text>'
                   for v in (lo + pad, (lo + hi) / 2, hi - pad))
    labels = "".join(f'<text x="{X(i):.1f}" y="{h-6}" text-anchor="{"end" if i == len(points) - 1 else "start" if i == 0 else "middle"}">{portable_strftime(datetime.fromisoformat(x["d"]), "%-d %b")}</text>'
                     for i, x in enumerate(points) if i in (0, len(points) - 1) or len(points) <= 7)
    area = f"44,{h-26} " + pts + f" {X(len(vals)-1):.1f},{h-26}"
    return (f'<svg class="lchart {c}" viewBox="0 0 {w} {h}" role="img" aria-label="Recent closing levels">'
            f'<g class="g">{grid}</g><polygon class="a" points="{area}"/><polyline class="l" points="{pts}"/>'
            f'<circle class="d" cx="{X(len(vals)-1):.1f}" cy="{Y(vals[-1]):.1f}" r="4"/><g class="x">{labels}</g></svg>')


def market_widget(posts, meta):
    hist = meta.get("history") or {}
    tabs, panels = [], []
    for i, name in enumerate([n for n in ("Nifty 50", "Sensex", "Bank Nifty") if hist.get(n)]):
        pts = hist[name]; last = float(pts[-1]["v"]); prev = float(pts[-2]["v"]) if len(pts) > 1 else last
        ch = last - prev; pc = ch / prev * 100 if prev else 0
        tabs.append(f'<button type="button" class="wt{" on" if i == 0 else ""}" data-panel="mw{i}">{e(name)}</button>')
        panels.append(f'<div class="wp" id="mw{i}"{"" if i == 0 else " hidden"}><div class="wbig"><b>{last:,.2f}</b>'
                      f'<span class="{"up" if ch >= 0 else "down"}">{ch:+,.2f} ({pc:+.2f}%)</span></div>{line_chart(pts)}'
                      f'<p class="wnote">Closing levels, last {len(pts)} sessions</p></div>')
    rep = next((p for p in posts if p.get("report")), None)
    gl = ""
    if rep:
        r = rep["report"]
        def rows(items):
            return "".join(f'<tr><th scope="row">{e(x.get("name"))}</th><td class="num">{e(x.get("price") or "")}</td>'
                           f'<td class="num {"down" if str(x.get("pct","")).startswith("-") else "up"}">{"" if str(x.get("pct","")).startswith(("-","+")) else "+"}{e(x.get("pct"))}%</td></tr>' for x in items[:5])
        gl = (f'<div class="wtabs sm"><button type="button" class="wt on" data-panel="mg0">Top gainers</button><button type="button" class="wt" data-panel="mg1">Top losers</button></div>'
              f'<div class="wp" id="mg0"><table class="mt"><tbody>{rows(r.get("gainers") or [])}</tbody></table></div>'
              f'<div class="wp" id="mg1" hidden><table class="mt"><tbody>{rows(r.get("losers") or [])}</tbody></table></div>'
              f'<a class="more" href="{url(rep)}">Full market report →</a>')
    if not tabs and not gl:
        return ""
    return f'<aside class="widget market"><div class="wtabs">{"".join(tabs)}</div>{"".join(panels)}{gl}</aside>'


def section_cols(posts):
    cols = []
    for key, icon in (("startups", "▲"), ("tech", "◆"), ("global", "◍"), ("commodities", "●")):
        items = [p for p in posts if p["category"] == key][:4]
        if not items:
            continue
        top = items[0]
        rest = "".join(mini(p) for p in items[1:])
        cols.append(f'<section class="scol" style="--dot:var(--c-{key})"><h2><a href="{BASE}{key}/"><span class="ic">{icon}</span>{e(CATS[key][0])} <span class="arr">→</span></a></h2>'
                    f'<a class="sfeat" href="{url(top)}"><img src="{cover_url(top)}" width="1600" height="900" alt="" loading="lazy" decoding="async">'
                    f'<b>{e(top["title"])}</b><span>{e(top.get("dek") or "")}</span><small>{e(ago(top))}</small></a>{rest}</section>')
    return f'<div class="scols">{"".join(cols)}</div>' if cols else ""


def latest_list(posts):
    chips = '<button type="button" class="chipf on" data-cat="all">All</button>' + "".join(
        f'<button type="button" class="chipf" data-cat="{k}">{e(v[0])}</button>' for k, v in CATS.items())
    rows = "".join(
        f'<li data-cat="{p["category"]}"><a href="{url(p)}"><img src="{cover_url(p)}" width="1600" height="900" alt="" loading="lazy" decoding="async">'
        f'<span><em style="--dot:var(--c-{p["category"]})">{e(CATS[p["category"]][0])}</em><b>{e(p["title"])}</b>'
        f'<i>{e(p.get("dek") or "")}</i><small>{e(ago(p))} · {int(p.get("readMins") or 2)} min read</small></span></a></li>' for p in posts[:30])
    return (f'<section class="latest"><div class="lhead"><h2>Latest news</h2></div><div class="chips" id="latestchips">{chips}</div>'
            f'<ul class="llist" id="latestlist">{rows}</ul></section>')


def side_panels(posts, results):
    rep = next((p for p in posts if p.get("report")), None)
    movers = ""
    if rep:
        r = rep["report"]
        rows = "".join(f'<tr><th scope="row">{e(x.get("name"))}</th><td class="num">{e(x.get("price") or "—")}</td>'
                       f'<td class="num {"down" if str(x.get("pct","")).startswith("-") else "up"}">{"" if str(x.get("pct","")).startswith(("-","+")) else "+"}{e(x.get("pct"))}%</td></tr>'
                       for x in (r.get("gainers") or [])[:5] + (r.get("losers") or [])[:5])
        movers = (f'<section class="panel"><h2>Market movers <small>{e(r.get("moversIndex") or "Nifty 50")} · {e(r.get("dateLabel") or "")}</small></h2>'
                  f'<table class="mt"><thead><tr><th>Stock</th><th>Price</th><th>% Chg</th></tr></thead><tbody>{rows}</tbody></table></section>')
    counts = {}
    for p in posts[:80]:
        for t in p["_tags"]:
            if t not in CATS_LABELS:
                counts[t] = counts.get(t, 0) + 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:14]
    trend = ('<section class="panel"><h2>Trending topics</h2><div class="tags">'
             + "".join(f'<a class="tag" href="{BASE}tag/{slug(t)}/">#{e(t)}</a>' for t, _ in top) + "</div></section>") if top else ""
    return hubs.ipo_widget(IPO_LIST, e, BASE) + tools.side_panel(BASE) + movers + results_widget(results) + trend


CATS_LABELS = {v[0] for v in CATS.values()}


def home_page(posts, meta, results=()):
    hc = {"e": e, "url": url, "base": BASE, "cover_url": cover_url, "ago": ago, "ist": IST, "cats": CATS, "site_name": SITE_NAME, "tagline": TAGLINE,
          "holidays": HOLIDAYS_PATH, "latest_list": latest_list}
    body = home.body(posts, meta, results, IPO_LIST, hc)
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "@id": SITE_URL + "/#website", "name": SITE_NAME, "url": SITE_URL + "/",
           "description": TAGLINE, "inLanguage": "en-IN", "publisher": {"@id": ORG_ID}}, org_ld()]
    return page(SITE_NAME, "Sensex and Nifty news, gold and silver rates, crude oil, rupee, IPOs, results and global markets, explained simply with what each move means for India.",
                BASE, body, meta, seo_title=HOME_TITLE, keywords=HOME_KEYWORDS, extra_head=f'<script type="application/ld+json">{json.dumps(ld)}</script>')


def search_index(posts):
    rows = [{"t": p["title"], "u": url(p), "c": CATS[p["category"]][0], "k": " ".join(p["_tags"]), "d": portable_strftime(p["_dt"].astimezone(IST), "%-d %b")}
            for p in posts[:400]]
    rows += [{"t": p["hi"]["title"], "u": hindi.hurl(p, BASE), "c": "हिंदी · " + hindi.CAT_HI[p["category"]], "k": " ".join(p["_tags"]) + " hindi " + p["title"],
              "d": portable_strftime(p["_dt"].astimezone(IST), "%-d %b")} for p in posts[:400] if hindi.has_hi(p)]
    return json.dumps(rows, ensure_ascii=False)


def rss(posts):
    items = []
    for p in posts[:50]:
        link = abs_url(url(p))
        items.append(f"""<item><title>{e(p['title'])}</title><link>{link}</link><guid isPermaLink="true">{link}</guid>
<pubDate>{p['_dt'].astimezone(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
<category>{e(CATS[p['category']][0])}</category><description>{e(desc(p))}</description></item>""")
    now = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>{SITE_NAME}</title><link>{SITE_URL}/</link>
<description>{e(TAGLINE)}</description><language>en-in</language><lastBuildDate>{now}</lastBuildDate>
{''.join(items)}
</channel></rss>
"""


def sitemap(posts):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    urls = [(SITE_URL + "/", now, "hourly")] + [(f"{SITE_URL}/{k}/", now, "hourly") for k in CATS] + [(SITE_URL + "/about/", None, "monthly"), (SITE_URL + "/results/", now, "daily"), (SITE_URL + "/market-report/", now, "daily")] + [(u, now, "daily") for u in TOOL_URLS] + [(f"{SITE_URL}/tag/{t}/", now, "daily") for t in TAG_SLUGS] + [(u, now, "daily") for u in HUB_URLS]
    urls += [(abs_url(url(p)), p["_dt"].astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), None) for p in posts]
    urls += [(u, now, "hourly") for u in hindi.HUB_URLS]
    urls += [(abs_url(hindi.hurl(p, BASE)), p["_dt"].astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), None) for p in posts if hindi.has_hi(p)]
    rows = "".join(f"<url><loc>{e(u)}</loc>{f'<lastmod>{m}</lastmod>' if m else ''}{f'<changefreq>{c}</changefreq>' if c else ''}</url>" for u, m, c in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{rows}</urlset>\n'


def news_sitemap(posts):
    cutoff = datetime.now(timezone.utc) - timedelta(days=2)
    rows = "".join(
        f"<url><loc>{e(abs_url(url(p)))}</loc><news:news><news:publication><news:name>{SITE_NAME}</news:name>"
        f"<news:language>en</news:language></news:publication><news:publication_date>{p['_dt'].isoformat()}</news:publication_date>"
        f"<news:title>{e(p['title'])}</news:title></news:news></url>"
        for p in posts if p["_dt"] >= cutoff) + "".join(
        f"<url><loc>{e(abs_url(hindi.hurl(p, BASE)))}</loc><news:news><news:publication><news:name>{SITE_NAME}</news:name>"
        f"<news:language>hi</news:language></news:publication><news:publication_date>{p['_dt'].isoformat()}</news:publication_date>"
        f"<news:title>{e(p['hi']['title'])}</news:title></news:news></url>"
        for p in posts if p["_dt"] >= cutoff and hindi.has_hi(p))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            f'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">{rows}</urlset>\n')


_COVER_IMG = re.compile(r'<img([^>]*?) src="(/covers/[^"]+?)\.webp"([^>]*)>')


def responsive_covers(html_):
    """Give every cover image an 800px + 1600px srcset so phones and small cards download the small file."""
    def rep(m):
        before, stem, after = m.group(1), m.group(2), m.group(3)
        if "srcset=" in before + after or stem.endswith("-800"):
            return m.group(0)
        hero = 'fetchpriority="high"' in before + after
        sizes = "(max-width: 1100px) 100vw, 760px" if hero else "(max-width: 700px) 100vw, 420px"
        return f'<img{before} src="{stem}.webp" srcset="{stem}-800.webp 800w, {stem}.webp 1600w" sizes="{sizes}"{after}>'
    return _COVER_IMG.sub(rep, html_)


def write(rel, content):
    if rel.endswith(".html"):
        content = hindi.link_english(rel, content, SITE_URL, BASE)
        content = responsive_covers(content)
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    meta = json.load(open(os.path.join(DATA, "meta.json"), encoding="utf-8"))
    posts = load_posts()
    if os.path.isdir(OUT):
        for name in os.listdir(OUT):
            if name in ("assets", "covers", "logos"):
                continue
            target = os.path.join(OUT, name)
            shutil.rmtree(target) if os.path.isdir(target) else os.remove(target)
    shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(OUT, "assets"), dirs_exist_ok=True)
    if os.path.isdir(LOGO_DIR):
        shutil.copytree(LOGO_DIR, os.path.join(OUT, "logos"), dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.md"))
    covers.ensure_covers(posts, os.path.join(OUT, "covers"))
    results = load_results()
    global COMPANY_SLUGS, IPO_LIST, HUB_URLS, HOLIDAYS_PATH
    HOLIDAYS_PATH = markets.holidays_path(datetime.now(IST).date())
    ctx = {"page": page, "e": e, "base": BASE, "card": card, "piggy_host": piggy_host, "meta": meta, "slug": slug, "ist": IST, "today": datetime.now(IST).date(), "now": datetime.now(IST)}
    cpages, comps = hubs.company_pages(posts, results, ctx)
    ipages, IPO_LIST = hubs.ipo_pages(posts, ctx)
    COMPANY_SLUGS = set(comps)
    ctx.update({"url": url, "site_url": SITE_URL, "piggy_box": piggy_data, "line_chart": line_chart})
    extra_pages = (markets.holidays_page(ctx) + markets.events_page(posts, results, ctx) + hubs.fii_dii_page(posts, ctx) + hubs.gainers_page(posts, ctx) + hubs.live_page(posts, ctx) + hubs.learn_page(ctx)
                   + hubs.global_page(posts, ctx) + hubs.nifty_page(posts, ctx))
    for rel, html_ in cpages + ipages + extra_pages:
        write(rel, html_)
        HUB_URLS.append(SITE_URL + "/" + rel.replace("index.html", ""))
    write("index.html", home_page(posts, meta, results))
    write("results/index.html", results_page(results, meta))
    write("market-report/index.html", report_page(posts, meta))
    global TAG_SLUGS
    TAG_SLUGS = tag_pages(posts, meta)
    for k in CATS:
        write(f"{k}/index.html", section_page(k, posts, meta, results))
    for p in posts:
        write(f"news/{p['id']}/index.html", article_page(p, posts, meta))
    write("about/index.html", about_page(meta))
    for rel, html_ in policy_pages(meta):
        write(rel, html_)
        HUB_URLS.append(SITE_URL + "/" + rel.replace("index.html", ""))
    hctx = {"page": page, "e": e, "base": BASE, "site_url": SITE_URL, "abs_url": abs_url, "url": url, "cover_url": cover_url, "cover_img": cover_img,
            "piggy_img": piggy_img, "parse_dt": parse_dt, "ist": IST, "report": report, "like_key": like_key, "comments_block": comments_block,
            "slug": slug, "page_keywords": page_keywords, "site_name": SITE_NAME, "data_table": data_table}
    for rel, html_ in hindi.build(posts, meta, hctx):
        write(rel, html_)
    for rel, html_ in hindi.data_pages(posts, meta, hctx):
        write(rel, html_)
    global TOOL_URLS
    tool_pages, TOOL_URLS = tools.build(page, e, BASE, SITE_URL, meta)
    for rel, html_ in tool_pages:
        write(rel, html_)
    write("404.html", page("Page not found", "This page does not exist.", f"{BASE}404.html",
                           f'<div class="empty"><h1>Page not found</h1><p><a href="{BASE}">Go to the latest stories</a></p></div>', meta, noindex=True))
    write("search.json", search_index(posts))
    write("rss.xml", rss(posts))
    write("sitemap.xml", sitemap(posts))
    write("news-sitemap.xml", news_sitemap(posts))
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\nSitemap: {SITE_URL}/news-sitemap.xml\n")
    write(".nojekyll", "")
    write("market-calendar.json", markets.calendar_json())
    write("data/index-closes.csv", markets.index_csv(meta))
    write("CNAME", "totalmarket.co.in\n")
    # Preserve dated, source-linked IPO desk reports across clean site builds.
    # These are static editorial archives, separate from the gated story pipeline.
    ipo_archive = os.path.join(DATA, "ipo_reports")
    if os.path.isdir(ipo_archive):
        for filename in sorted(os.listdir(ipo_archive)):
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.html", filename):
                continue
            archive_dir = os.path.join(OUT, "ipo-update-" + filename[:-5])
            os.makedirs(archive_dir, exist_ok=True)
            shutil.copyfile(os.path.join(ipo_archive, filename), os.path.join(archive_dir, "index.html"))

    shutil.copy(os.path.join(ROOT, "assets", "favicon.ico"), os.path.join(OUT, "favicon.ico"))
    write("site.webmanifest", json.dumps({"name": "TotalMarket", "short_name": "TotalMarket", "start_url": "/", "display": "standalone",
                                          "background_color": "#102A43", "theme_color": "#102A43",
                                          "icons": [{"src": "/assets/icon-192.png", "sizes": "192x192", "type": "image/png"},
                                                    {"src": "/assets/icon-512.png", "sizes": "512x512", "type": "image/png"}]}))  # custom domain for GitHub Pages
    print(f"Built {len(posts)} stories into docs/")
    for w in markets.calendar_warnings(datetime.now(IST).date()) + markets.events_warnings(datetime.now(IST).date()):
        print(w)


if __name__ == "__main__":
    main()
