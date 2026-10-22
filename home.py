"""TotalMarket homepage (v2 design): reusable, data-driven components.

Every block reads real site data (posts, data/meta.json history, the latest
daily report, data/ipos.json, data/rates.json, data/results.json). If a source
is missing, the block hides or shows a clear "not available" note — never a
made-up number. Each market block carries its data type (EOD / delayed),
source and last-update time.
"""
import json, os
from datetime import datetime, timedelta, date

ROOT = os.path.dirname(os.path.abspath(__file__))

ICONS = {  # small inline SVG icons (no icon font, no extra requests)
    "news": '<path d="M4 5h13v14H6a2 2 0 0 1-2-2V5Zm13 4h3v8a2 2 0 0 1-2 2h-1M7 9h7M7 13h7M7 17h4"/>',
    "chart": '<path d="M4 19h16M6 15l4-5 3 3 5-7"/>',
    "ipo": '<path d="M12 3v14M7 8l5-5 5 5M5 21h14"/>',
    "tech": '<rect x="7" y="7" width="10" height="10" rx="2"/><path d="M10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18"/>',
    "coin": '<ellipse cx="12" cy="7" rx="7" ry="3"/><path d="M5 7v5c0 1.7 3.1 3 7 3s7-1.3 7-3V7M5 12v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5"/>',
    "cal": '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M8 3v4M16 3v4M4 10h16"/>',
    "report": '<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h6"/>',
    "learn": '<path d="M3 8l9-4 9 4-9 4-9-4Z"/><path d="M7 10v5c3 2 7 2 10 0v-5"/>',
    "calc": '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 7h8M8 11h2M12 11h2M16 11h0M8 15h2M12 15h2M8 18h2M12 18h2"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
}


def icon(name, cls="ic"):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


def shead(c, title, ic, link=None, label="View all", h="h2", extra=""):
    e = c["e"]
    more = f'<a class="vall" href="{e(link)}">{label} {icon("arrow", "ia")}</a>' if link else ""
    return f'<div class="shead"><{h}><span class="sic">{icon(ic)}</span>{e(title)}</{h}>{extra}{more}</div>'


def short_ago(p, ist):
    mins = int((datetime.now(ist) - p["_dt"]).total_seconds() // 60)
    if mins < 60: return f"{max(mins, 1)}m"
    if mins < 60 * 24: return f"{mins // 60}h"
    return p["_dt"].astimezone(ist).strftime("%d %b")


def fresh_badge(kind, text=None):
    """Data-type label: we never show 'live' (no licensed real-time feed)."""
    k = str(kind or "").lower()
    lbl = {"close": "EOD", "eod": "EOD", "intraday": "Delayed", "delayed": "Delayed", "preliminary": "Preliminary"}.get(k, "As reported")
    if text and "prelim" in str(text).lower():
        lbl = "Preliminary"
    return f'<span class="fb fb-{lbl.lower().replace(" ", "")}">{lbl}</span>'


# ------------------------------------------------------------------ hero + latest
def hero(posts, c):
    e, url = c["e"], c["url"]
    lead = next((p for p in posts[:12] if p.get("lead")), posts[0])
    rest = [p for p in posts if p is not lead and not p.get("report")]
    side = [p for p in rest if p["category"] != lead["category"]][:2] or rest[:2]
    cat = c["cats"][lead["category"]][0]
    big = (f'<article class="hcard" style="--dot:var(--c-{lead["category"]})"><a href="{url(lead)}">'
           f'<img src="{c["cover_url"](lead)}" width="1600" height="900" alt="{e(lead.get("coverAlt") or "")}" fetchpriority="high" decoding="async">'
           f'<div class="hbody"><span class="kick">{e(cat)}</span><h2>{e(lead["title"])}</h2>'
           f'<p>{e(lead.get("dek") or "")}</p><div class="hmeta"><time datetime="{e(lead["_dt"].isoformat())}">{e(c["ago"](lead))}</time>'
           f'<span class="btn sm">Read full story {icon("arrow", "ia")}</span></div></div></a></article>')
    sec = "".join(
        f'<article class="scard"><a href="{url(p)}"><img src="{c["cover_url"](p)}" width="1600" height="900" alt="" loading="lazy" decoding="async">'
        f'<div><span class="kick" style="--dot:var(--c-{p["category"]})">{e(c["cats"][p["category"]][0])}</span><h3>{e(p["title"])}</h3>'
        f'<small><time datetime="{e(p["_dt"].isoformat())}">{e(c["ago"](p))}</time></small></div></a></article>' for p in side)
    used = {lead["id"]} | {p["id"] for p in side}
    tl = "".join(
        f'<li style="--dot:var(--c-{p["category"]})"><a href="{url(p)}"><time datetime="{e(p["_dt"].isoformat())}" title="{e(c["ago"](p))}">{e(short_ago(p, c["ist"]))}</time>'
        f'<span class="tlc">{e(c["cats"][p["category"]][0])}</span><b>{e(p["title"])}</b></a></li>'
        for p in [x for x in posts if x["id"] not in used][:7])
    latest = (f'<aside class="panel tline" aria-label="Latest news">{shead(c, "Latest news", "news", c["base"] + "live/", h="h2")}'
              f'<ol>{tl}</ol><a class="btn ghost full" href="{c["base"]}live/">View all news {icon("arrow", "ia")}</a></aside>')
    return f'<section class="g12 herorow"><div class="c6 hr-main">{big}</div><div class="c3 sstack">{sec}</div><div class="c3 hr-latest">{latest}</div></section>'


# ------------------------------------------------------------------ dashboard
def big_chart(points, w=640, h=230, label="Closing levels"):
    vals = [float(x["v"]) for x in points]
    if len(vals) < 2:
        return '<p class="empty-note">The chart appears once at least two daily closes are recorded.</p>'
    lo, hi = min(vals), max(vals); pad = (hi - lo) * .15 or 1; lo -= pad; hi += pad
    L, R, T, B = 56, 28, 12, 30
    X = lambda i: L + i * (w - L - R) / (len(vals) - 1)
    Y = lambda v: T + (hi - v) / (hi - lo) * (h - T - B)
    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
    up = vals[-1] >= vals[0]
    grid = "".join(f'<line x1="{L}" x2="{w-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/><text x="{L-8}" y="{Y(v)+4:.1f}" text-anchor="end">{v:,.0f}</text>'
                   for v in [lo + pad + (hi - lo - 2 * pad) * k / 3 for k in range(4)])
    step = max(1, len(points) // 7)
    xl = "".join(f'<text x="{X(i):.1f}" y="{h-8}" text-anchor="middle">{datetime.fromisoformat(x["d"]).strftime("%d %b")}</text>'
                 for i, x in enumerate(points) if i % step == 0 or i == len(points) - 1)
    dots = "".join(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3"><title>{datetime.fromisoformat(points[i]["d"]).strftime("%d %b %Y")}: {v:,.2f}</title></circle>'
                   for i, v in enumerate(vals))
    area = f"{L},{h-B} {pts} {X(len(vals)-1):.1f},{h-B}"
    return (f'<svg class="bchart {"up" if up else "down"}" viewBox="0 0 {w} {h}" role="img" aria-label="{label}: {len(vals)} sessions, latest {vals[-1]:,.2f}">'
            f'<defs><linearGradient id="bcg" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="currentColor" stop-opacity=".22"/><stop offset="1" stop-color="currentColor" stop-opacity="0"/></linearGradient></defs>'
            f'<g class="g">{grid}</g><polygon points="{area}" fill="url(#bcg)"/><polyline class="l" points="{pts}"/><g class="dots">{dots}</g><g class="x">{xl}</g></svg>')


def movers_table(items, e, cls):
    if not items:
        return '<p class="empty-note">Not available for the latest session.</p>'
    rows = "".join(f'<tr><th scope="row">{e(x.get("name"))}</th><td class="num">{e(x.get("price") or "—")}</td>'
                   f'<td class="num {cls}">{"" if str(x.get("pct", "")).startswith(("-", "+")) else "+"}{e(x.get("pct"))}%</td></tr>' for x in items[:5])
    return f'<table class="mt"><tbody>{rows}</tbody></table>'


def donut(b, e):
    try:
        a, d, u = float(b["advances"]), float(b["declines"]), float(b.get("unchanged") or 0)
    except Exception:
        return '<p class="empty-note">Breadth figures are not available for the latest session.</p>'
    tot = a + d + u; R = 54; C = 2 * 3.14159 * R
    seg = lambda v: v / tot * C
    off_d = -seg(a); off_u = -(seg(a) + seg(d))
    return (f'<div class="donut"><svg viewBox="0 0 140 140" role="img" aria-label="{int(a)} advances, {int(d)} declines, {int(u)} unchanged">'
            f'<circle r="{R}" cx="70" cy="70" class="trk"/>'
            f'<circle r="{R}" cx="70" cy="70" class="s up" stroke-dasharray="{seg(a):.1f} {C:.1f}"/>'
            f'<circle r="{R}" cx="70" cy="70" class="s down" stroke-dasharray="{seg(d):.1f} {C:.1f}" stroke-dashoffset="{off_d:.1f}"/>'
            f'<circle r="{R}" cx="70" cy="70" class="s fl" stroke-dasharray="{seg(u):.1f} {C:.1f}" stroke-dashoffset="{off_u:.1f}"/>'
            f'<text x="70" y="68" text-anchor="middle" class="t1">{int(tot):,}</text><text x="70" y="86" text-anchor="middle" class="t2">stocks</text></svg>'
            f'<ul><li><i class="up"></i>Advances <b>{int(a):,}</b> <small>{a/tot*100:.0f}%</small></li>'
            f'<li><i class="down"></i>Declines <b>{int(d):,}</b> <small>{d/tot*100:.0f}%</small></li>'
            f'<li><i class="fl"></i>Unchanged <b>{int(u):,}</b> <small>{u/tot*100:.0f}%</small></li></ul></div>')


def dashboard(posts, meta, c):
    e, url, base = c["e"], c["url"], c["base"]
    hist = meta.get("history") or {}
    names = [n for n in ("Nifty 50", "Sensex", "Bank Nifty") if len(hist.get(n) or []) >= 1]
    rep = next((p for p in posts if p.get("report")), None)
    r = (rep or {}).get("report") or {}
    tabs, panels = [], []
    for i, n in enumerate(names):
        pts = hist[n]; last = float(pts[-1]["v"]); prev = float(pts[-2]["v"]) if len(pts) > 1 else None
        chg = f'<span class="{"up" if last >= prev else "down"}">{"▲" if last >= prev else "▼"} {last - prev:+,.2f} ({(last - prev) / prev * 100:+.2f}%)</span>' if prev else ""
        srcs = sorted({x.get("s") for x in pts if x.get("s")})
        when = datetime.fromisoformat(pts[-1]["d"]).strftime("%d %b %Y")
        tabs.append(f'<button type="button" class="seg{" on" if i == 0 else ""}" data-panel="dash{i}" aria-pressed="{"true" if i == 0 else "false"}">{e(n)}</button>')
        panels.append(f'<div class="wp" id="dash{i}"{"" if i == 0 else " hidden"}><div class="dhead"><div><span class="dname">{e(n)}</span>'
                      f'<b class="dval">{last:,.2f}</b>{chg}</div><p class="asof">{fresh_badge("close")} Close on {e(when)} · last {len(pts)} sessions'
                      f'{" · source: " + e(", ".join(srcs)) if srcs else ""}</p></div>'
                      f'<div class="lwc" data-series="{e(json.dumps([[x["d"], float(x["v"])] for x in pts]))}" data-name="{e(n)}">{big_chart(pts, label=n + " closing levels")}</div></div>')
    if not panels:
        panels.append('<p class="empty-note">Index history is not available yet.</p>')
    dl = r.get("dateLabel") or ""
    gain = (f'<div class="panel sub"><h3><span class="dot up"></span>Top gainers <small>{e(r.get("moversIndex") or "Nifty 50")}</small></h3>{movers_table(r.get("gainers"), e, "up")}</div>'
            f'<div class="panel sub"><h3><span class="dot down"></span>Top losers <small>{e(r.get("moversIndex") or "Nifty 50")}</small></h3>{movers_table(r.get("losers"), e, "down")}</div>')
    b = r.get("breadth") or {}
    br = (f'<div class="panel sub"><h3>Market breadth <small>{e(b.get("exchange") or "NSE")}</small></h3>{donut(b, e)}'
          f'<p class="asof">{fresh_badge("close")} {e(dl)}{" · " + e(", ".join(s.get("name", "") for s in (rep.get("sources") or [])[:1])) if rep else ""}</p></div>')
    foot = (f'<p class="dfoot">Movers and breadth are end-of-day figures from our <a href="{url(rep)}">daily report for {e(dl)}</a>. '
            f'TotalMarket has no real-time feed; check <a href="https://www.nseindia.com/market-data/live-market-indices" rel="nofollow noopener" target="_blank">NSE</a> for live prices.</p>') if rep else ""
    seg = f'<div class="segs" role="group" aria-label="Choose index">{"".join(tabs)}</div>' if tabs else ""
    return (f'<section class="panel dash" aria-label="Market dashboard">{shead(c, "Market dashboard", "chart", base + "nifty-50/", "Nifty 50 page", extra=seg)}'
            f'<div class="g12"><div class="c7 dchart">{"".join(panels)}</div><div class="c5 dside">{gain}{br}</div></div>{foot}</section>')


# ------------------------------------------------------------------ IPO watch + Boss Piggy
def ipo_watch(ipos, c):
    e, base = c["e"], c["base"]
    order = {"listing": 0, "open": 1, "upcoming": 2, "closed": 3}
    live = sorted([x for x in ipos if x.get("_status") in order], key=lambda x: (order[x["_status"]], x.get("open") or ""))[:3]
    label = {"open": "Open now", "upcoming": "Upcoming", "closed": "Closed · listing soon", "listing": "Listing today"}
    def dr(x):
        try:
            o, cl = date.fromisoformat(x["open"]), date.fromisoformat(x["close"])
            return f'{o.day}–{cl.strftime("%d %b %Y")}' if o.month == cl.month else f'{o.strftime("%d %b")} – {cl.strftime("%d %b %Y")}'
        except Exception:
            return "Dates to be announced"
    cards = "".join(
        f'<article class="ipoc"><a href="{base}ipo/{e(x["slug"])}/"><div class="ipot"><span class="ipoav" aria-hidden="true">{e(x["name"][:1])}</span>'
        f'<div><h3>{e(x["name"])} IPO</h3><span class="ipst st-{x["_status"]}">{label[x["_status"]]}</span></div></div>'
        f'<dl><div><dt>Price band</dt><dd>{e(x.get("priceBand") or "—")}</dd></div><div><dt>Issue size</dt><dd>{e(x.get("issueSize") or "—")}</dd></div>'
        f'<div><dt>Dates</dt><dd>{e(dr(x))}</dd></div></dl></a></article>' for x in live)
    subs = [x for x in ipos if x.get("_status") in ("open", "closed", "listing") and (x.get("subscription") or {}).get("total") is not None][:4]
    mx = max([float(x["subscription"]["total"]) for x in subs] + [1])
    srows = "".join(
        f'<li><a href="{base}ipo/{e(x["slug"])}/"><span>{e(x["name"])}</span><b>{float(x["subscription"]["total"]):.2f}x</b></a>'
        f'<i style="--w:{min(100, float(x["subscription"]["total"]) / mx * 100):.0f}%"></i><small>{e(x["subscription"].get("asOf", ""))} · {e((x["subscription"].get("source") or {}).get("name", ""))}</small></li>'
        for x in subs)
    sub = (f'<div class="panel sub substat"><h3>Subscription status</h3><ul>{srows}</ul>'
           f'<a class="btn ghost full" href="{base}ipo/">View all IPOs {icon("arrow", "ia")}</a></div>') if srows else ""
    if not cards and not sub:
        return ""
    return (f'<section class="panel ipow2" aria-label="IPO watch">{shead(c, "IPO watch", "ipo", base + "ipo/")}'
            f'<div class="ipogrid">{cards}{sub}</div></section>')


def piggy_panel(c):
    base = c["base"]
    return (f'<aside class="pgp" aria-label="Learn with Boss Piggy"><div><span class="pgk">Learn with</span><h2>Boss Piggy</h2>'
            f'<p class="pgq">“Same market. Smarter you.”</p><ul><li>Simple explanations of every big move</li><li>What to watch next, in plain words</li><li>Never tips, never targets</li></ul>'
            f'<a class="btn" href="{base}learn/">Start learning {icon("arrow", "ia")}</a></div>'
            f'<img src="{base}assets/piggy/boss-piggy-360.webp" width="216" height="360" alt="Boss Piggy, TotalMarket\'s market guide" loading="lazy" decoding="async"></aside>')


# ------------------------------------------------------------------ category columns, rates
def cat_col(posts, key, ic, c):
    e, url = c["e"], c["url"]
    items = [p for p in posts if p["category"] == key][:3]
    if not items:
        return ""
    top, rest = items[0], items[1:]
    minis = "".join(f'<a class="mrow" href="{url(p)}"><img src="{c["cover_url"](p)}" width="1600" height="900" alt="" loading="lazy" decoding="async">'
                    f'<span><b>{e(p["title"])}</b><small>{e(c["ago"](p))}</small></span></a>' for p in rest)
    return (f'<section class="panel ccol" style="--dot:var(--c-{key})">{shead(c, c["cats"][key][0], ic, c["base"] + key + "/")}'
            f'<a class="cfeat" href="{url(top)}"><img src="{c["cover_url"](top)}" width="1600" height="900" alt="" loading="lazy" decoding="async">'
            f'<h3>{e(top["title"])}</h3><p>{e(top.get("dek") or "")}</p><small>{e(c["ago"](top))}</small></a>{minis}</section>')


def rates_card(meta, c):
    e, base = c["e"], c["base"]
    import tools
    try:
        r = json.load(open(os.path.join(ROOT, "data", "rates.json"), encoding="utf-8"))
    except Exception:
        return ""
    inr = tools.inr
    rows = []
    m = r.get("mcx") or {}
    if m.get("gold"):
        rows.append(("Gold (MCX, 10 g)", inr(m["gold"]), m.get("goldChangePct"), "gold", m.get("asOf")))
    if m.get("silver"):
        rows.append(("Silver (MCX, 1 kg)", inr(m["silver"]), m.get("silverChangePct"), "silver", m.get("asOf")))
    rr = r.get("retailRange") or {}
    if rr.get("gold24"):
        rows.append(("Gold 24K, 10 g (shops)", inr(rr["gold24"][0]), None, "gold", (r.get("citySource") or {}).get("asOf")))
    sr = r.get("silverRetail") or {}
    if sr.get("range"):
        try:
            sd = date.fromisoformat(sr.get("date")).strftime("%d %b %Y")
        except Exception:
            sd = sr.get("date")
        rows.append(("Silver, 1 kg (shops)", inr(sr["range"][0]), None, "silver", sd))
    fx = next((x for x in meta.get("ticker") or [] if x.get("label") in ("USD/INR", "Rupee")), None)
    if fx and fx.get("value"):
        rows.append(("USD/INR", e(fx["value"]), fx.get("change"), "fx", fx.get("asOfText")))
    if not rows:
        return ""
    def chg(v):
        if v is None or v == "":
            return ""
        s = str(v) if isinstance(v, str) else f"{v:+.2f}%"
        return f'<span class="pchip {"down" if s.lstrip("~").startswith(("-", "−")) else "up"}">{e(s)}</span>'
    lis = "".join(f'<li><span class="mi {k}" aria-hidden="true"></span><div><small>{e(l)}</small><b>{v}</b><i>{e(a or "")}</i></div>{chg(ch)}</li>' for l, v, ch, k, a in rows)
    return (f'<section class="panel rates" aria-label="Gold and silver rates">{shead(c, "Gold & silver rates", "coin", base + "gold-rate-today/", "All rates")}'
            f'<ul>{lis}</ul><p class="asof">{fresh_badge("delayed")} Shop rates exclude GST and making charges. MCX = futures.</p>'
            f'<a class="btn ghost full" href="{base}gold-rate-today/">City-wise gold rates {icon("arrow", "ia")}</a></section>')


# ------------------------------------------------------------------ earnings, report, education, tools
def earnings(results, c):
    e, base = c["e"], c["base"]
    today = datetime.now(c["ist"]).date()
    wk_end = today + timedelta(days=6 - today.weekday())
    nx_end = wk_end + timedelta(days=7)
    def d(x):
        v = x.get("date")
        if isinstance(v, date): return v
        try: return date.fromisoformat(str(v))
        except Exception: return None
    groups = [("Today", [x for x in results if d(x) == today]), ("This week", [x for x in results if d(x) and today < d(x) <= wk_end]),
              ("Next week", [x for x in results if d(x) and wk_end < d(x) <= nx_end])]
    tabs = "".join(f'<button type="button" class="seg{" on" if i == 0 else ""}" data-panel="earn{i}">{n} <small>{len(g)}</small></button>' for i, (n, g) in enumerate(groups))
    def li(x):
        when = "Today" if d(x) == today else d(x).strftime("%a %d %b")
        return f'<li><span class="eav" aria-hidden="true">{e(x["company"][:1])}</span><span class="en">{e(x["company"])}<small>{e(x.get("note") or "Results")}</small></span><time>{when}</time></li>'
    panels = "".join(f'<div class="wp" id="earn{i}"{"" if i == 0 else " hidden"}>' + (f'<ul class="elist">{"".join(li(x) for x in g[:7])}</ul>' if g else '<p class="empty-note">No results scheduled in our calendar for this period.</p>') + "</div>"
                     for i, (n, g) in enumerate(groups))
    return (f'<section class="panel earn" aria-label="Earnings calendar">{shead(c, "Earnings calendar", "cal", base + "results/")}'
            f'<div class="segs sm">{tabs}</div>{panels}</section>')


def report_card(posts, c):
    e, url = c["e"], c["url"]
    rep = next((p for p in posts if p.get("report")), None)
    if not rep:
        return ""
    r = rep["report"]
    k = (r.get("kpis") or [])[:3]
    kp = "".join(f'<div><small>{e(x.get("label"))}</small><b>{e(x.get("value"))}</b><span class="{"down" if x.get("dir") == "down" else "up"}">{e(x.get("change"))}</span></div>' for x in k)
    return (f'<section class="panel rcard" aria-label="Daily market report">{shead(c, "Daily market report", "report", c["base"] + "market-report/", "Archive", extra=f"<span class=rdate>{e(r.get("dateLabel") or "")}</span>")}'
            f'<a class="rbox" href="{url(rep)}"><span class="rk">{e(r.get("mood") or "Market")} day</span><h3>{e(rep["title"])}</h3><div class="rk3">{kp}</div>'
            f'<span class="btn light sm">Read the full report {icon("arrow", "ia")}</span></a></section>')


def education(c):
    base = c["base"]
    items = [("Stock market basics", "A beginner's guide to investing in India", f"{base}learn/", "learn"),
             ("How IPOs work", "From price band to listing, explained simply", f"{base}ipo/", "ipo"),
             ("Read a market report", "Breadth, sectors and FII/DII in plain words", f"{base}market-report/", "report")]
    cards = "".join(f'<a class="edc" href="{h}"><span class="sic big">{icon(i)}</span><b>{t}</b><small>{d}</small></a>' for t, d, h, i in items)
    return f'<section class="panel educ" aria-label="Market education">{shead(c, "Market education", "learn", base + "learn/")}<div class="edgrid">{cards}</div></section>'


def tools_grid(c):
    base = c["base"]
    items = [("SIP calculator", f"{base}calculators/sip/"), ("EMI calculator", f"{base}calculators/emi/"), ("Gold rate today", f"{base}gold-rate-today/"),
             ("Silver rate today", f"{base}silver-rate-today/"), ("FII / DII data", f"{base}fii-dii-data/"), ("Market holidays", f"{base}{c['holidays']}"),
             ("Corporate actions", f"{base}corporate-events/"), ("Companies A–Z", f"{base}stock/")]
    cards = "".join(f'<a class="tlink" href="{h}"><span class="sic">{icon("calc")}</span>{t}</a>' for t, h in items)
    return f'<section class="panel tools" aria-label="Tools and calculators">{shead(c, "Tools & calculators", "calc", base + "calculators/")}<div class="tlgrid">{cards}</div></section>'


# ------------------------------------------------------------------ page
def body(posts, meta, results, ipos, c):
    if not posts:
        return '<div class="empty"><p>The first update is on its way.</p></div>'
    cols = "".join(cat_col(posts, k, i, c) for k, i in (("tech", "tech"), ("global", "globe"), ("commodities", "coin")))
    return (f'<h1 class="sr">{c["e"](c["site_name"])}: {c["e"](c["tagline"])}</h1>'
            + hero(posts, c)
            + dashboard(posts, meta, c)
            + f'<div class="g12"><div class="c9">{ipo_watch(ipos, c)}</div><div class="c3">{piggy_panel(c)}</div></div>'
            + f'<div class="g12 cols4"><div class="c9 cols3">{cols}</div><div class="c3">{rates_card(meta, c)}</div></div>'
            + f'<div class="g12"><div class="c4">{earnings(results, c)}</div><div class="c4">{report_card(posts, c)}</div><div class="c4">{education(c)}{tools_grid(c)}</div></div>'
            + c["latest_list"](posts[:16]).replace("</ul></section>", f'</ul><a class="btn ghost full" href="{c["base"]}live/">See every update {icon("arrow", "ia")}</a></section>'))
