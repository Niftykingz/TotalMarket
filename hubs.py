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
