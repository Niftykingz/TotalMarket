"""Company pages (/stock/<slug>/) and the IPO hub (/ipo/ and /ipo/<slug>/).

Both are generated from data the update runs already write:
- companies: the `companies` field on stories, plus data/results.json for the next results date
- IPOs: data/ipos.json (see README "IPO hub")
"""
import json
import os
import re
from datetime import date, datetime, time, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")




def _datefmt(dt, pattern):
    """Portable strftime for Windows and Unix (no platform-specific %-d/%-I)."""
    day = str(dt.day)
    hour = str(dt.hour % 12 or 12) if "%-I" in pattern else ""
    # Substitute tokens before strftime to avoid platform-specific directives.
    return dt.strftime(pattern.replace("%-d", "__TM_DAY__").replace("%-I", "__TM_HOUR__")).replace("__TM_DAY__", day).replace("__TM_HOUR__", hour)

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
    return _datefmt(d, "%a %-d %b") if d else "—"


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
        facts.append(("Latest update", _datefmt(c["posts"][0]["_dt"].astimezone(ctx["ist"]), "%-d %b %Y, %-I:%M %p IST")))
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


# ------------------------------------------------------------------ IPO timeline (IST)
# Indian mainboard and SME IPOs: bidding opens 10:00 am on the open date and closes 5:00 pm
# on the close date (UPI mandates must be accepted by then); allotment is finalised on the
# allotment date (T+1); shares start trading at 10:00 am on the listing date (T+3), after
# the 9:00–10:00 special pre-open session. A record may override any time with
# openTime / closeTime / listingTime ("HH:MM", IST).
IST_TZ = timezone(timedelta(hours=5, minutes=30))
OPEN_AT, CLOSE_AT, LIST_AT = time(10, 0), time(17, 0), time(10, 0)


def _hm(x, key, default):
    try:
        h, m = str(x.get(key) or "").split(":")
        return time(int(h), int(m))
    except Exception:
        return default


def _now(now):
    """Accept a datetime (any zone) or a bare date (treated as midday IST, the old behaviour)."""
    if isinstance(now, datetime):
        return now.astimezone(IST_TZ) if now.tzinfo else now.replace(tzinfo=IST_TZ)
    if isinstance(now, date):
        return datetime.combine(now, time(12, 0), IST_TZ)
    return datetime.now(IST_TZ)


def ipo_times(x):
    """Key moments of an IPO as IST datetimes (None when the date is unknown)."""
    at = lambda d, t: datetime.combine(d, t, IST_TZ) if d else None
    o, c, a, l = _d(x.get("open")), _d(x.get("close")), _d(x.get("allotment")), _d(x.get("listing"))
    return {"open": at(o, _hm(x, "openTime", OPEN_AT)), "close": at(c, _hm(x, "closeTime", CLOSE_AT)),
            "allotment": a, "listing": at(l, _hm(x, "listingTime", LIST_AT))}


def ipo_status(x, now=None):
    """upcoming → open → closed (allotment / awaiting listing) → listing (listing day) → listed."""
    n = _now(now)
    t = ipo_times(x)
    if x.get("listingPrice") or (x.get("listed") and t["listing"] and n >= t["listing"]):
        return "listed"
    if t["listing"] and n.date() >= t["listing"].date():
        return "listing"          # listing day (before 10 am: pre-open; after: trading, price not yet recorded)
    if t["close"] and n >= t["close"]:
        return "closed"
    if t["open"] and n >= t["open"]:
        return "open"
    if t["open"]:
        return "upcoming"
    return "closed" if t["close"] and n.date() > t["close"].date() else "upcoming"


def _when(dt, n):
    d = dt.date() if isinstance(dt, datetime) else dt
    if d == n.date():
        return "today"
    if d == n.date() + timedelta(days=1):
        return "tomorrow"
    return _fmt(d)


def _clock(dt):
    h = dt.hour % 12 or 12
    return f"{h}{':' + format(dt.minute, '02d') if dt.minute else ''} {'am' if dt.hour < 12 else 'pm'}"


def ipo_phase(x, now=None):
    """One plain line for readers: what happens next and when (IST)."""
    n, t, st = _now(now), ipo_times(x), ipo_status(x, now)
    if st == "upcoming" and t["open"]:
        return f"Opens {_when(t['open'], n)}, {_clock(t['open'])}"
    if st == "open" and t["close"]:
        return f"Bidding closes {_when(t['close'], n)}, {_clock(t['close'])}"
    if st == "closed":
        a = t["allotment"]
        if a and a > n.date():
            return f"Bidding closed · allotment {_when(a, n)}" + (f" · lists {_fmt(t['listing'].date())}" if t["listing"] else "")
        if a and a == n.date():
            return "Allotment today" + (f" · lists {_when(t['listing'], n)}" if t["listing"] else "")
        return "Allotment done" + (f" · lists {_when(t['listing'], n)}, {_clock(t['listing'])}" if t["listing"] else " · listing date to be announced")
    if st == "listing" and t["listing"]:
        return f"Lists today, trading from {_clock(t['listing'])}" if n < t["listing"] else "Listing today · trading now"
    if st == "listed" and t["listing"]:
        return f"Listed {_fmt(t['listing'].date())}"
    return ""


def ipo_data_attrs(x, lang="en"):
    """data-* attributes the browser script uses to keep the status correct after the page was built."""
    t = ipo_times(x)
    iso = lambda v: v.isoformat() if isinstance(v, datetime) else (v.isoformat() if v else "")
    return (f' data-ipo-open="{iso(t["open"])}" data-ipo-close="{iso(t["close"])}" data-ipo-allot="{iso(t["allotment"])}"'
            f' data-ipo-list="{iso(t["listing"])}" data-ipo-listed="{1 if (x.get("listingPrice") or x.get("listed")) else 0}" data-ipo-lang="{lang}"')


STATUS_LABEL = {"open": "Open now", "upcoming": "Upcoming", "closed": "Bidding closed", "listing": "Listing today", "listed": "Listed"}

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
    lab, ph = STATUS_LABEL.get(x["_status"], ""), x.get("_phase") or ""
    rows = [("Status", ph if ph.startswith(lab) else " · ".join(v for v in (lab, ph) if v)), ("Segment", x.get("segment") or "Mainboard"), ("Exchanges", x.get("exchange") or "NSE, BSE"),
            ("Price band", x.get("priceBand")), ("Lot size", f'{x["lot"]} shares' if x.get("lot") else None),
            ("Minimum investment", _inr(x["minAmount"]) + " (at upper band)" if x.get("minAmount") else None),
            ("Issue size", x.get("issueSize")), ("Fresh issue", x.get("fresh")), ("Offer for sale (OFS)", x.get("ofs")),
            ("Opens", f'{_fmt(_d(x.get("open")))}, {_clock(ipo_times(x)["open"])} IST' if x.get("open") else None),
            ("Closes", f'{_fmt(_d(x.get("close")))}, {_clock(ipo_times(x)["close"])} IST (bidding and UPI mandate cut-off)' if x.get("close") else None),
            ("Allotment", _fmt(_d(x.get("allotment"))) if x.get("allotment") else None), ("Listing", f'{_fmt(_d(x.get("listing")))}, trading from {_clock(ipo_times(x)["listing"])} IST' if x.get("listing") else None),
            ("Issue price", _inr(x["issuePrice"]) if x.get("issuePrice") else None),
            ("Listing price", f'{_inr(x["listingPrice"])} ({x["listingGainPct"]:+.1f}%)' if x.get("listingPrice") and x.get("listingGainPct") is not None else None),
            ("After listing", x.get("afterListing")),
            ("Grey market premium", f'{x["gmp"]["value"]} · {x["gmp"].get("asOf", "")} · unofficial' if x.get("gmp") else None)]
    return "".join(f'<tr><th scope="row">{e(k)}</th><td>{e(v)}</td></tr>' for k, v in rows if v)


def _ipo_card(x, e, base):
    meta = " · ".join(v for v in [x.get("priceBand"), f'lot {x["lot"]}' if x.get("lot") else None] if v)
    gain = ""
    if x.get("listingGainPct") is not None:
        gain = f'<span class="ipogain {"up" if x["listingGainPct"] >= 0 else "down"}">{x["listingGainPct"]:+.1f}% on listing</span>'
    return (f'<article class="ipocard"{ipo_data_attrs(x)}><div class="iptop"><span class="ipst st-{x["_status"]}" data-ipo-badge>{e(STATUS_LABEL[x["_status"]])}</span>{gain}</div>'
            f'<h3><a href="{base}ipo/{x["slug"]}/">{e(x["name"])} IPO</a></h3><p class="ipphase" data-ipo-phase>{e(x.get("_phase") or "")}</p><p class="ipmeta">{e(meta)}</p>'
            f'{("<p class=\"ipbiz\">" + e(x["business"]) + "</p>") if x.get("business") else ""}{_sub_html(x.get("subscription"), e)}</article>')


def ipo_pages(posts, ctx):
    page, e, base, card = ctx["page"], ctx["e"], ctx["base"], ctx["card"]
    data = load_ipos()
    now = ctx.get("now") or ctx["today"]
    ipos = []
    for x in data.get("ipos", []):
        if not x.get("name"):
            continue
        x = dict(x)
        x["slug"] = x.get("slug") or _slug(x["name"])
        x["_status"] = ipo_status(x, now)
        x["_phase"] = ipo_phase(x, now)
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
        title = f"{nm} IPO: GMP, Subscription, Listing Date"
        out.append((f"ipo/{x['slug']}/index.html", page(title, f"{nm} IPO details: price band, lot size, dates, subscription by category, listing price and latest news.",
                                                      f"{base}ipo/{x['slug']}/", body, ctx["meta"], keywords=kw)))
    groups = []
    for st in ("open", "listing", "closed", "upcoming", "listed"):
        g = [x for x in ipos if x["_status"] == st]
        if g:
            groups.append(f'<section class="edition" data-ipo-group="{st}"><h2 class="edhead"><b>{e(STATUS_LABEL[st])}</b><span>{len(g)}</span></h2><div class="ipogrid">{"".join(_ipo_card(x, e, base) for x in g)}</div></section>')
    lessons = "".join(f'<details class="lessonq"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in LESSONS)
    news = (f'<section class="edition"><h2 class="edhead"><b>Latest IPO news and IPO daily</b></h2><div class="grid">{"".join(card(p) for p in ipo_posts[:12])}</div></section>') if ipo_posts else ""
    body = (f'<div class="sechead"><h1>IPO today: open, upcoming and recently listed IPOs</h1>'
            f'<p>Every mainboard IPO in one place: price bands, lot sizes, subscription by investor category, listing dates and listing gains, plus a daily lesson on how IPOs work. '
            f'Data as of {e(data.get("asOf") or "")}. Grey market premium is unofficial and shown only for context.</p></div>'
            + ctx["piggy_host"]("Boss Piggy's IPO guide", "Every IPO below shows the facts first: dates, price band, lot size and who has applied so far. Open any IPO for the full details, and scroll down to my IPO school to learn what each term means before you read the numbers.", (f"{base}learn/", "More lessons"))
            + ("".join(groups) or '<div class="empty"><p>No IPOs listed right now.</p></div>')
            + news
            + f'<section class="lesson" id="learn"><h2>IPO school: learn the basics</h2>{lessons}</section>'
            + '<p class="disc">For information and education only. TotalMarket does not recommend applying for or avoiding any IPO.</p>')
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in LESSONS]}
    extra = f'<script type="application/ld+json">{json.dumps(faq, ensure_ascii=False)}</script>'
    out.append(("ipo/index.html", page("IPO Today: Upcoming IPOs, Subscription Status, GMP & Listing",
                                       "Upcoming and open IPOs in India: price band, lot size, subscription status by category, listing dates, listing gains and simple IPO lessons.",
                                       f"{base}ipo/", body, ctx["meta"], extra_head=extra,
                                       keywords=["IPO today", "upcoming IPO", "IPO GMP today", "IPO subscription status", "IPO listing today", "new IPO", "mainboard IPO"],
                                       seo_title="IPO Today: Upcoming IPOs, GMP & Subscription | TotalMarket")))
    return out, ipos


def ipo_widget(ipos, e, base):
    live = [x for x in ipos if x["_status"] in ("open", "listing", "closed", "upcoming")][:5]
    if not live:
        return ""
    rows = "".join(f'<li{ipo_data_attrs(x)}><a href="{base}ipo/{x["slug"]}/"><b>{e(x["name"])}</b><span class="ipst st-{x["_status"]}" data-ipo-badge>{e(STATUS_LABEL[x["_status"]])}</span>'
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
        f'<li class="lv"><time datetime="{e(p["_dt"].isoformat())}">{e(_datefmt(p["_dt"].astimezone(ist), "%-I:%M %p"))}</time>'
        f'<div><span class="lvslot">{e((p.get("editionLabel") or "").split("·")[-1].strip())}</span><h3><a href="{url(p)}">{e(p["title"])}</a></h3>'
        f'<p>{e(p.get("dek") or "")}</p></div></li>' for p in todays)
    dl = _datefmt(day, "%-d %B %Y")
    ld = {"@context": "https://schema.org", "@type": "LiveBlogPosting", "headline": f"Stock market today: all updates for {dl}",
          "url": ctx["site_url"] + "/live/", "coverageStartTime": todays[-1]["_dt"].isoformat(), "coverageEndTime": todays[0]["_dt"].isoformat(),
          "liveBlogUpdate": [{"@type": "BlogPosting", "headline": p["title"][:110], "datePublished": p["_dt"].isoformat(), "url": ctx["site_url"] + url(p)} for p in todays[:30]]}
    body = (f'<div class="sechead"><h1><span class="livedot" aria-hidden="true"></span>Stock market today: all updates for {e(dl)}</h1>'
            f'<p>Every TotalMarket update for {e(dl)} in one timeline, newest first: pre-market brief, midday check, closing wrap, daily report and evening update. '
            f'{len(todays)} updates so far. Times are IST.</p></div><ol class="lvlist">{items}</ol>')
    return [("live/index.html", page(f"Stock Market Today {dl}: All Updates on Sensex, Nifty, IPOs",
             f"Stock market today, {dl}: every TotalMarket update on Sensex, Nifty, IPOs, gold, crude and the rupee in one timeline, newest first.",
             f"{base}live/", body, ctx["meta"], extra_head=f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>',
             keywords=["stock market today", "share market today", "stock market updates", "Sensex today", "Nifty today"],
             seo_title=f"Stock Market Today ({dl}): All Updates | TotalMarket"))]


def learn_page(ctx):
    page, e, base = ctx["page"], ctx["e"], ctx["base"]
    def sec(title, items, pre):
        return (f'<section class="lesson"><h2>{e(title)}</h2>'
                + "".join(f'<details class="lessonq" id="{pre}-{_slug(q)[:40]}"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in items) + "</section>")
    body = (f'<div class="sechead"><h1>Learn: stock market and IPO basics</h1><p>Short, plain-language lessons on the words you see in TotalMarket stories every day. '
            f'Tap a question to open it. Also see the <a href="{base}calculators/">SIP and EMI calculators</a> and the <a href="{base}ipo/">IPO hub</a>.</p></div>'
            + ctx["piggy_host"]("Learn with Boss Piggy", "Markets have a lot of jargon. Pick any question below and I'll explain it in plain words, with a small example. Start with Sensex and Nifty, then FIIs, then IPO basics.", (f"{base}ipo/", "See today's IPOs"))
            + sec("Stock market basics", MARKET_LESSONS, "m") + sec("IPO basics", LESSONS, "ipo")
            + '<p class="disc">Education only, not investment advice.</p>')
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in MARKET_LESSONS + LESSONS]}
    return [("learn/index.html", page("Learn Stock Market Basics: Sensex, Nifty, FII, IPO Explained",
             "Simple lessons on stock market and IPO basics for Indian beginners: Sensex, Nifty, FII and DII, VIX, GIFT Nifty, IPO price band, GMP, allotment and more.",
             f"{base}learn/", body, ctx["meta"], extra_head=f'<script type="application/ld+json">{json.dumps(faq, ensure_ascii=False)}</script>',
             keywords=["stock market basics", "share market for beginners", "what is Nifty", "what is FII DII", "IPO basics", "what is GMP"],
             seo_title="Learn Stock Market Basics for Beginners in India | TotalMarket"))]


# ------------------------------------------------------------------ evergreen market-data pages
def _pct_cls(v):
    s = str(v or "")
    return "down" if s.startswith("-") else ("up" if s.strip("+") not in ("", "0", "0.0") else "")


def global_page(posts, ctx):
    page, e, base, url = ctx["page"], ctx["e"], ctx["base"], ctx["url"]
    path = os.path.join(DATA, "global.json")
    if not os.path.exists(path):
        return []
    g = json.load(open(path, encoding="utf-8"))
    secs = []
    for reg in g.get("regions", []):
        rows = "".join(
            f'<tr><th scope="row">{e(r["name"])}</th><td class="num">{e(r.get("value") or "—")}</td>'
            f'<td class="num {_pct_cls(r.get("pct") or r.get("change"))}">{e(r.get("change") or "")}</td>'
            f'<td class="num {_pct_cls(r.get("pct"))}">{e((r["pct"] + "%") if r.get("pct") else "")}</td>'
            f'<td><span class="dtype t-{e(r.get("type"))}">{"Close" if r.get("type") == "close" else "Intraday"}</span> {e(r.get("asOf"))}</td>'
            f'<td><a href="{e((r.get("source") or {}).get("url"))}" rel="nofollow noopener" target="_blank">{e((r.get("source") or {}).get("name"))}</a></td></tr>'
            for r in reg.get("rows", []))
        secs.append(f'<section class="edition"><h2 class="edhead"><b>{e(reg["region"])}</b></h2><div class="tablewrap"><table class="dt"><thead><tr>'
                    f'<th>Index</th><th>Level</th><th>Change</th><th>% Chg</th><th>As of</th><th>Source</th></tr></thead><tbody>{rows}</tbody></table></div></section>')
    news = [p for p in posts if p["category"] == "global"][:6]
    upd = _d(str(g.get("updatedAt", ""))[:10])
    piggy = ctx["piggy_box"]({"happened": "This page lists the latest closing (or clearly marked intraday) level of the world's main stock indices, each with its date, time and source.",
                              "matters": "Overnight moves in the US and Asia often set the mood for Indian markets the next morning, because global funds move money across countries and the same worries (oil, US interest rates, AI stocks) affect everyone.",
                              "watch": ["The US close each evening (IST night) and GIFT Nifty before 9:15 am", "US 10-year bond yields and the dollar", "Big moves in Asian chip stocks such as Korea and Taiwan"]})
    body = (f'<nav class="crumbs"><a href="{base}">Home</a> / <a href="{base}global/">Global Markets</a></nav>'
            f'<div class="sechead"><h1>Global indices today: US, Asia and India</h1>'
            f'<p>Latest verified levels of the Dow, S&amp;P 500, Nasdaq, Nikkei, Hang Seng, Kospi and more, with what each move means for India. '
            f'Updated with every pre-market brief{(" · last updated " + e(_datefmt(upd, "%-d %b %Y"))) if upd else ""}. {e(g.get("note") or "")}</p></div>'
            + "".join(secs) + piggy
            + ((f'<section class="edition"><h2 class="edhead"><b>Latest global market news</b></h2><div class="grid">{"".join(ctx["card"](p) for p in news)}</div></section>') if news else "")
            + f'<p class="cm-note">See also: <a href="{base}nifty-50/">Nifty 50 today</a> · <a href="{base}live/">Today\'s updates</a> · <a href="{base}market-report/">Daily market report</a></p>'
            + '<p class="disc">Index levels are taken from the news sources linked in each row and may be delayed. TotalMarket does not provide live prices. For information only, not investment advice.</p>')
    return [("global-indices/index.html", page("Global Indices Today: Dow, Nasdaq, Nikkei, Hang Seng & More",
             "Global indices today: latest Dow Jones, S&P 500, Nasdaq, Nikkei, Hang Seng, Kospi and Shanghai levels with date, source and what the moves mean for India.",
             f"{base}global-indices/", body, ctx["meta"], keywords=["global market", "global indices", "global market today", "Dow Jones today", "Nasdaq today", "Nikkei today", "Hang Seng today", "US market today"],
             seo_title="Global Indices Today: Dow, Nasdaq, Nikkei, Hang Seng | TotalMarket"))]


def nifty_page(posts, ctx):
    page, e, base, url, meta = ctx["page"], ctx["e"], ctx["base"], ctx["url"], ctx["meta"]
    hist = (meta.get("history") or {}).get("Nifty 50") or []
    if not hist:
        return []
    last = hist[-1]
    prev = hist[-2] if len(hist) > 1 else None
    rep = next((p for p in posts if p.get("report")), None)
    r = rep["report"] if rep else {}
    row = next((x for x in r.get("indices", []) if x.get("name") == "Nifty 50"), None) if r.get("date") == last["d"] else None
    chg = last["v"] - prev["v"] if prev else None
    pct = chg / prev["v"] * 100 if prev else None
    ld = _d(last["d"])
    kp = [("Last close", f'{last["v"]:,.2f}', f'{chg:+,.2f} ({pct:+.2f}%)' if chg is not None else "")]
    if row:
        kp += [("Day open", row.get("open"), ""), ("Day high", row.get("high"), ""), ("Day low", row.get("low"), "")]
    kpis = '<div class="dkpis">' + "".join(f'<div><span>{e(k)} · {e(_fmt(ld))}</span><b class="{_pct_cls(c)}">{e(v)}</b>{("<small class=\"" + _pct_cls(c) + "\">" + e(c) + "</small>") if c else ""}</div>' for k, v, c in kp) + "</div>"
    chart = ctx["line_chart"](hist[-30:]) if ctx.get("line_chart") else ""
    trows = []
    for i in range(len(hist) - 1, max(0, len(hist) - 15), -1):
        x, p0 = hist[i], hist[i - 1] if i > 0 else None
        c = (x["v"] - p0["v"]) if p0 else None
        trows.append(f'<tr><th scope="row">{e(_fmt(_d(x["d"])))}</th><td class="num">{x["v"]:,.2f}</td>'
                     f'<td class="num {"down" if c is not None and c < 0 else "up"}">{"" if c is None else f"{c:+,.2f}"}</td>'
                     f'<td class="num {"down" if c is not None and c < 0 else "up"}">{"" if c is None else f"{c / p0["v"] * 100:+.2f}%"}</td></tr>')
    def gl(items):
        return "".join(f'<tr><th scope="row">{e(x.get("name"))}</th><td class="num">{e(x.get("price") or "—")}</td>'
                       f'<td class="num {_pct_cls(x.get("pct"))}">{"" if str(x.get("pct","")).startswith(("-","+")) else "+"}{e(x.get("pct"))}%</td></tr>' for x in items[:5])
    movers = ""
    if r.get("gainers"):
        movers = (f'<section class="edition"><h2 class="edhead"><b>Top Nifty 50 movers · {e(r.get("dateLabel"))}</b></h2><div class="gl2">'
                  f'<div class="tablewrap"><table class="dt"><thead><tr><th>Gainers</th><th>Close</th><th>%</th></tr></thead><tbody>{gl(r.get("gainers") or [])}</tbody></table></div>'
                  f'<div class="tablewrap"><table class="dt"><thead><tr><th>Losers</th><th>Close</th><th>%</th></tr></thead><tbody>{gl(r.get("losers") or [])}</tbody></table></div></div>'
                  f'<p class="cm-note">From the <a href="{url(rep)}">daily market report for {e(r.get("dateLabel"))}</a>. More on the <a href="{base}top-gainers-losers-today/">top gainers and losers page</a>.</p></section>')
    reports = [p for p in posts if p.get("report")][:5]
    rlinks = "".join(f'<li><a href="{url(p)}">{e(p["title"])}</a></li>' for p in reports)
    piggy = ctx["piggy_box"]({"happened": f"The Nifty 50 last closed at {last['v']:,.2f} on {_fmt(ld)}" + (f", {chg:+,.2f} points ({pct:+.2f}%) from the previous session." if chg is not None else "."),
                              "matters": "The Nifty 50 tracks 50 of the largest companies on NSE, so it is the quickest way to see how big Indian shares did. Most index funds and many mutual funds are measured against it.",
                              "watch": ["FII and DII flows, published every evening", "Results from large Nifty companies this week", "Global cues: the US close and GIFT Nifty before 9:15 am"]})
    body = (f'<nav class="crumbs"><a href="{base}">Home</a> / <a href="{base}markets/">Markets</a></nav>'
            f'<div class="sechead"><h1>Nifty 50 today: latest close, chart and top movers</h1>'
            f'<p>Closing levels of the Nifty 50 index from TotalMarket\'s daily market reports, with the day\'s range, the last {len(hist)} sessions and the biggest movers. '
            f'Data is end-of-day, not live; latest close: {e(_fmt(ld))}.</p></div>'
            + kpis + (f'<section class="panel nchart"><h2>Nifty 50 closing levels, last {len(hist[-30:])} sessions</h2>{chart}</section>' if chart else "")
            + piggy + movers
            + f'<section class="edition"><h2 class="edhead"><b>Nifty 50 history</b></h2><div class="tablewrap"><table class="dt"><thead><tr><th>Date</th><th>Close</th><th>Change</th><th>% Chg</th></tr></thead><tbody>{"".join(trows)}</tbody></table></div></section>'
            + '<section class="lesson"><h2>About the Nifty 50</h2><p>The Nifty 50 is NSE\'s main index of 50 large, actively traded Indian companies across sectors. Each company\'s weight depends on the value of its shares available for trading (free-float market capitalisation), so the biggest companies move the index most. '
              'NSE reviews the list twice a year, which is why companies are occasionally added or removed.</p>'
              '<p>The official, current list of the 50 companies and their weights is published by NSE Indices on <a href="https://www.niftyindices.com/" rel="nofollow noopener" target="_blank">niftyindices.com</a>. We link to it rather than copying it, because it changes after each review.</p></section>'
            + (f'<section class="lesson"><h2>Recent daily market reports</h2><ul>{rlinks}</ul></section>' if rlinks else "")
            + f'<p class="cm-note">See also: <a href="{base}global-indices/">Global indices</a> · <a href="{base}fii-dii-data/">FII/DII data</a> · <a href="{base}live/">Today\'s updates</a></p>'
            + '<p class="disc">Closing levels as reported in the sources of TotalMarket\'s daily reports. For information only, not investment advice.</p>')
    return [("nifty-50/index.html", page("Nifty 50 Today: Latest Close, Chart, Top Gainers & Losers",
             f"Nifty 50 today: last close {last['v']:,.2f} ({_fmt(ld)}), day range, closing history, chart and top gainers and losers, with what the moves mean.",
             f"{base}nifty-50/", body, meta, keywords=["Nifty 50", "Nifty 50 today", "Nifty today", "Nifty 50 chart", "Nifty closing", "Nifty top gainers"],
             seo_title="Nifty 50 Today: Latest Close, Chart & Top Movers | TotalMarket"))]
