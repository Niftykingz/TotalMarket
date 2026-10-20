"""Render the structured Daily Market Report (story field "report") as rich HTML."""
import html

e = lambda s: html.escape(str(s if s is not None else ""), quote=True)


def num(v):
    try:
        return float(str(v).replace(",", "").replace("%", "").replace("₹", "").replace("+", "").strip())
    except Exception:
        return None


def fmt_pct(v):
    n = num(v)
    if n is None:
        return e(v) if v not in (None, "") else "—"
    return f"{'+' if n > 0 else ''}{n:.2f}%"


def cls(v):
    n = num(v)
    return "" if n is None or n == 0 else ("up" if n > 0 else "down")


def section(title, body, sub=""):
    s = f'<p class="rp-sub">{e(sub)}</p>' if sub else ""
    return f'<section class="rp-sec"><h2 class="rp-h">{e(title)}</h2>{s}{body}</section>'


def mood_banner(r):
    mood = r.get("mood") or ""
    m = mood.lower()
    c = "down" if "bear" in m or "weak" in m else "up" if "bull" in m or "strong" in m else "flat"
    arrow = {"down": "▼", "up": "▲", "flat": "◆"}[c]
    return (f'<div class="rp-mood {c}"><span class="rp-moodtag">{arrow} Market mood: {e(mood or "Mixed")}</span>'
            f'<span class="rp-date">{e(r.get("dateLabel") or r.get("date") or "")}</span></div>')


def kpis(r):
    items = r.get("kpis") or []
    if not items:
        return ""
    cards = "".join(
        f'<div class="rp-kpi {k.get("dir") or cls(k.get("change"))}"><span class="l">{e(k.get("label"))}</span>'
        f'<span class="v">{e(k.get("value"))}</span><span class="c">{e(k.get("change") or "")}</span></div>' for k in items)
    return f'<div class="rp-kpis">{cards}</div>'


def range_bar(o, h, l, c):
    H, L, C, O = num(h), num(l), num(c), num(o)
    if H is None or L is None or C is None or H <= L:
        return '<span class="rp-na">Range not available</span>'
    pos = max(0, min(100, (C - L) / (H - L) * 100))
    op = "" if O is None else f'<i class="o" style="left:{max(0, min(100, (O - L) / (H - L) * 100)):.1f}%" title="Open"></i>'
    return (f'<div class="rp-range"><span class="lo">{e(l)}</span><div class="bar">{op}'
            f'<b style="left:{pos:.1f}%" title="Close"></b></div><span class="hi">{e(h)}</span></div>')


def indices(r):
    rows = r.get("indices") or []
    if not rows:
        return ""
    trs = "".join(
        f'<tr><th scope="row">{e(x.get("name"))}</th><td class="num">{e(x.get("close"))}</td>'
        f'<td class="num {cls(x.get("pct"))}">{e(x.get("change") or "")}<br><small>{fmt_pct(x.get("pct"))}</small></td>'
        f'<td class="rng">{range_bar(x.get("open"), x.get("high"), x.get("low"), x.get("close"))}</td></tr>' for x in rows)
    return section("Index scoreboard", f'<div class="tablewrap"><table class="dt rp-idx"><thead><tr><th>Index</th><th>Close</th><th>Change</th>'
                   f'<th>Day low → day high (● close, | open)</th></tr></thead><tbody>{trs}</tbody></table></div>')


def bars(items, title, sub=""):
    vals = [num(x.get("pct")) for x in items]
    vals = [v for v in vals if v is not None]
    if not vals:
        return ""
    mx = max(abs(v) for v in vals) or 1
    rows = []
    for x in items:
        v = num(x.get("pct"))
        if v is None:
            continue
        w = abs(v) / mx * 50
        side = f'left:50%;width:{w:.1f}%' if v >= 0 else f'right:50%;width:{w:.1f}%'
        rows.append(f'<div class="rp-bar"><span class="n">{e(x.get("name"))}</span><div class="t"><i class="{cls(v)}" style="{side}"></i><em></em></div>'
                    f'<span class="p {cls(v)}">{fmt_pct(v)}</span></div>')
    return section(title, f'<div class="rp-bars">{"".join(rows)}</div>', sub)


def caps_summary(caps):
    vals = [(x.get("name"), num(x.get("pct"))) for x in caps if num(x.get("pct")) is not None]
    if len(vals) < 2:
        return ""
    best = max(vals, key=lambda t: t[1]); worst = min(vals, key=lambda t: t[1])
    return f"{best[0]} did best ({fmt_pct(best[1])}) and {worst[0]} did worst ({fmt_pct(worst[1])})."


def heatmap(r):
    secs = [s for s in (r.get("sectors") or []) if num(s.get("pct")) is not None]
    if not secs:
        return ""
    secs.sort(key=lambda s: num(s["pct"]), reverse=True)
    mx = max(abs(num(s["pct"])) for s in secs) or 1
    tiles = []
    for s in secs:
        v = num(s["pct"]); a = .18 + .72 * abs(v) / mx
        tiles.append(f'<div class="rp-tile {cls(v)}" style="--a:{a:.2f}"><span>{e(s.get("name"))}</span><b>{fmt_pct(v)}</b></div>')
    best, worst = secs[0], secs[-1]
    sub = f'Best: {best.get("name")} ({fmt_pct(best["pct"])}). Worst: {worst.get("name")} ({fmt_pct(worst["pct"])}).'
    return section("Sector heatmap", f'<div class="rp-heat">{"".join(tiles)}</div>', sub)


def movers_list(items, up):
    if not items:
        return ""
    mx = max((abs(num(x.get("pct")) or 0) for x in items), default=1) or 1
    li = "".join(
        f'<li><span class="n">{e(x.get("name"))}</span><span class="pr">{e(x.get("price") or "")}</span>'
        f'<span class="p {"up" if up else "down"}">{fmt_pct(x.get("pct"))}</span>'
        f'<i class="{"up" if up else "down"}" style="width:{abs(num(x.get("pct")) or 0) / mx * 100:.0f}%"></i></li>' for x in items)
    return f'<ol class="rp-movers">{li}</ol>'


def gainers_losers(r):
    g, l = r.get("gainers") or [], r.get("losers") or []
    if not g and not l:
        return ""
    t = r.get("moversIndex") or "Nifty 50"
    body = (f'<div class="rp-gl"><div><h3 class="up">Top gainers ▲</h3>{movers_list(g, True)}</div>'
            f'<div><h3 class="down">Top losers ▼</h3>{movers_list(l, False)}</div></div>')
    extra = ""
    m = r.get("movers")
    if m and (m.get("up") or m.get("down")):
        extra = (f'<h3 class="rp-h3">{e(m.get("title") or "Biggest movers in the broader market")}</h3><div class="rp-gl">'
                 f'<div>{movers_list(m.get("up") or [], True)}</div><div>{movers_list(m.get("down") or [], False)}</div></div>')
    return section(f"Top gainers and losers ({t})", body + extra)


def breadth(r):
    b = r.get("breadth")
    if not b:
        return ""
    a, d, u = (num(b.get(k)) or 0 for k in ("advances", "declines", "unchanged"))
    tot = a + d + u
    bar = ""
    if tot:
        bar = (f'<div class="rp-breadth"><i class="up" style="width:{a / tot * 100:.1f}%"></i><i class="flat" style="width:{u / tot * 100:.1f}%"></i>'
               f'<i class="down" style="width:{d / tot * 100:.1f}%"></i></div>'
               f'<div class="rp-blegend"><span class="up">▲ {int(a):,} advanced</span><span>◆ {int(u):,} unchanged</span><span class="down">▼ {int(d):,} declined</span></div>')
    stats = [("52-week highs", b.get("highs52")), ("52-week lows", b.get("lows52")), ("Upper circuit", b.get("upperCircuit")),
             ("Lower circuit", b.get("lowerCircuit")), ("Investor wealth", b.get("wealth"))]
    chips = "".join(f'<div class="rp-stat"><span>{e(k)}</span><b>{e(v)}</b></div>' for k, v in stats if v not in (None, ""))
    sub = f"{b.get('exchange') or 'NSE'}: advance-decline ratio {a / d:.2f}" if d else ""
    return section("Market breadth", bar + f'<div class="rp-stats">{chips}</div>', sub)


def flow_card(name, x):
    if not x:
        return ""
    n = num(x.get("net"))
    return (f'<div class="rp-flow {cls(n)}"><span class="who">{e(name)}</span><b class="net">{"+" if n and n > 0 else ""}{e(x.get("net"))} cr</b>'
            f'<span class="tag">{"Net buyers" if n and n > 0 else "Net sellers" if n else ""}</span>'
            f'<div class="bs"><span>Bought ₹{e(x.get("buy") or "—")} cr</span><span>Sold ₹{e(x.get("sell") or "—")} cr</span></div></div>')


def fii_dii(r):
    f = r.get("fiiDii")
    if not f:
        return ""
    mtd = f.get("mtd") or {}
    mt = ""
    if mtd:
        mt = (f'<div class="rp-stats"><div class="rp-stat {cls(mtd.get("fii"))}"><span>FII month to date</span><b>₹{e(mtd.get("fii"))} cr</b></div>'
              f'<div class="rp-stat {cls(mtd.get("dii"))}"><span>DII month to date</span><b>₹{e(mtd.get("dii"))} cr</b></div></div>')
    note = f'<p class="rp-note">{e(f.get("note"))}</p>' if f.get("note") else ""
    return section(f"FII / DII activity (cash, {f.get('asOf') or 'provisional'})",
                   f'<div class="rp-flows">{flow_card("FIIs / FPIs", f.get("fii"))}{flow_card("DIIs", f.get("dii"))}</div>{mt}{note}')


def ipos(r):
    rows = r.get("ipos") or []
    if not rows and not r.get("ipoUpcoming"):
        return ""
    trs = [] if rows else ['<tr class="ipo-note"><td colspan="4">No mainboard IPO listed this session.</td></tr>']
    for x in rows:
        trs.append(f'<tr><th scope="row">{e(x.get("name"))}<span class="sub">{e(x.get("exchange") or "")}{" · " if x.get("exchange") and x.get("segment") else ""}{e(x.get("segment") or "")}</span></th>'
                   f'<td class="num">₹{e(x.get("issuePrice"))}</td><td class="num">₹{e(x.get("listingPrice"))}<br><small class="{cls(x.get("listingGainPct"))}">{fmt_pct(x.get("listingGainPct"))}</small></td>'
                   f'<td class="num">{("₹" + e(x.get("close"))) if x.get("close") else "—"}<br><small class="{cls(x.get("closeVsIssuePct"))}">{fmt_pct(x.get("closeVsIssuePct")) if x.get("closeVsIssuePct") not in (None, "") else ""}</small></td></tr>')
        if x.get("note"):
            trs.append(f'<tr class="ipo-note"><td colspan="4">{e(x.get("note"))}</td></tr>')
    upcoming = r.get("ipoUpcoming") or []
    up = ""
    if upcoming:
        up = '<ul class="rp-list watch">' + "".join(f"<li>{e(i)}</li>" for i in upcoming) + "</ul>"
    return section("IPO listings and what happened after", f'<div class="tablewrap"><table class="dt"><thead><tr><th>Company</th><th>Issue price</th><th>Listed at (gain)</th><th>Day-1 close (vs issue)</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div>{up}')


def levels(r):
    lv = r.get("levels") or []
    if not lv:
        return ""
    trs = "".join(f'<tr><th scope="row">{e(x.get("index"))}</th><td class="num down">{e(x.get("support"))}</td><td class="num up">{e(x.get("resistance"))}</td>'
                  f'<td class="note">{e(x.get("source"))}</td></tr>' for x in lv)
    return section("Levels analysts are watching", f'<div class="tablewrap"><table class="dt"><thead><tr><th>Index</th><th>Support</th><th>Resistance</th><th>Cited by</th></tr></thead><tbody>{trs}</tbody></table></div>',
                   "Reported for information only. These are third-party technical levels, not a recommendation.")


def bullets(title, items, cls_):
    if not items:
        return ""
    return section(title, f'<ul class="rp-list {cls_}">{"".join(f"<li>{e(i)}</li>" for i in items)}</ul>')


def render(r):
    if not r:
        return ""
    caps = r.get("caps") or []
    parts = [mood_banner(r), kpis(r),
             bullets("Key takeaways", r.get("takeaways"), "take"),
             indices(r),
             bars(caps, "Large cap vs mid cap vs small cap", caps_summary(caps)) if caps else "",
             heatmap(r), gainers_losers(r), breadth(r), fii_dii(r), ipos(r),
             bars(r.get("global") or [], "Global and commodity cues", "") if r.get("global") else "",
             levels(r), bullets("What to watch next session", r.get("watch"), "watch")]
    return '<div class="report">' + "".join(p for p in parts if p) + "</div>"
