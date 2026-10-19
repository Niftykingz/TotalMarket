#!/usr/bin/env python3
"""Build the TotalMarket static site.

Reads stories from data/posts/*.json and data/meta.json, writes the public
site to docs/ (served by GitHub Pages). No third-party packages needed.

Run:  python3 build.py
"""
import html, json, os, re, shutil, sys
import covers
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
IST = ZoneInfo("Asia/Kolkata")
HOME_LIMIT = 60
SECTION_LIMIT = 80

CATS = {
    "markets":  ("Markets", "Sensex and Nifty moves, big stock news, quarterly results and what drove them."),
    "tech":     ("Tech & AI", "AI, big tech and Indian tech companies: launches, deals and regulation."),
    "startups": ("Startups & IPOs", "Indian startup funding, upcoming IPOs, price bands, subscriptions and listings."),
    "policy":   ("Policy & Economy", "RBI, SEBI, budget, tax and government decisions that affect your money."),
    "global":   ("Global", "US markets, crude oil, gold, the dollar and world events that move Indian markets."),
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


def page(title, description, path, body, meta, og_type="website", extra_head="", noindex=False, image=None):
    canon = abs_url(path)
    og = image or f"{SITE_URL}/assets/og.png"
    full_title = title if title == SITE_NAME else f"{title} | {SITE_NAME}"
    head = f"""<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(description)}">
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
    nav = "".join(
        f'<a class="tab{" on" if path == f"{BASE}{k}/" else ""}" href="{BASE}{k}/" style="--dot:var(--c-{k})"><i></i>{e(v[0])}</a>'
        for k, v in CATS.items())
    upd = parse_dt(meta.get("updatedAt"))
    stamp = f'<b>{e(meta.get("editionLabel") or "Latest update")}</b>'
    if upd:
        stamp += f'<span>Updated {e(fmt_ist(upd))}</span>'
    return f"""<header class="top">
<div class="wrap">
<div class="mast"><a class="brand" href="{BASE}">Total<span>Market</span></a><div class="stamp">{stamp}</div></div>
{tick}
<nav class="rail" aria-label="Sections"><a class="tab{' on' if path == BASE else ''}" href="{BASE}">All</a>{nav}</nav>
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


def lead(p):
    dek = f'<p class="dek">{e(p.get("dek"))}</p>' if p.get("dek") else ""
    return (f'<article class="lead" style="--dot:var(--c-{p["category"]})">{cover_img(p, "hero", True)}<div class="lbody"><div>{chip(p)}'
            f'<h2><a href="{url(p)}">{e(p["title"])}</a></h2></div><aside>{why(p) or dek}{meta_row(p)}</aside></div></article>')


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
    extra = (f'<meta property="article:published_time" content="{e(p["_dt"].isoformat())}">'
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
{why(p)}
<div class="share" aria-label="Share this story">
<a href="https://wa.me/?text={text}" target="_blank" rel="noopener">Share on WhatsApp</a>
<a href="https://twitter.com/intent/tweet?text={quote(p['title'])}&url={quote(link)}" target="_blank" rel="noopener">Share on X</a>
<a href="https://t.me/share/url?url={quote(link)}&text={quote(p['title'])}" target="_blank" rel="noopener">Share on Telegram</a>
<button type="button" class="copy" data-url="{e(link)}">Copy link</button>
</div>
{'<div class="sources"><h2>Sources</h2><ul>' + srcs + '</ul></div>' if srcs else ''}
<p class="disc">News and explanation only. This is not investment advice and not a recommendation to buy or sell any security.</p>
</article>
{rel}
<script>document.querySelectorAll('.copy').forEach(b=>b.addEventListener('click',()=>{{navigator.clipboard&&navigator.clipboard.writeText(b.dataset.url).then(()=>{{b.textContent='Link copied'}}).catch(()=>{{}})}}))</script>"""
    return page(p["title"], desc(p), path, body, meta, og_type="article", extra_head=extra, image=cover_url(p, True))


def about_page(meta):
    path = f"{BASE}about/"
    body = f"""<article class="story">
<h1>About TotalMarket</h1>
<div class="body">
<p>TotalMarket is a free news site for Indian investors and traders who also follow technology. It covers stock market moves, IPOs and startup funding, tech and AI, RBI and SEBI decisions, and global events that move Indian markets.</p>
<p><b>How it is made.</b> Every story is researched and written automatically by Claude, an AI model made by Anthropic, using reporting from the sources linked at the end of each story. The site updates four times on each market day: a pre-market brief around 8:45 am, a midday check around 12:45 pm, a closing wrap around 3:45 pm and an evening tech and startups update around 8:45 pm IST, with one roundup on weekends and market holidays.</p>
<p><b>Accuracy.</b> Stories state only facts found in their sources and link to them so you can check. AI can still make mistakes, so for anything that affects a decision, open the original source.</p>
<p><b>Not investment advice.</b> TotalMarket reports and explains news. It never recommends buying, selling or holding any security, does not give price targets, and is not registered with SEBI as an investment adviser or research analyst.</p>
<p><b>Follow along.</b> Subscribe with any feed reader using the <a href="{SITE_URL}/rss.xml">RSS feed</a>.</p>
</div></article>"""
    return page("About TotalMarket", "How TotalMarket covers Indian markets and tech news, and how its AI-written stories are made.", path, body, meta)


def section_page(key, posts, meta):
    name, blurb = CATS[key]
    items = [p for p in posts if p["category"] == key][:SECTION_LIMIT]
    path = f"{BASE}{key}/"
    body = (f'<div class="sechead"><h1>{e(name)}</h1><p>{e(blurb)}</p></div>'
            + (grouped(items, False) if items else '<div class="empty"><p>No stories here yet. This section fills up with the next update.</p></div>'))
    return page(f"{name} news", blurb, path, body, meta)


def home_page(posts, meta):
    body = (f'<h1 class="sr">{SITE_NAME}: {e(TAGLINE)}</h1>'
            + (grouped(posts[:HOME_LIMIT], True) if posts else '<div class="empty"><p>The first update is on its way.</p></div>'))
    ld = {"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/",
          "description": TAGLINE}
    return page(SITE_NAME, f"{TAGLINE}. Updated before the open, at midday, after the close and in the evening.",
                BASE, body, meta, extra_head=f'<script type="application/ld+json">{json.dumps(ld)}</script>')


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
    urls = [(SITE_URL + "/", now, "hourly")] + [(f"{SITE_URL}/{k}/", now, "hourly") for k in CATS] + [(SITE_URL + "/about/", None, "monthly")]
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
    write("index.html", home_page(posts, meta))
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
