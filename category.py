"""Shared category-page template (Markets, Tech & AI and every other section).

Components: header with topic chips + session filter, featured block (1 main + 2
supporting), a continuous card feed with Load more, and a sidebar of widgets.
Topics come from an optional `topics` list on a story, otherwise from simple
keyword rules on its title, tags, companies and session. Nothing is invented: a
widget without verified data is left out.
"""
import json, re
import tmdate
from datetime import datetime

# topic key -> (label, rule). Order = chip order. Rules receive the story dict.
def _txt(p):
    return " ".join([p.get("title", ""), p.get("dek", ""), " ".join(p.get("tags") or [])]).lower()


def _ed(p):
    return str(p.get("editionLabel") or "").split("·")[-1].strip().lower()


WRAP_EDS = ("closing wrap", "daily market report", "midday check", "market holiday briefing")
PRE_EDS = ("pre-market brief", "overnight global wrap")
RX = lambda pat: re.compile(pat, re.I)
R_INDEX = RX(r"\b(sensex|nifty)\b")
R_EARN = RX(r"\b(results?|q[1-4]|profit|revenue|earnings)\b")
R_ECON = RX(r"\b(rbi|gdp|inflation|rupee|repo|fiscal|budget|gst|economy|cpi|iip|fed)\b")


def _is_wrap(p):
    return bool(R_INDEX.search(p.get("title", ""))) and (_ed(p) in WRAP_EDS or bool(p.get("report")))


def _is_pre(p):
    return _ed(p) in PRE_EDS or "what to watch" in _txt(p) or "weak start" in _txt(p)


TOPICS = {
    "markets": [
        ("wrap", "Market Wrap", _is_wrap),
        ("premarket", "Pre-Market", lambda p: _is_pre(p) and not _is_wrap(p)),
        ("company", "Company News", lambda p: bool(p.get("companies")) and not _is_wrap(p) and not _is_pre(p)),
        ("earnings", "Earnings", lambda p: bool(R_EARN.search(p.get("title", "") + " " + " ".join(p.get("tags") or [])))),
        ("economy", "Economy", lambda p: bool(R_ECON.search(_txt(p)))),
    ],
    "tech": [
        ("ai", "AI", lambda p: bool(RX(r"\b(ai|openai|anthropic|gemini|deepseek|llm|chatgpt|claude|agents?)\b").search(_txt(p)))),
        ("bigtech", "Big Tech", lambda p: bool(RX(r"\b(meta|google|alphabet|microsoft|apple|amazon|tesla|nvidia|youtube|netflix)\b").search(_txt(p)))),
        ("cyber", "Cybersecurity", lambda p: bool(RX(r"\b(hack(er|ed|ing)?|breach|cyber|security|malware|ransomware|privacy|home address)\b").search(_txt(p)))),
        ("chips", "Semiconductors", lambda p: bool(RX(r"\b(chips?|semiconductors?|nvidia|tsmc|samsung|sk hynix|micron|intel|amd|tenstorrent)\b").search(_txt(p)))),
        ("aistartups", "AI Startups", lambda p: bool(RX(r"\b(startups?|funding|raises|seed|series [a-e])\b").search(_txt(p)))),
        ("deals", "Deals", lambda p: bool(RX(r"\b(deal|acquir\w*|merger|stake|invest\w*|data cent(er|re)|fund)\b").search(_txt(p)))),
        ("regulation", "Regulation", lambda p: bool(RX(r"\b(regulat\w*|bans?|law|court|fine|government|dhs|eu|antitrust|labels)\b").search(_txt(p)))),
    ],
    "startups": [
        ("funding", "Funding", lambda p: bool(RX(r"\b(raises?|funding|valuation|hits \$|investors?)\b").search(_txt(p)))),
        ("ipo", "IPOs", lambda p: bool(RX(r"\bipos?\b").search(_txt(p)))),
        ("listing", "Listings", lambda p: bool(RX(r"\b(lists?|listing|debut)\b").search(p.get("title", "")))),
        ("subscription", "Subscription status", lambda p: bool(RX(r"\bsubscri\w*|\d+(\.\d+)?x\b").search(p.get("title", "")))),
        ("deals", "Acquisitions", lambda p: bool(RX(r"\b(acquir\w*|merger|buyout)\b").search(_txt(p)))),
    ],
    "policy": [
        ("rbi", "RBI", lambda p: bool(RX(r"\b(rbi|repo|reserve bank)\b").search(_txt(p)))),
        ("inflation", "Inflation", lambda p: bool(RX(r"\b(inflation|cpi|wpi)\b").search(_txt(p)))),
        ("gdp", "GDP", lambda p: bool(RX(r"\bgdp\b").search(_txt(p)))),
        ("budget", "Union Budget", lambda p: bool(RX(r"\bbudget\b").search(_txt(p)))),
        ("tax", "Taxation", lambda p: bool(RX(r"\b(tax|gst|income tax|tds)\b").search(_txt(p)))),
        ("govt", "Government & regulators", lambda p: bool(RX(r"\b(sebi|government|ministry|cabinet|policy|rules?)\b").search(_txt(p)))),
    ],
    "global": [
        ("us", "US Markets", lambda p: bool(RX(r"\b(dow|nasdaq|s&p|wall street|us )").search(_txt(p) + " "))),
        ("asia", "Asian Markets", lambda p: bool(RX(r"\b(kospi|nikkei|hang seng|asia\w*|china|japan)\b").search(_txt(p)))),
        ("europe", "European Markets", lambda p: bool(RX(r"\b(europe\w*|ftse|dax|stoxx|cac)\b").search(_txt(p)))),
        ("cb", "Central Banks", lambda p: bool(RX(r"\b(fed|ecb|boj|central bank|rate (hike|cut|rise)|yields?)\b").search(_txt(p)))),
        ("econ", "Global Economy", lambda p: bool(RX(r"\b(inflation|gdp|jobs|economy|recession|oil)\b").search(_txt(p)))),
    ],
    "commodities": [
        ("gold", "Gold", lambda p: bool(RX(r"\bgold\b").search(_txt(p)))),
        ("silver", "Silver", lambda p: bool(RX(r"\bsilver\b").search(_txt(p)))),
        ("crude", "Crude Oil", lambda p: bool(RX(r"\b(crude|oil|brent|wti)\b").search(_txt(p)))),
        ("gas", "Natural Gas", lambda p: bool(RX(r"\bnatural gas\b").search(_txt(p)))),
        ("metals", "Base Metals", lambda p: bool(RX(r"\b(copper|aluminium|aluminum|zinc|nickel|base metals?)\b").search(_txt(p)))),
        ("forex", "Forex", lambda p: bool(RX(r"\b(rupee|dollar|forex|usd/inr|currency)\b").search(_txt(p)))),
    ],
}


def topics_for(p, key):
    rules = TOPICS.get(key) or []
    explicit = [t for t in (p.get("topics") or []) if any(t == k for k, _, _ in rules)]
    if explicit:
        return explicit
    return [k for k, _, f in rules if f(p)]


def session(p):
    lab = str(p.get("editionLabel") or "")
    return lab.split("·")[-1].strip() if "·" in lab else lab


# ------------------------------------------------------------------ components
def chips(key, items, c):
    e = c["e"]
    rules = TOPICS.get(key) or []
    counts = {k: sum(1 for p in items if k in p["_topics"]) for k, _, _ in rules}
    btn = lambda k, lab, n, on=False: (f'<button type="button" class="chipf{" on" if on else ""}" data-topic="{k}" aria-pressed="{"true" if on else "false"}"'
                                      f'{" data-zero=\"1\"" if n == 0 else ""}>{e(lab)} <small>{n}</small></button>')
    out = btn("all", "All", len(items), True) + "".join(btn(k, lab, counts[k]) for k, lab, _ in rules)
    sessions = []
    for p in items:
        s = session(p)
        if s and s not in sessions:
            sessions.append(s)
    sel = ""
    if len(sessions) > 1:
        opts = "".join(f'<option value="{e(s)}">{e(s)}</option>' for s in sorted(sessions))
        sel = (f'<label class="sessf" for="sessf-{key}">Session <select id="sessf-{key}" data-session-filter>'
               f'<option value="">All sessions</option>{opts}</select></label>')
    return f'<div class="cfilters" role="toolbar" aria-label="Filter stories"><div class="chips" data-topic-chips>{out}</div>{sel}</div>'


def meta_line(p, c, topic_labels):
    e = c["e"]
    bits = [f'<time datetime="{e(p["_dt"].isoformat())}">{e(c["ago"](p))}</time>']
    s = session(p)
    if s:
        bits.append(f'<span class="sess">{e(s)}</span>')
    if p.get("readMins"):
        bits.append(f'{int(p["readMins"])} min read')
    return '<div class="fmeta">' + "<i>·</i>".join(bits) + "</div>"


def kicker(p, key, c):
    e = c["e"]
    labels = dict((k, lab) for k, lab, _ in TOPICS.get(key, []))
    t = [labels[x] for x in p["_topics"] if x in labels][:2]
    st = c["status_badge"](p)
    k = " · ".join(t) if t else c["cats"][p["category"]][0]
    return f'<span class="kick" style="--dot:var(--c-{p["category"]})">{e(k)}</span>{st}'


def featured(main, side, key, c):
    e, url = c["e"], c["url"]
    big = (f'<article class="fmain"><a href="{url(main)}"><img src="{c["cover_url"](main)}" width="1600" height="900" alt="{e(main.get("coverAlt") or "")}" fetchpriority="high" decoding="async">'
           f'<div class="fbody">{kicker(main, key, c)}<h2>{e(main["title"])}</h2><p>{e(main.get("dek") or "")}</p>{meta_line(main, c, None)}</div></a></article>')
    sup = "".join(f'<article class="fsup"><a href="{url(p)}"><img src="{c["cover_url"](p)}" width="1600" height="900" alt="" loading="lazy" decoding="async">'
                  f'<div>{kicker(p, key, c)}<h3>{e(p["title"])}</h3>{meta_line(p, c, None)}</div></a></article>' for p in side)
    return f'<section class="feat" aria-label="Featured stories">{big}<div class="fside">{sup}</div></section>'


def feed_card(p, key, c):
    e, url = c["e"], c["url"]
    return (f'<article class="fcard" data-topics="{" ".join(p["_topics"])}" data-session="{e(session(p))}">'
            f'<a href="{url(p)}"><img src="{c["cover_url"](p)}" width="1600" height="900" alt="" loading="lazy" decoding="async">'
            f'<div class="fcb">{kicker(p, key, c)}<h3>{e(p["title"])}</h3><p>{e(p.get("dek") or "")}</p>{meta_line(p, c, None)}</div></a></article>')


def feed(items, key, c, page_size=12, feat=()):
    cards = "".join(feed_card(p, key, c).replace('<article class="fcard"', '<article class="fcard" data-feat="1" hidden', 1) for p in feat)
    cards += "".join(feed_card(p, key, c) for p in items)
    return (f'<section class="cfeed" id="feed" aria-label="All stories" data-page="{page_size}" data-step="9">'
            f'<div class="fhead"><h2>All {c["e"](c["cats"][key][0])} stories</h2><span class="fcount" aria-live="polite"></span></div>'
            f'<div class="fgrid">{cards}</div>'
            f'<p class="fempty" hidden>No stories match this filter yet.</p>'
            f'<button type="button" class="btn ghost full fmore">Load more stories</button></section>')


# ------------------------------------------------------------------ sidebar widgets
def w_trending(items, c):
    e, base = c["e"], c["base"]
    counts = {}
    for p in items:
        for t in p["_tags"]:
            if t not in c["cat_labels"]:
                counts[t] = counts.get(t, 0) + 1
    top = [t for t, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])) if n >= 1][:10]
    if not top:
        return ""
    return ('<section class="panel sw"><h2 class="swh">Trending topics</h2><div class="tags">'
            + "".join(f'<a class="tag" href="{base}tag/{c["slug"](t)}/">#{e(t)}</a>' for t in top) + "</div></section>")


def w_list(title, items, c, more=None):
    e, url = c["e"], c["url"]
    if not items:
        return ""
    rows = "".join(f'<li><a href="{url(p)}"><b>{e(p["title"])}</b><small>{e(c["cats"][p["category"]][0])} · {e(c["ago"](p))}</small></a></li>' for p in items)
    m = f'<a class="vall" href="{e(more[0])}">{e(more[1])} →</a>' if more else ""
    return f'<section class="panel sw"><h2 class="swh">{e(title)}</h2><ol class="swl">{rows}</ol>{m}</section>'


def w_pulse(posts, meta, c):
    e, url, base = c["e"], c["url"], c["base"]
    hist = meta.get("history") or {}
    rows = []
    for n in ("Nifty 50", "Sensex", "Bank Nifty"):
        pts = hist.get(n) or []
        if len(pts) >= 2:
            last, prev = float(pts[-1]["v"]), float(pts[-2]["v"])
            ch = (last - prev) / prev * 100
            when = tmdate.fmt(pts[-1]["d"], "%-d %b")
            rows.append(f'<tr><th scope="row">{e(n)}<small>Close {e(when)}</small></th><td class="num">{last:,.2f}</td>'
                        f'<td class="num"><span class="pchip {"up" if ch >= 0 else "down"}">{ch:+.2f}%</span></td></tr>')
    rep = next((p for p in posts if p.get("report")), None)
    r = (rep or {}).get("report") or {}
    b = r.get("breadth") or {}
    extra = ""
    if b.get("advances") and b.get("declines"):
        extra += f'<p class="pul">Breadth ({e(b.get("exchange") or "NSE")}): <b class="up">{e(b["advances"])}</b> up · <b class="down">{e(b["declines"])}</b> down</p>'
    g, l = (r.get("gainers") or [])[:1], (r.get("losers") or [])[:1]
    if g and l:
        extra += (f'<p class="pul">Top gainer: <b>{e(g[0]["name"])}</b> <span class="up">+{e(str(g[0]["pct"]).lstrip("+"))}%</span> · '
                  f'top loser: <b>{e(l[0]["name"])}</b> <span class="down">{e(l[0]["pct"])}%</span></p>')
    if not rows and not extra:
        return ""
    src = f'<a href="{url(rep)}">daily report, {e(r.get("dateLabel") or "")}</a>' if rep else "daily closes"
    return (f'<section class="panel sw pulse"><h2 class="swh">Market pulse <span class="fb fb-eod">EOD</span></h2>'
            f'<table class="mt"><tbody>{"".join(rows)}</tbody></table>{extra}'
            f'<p class="asof">End-of-day figures from our {src}. Not live.</p><a class="vall" href="{base}nifty-50/">Nifty 50 chart →</a></section>')


def w_earnings(results, c):
    e, base = c["e"], c["base"]
    today = datetime.now(c["ist"]).date()
    up = [x for x in results if x["date"] >= today][:6]
    if not up:
        return ""
    rows = "".join(f'<li><span>{e(x["company"])}</span><time>{"Today" if x["date"] == today else tmdate.fmt(x["date"], "%a %-d %b")}</time></li>' for x in up)
    return f'<section class="panel sw"><h2 class="swh">Earnings this week</h2><ul class="swe">{rows}</ul><a class="vall" href="{base}results/">Results calendar →</a></section>'


def w_companies(items, c):
    e, base = c["e"], c["base"]
    seen = []
    for p in items:
        for co in p.get("companies") or []:
            n = co.get("name")
            if n and n not in [s[0] for s in seen]:
                seen.append((n, co.get("ticker") or ""))
    if not seen:
        return ""
    def link(n):
        s = c["slug"](n)
        return f'{base}stock/{s}/' if s in c["company_slugs"] else None
    rows = "".join((f'<li><a href="{link(n)}"><b>{e(n)}</b><small>{e(t)}</small></a></li>' if link(n) else f'<li><span><b>{e(n)}</b><small>{e(t)}</small></span></li>') for n, t in seen[:8])
    return f'<section class="panel sw"><h2 class="swh">Companies in the news</h2><ul class="swc">{rows}</ul></section>'


def sidebar(key, items, posts, meta, results, c):
    others = [p for p in posts if p["category"] != key][:5]
    parts = []
    if key == "markets":
        parts += [w_pulse(posts, meta, c), w_earnings(results, c)]
    if key == "tech":
        ai = [p for p in items if "ai" in p["_topics"]][:5]
        parts += [w_list("Latest in AI", ai, c), w_companies(items, c)]
    if key == "startups" and c.get("ipo_widget"):
        parts.append(c["ipo_widget"])
    if key == "commodities" and c.get("rates_card"):
        parts.append(c["rates_card"])
    parts += [w_trending(items, c), w_list("Elsewhere on TotalMarket", others, c, (c["base"] + "live/", "All updates"))]
    return '<aside class="cside" aria-label="More from TotalMarket">' + "".join(parts) + "</aside>"


def body(key, posts, meta, results, c):
    e = c["e"]
    name, blurb = c["cats"][key]
    items = [p for p in posts if p["category"] == key][: c["limit"]]
    for p in items:
        p["_topics"] = topics_for(p, key)
    head = f'<header class="chead"><h1>{e(name)}</h1><p>{e(blurb)}</p>{chips(key, items, c) if items else ""}</header>'
    if not items:
        return head + '<div class="empty"><p>No stories here yet. This section fills up with the next update.</p></div>'
    main = next((p for p in items[:8] if p.get("lead")), items[0])
    rest = [p for p in items if p is not main]
    side, feed_items = rest[:2], rest[2:]
    top = featured(main, side, key, c)
    # The featured stories also sit in the feed as hidden cards (data-feat) so a topic or
    # session filter can show every match in one grid; with "All" they stay hidden (no duplicates).
    return (head + f'<div class="cwrap"><div class="cmain" data-filter-root>{top}{feed(feed_items, key, c, feat=[main] + side)}</div>'
            + sidebar(key, items, posts, meta, results, c) + "</div>")
