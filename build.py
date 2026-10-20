#!/usr/bin/env python3
"""Build the TotalMarket static site.

Reads stories from data/posts/*.json and data/meta.json, writes the public
site to docs/ (served by GitHub Pages). No third-party packages needed.

Run:  python3 build.py
"""
import hashlib, html, json, os, re, shutil, sys
import covers
import report
import art
import tools
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "docs")
SITE_URL = "https://niftykingz.github.io/TotalMarket"   # no trailing slash
BASE = "/TotalMarket/"                                   # path prefix on GitHub Pages
SITE_NAME = "TotalMarket"
TAGLINE = "Indian markets, IPOs, tech and AI news, explained"
TAG_SLUGS = []
TOOL_URLS = []
HOME_TITLE = "TotalMarket: Sensex, Nifty, Gold Rate, Crude Oil, IPO & Global Market News Today"
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


def fmt_ist(d, with_date=True):
    d = d.astimezone(IST)
    t = d.strftime("%-I:%M %p").lower()
    return (d.strftime("%-d %b %Y, ") + t + " IST") if with_date else t + " IST"


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
    return d if len(d) <= 160 else d[:157].rsplit(" ", 1)[0] + "…"


FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Condensed:wght@600;700'
         '&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">')


def page(title, description, path, body, meta, og_type="website", extra_head="", noindex=False, image=None, seo_title=None, keywords=(), news_kw=None):
    canon = abs_url(path)
    nk = list(news_kw if news_kw else keywords)[:10]
    kw = (f'<meta name="keywords" content="{e(", ".join(keywords))}">' if keywords else "") + (f'<meta name="news_keywords" content="{e(", ".join(nk))}">' if nk else "")
    og = image or f"{SITE_URL}/assets/og.png"
    full_title = seo_title or (title if title.startswith(SITE_NAME) else f"{title} | {SITE_NAME}")
    head = f"""<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(description)}">
{kw}
<link rel="canonical" href="{e(canon)}">
{'<meta name="robots" content="noindex">' if noindex else '<meta name="robots" content="index,follow,max-image-preview:large">'}
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(canon)}">
<meta property="og:image" content="{e(og)}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="675">
<meta property="og:locale" content="en_IN">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(description)}">
<meta name="twitter:image" content="{e(og)}">
<meta name="theme-color" content="#0A0B0D">
<meta name="google-site-verification" content="R-bU7412W25OlS3wPOdJYbHHIF8P7FdcDqTH9Zd-Xfo">
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag("js",new Date());gtag("config","{GA_ID}");</script>
<link rel="icon" href="{BASE}assets/favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="{SITE_NAME}" href="{SITE_URL}/rss.xml">
<script>try{{var t=localStorage.getItem("tm-theme");if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
{FONTS}
<link rel="stylesheet" href="{BASE}assets/style.css">
{extra_head}
</head>
<body>
{header(meta, path)}
<main class="wrap main">
{body}
</main>
{footer()}
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


def header(meta, path):
    t = meta.get("ticker") or []
    cards = "".join(
        f'<div class="tcard"><span class="tl">{e(x.get("label"))}</span><span class="tv">{e(x.get("value") or "—")}</span>'
        f'<span class="tc {"down" if str(x.get("change","")).startswith("-") else "up"}">{e(x.get("change"))}</span>{spark(hist_vals(meta, x.get("label")))}</div>'
        for x in t)
    asof = f'<div class="tcard asof"><span class="tl">As of</span><span class="tv small">{e(meta.get("tickerAsOf"))}</span></div>' if meta.get("tickerAsOf") else ""
    tick = f'<div class="tickers" aria-label="Market snapshot"><div class="wrap trow">{cards}{asof}</div></div>' if t else ""
    links = [("", "Home")] + [(k + "/", v[0]) for k, v in CATS.items()] + [("market-report/", "Daily report"), ("gold-rate-today/", "Gold rate"), ("calculators/", "Calculators"), ("results/", "Results")]
    nav = "".join(f'<a class="tab{" on" if path == BASE + k else ""}" href="{BASE}{k}">{e(n)}</a>' for k, n in links)
    return f"""<header class="top">
<div class="wrap bar1">
<a class="brand" href="{BASE}"><span class="bm">Total<b>Market</b></span><span class="bt">Markets · Startups · IPOs · Tech · Global</span></a>
<div class="search" role="search"><input id="q" type="search" placeholder="Search companies, IPOs, news, markets…" aria-label="Search TotalMarket" autocomplete="off"><div id="qres" class="qres" hidden></div></div>
<button class="themebtn" id="themebtn" type="button" aria-label="Switch light or dark theme">◐</button>
</div>
<nav class="wrap rail" aria-label="Sections">{nav}</nav>
</header>
{tick}"""


def footer():
    return f"""<footer class="wrap foot">
<p><b>Not investment advice.</b> TotalMarket reports and explains news. It does not recommend buying, selling or holding any security and is not a SEBI-registered investment adviser or research analyst. Do your own research or consult a registered adviser before investing.</p>
<p>Stories are written and published automatically by Claude, an AI model from Anthropic, based on the linked reporting. Every story lists its sources. <a href="{BASE}about/">About TotalMarket</a> · <a href="{SITE_URL}/rss.xml">RSS feed</a></p>
</footer>"""


def chip(p):
    c = p["category"]
    return f'<span class="chip" style="--dot:var(--c-{c})">{e(CATS[c][0])}</span>'


def meta_row(p):
    src = (p.get("sources") or [{}])[0].get("name")
    bits = [f'<time datetime="{e(p["_dt"].isoformat())}">{e(fmt_ist(p["_dt"]))}</time>']
    if p.get("readMins"): bits.append(f'{int(p["readMins"])} min read')
    if src: bits.append(e(src))
    return '<div class="meta">' + "".join(f"<span>{b}</span>" for b in bits) + "</div>"


def cover_url(p, absolute=False):
    rel = f"{BASE}covers/{p['_cover_og'] if absolute else p['_cover']}"
    return abs_url(rel) if absolute else rel


def cover_img(p, cls, eager=False):
    return (f'<img class="{cls}" src="{cover_url(p)}" width="1600" height="900" alt="" '
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
        comps.append(f'<div class="company">{logo}<span><b>{e(c.get("name"))}</b><small>{e(c.get("ticker") or "")}</small></span></div>')
    if not ppl and not comps:
        return ""
    out = '<div class="pstrip">'
    if ppl:
        out += f'<div class="pgroup"><h2>People in this story</h2><div class="prow">{"".join(ppl)}</div></div>'
    if comps:
        out += f'<div class="pgroup"><h2>Companies in this story</h2><div class="prow">{"".join(comps)}</div></div>'
    return out + "</div>"


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
        cols.append(f'<div class="rday"><h3>{e(d.strftime("%a %-d %b"))}</h3><ul>{names}{more}</ul></div>')
    return (f'<section class="rwidget"><div class="rhead"><h2>Upcoming results</h2><a href="{BASE}results/">Full calendar →</a></div>'
            f'<div class="rdays">{"".join(cols)}</div></section>')


def results_page(results, meta):
    path = f"{BASE}results/"
    by = upcoming(results)
    days = []
    for d, rs in by.items():
        rows = "".join(f'<tr class="{"big" if r["big"] else ""}"><th scope="row">{e(r["company"])}</th><td>{e(r["note"])}</td></tr>' for r in rs)
        days.append(f'<section class="rsec"><h2 class="edhead"><b>{e(d.strftime("%A %-d %B"))}</b><span>{len(rs)} {"company" if len(rs)==1 else "companies"}</span></h2>'
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
        label = items[0].get("editionLabel") or items[0]["_dt"].astimezone(IST).strftime("%a %-d %b")
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
        "mainEntityOfPage": link, "image": [cover_url(p, True)],
        "articleSection": CATS[p["category"]][0],
        "author": {"@type": "Organization", "name": SITE_NAME, "url": SITE_URL + "/about/"},
        "publisher": {"@type": "Organization", "name": SITE_NAME,
                      "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/assets/logo.png"}},
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
    body_html = "".join(f"<p>{e(t)}</p>" for t in p["_paras"])
    dek = f'<p class="dek">{e(p.get("dek"))}</p>' if p.get("dek") else ""
    body = f"""<article class="story" style="--dot:var(--c-{p['category']})">
<nav class="crumbs"><a href="{BASE}">Home</a> / <a href="{BASE}{p['category']}/">{e(CATS[p['category']][0])}</a></nav>
{cover_img(p, "hero", True)}
{chip(p)}
<h1>{e(p['title'])}</h1>
{dek}
{meta_row(p)}
<div class="byline">By Claude (AI) for TotalMarket · automated update</div>
{people_strip(p)}
<div class="body">{body_html}</div>
{report.render(p.get("report"))}
{data_table(p)}
{impacts(p)}
{why(p)}
{engage_card(p)}
<div class="share" aria-label="Share this story">
<a href="https://wa.me/?text={text}" target="_blank" rel="noopener">Share on WhatsApp</a>
<a href="https://twitter.com/intent/tweet?text={quote(p['title'])}&url={quote(link)}" target="_blank" rel="noopener">Share on X</a>
<a href="https://t.me/share/url?url={quote(link)}&text={quote(p['title'])}" target="_blank" rel="noopener">Share on Telegram</a>
<button type="button" class="copy" data-url="{e(link)}">Copy link</button>
</div>
<div class="tags" aria-label="Topics">{"".join(f'<a class="tag" href="{BASE}tag/{slug(t)}/">#{e(t)}</a>' for t in p["_tags"])}</div>
{'<div class="sources"><h2>Sources</h2><ul>' + srcs + '</ul></div>' if srcs else ''}
<p class="disc">News and explanation only. This is not investment advice and not a recommendation to buy or sell any security.</p>
{comments_block(p)}
</article>
<div class="fab" aria-label="Like or comment"><button type="button" class="fab-like" data-like-key="{like_key(p)}" aria-label="Like this story">&#9829; <span class="lc">Like</span></button><a class="fab-cm" href="#comments" aria-label="Go to comments">&#128172; Comment</a></div>
{rel}"""
    return page(p["title"], p.get("seoDescription") or desc(p), path, body, meta, og_type="article", extra_head=extra, image=cover_url(p, True),
                seo_title=(p.get("seoTitle") + f" | {SITE_NAME}") if p.get("seoTitle") else None, keywords=page_keywords(p), news_kw=p["_tags"][:10])


def about_page(meta):
    path = f"{BASE}about/"
    body = f"""<article class="story">
<h1>About TotalMarket</h1>
<div class="body">
<p>TotalMarket is a free news site for Indian investors and traders who also follow technology. It covers stock market moves and upcoming results, IPOs and startup funding, tech and AI, RBI and SEBI decisions, overnight global markets, and gold, silver, crude oil and currencies, with what each move means globally and for India.</p>
<p><b>How it is made.</b> Every story is researched and written automatically by Claude, an AI model made by Anthropic, using reporting from the sources linked at the end of each story. The site updates four times on each market day: a pre-market brief around 8:45 am, a midday check around 12:45 pm, a closing wrap around 3:45 pm and an evening tech and startups update around 8:45 pm IST, with one roundup on weekends and market holidays.</p>
<p><b>Analytics and likes.</b> The site uses Google Analytics to count visits and popular stories, and a simple anonymous counter for likes. Comments, when enabled, are stored in GitHub Discussions.</p>
<p><b>Accuracy.</b> Stories state only facts found in their sources and link to them so you can check. AI can still make mistakes, so for anything that affects a decision, open the original source.</p>
<p><b>Not investment advice.</b> TotalMarket reports and explains news. It never recommends buying, selling or holding any security, does not give price targets, and is not registered with SEBI as an investment adviser or research analyst.</p>
<p><b>Follow along.</b> Subscribe with any feed reader using the <a href="{SITE_URL}/rss.xml">RSS feed</a>.</p>
</div></article>"""
    return page("About TotalMarket", "How TotalMarket covers Indian markets and tech news, and how its AI-written stories are made.", path, body, meta)


def tag_pages(posts, meta):
    by = {}
    for p in posts:
        for t in p["_tags"]:
            by.setdefault(slug(t), [t, []])[1].append(p)
    for sl, (name, items) in by.items():
        path = f"{BASE}tag/{sl}/"
        body = (f'<div class="sechead"><h1>{e(name)}</h1><p>Latest TotalMarket news and explainers on {e(name)}, with what it means for India.</p></div>'
                + grouped(items[:SECTION_LIMIT], False))
        write(f"tag/{sl}/index.html", page(f"{name}: latest news and analysis", f"Latest news on {name}: market moves, key numbers and what it means for India.",
                                          path, body, meta, keywords=[name, "India", "market news"]))
    return list(by)


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
            + report_banner(reps) + (grouped(reps[1:SECTION_LIMIT], False) if len(reps) > 1 else "")
            + ("" if reps else '<div class="empty"><p>The first report is on its way. It publishes after 8 pm on each market day.</p></div>'))
    return page("Daily Stock Market Report", "Daily Indian stock market report: Sensex, Nifty, Bank Nifty closing, day high and low, FII DII data, top gainers and losers, sector performance, IPO listings and market breadth.",
                path, body, meta, seo_title="Stock Market Today: Daily Sensex & Nifty Closing Report, FII DII Data, Top Gainers & Losers | TotalMarket",
                keywords=["stock market today", "share market today", "Sensex today", "Nifty today", "FII DII data", "top gainers and losers", "sector performance", "IPO listing today", "market report"])


def section_page(key, posts, meta):
    name, blurb = CATS[key]
    items = [p for p in posts if p["category"] == key][:SECTION_LIMIT]
    path = f"{BASE}{key}/"
    body = (f'<div class="sechead"><h1>{e(name)}</h1><p>{e(blurb)}</p></div>'
            + (grouped(items, False) if items else '<div class="empty"><p>No stories here yet. This section fills up with the next update.</p></div>'))
    kw = {"markets": ["Sensex today", "Nifty 50", "stock market news India", "share market today"], "tech": ["AI news", "tech news India"],
          "startups": ["IPO news", "upcoming IPO", "startup funding India"], "policy": ["RBI policy", "SEBI news", "budget"],
          "global": ["global market news", "US stock market", "Fed rate"], "commodities": ["gold rate today", "silver price today", "crude oil price", "rupee vs dollar"]}[key]
    return page(f"{name} news today", blurb, path, body, meta, keywords=kw)


def ago(p):
    mins = int((datetime.now(IST) - p["_dt"]).total_seconds() // 60)
    if mins < 60: return f"{max(mins,1)} min ago"
    if mins < 60 * 24: return f"{mins // 60} hours ago" if mins >= 120 else "1 hour ago"
    return p["_dt"].astimezone(IST).strftime("%-d %b")


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
    labels = "".join(f'<text x="{X(i):.1f}" y="{h-6}" text-anchor="{"end" if i == len(points) - 1 else "start" if i == 0 else "middle"}">{datetime.fromisoformat(x["d"]).strftime("%-d %b")}</text>'
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
    return tools.side_panel(BASE) + movers + results_widget(results) + trend


CATS_LABELS = {v[0] for v in CATS.values()}


def home_page(posts, meta, results=()):
    if not posts:
        body = '<div class="empty"><p>The first update is on its way.</p></div>'
    else:
        lead_p = next((p for p in posts[:12] if p.get("lead")), posts[0])
        others = [p for p in posts if p is not lead_p]
        hero = (f'<a class="hero1" href="{url(lead_p)}" style="--dot:var(--c-{lead_p["category"]})"><img src="{cover_url(lead_p)}" width="1600" height="900" alt="" fetchpriority="high">'
                f'<span class="hov"><em>{e(CATS[lead_p["category"]][0])}</em><b>{e(lead_p["title"])}</b><i>{e(lead_p.get("dek") or "")}</i>'
                f'<small>{e(ago(lead_p))} · By TotalMarket · {int(lead_p.get("readMins") or 2)} min read</small></span></a>')
        topst = [p for p in others if p.get("stat")][:5] or others[:5]
        stories = (f'<aside class="widget stories"><div class="wtabs"><button type="button" class="wt on" data-panel="st0">Top stories</button>'
                   f'<button type="button" class="wt" data-panel="st1">Latest</button></div>'
                   f'<div class="wp" id="st0">{"".join(mini(p) for p in topst)}</div><div class="wp" id="st1" hidden>{"".join(mini(p) for p in others[:5])}</div></aside>')
        body = (f'<h1 class="sr">{SITE_NAME}: {e(TAGLINE)}</h1>'
                f'<div class="topgrid">{hero}{stories}{market_widget(posts, meta)}</div>'
                + report_banner(posts) + section_cols(posts)
                + f'<div class="lower">{latest_list(posts)}<div class="side">{side_panels(posts, results)}</div></div>')
    ld = {"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/",
          "description": TAGLINE}
    return page(SITE_NAME, "Sensex and Nifty news, gold and silver rates, crude oil, rupee vs dollar, IPOs, results calendar and overnight global markets, with what each move means for India. Updated four times every market day.",
                BASE, body, meta, seo_title=HOME_TITLE, keywords=HOME_KEYWORDS, extra_head=f'<script type="application/ld+json">{json.dumps(ld)}</script>')


def search_index(posts):
    return json.dumps([{"t": p["title"], "u": url(p), "c": CATS[p["category"]][0], "k": " ".join(p["_tags"]), "d": p["_dt"].astimezone(IST).strftime("%-d %b")}
                       for p in posts[:400]], ensure_ascii=False)


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
    urls = [(SITE_URL + "/", now, "hourly")] + [(f"{SITE_URL}/{k}/", now, "hourly") for k in CATS] + [(SITE_URL + "/about/", None, "monthly"), (SITE_URL + "/results/", now, "daily"), (SITE_URL + "/market-report/", now, "daily")] + [(u, now, "daily") for u in TOOL_URLS] + [(f"{SITE_URL}/tag/{t}/", now, "daily") for t in TAG_SLUGS]
    urls += [(abs_url(url(p)), p["_dt"].astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), None) for p in posts]
    rows = "".join(f"<url><loc>{e(u)}</loc>{f'<lastmod>{m}</lastmod>' if m else ''}{f'<changefreq>{c}</changefreq>' if c else ''}</url>" for u, m, c in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{rows}</urlset>\n'


def news_sitemap(posts):
    cutoff = datetime.now(timezone.utc) - timedelta(days=2)
    rows = "".join(
        f"<url><loc>{e(abs_url(url(p)))}</loc><news:news><news:publication><news:name>{SITE_NAME}</news:name>"
        f"<news:language>en</news:language></news:publication><news:publication_date>{p['_dt'].isoformat()}</news:publication_date>"
        f"<news:title>{e(p['title'])}</news:title></news:news></url>"
        for p in posts if p["_dt"] >= cutoff)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            f'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">{rows}</urlset>\n')


def write(rel, content):
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
    write("index.html", home_page(posts, meta, results))
    write("results/index.html", results_page(results, meta))
    write("market-report/index.html", report_page(posts, meta))
    global TAG_SLUGS
    TAG_SLUGS = tag_pages(posts, meta)
    for k in CATS:
        write(f"{k}/index.html", section_page(k, posts, meta))
    for p in posts:
        write(f"news/{p['id']}/index.html", article_page(p, posts, meta))
    write("about/index.html", about_page(meta))
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
    print(f"Built {len(posts)} stories into docs/")


if __name__ == "__main__":
    main()
