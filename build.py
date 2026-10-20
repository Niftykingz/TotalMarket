#!/usr/bin/env python3
"""Build the TotalMarket static site.

Reads stories from data/posts/*.json and data/meta.json, writes the public
site to docs/ (served by GitHub Pages). No third-party packages needed.

Run:  python3 build.py
"""
import html, json, os, re, shutil, sys
import covers
import report
import art
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
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800'
         '&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Mono:wght@400;500&display=swap">')


def page(title, description, path, body, meta, og_type="website", extra_head="", noindex=False, image=None, seo_title=None, keywords=()):
    canon = abs_url(path)
    kw = f'<meta name="keywords" content="{e(", ".join(keywords))}"><meta name="news_keywords" content="{e(", ".join(keywords))}">' if keywords else ""
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
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:locale" content="en_IN">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(description)}">
<meta name="twitter:image" content="{e(og)}">
<meta name="theme-color" content="#0B6E4F">
<meta name="google-site-verification" content="R-bU7412W25OlS3wPOdJYbHHIF8P7FdcDqTH9Zd-Xfo">
<link rel="icon" href="{BASE}assets/favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="{SITE_NAME}" href="{SITE_URL}/rss.xml">
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
</body>
</html>
"""
    return head


def header(meta, path):
    tick = ""
    t = meta.get("ticker") or []
    if t:
        items = "".join(
            f'<span class="tk"><span>{e(x.get("label"))}</span>{e(x.get("value"))}'
            f'<em class="{"down" if str(x.get("change","")).startswith("-") else "up"}">{e(x.get("change"))}</em></span>'
            for x in t)
        asof = f'<span class="tk"><span>{e(meta.get("tickerAsOf"))}</span></span>' if meta.get("tickerAsOf") else ""
        tick = f'<div class="ticker" aria-label="Market snapshot">{items}{asof}</div>'
    nav_extra = f'<a class="tab{" on" if path == f"{BASE}market-report/" else ""}" href="{BASE}market-report/" style="--dot:#F2C14E"><i></i>Daily market report</a>'
    nav_extra += f'<a class="tab{" on" if path == f"{BASE}results/" else ""}" href="{BASE}results/" style="--dot:var(--accent)"><i></i>Results calendar</a>'
    nav = "".join(
        f'<a class="tab{" on" if path == f"{BASE}{k}/" else ""}" href="{BASE}{k}/" style="--dot:var(--c-{k})"><i></i>{e(v[0])}</a>'
        for k, v in CATS.items())
    upd = parse_dt(meta.get("updatedAt"))
    stamp = f'<b>{e(meta.get("editionLabel") or "Latest update")}</b>'
    if upd:
        stamp += f'<span>Updated {e(fmt_ist(upd))}</span>'
    return f"""<header class="top band">
<div class="wrap">
<div class="mast"><a class="brand" href="{BASE}">Total<span>Market</span></a><div class="stamp">{stamp}</div></div>
{tick}
<nav class="rail" aria-label="Sections"><a class="tab{' on' if path == BASE else ''}" href="{BASE}">All</a>{nav}{nav_extra}</nav>
</div>
</header>"""


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
    rel = f"{BASE}covers/{p['_cover']}"
    return abs_url(rel) if absolute else rel


def cover_img(p, cls, eager=False):
    return (f'<img class="{cls}" src="{cover_url(p)}" width="1200" height="630" alt="" '
            f'{"fetchpriority=\"high\"" if eager else "loading=\"lazy\""} decoding="async">')


def card(p):
    dek = f'<p>{e(p.get("dek"))}</p>' if p.get("dek") else ""
    return (f'<article class="card" style="--dot:var(--c-{p["category"]})">{cover_img(p, "thumb")}<div class="cbody">{chip(p)}'
            f'<h3><a href="{url(p)}">{e(p["title"])}</a></h3>{dek}{meta_row(p)}</div></article>')


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
    trs = "".join(
        f'<tr><th scope="row">{e(r.get("label"))}{f"<span class=sub>{e(r.get(chr(110)+chr(111)+chr(116)+chr(101)))}</span>" if r.get("note") else ""}</th><td class="num">{e(r.get("value"))}</td>'
        f'<td class="num {"down" if str(r.get("change","")).startswith("-") else "up" if str(r.get("change","")).startswith("+") else ""}">{e(r.get("change"))}</td>'
        f'</tr>' for r in rows)
    cap = f'<caption>{e(t.get("title"))}</caption>' if t.get("title") else ""
    return f'<div class="tablewrap"><table class="dt">{cap}<thead><tr><th>Market</th><th>Level</th><th>Change</th></tr></thead><tbody>{trs}</tbody></table></div>'


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
    ld["keywords"] = ", ".join(p["_tags"])
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
<div class="body">{body_html}</div>
{report.render(p.get("report"))}
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
<p class="disc">News and explanation only. This is not investment advice and not a recommendation to buy or sell any security.</p>
</article>
{rel}
<script>document.querySelectorAll('.copy').forEach(b=>b.addEventListener('click',()=>{{navigator.clipboard&&navigator.clipboard.writeText(b.dataset.url).then(()=>{{b.textContent='Link copied'}}).catch(()=>{{}})}}))</script>"""
    return page(p["title"], p.get("seoDescription") or desc(p), path, body, meta, og_type="article", extra_head=extra, image=cover_url(p, True),
                seo_title=(p.get("seoTitle") + f" | {SITE_NAME}") if p.get("seoTitle") else None, keywords=p["_tags"])


def about_page(meta):
    path = f"{BASE}about/"
    body = f"""<article class="story">
<h1>About TotalMarket</h1>
<div class="body">
<p>TotalMarket is a free news site for Indian investors and traders who also follow technology. It covers stock market moves and upcoming results, IPOs and startup funding, tech and AI, RBI and SEBI decisions, overnight global markets, and gold, silver, crude oil and currencies, with what each move means globally and for India.</p>
<p><b>How it is made.</b> Every story is researched and written automatically by Claude, an AI model made by Anthropic, using reporting from the sources linked at the end of each story. The site updates four times on each market day: a pre-market brief around 8:45 am, a midday check around 12:45 pm, a closing wrap around 3:45 pm and an evening tech and startups update around 8:45 pm IST, with one roundup on weekends and market holidays.</p>
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


def home_page(posts, meta, results=()):
    body = (f'<h1 class="sr">{SITE_NAME}: {e(TAGLINE)}</h1>' + report_banner(posts) + results_widget(results)
            + (grouped(posts[:HOME_LIMIT], True) if posts else '<div class="empty"><p>The first update is on its way.</p></div>'))
    ld = {"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/",
          "description": TAGLINE}
    return page(SITE_NAME, "Sensex and Nifty news, gold and silver rates, crude oil, rupee vs dollar, IPOs, results calendar and overnight global markets, with what each move means for India. Updated four times every market day.",
                BASE, body, meta, seo_title=HOME_TITLE, keywords=HOME_KEYWORDS, extra_head=f'<script type="application/ld+json">{json.dumps(ld)}</script>')


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
    urls = [(SITE_URL + "/", now, "hourly")] + [(f"{SITE_URL}/{k}/", now, "hourly") for k in CATS] + [(SITE_URL + "/about/", None, "monthly"), (SITE_URL + "/results/", now, "daily"), (SITE_URL + "/market-report/", now, "daily")] + [(f"{SITE_URL}/tag/{t}/", now, "daily") for t in TAG_SLUGS]
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
            if name in ("assets", "covers"):
                continue
            target = os.path.join(OUT, name)
            shutil.rmtree(target) if os.path.isdir(target) else os.remove(target)
    shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(OUT, "assets"), dirs_exist_ok=True)
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
    write("404.html", page("Page not found", "This page does not exist.", f"{BASE}404.html",
                           f'<div class="empty"><h1>Page not found</h1><p><a href="{BASE}">Go to the latest stories</a></p></div>', meta, noindex=True))
    write("rss.xml", rss(posts))
    write("sitemap.xml", sitemap(posts))
    write("news-sitemap.xml", news_sitemap(posts))
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\nSitemap: {SITE_URL}/news-sitemap.xml\n")
    write(".nojekyll", "")
    print(f"Built {len(posts)} stories into docs/")


if __name__ == "__main__":
    main()
