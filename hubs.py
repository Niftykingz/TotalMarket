"""Company pages (/stock/<slug>/) and the IPO hub (/ipo/ and /ipo/<slug>/).

Both are generated from data the update runs already write:
- companies: the `companies` field on stories, plus data/results.json for the next results date
- IPOs: data/ipos.json (see README "IPO hub")
"""
import json
import os
import re
from datetime import date, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")


def _slug(t):
    s = re.sub(r"[^a-z0-9]+", "-", str(t).lower().replace("&", " and ")).strip("-")
    return s[:80] or "x"


def company_slug(name):
    return _slug(name)


def _inr(n):
    """Indian digit grouping for an integer number of rupees."""
    try:
        n = int(round(float(n)))
    except Exception:
        return str(n)
    s, neg = str(abs(n)), n < 0
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        s = head + "," + tail
    return ("-" if neg else "") + "₹" + s


def _d(s):
    try:
        return datetime.fromisoformat(str(s)).date()
    except Exception:
        return None


def _fmt(d):
    return d.strftime("%a %-d %b") if d else "—"


# ------------------------------------------------------------------ companies
def collect_companies(posts):
    by = {}
    for p in posts:
        for c in p.get("companies") or []:
            if not isinstance(c, dict) or not c.get("name"):
                continue
            sl = company_slug(c["name"])
            ent = by.setdefault(sl, {"slug": sl, "name": c["name"], "ticker": c.get("ticker") or "", "posts": []})
            if p not in ent["posts"]:
                ent["posts"].append(p)
            if not ent["ticker"] and c.get("ticker"):
                ent["ticker"] = c["ticker"]
    return by


def company_pages(posts, results, ctx):
    page, e, base, card = ctx["page"], ctx["e"], ctx["base"], ctx["card"]
    comps = collect_companies(posts)
    today = ctx["today"]
    res_by = {}
    for r in results:
        res_by.setdefault(company_slug(r["company"]), []).append(r)
    out = []
    for sl, c in comps.items():
        nxt = [r for r in res_by.get(sl, []) if r["date"] >= today]
        facts = [("Ticker", c["ticker"] or "—")]
        if nxt:
            facts.append(("Next results", f'{_fmt(nxt[0]["date"])} · {nxt[0]["note"]}'))
        facts.append(("Stories on TotalMarket", str(len(c["posts"]))))
        facts.append(("Latest update", c["posts"][0]["_dt"].astimezone(ctx["ist"]).strftime("%-d %b %Y, %-I:%M %p IST")))
        tags = {}
        for p in c["posts"]:
            for t in p["_tags"]:
                tags[t] = tags.get(t, 0) + 1
        toptags = sorted(tags.items(), key=lambda kv: -kv[1])[:10]
        name = c["name"]
        frows = "".join(f'<tr><th scope="row">{e(k)}</th><td>{e(v)}</td></tr>' for k, v in facts)
        body = (f'<nav class="crumbs"><a href="{base}">Home</a> / <a href="{base}stock/">Companies</a></nav>'
                f'<div class="sechead"><h1>{e(name)} share news, results and updates</h1>'
                f'<p>Every TotalMarket story about {e(name)}{" (" + e(c["ticker"]) + ")" if c["ticker"] else ""}: share price moves, quarterly results, '
                f'IPO and corporate news, explained simply with what it means for investors. News only, not investment advice.</p></div>'
                f'<div class="cofacts"><div class="tablewrap"><table class="dt"><tbody>{frows}</tbody></table></div>'
                + (f'<div class="tags">{"".join(f"<a class=\"tag\" href=\"{base}tag/{ctx["slug"](t)}/\">#{e(t)}</a>" for t, _ in toptags)}</div>' if toptags else "")
                + '</div>'
                f'<section class="edition"><h2 class="edhead"><b>Latest {e(name)} news</b><span>{len(c["posts"])} {"story" if len(c["posts"]) == 1 else "stories"}</span></h2>'
                f'<div class="grid">{"".join(card(p) for p in c["posts"][:40])}</div></section>')
        kw = [f"{name} share price", f"{name} share news", f"{name} news today", f"{name} results"]
        if c["ticker"]:
            kw.append(f'{c["ticker"]} share')
        title = f"{name} Share News Today: Results, Price Moves & Updates"
        descr = f"Latest {name} news: share price moves, quarterly results and corporate updates, explained simply for Indian investors."
        out.append((f"stock/{sl}/index.html", page(title, descr, f"{base}stock/{sl}/", body, ctx["meta"], keywords=kw, seo_title=f"{title} | TotalMarket")))
    # index
    items = sorted(comps.values(), key=lambda c: c["name"].lower())
    rows = "".join(f'<li><a href="{base}stock/{c["slug"]}/"><b>{e(c["name"])}</b><small>{e(c["ticker"])} · {len(c["posts"])} {"story" if len(c["posts"]) == 1 else "stories"}</small></a></li>' for c in items)
    body = (f'<div class="sechead"><h1>Companies A–Z</h1><p>Every company covered on TotalMarket, with all its news, results and IPO updates on one page.</p></div>'
            f'<ul class="colist">{rows}</ul>')
    out.append(("stock/index.html", page("Company news A–Z", "All companies covered by TotalMarket: share news, results and IPO updates by company.",
                                         f"{base}stock/", body, ctx["meta"], keywords=["share news", "company news India", "stock news"])))
    return out, comps


# ------------------------------------------------------------------ IPOs
def load_ipos():
    path = os.path.join(DATA, "ipos.json")
    if not os.path.exists(path):
        return {"ipos": []}
    return json.load(open(path, encoding="utf-8"))


def ipo_status(x, today):
    o, c, l = _d(x.get("open")), _d(x.get("close")), _d(x.get("listing"))
    if x.get("listingPrice") or (l and l <= today and x.get("listed")):
        return "listed"
    if l and l <= today:
        return "listing"
    if c and c < today:
        return "closed"
    if o and o <= today <= (c or o):
        return "open"
    if o and o > today:
        return "upcoming"
    return "upcoming" if not o else "closed"


STATUS_LABEL = {"open": "Open now", "upcoming": "Upcoming", "closed": "Closed · awaiting listing", "listing": "Listing today", "listed": "Listed"}

LESSONS = [
    ("What is an IPO?", "An initial public offering is the first time a company sells its shares to the public. After the IPO, the shares trade on NSE and BSE like any other stock."),
    ("Price band and cut-off price", "The company sets a range, say ₹660–693. Investors bid within it; the final price is usually the top of the band. Retail investors can tick 'cut-off' to accept whatever final price is set."),
    ("Lot size and minimum investment", "You apply in fixed bundles called lots. If the lot is 21 shares and the top price is ₹693, the minimum application is 21 × ₹693 = ₹14,553."),
    ("Fresh issue vs offer for sale (OFS)", "In a fresh issue the company creates new shares and keeps the money. In an OFS, existing owners sell their shares and the money goes to them, not the company."),
    ("Anchor investors", "Big institutions that buy a part of the issue one working day before it opens. Half their shares are locked for 30 days and the rest for 90 days, so their lock-in end dates can bring selling."),
    ("QIB, NII and retail quotas", "The issue is split by investor type: QIBs (mutual funds, insurers, foreign funds), NIIs or HNIs (individuals applying above ₹2 lakh) and retail (up to ₹2 lakh). Each quota has its own subscription number."),
    ("What does '10x subscribed' mean?", "Investors applied for 10 shares for every share on offer. When retail is oversubscribed, lots are allotted by a computerised lottery, so many applicants get nothing."),
    ("Grey market premium (GMP)", "An unofficial price quoted by dealers before listing. It is unregulated, not recognised by SEBI or the exchanges, and often wrong. Treat it as gossip, not data."),
    ("ASBA and UPI mandate", "When you apply, the money is only blocked in your bank account, not taken. If you get no shares, the block is released; if you do, only the allotted amount is debited."),
    ("Red flags to check in the RHP", "The Red Herring Prospectus is the official offer document. Look at the use of proceeds, how much is OFS, debt levels, profit history, pending legal cases and how the price compares with listed peers."),
    ("SME vs mainboard IPOs", "SME IPOs are small companies on the NSE Emerge or BSE SME platforms, with bigger minimum lots and thinner trading. They carry higher risk than mainboard IPOs."),
]


def _sub_html(sub, e):
    if not sub:
        return ""
    cats = [("QIB", sub.get("qib")), ("NII", sub.get("nii")), ("Retail", sub.get("retail")), ("Employees", sub.get("employee")), ("Shareholders", sub.get("shareholder"))]
    bars = "".join(f'<div class="sbar"><span>{k}</span><i style="--w:{min(100, float(v) * 20):.0f}%"></i><b>{float(v):.2f}x</b></div>' for k, v in cats if v is not None)
    src = sub.get("source") or {}
    srcl = f' · <a href="{e(src.get("url"))}" rel="nofollow noopener" target="_blank">{e(src.get("name"))}</a>' if src.get("url") else ""
    return (f'<div class="subs"><div class="stot"><b>{float(sub.get("total", 0)):.2f}x</b><span>subscribed · as of {e(sub.get("asOf"))}{srcl}</span></div>{bars}</div>')


def _ipo_rows(x, e):
    rows = [("Status", STATUS_LABEL.get(x["_status"], "")), ("Segment", x.get("segment") or "Mainboard"), ("Exchanges", x.get("exchange") or "NSE, BSE"),
            ("Price band", x.get("priceBand")), ("Lot size", f'{x["lot"]} shares' if x.get("lot") else None),
            ("Minimum investment", _inr(x["minAmount"]) + " (at upper band)" if x.get("minAmount") else None),
            ("Issue size", x.get("issueSize")), ("Fresh issue", x.get("fresh")), ("Offer for sale (OFS)", x.get("ofs")),
            ("Opens", _fmt(_d(x.get("open"))) if x.get("open") else None), ("Closes", _fmt(_d(x.get("close"))) if x.get("close") else None),
            ("Allotment", _fmt(_d(x.get("allotment"))) if x.get("allotment") else None), ("Listing", _fmt(_d(x.get("listing"))) if x.get("listing") else None),
            ("Issue price", _inr(x["issuePrice"]) if x.get("issuePrice") else None),
            ("Listing price", f'{_inr(x["listingPrice"])} ({x["listingGainPct"]:+.1f}%)' if x.get("listingPrice") and x.get("listingGainPct") is not None else None),
            ("After listing", x.get("afterListing")),
            ("Grey market premium", f'{x["gmp"]["value"]} · {x["gmp"].get("asOf", "")} · unofficial' if x.get("gmp") else None)]
    return "".join(f'<tr><th scope="row">{e(k)}</th><td>{e(v)}</td></tr>' for k, v in rows if v)


def _ipo_card(x, e, base):
    meta = " · ".join(v for v in [x.get("priceBand"), f'lot {x["lot"]}' if x.get("lot") else None,
                                  f'closes {_fmt(_d(x.get("close")))}' if x["_status"] == "open" else None,
                                  f'opens {_fmt(_d(x.get("open")))}' if x["_status"] == "upcoming" and x.get("open") else None,
                                  f'lists {_fmt(_d(x.get("listing")))}' if x.get("listing") and x["_status"] != "listed" else None] if v)
    gain = ""
    if x.get("listingGainPct") is not None:
        gain = f'<span class="ipogain {"up" if x["listingGainPct"] >= 0 else "down"}">{x["listingGainPct"]:+.1f}% on listing</span>'
    return (f'<article class="ipocard"><div class="iptop"><span class="ipst st-{x["_status"]}">{e(STATUS_LABEL[x["_status"]])}</span>{gain}</div>'
            f'<h3><a href="{base}ipo/{x["slug"]}/">{e(x["name"])} IPO</a></h3><p class="ipmeta">{e(meta)}</p>'
            f'{("<p class=\"ipbiz\">" + e(x["business"]) + "</p>") if x.get("business") else ""}{_sub_html(x.get("subscription"), e)}</article>')


def ipo_pages(posts, ctx):
    page, e, base, card = ctx["page"], ctx["e"], ctx["base"], ctx["card"]
    data = load_ipos()
    today = ctx["today"]
    ipos = []
    for x in data.get("ipos", []):
        if not x.get("name"):
            continue
        x = dict(x)
        x["slug"] = x.get("slug") or _slug(x["name"])
        x["_status"] = ipo_status(x, today)
        ipos.append(x)
    order = {"open": 0, "listing": 1, "closed": 2, "upcoming": 3, "listed": 4}
    ipos.sort(key=lambda x: (order[x["_status"]], _d(x.get("close")) or _d(x.get("listing")) or date.max))
    ipo_posts = [p for p in posts if p["category"] == "startups" and any("ipo" in t.lower() for t in p["_tags"])]
    out = []
    for x in ipos:
        key = x["name"].lower().split()[0]
        rel = [p for p in ipo_posts if key in (p["title"] + " " + " ".join(p["_tags"])).lower()][:12]
        srcs = "".join(f'<li><a href="{e(s.get("url"))}" rel="noopener nofollow" target="_blank">{e(s.get("name"))}</a></li>' for s in x.get("sources") or [] if s.get("url"))
        body = (f'<nav class="crumbs"><a href="{base}">Home</a> / <a href="{base}ipo/">IPO</a></nav>'
                f'<div class="sechead"><h1>{e(x["name"])} IPO: dates, price band, subscription and listing</h1>'
                f'<p>{e(x.get("business") or "")} All key IPO details in one place, updated by TotalMarket on every market day. '
                f'Last checked {e(data.get("asOf") or "")}.</p></div>'
                f'<div class="ipodetail"><div class="tablewrap"><table class="dt"><tbody>{_ipo_rows(x, e)}</tbody></table></div>{_sub_html(x.get("subscription"), e)}</div>'
                + (f'<p class="cm-note">{e(x["note"])}</p>' if x.get("note") else "")
                + (f'<section class="edition"><h2 class="edhead"><b>{e(x["name"])} IPO news</b></h2><div class="grid">{"".join(card(p) for p in rel)}</div></section>' if rel else "")
                + (f'<div class="sources"><h2>Sources</h2><ul>{srcs}</ul></div>' if srcs else "")
                + '<p class="disc">IPO details come from offer documents, exchanges and the sources linked above and can change. Grey market premium is unofficial. This page is for information only and is not a recommendation to apply for or avoid any IPO.</p>')
        nm = x["name"]
        kw = [f"{nm} IPO", f"{nm} IPO GMP", f"{nm} IPO subscription status", f"{nm} IPO listing date", f"{nm} IPO price band", f"{nm} IPO allotment status"]
        title = f"{nm} IPO: Price Band, GMP, Subscription Status, Listing Date"
        out.append((f"ipo/{x['slug']}/index.html", page(title, f"{nm} IPO details: price band, lot size, dates, subscription by category, listing price and latest news.",
                                                      f"{base}ipo/{x['slug']}/", body, ctx["meta"], keywords=kw, seo_title=f"{title} | TotalMarket")))
    groups = []
    for st in ("open", "listing", "closed", "upcoming", "listed"):
        g = [x for x in ipos if x["_status"] == st]
        if g:
            groups.append(f'<section class="edition"><h2 class="edhead"><b>{e(STATUS_LABEL[st])}</b><span>{len(g)}</span></h2><div class="ipogrid">{"".join(_ipo_card(x, e, base) for x in g)}</div></section>')
    lessons = "".join(f'<details class="lessonq"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in LESSONS)
    news = (f'<section class="edition"><h2 class="edhead"><b>Latest IPO news and IPO daily</b></h2><div class="grid">{"".join(card(p) for p in ipo_posts[:12])}</div></section>') if ipo_posts else ""
    body = (f'<div class="sechead"><h1>IPO today: open, upcoming and recently listed IPOs</h1>'
            f'<p>Every mainboard IPO in one place: price bands, lot sizes, subscription by investor category, listing dates and listing gains, plus a daily lesson on how IPOs work. '
            f'Data as of {e(data.get("asOf") or "")}. Grey market premium is unofficial and shown only for context.</p></div>'
            + ("".join(groups) or '<div class="empty"><p>No IPOs listed right now.</p></div>')
            + news
            + f'<section class="lesson"><h2>IPO school: learn the basics</h2>{lessons}</section>'
            + '<p class="disc">For information and education only. TotalMarket does not recommend applying for or avoiding any IPO.</p>')
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in LESSONS]}
    extra = f'<script type="application/ld+json">{json.dumps(faq, ensure_ascii=False)}</script>'
    out.append(("ipo/index.html", page("IPO Today: Upcoming IPOs, Subscription Status, GMP & Listing",
                                       "Upcoming and open IPOs in India: price band, lot size, subscription status by category, listing dates, listing gains and simple IPO lessons.",
                                       f"{base}ipo/", body, ctx["meta"], extra_head=extra,
                                       keywords=["IPO today", "upcoming IPO", "IPO GMP today", "IPO subscription status", "IPO listing today", "new IPO", "mainboard IPO"],
                                       seo_title="IPO Today: Upcoming IPO List, Subscription Status, GMP & Listing Dates | TotalMarket")))
    return out, ipos


def ipo_widget(ipos, e, base):
    live = [x for x in ipos if x["_status"] in ("open", "listing", "closed", "upcoming")][:5]
    if not live:
        return ""
    rows = "".join(f'<li><a href="{base}ipo/{x["slug"]}/"><b>{e(x["name"])}</b><span class="ipst st-{x["_status"]}">{e(STATUS_LABEL[x["_status"]])}</span>'
                   f'<small>{e(x.get("priceBand") or "")}{" · " + format(float(x["subscription"]["total"]), ".2f") + "x" if x.get("subscription") else ""}</small></a></li>' for x in live)
    return f'<section class="panel ipow"><h2>IPO watch <a href="{base}ipo/">All IPOs →</a></h2><ul>{rows}</ul></section>'


# ------------------------------------------------------------------ data pages, live page, learn hub
def _cr(v):
    try:
        v = float(v)
    except Exception:
        return str(v)
    s = f"{abs(v):,.2f}"
    whole, frac = s.split(".")
    whole = whole.replace(",", "")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        whole = head + "," + tail
    return ("−" if v < 0 else "+") + "₹" + whole + "." + frac + " cr"


MARKET_LESSONS = [
    ("What are Sensex and Nifty 50?", "They are stock market indices: the Sensex tracks 30 large companies on BSE, the Nifty 50 tracks 50 large companies on NSE. When people say 'the market rose 1%', they usually mean one of these."),
    ("What are FIIs and DIIs?", "FIIs (or FPIs) are foreign institutional investors such as overseas funds. DIIs are domestic institutional investors such as Indian mutual funds, insurers and pension funds. Their daily buying and selling often explains big market moves."),
    ("What is India VIX?", "The 'fear gauge'. It measures how much traders expect the Nifty to swing over the next 30 days. A rising VIX means traders expect bigger moves, in either direction."),
    ("What is GIFT Nifty?", "A Nifty futures contract traded at GIFT City in Gujarat almost round the clock. Its price before 9:15 am hints at whether Indian markets may open higher or lower."),
    ("Large cap, midcap and smallcap", "Companies are grouped by size (market value). Large caps are the biggest 100, midcaps the next 150, smallcaps the rest. Smaller companies usually rise and fall more sharply."),
    ("What is market breadth?", "The count of shares that rose (advances) versus fell (declines). If the Nifty is flat but 2,700 shares fell and 850 rose, most investors actually lost money that day."),
    ("Support and resistance", "Price levels where buyers (support) or sellers (resistance) have tended to step in before. They are analysts' observations, not guarantees."),
    ("Upper and lower circuit", "The maximum a share is allowed to rise or fall in one day, set by the exchange. A stock 'in upper circuit' has only buyers left at the limit price."),
    ("What is the closing auction session?", "A short session at the end of the day that sets the official closing price of shares from collected orders, meant to make closing prices fairer."),
    ("What is MCX?", "The Multi Commodity Exchange, where gold, silver, crude oil and other commodities trade as futures. MCX gold prices differ from jewellers' shop rates, which add GST and making charges."),
    ("Why does the rupee move?", "Mainly because of dollar demand and supply: oil imports, foreign investors buying or selling Indian shares, and RBI action. A weaker rupee makes imports costlier and exports more competitive."),
    ("What is a P/E ratio?", "Price divided by earnings per share. A P/E of 30 means investors pay ₹30 for every ₹1 of yearly profit. Compare it only with similar companies."),
]


def fii_dii_page(posts, ctx):
    page, e, base = ctx["page"], ctx["e"], ctx["base"]
    path = os.path.join(DATA, "fii_dii.json")
    if not os.path.exists(path):
        return []
    d = json.load(open(path, encoding="utf-8"))
    days = d.get("days", [])
    def nc(v):
        return f'<td class="num {"down" if float(v) < 0 else "up"}">{e(_cr(v))}</td>'
    rows = "".join(f'<tr><th scope="row">{e(_fmt(_d(x["date"])))}</th>{nc(x["fii"]["net"])}{nc(x["dii"]["net"])}'
                   f'<td class="num">{e(_cr(x["fii"]["buy"]).lstrip("+"))} / {e(_cr(x["fii"]["sell"]).lstrip("+"))}</td></tr>' for x in days[:30])
    m = d.get("month") or {}
    latest = days[0] if days else None
    kpis = ""
    if latest:
        kpis = (f'<div class="dkpis"><div><span>FII net · {e(_fmt(_d(latest["date"])))}</span><b class="{"down" if latest["fii"]["net"] < 0 else "up"}">{e(_cr(latest["fii"]["net"]))}</b></div>'
                f'<div><span>DII net · {e(_fmt(_d(latest["date"])))}</span><b class="{"down" if latest["dii"]["net"] < 0 else "up"}">{e(_cr(latest["dii"]["net"]))}</b></div>'
                + (f'<div><span>FII net · {e(m.get("label"))}</span><b class="{"down" if m["fii"]["net"] < 0 else "up"}">{e(_cr(m["fii"]["net"]))}</b></div>'
                   f'<div><span>DII net · {e(m.get("label"))}</span><b class="{"down" if m["dii"]["net"] < 0 else "up"}">{e(_cr(m["dii"]["net"]))}</b></div>' if m else "")
                + '</div>')
    src = d.get("source") or {}
    body = (f'<div class="sechead"><h1>FII DII data today</h1><p>Daily net buying and selling of Indian shares by foreign institutional investors (FIIs) and domestic institutional investors (DIIs) in the cash market, in ₹ crore. '
            f'Figures are provisional, published after market hours, from <a href="{e(src.get("url"))}" rel="nofollow noopener">{e(src.get("name"))}</a>. Latest data: {e(_fmt(_d(latest["date"])) if latest else "—")}.</p></div>'
            + kpis
            + f'<div class="tablewrap"><table class="dt"><thead><tr><th>Date</th><th>FII net</th><th>DII net</th><th>FII buy / sell</th></tr></thead><tbody>{rows}</tbody></table></div>'
            + '<section class="lesson"><h2>How to read FII and DII data</h2><p>A minus sign means net selling: the group sold more shares than it bought that day. When FIIs sell heavily, they also convert rupees into dollars, which can weaken the rupee. In 2026, DIIs, powered by monthly SIP money from Indian savers, have often bought almost as much as FIIs sold, which cushions the market.</p>'
            '<p>Worked example: if FIIs are −₹5,285 crore and DIIs +₹3,319 crore on a day, institutions together sold about ₹1,966 crore, so the market more likely fell. One day\'s number matters less than the trend over weeks.</p></section>'
            + '<p class="disc">Provisional exchange data as reported by the source above; final figures can differ slightly. For information only, not investment advice.</p>')
    return [("fii-dii-data/index.html", page("FII DII Data Today: Foreign & Domestic Institutional Investor Activity",
             "FII and DII data today: daily net buying and selling in Indian shares by foreign and domestic institutions, with month-to-date totals and a simple explanation.",
             f"{base}fii-dii-data/", body, ctx["meta"], keywords=["FII DII data", "FII DII data today", "FII data today", "DII data today", "FPI selling", "FII selling October"],
             seo_title="FII DII Data Today: FII & DII Buy, Sell, Net (₹ Crore) | TotalMarket"))]


def gainers_page(posts, ctx):
    page, e, base, url = ctx["page"], ctx["e"], ctx["base"], ctx["url"]
    rep = next((p for p in posts if p.get("report")), None)
    if not rep:
        return []
    r = rep["report"]
    def tbl(items):
        return "".join(f'<tr><th scope="row">{e(x.get("name"))}</th><td class="num">{e(x.get("price") or "—")}</td>'
                       f'<td class="num {"down" if str(x.get("pct","")).startswith("-") else "up"}">{"" if str(x.get("pct","")).startswith(("-","+")) else "+"}{e(x.get("pct"))}%</td></tr>' for x in items)
    b = r.get("breadth") or {}
    br = ""
    if b:
        br = (f'<div class="dkpis"><div><span>Advances</span><b class="up">{e(b.get("advances"))}</b></div><div><span>Declines</span><b class="down">{e(b.get("declines"))}</b></div>'
              f'<div><span>52-week highs / lows</span><b>{e(b.get("highs52"))} / {e(b.get("lows52"))}</b></div><div><span>Investor wealth</span><b>{e(b.get("wealth") or "—")}</b></div></div>')
    mv = r.get("movers") or {}
    mrows = ""
    if mv:
        mrows = (f'<section class="edition"><h2 class="edhead"><b>{e(mv.get("title") or "Broader market movers")}</b></h2><div class="gl2">'
                 f'<div class="tablewrap"><table class="dt"><thead><tr><th>Gainers</th><th>Price</th><th>%</th></tr></thead><tbody>{tbl(mv.get("up") or [])}</tbody></table></div>'
                 f'<div class="tablewrap"><table class="dt"><thead><tr><th>Losers</th><th>Price</th><th>%</th></tr></thead><tbody>{tbl(mv.get("down") or [])}</tbody></table></div></div></section>')
    body = (f'<div class="sechead"><h1>Top gainers and losers today</h1><p>{e(r.get("moversIndex") or "Nifty 50")} top gainers and losers at the close on {e(r.get("dateLabel"))}, with market breadth. '
            f'Updated every market day with the evening report. <a href="{url(rep)}">Read the full daily market report →</a></p></div>'
            + br
            + f'<div class="gl2"><div class="tablewrap"><table class="dt"><thead><tr><th>Top gainers</th><th>Close</th><th>% Chg</th></tr></thead><tbody>{tbl(r.get("gainers") or [])}</tbody></table></div>'
            f'<div class="tablewrap"><table class="dt"><thead><tr><th>Top losers</th><th>Close</th><th>% Chg</th></tr></thead><tbody>{tbl(r.get("losers") or [])}</tbody></table></div></div>'
            + mrows
            + '<p class="disc">Closing prices as reported in the sources of the linked daily report. For information only, not investment advice.</p>')
    return [("top-gainers-losers-today/index.html", page("Top Gainers and Losers Today: Nifty 50 Stocks",
             f"Top gainers and losers today in the Nifty 50 with closing prices and % change, plus advances, declines and 52-week highs ({r.get('dateLabel')}).",
             f"{base}top-gainers-losers-today/", body, ctx["meta"], keywords=["top gainers today", "top losers today", "top gainers and losers", "Nifty top gainers", "market breadth"],
             seo_title="Top Gainers and Losers Today: Nifty 50, Advances & Declines | TotalMarket"))]


def live_page(posts, ctx):
    page, e, base, url, ist = ctx["page"], ctx["e"], ctx["base"], ctx["url"], ctx["ist"]
    if not posts:
        return []
    day = posts[0]["_dt"].astimezone(ist).date()
    todays = [p for p in posts if p["_dt"].astimezone(ist).date() == day]
    items = "".join(
        f'<li class="lv"><time datetime="{e(p["_dt"].isoformat())}">{e(p["_dt"].astimezone(ist).strftime("%-I:%M %p"))}</time>'
        f'<div><span class="lvslot">{e((p.get("editionLabel") or "").split("·")[-1].strip())}</span><h3><a href="{url(p)}">{e(p["title"])}</a></h3>'
        f'<p>{e(p.get("dek") or "")}</p></div></li>' for p in todays)
    dl = day.strftime("%-d %B %Y")
    ld = {"@context": "https://schema.org", "@type": "LiveBlogPosting", "headline": f"Stock market live today, {dl}",
          "url": ctx["site_url"] + "/live/", "coverageStartTime": todays[-1]["_dt"].isoformat(), "coverageEndTime": todays[0]["_dt"].isoformat(),
          "liveBlogUpdate": [{"@type": "BlogPosting", "headline": p["title"][:110], "datePublished": p["_dt"].isoformat(), "url": ctx["site_url"] + url(p)} for p in todays[:30]]}
    body = (f'<div class="sechead"><h1><span class="livedot" aria-hidden="true"></span>Stock market live today: {e(dl)}</h1>'
            f'<p>Every TotalMarket update for {e(dl)} in one timeline, newest first: pre-market brief, midday check, closing wrap, daily report and evening update. '
            f'{len(todays)} updates so far. Times are IST.</p></div><ol class="lvlist">{items}</ol>')
    return [("live/index.html", page(f"Stock Market Live Today {dl}: Sensex, Nifty, IPO Updates",
             f"Stock market live updates for {dl}: Sensex, Nifty, IPOs, gold, crude and rupee, all of today's TotalMarket updates in one timeline.",
             f"{base}live/", body, ctx["meta"], extra_head=f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>',
             keywords=["stock market live", "share market live today", "Sensex live", "Nifty live", "stock market today"],
             seo_title=f"Stock Market Live Today ({dl}): Sensex, Nifty, IPO Updates | TotalMarket"))]


def learn_page(ctx):
    page, e, base = ctx["page"], ctx["e"], ctx["base"]
    def sec(title, items, pre):
        return (f'<section class="lesson"><h2>{e(title)}</h2>'
                + "".join(f'<details class="lessonq" id="{pre}-{_slug(q)[:40]}"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in items) + "</section>")
    body = (f'<div class="sechead"><h1>Learn: stock market and IPO basics</h1><p>Short, plain-language lessons on the words you see in TotalMarket stories every day. '
            f'Tap a question to open it. Also see the <a href="{base}calculators/">SIP and EMI calculators</a> and the <a href="{base}ipo/">IPO hub</a>.</p></div>'
            + sec("Stock market basics", MARKET_LESSONS, "m") + sec("IPO basics", LESSONS, "ipo")
            + '<p class="disc">Education only, not investment advice.</p>')
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in MARKET_LESSONS + LESSONS]}
    return [("learn/index.html", page("Learn Stock Market Basics: Sensex, Nifty, FII, IPO Explained",
             "Simple lessons on stock market and IPO basics for Indian beginners: Sensex, Nifty, FII and DII, VIX, GIFT Nifty, IPO price band, GMP, allotment and more.",
             f"{base}learn/", body, ctx["meta"], extra_head=f'<script type="application/ld+json">{json.dumps(faq, ensure_ascii=False)}</script>',
             keywords=["stock market basics", "share market for beginners", "what is Nifty", "what is FII DII", "IPO basics", "what is GMP"],
             seo_title="Learn Stock Market Basics for Beginners in India | TotalMarket"))]
