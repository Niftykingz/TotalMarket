"""Official-market-data style features: market session status, NSE holiday calendar,
market breadth card, corporate events feed and the report/history archive.

TotalMarket has no licensed live data feed, so every figure here comes from a named,
dated source (usually a news report quoting NSE) with a link to the matching official
NSE page. Nothing is shown as live; missing values show "Unavailable".
"""
import csv
import io
import json
import os
from datetime import date, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")

NSE_MARKET_STATS = "https://www.nseindia.com/"  # NSE home page shows the official market statistics panel


def _load(name, default):
    p = os.path.join(DATA, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def _d(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def _fmt(d, long=False):
    return d.strftime("%A, %-d %B %Y" if long else "%a %-d %b") if d else "—"


# ------------------------------------------------------------------ market calendar
def calendar():
    return _load("market_calendar.json", {})


def years():
    """All yearly holiday lists, oldest first."""
    return sorted(calendar().get("years", []), key=lambda y: y["year"])


def current_year(today):
    """The holiday year readers need now: this year if we have it, else the latest we have."""
    ys = [y["year"] for y in years()]
    return today.year if today.year in ys else (max(ys) if ys else today.year)


def holidays_path(today):
    return f"stock-market-holidays-{current_year(today)}/"


def calendar_warnings(today):
    """Problems the scheduled runs must fix (printed by build.py)."""
    ys = [y["year"] for y in years()]
    out = []
    if today.year not in ys:
        out.append(f"WARNING: no NSE holiday list for {today.year} in data/market_calendar.json; add the official list now.")
    if today.month == 12 and (today.year + 1) not in ys:
        out.append(f"WARNING: NSE holiday list for {today.year + 1} is missing; NSE usually publishes it in December. Add it as soon as the circular is out.")
    return out


def calendar_json():
    """Small public file the browser uses to show 'Market open / closed' from the schedule."""
    c = calendar()
    hol = [h for y in years() for h in y.get("holidays", [])]
    return json.dumps({"hours": c.get("hours"), "holidays": [h["date"] for h in hol],
                       "names": {h["date"]: h["name"] for h in hol}}, ensure_ascii=False)


def holidays_page(ctx):
    out = []
    for y in years():
        out += _holidays_page(dict(calendar(), **y), ctx)
    return out


def _holidays_page(c, ctx):
    page, e, base = ctx["page"], ctx["e"], ctx["base"]
    if not c.get("holidays"):
        return []
    today = ctx["today"]
    yr = c.get("year", today.year)
    nxt = next((h for h in c["holidays"] if _d(h["date"]) >= today), None)
    rows = "".join(
        f'<tr class="{"past" if _d(h["date"]) < today else ""}"><th scope="row">{e(_d(h["date"]).strftime("%-d %b %Y"))}</th><td>{e(_d(h["date"]).strftime("%A"))}</td><td>{e(h["name"])}</td></tr>'
        for h in c["holidays"])
    wk = "".join(f'<li>{e(_d(h["date"]).strftime("%-d %b"))} ({e(_d(h["date"]).strftime("%A"))}): {e(h["name"])}</li>' for h in c.get("weekendHolidays", []))
    sp = "".join(f'<li><b>{e(_d(s["date"]).strftime("%-d %b %Y"))}, {e(s["name"])}.</b> {e(s.get("note", ""))}</li>' for s in c.get("specialSessions", []))
    hrs = c.get("hours", {})
    srcs = " and ".join(f'<a href="{e(s["url"])}" rel="nofollow noopener" target="_blank">{e(s["name"])}</a>' for s in c.get("sources", []))
    nxt_html = (f'<div class="dkpis"><div><span>Next market holiday</span><b>{e(_d(nxt["date"]).strftime("%a %-d %b"))}</b><small>{e(nxt["name"])}</small></div>'
                f'<div><span>Holidays on weekdays in {yr}</span><b>{len(c["holidays"])}</b></div>'
                f'<div><span>Normal session</span><b>{e(hrs.get("normal", ["", ""])[0])}–{e(hrs.get("normal", ["", ""])[1])}</b><small>IST, Monday–Friday</small></div></div>') if nxt else ""
    piggy = ctx["piggy_box"]({"happened": f"This is the list of weekdays in {yr} when NSE's equity market is shut, plus the normal trading hours.",
                              "matters": "On a holiday you can't buy or sell shares, and money and shares don't settle, so a sale on the day before a holiday reaches your account a day later. SIP dates that fall on a holiday usually move to the next working day.",
                              "watch": ["NSE's separate circular with the Muhurat trading timings for Diwali", "Any change to the list announced by the exchange"]})
    body = (f'<nav class="crumbs"><a href="{base}">Home</a> / <a href="{base}markets/">Markets</a></nav>'
            f'<div class="sechead"><h1>Stock market holidays {yr}: NSE and BSE trading holidays</h1>'
            f'<p>Every weekday in {yr} when the Indian stock market (equity segment) is closed, with market timings. Checked on {e(_fmt(_d(c.get("checked")), True))} against two published copies of the NSE list ({srcs}). '
            f'Always confirm on <a href="{e(c.get("officialUrl"))}" rel="nofollow noopener" target="_blank">NSE\'s official holiday page</a>.</p></div>'
            + nxt_html
            + f'<div class="tablewrap"><table class="dt holi"><thead><tr><th>Date</th><th>Day</th><th>Holiday</th></tr></thead><tbody>{rows}</tbody></table></div>'
            + f'<section class="lesson"><h2>NSE market timings</h2><ul class="plain">'
              f'<li><b>Pre-open session:</b> {e(hrs.get("preOpen", ["", ""])[0])} to {e(hrs.get("preOpen", ["", ""])[1])} am IST, when orders are collected to set the opening price.</li>'
              f'<li><b>Normal market:</b> {e(hrs.get("normal", ["", ""])[0])} am to 3:30 pm IST.</li>'
              f'<li><b>Closing session:</b> 3:30 to 4:00 pm IST, used to set the official closing price.</li></ul></section>'
            + (f'<section class="lesson"><h2>Holidays that fall on a weekend</h2><ul class="plain">{wk}</ul></section>' if wk else "")
            + (f'<section class="lesson"><h2>Special sessions</h2><ul class="plain">{sp}</ul></section>' if sp else "")
            + piggy
            + '<p class="disc">Holiday dates as published by the exchange and reproduced by the sources above; the exchange can change them by circular. For information only.</p>')
    return [(f"stock-market-holidays-{yr}/index.html", page(f"Stock Market Holidays {yr}: NSE & BSE Trading Holiday List",
             f"Stock market holidays {yr}: full list of NSE and BSE trading holidays with dates and days, next holiday, market timings and Muhurat trading.",
             f"{base}stock-market-holidays-{yr}/", body, ctx["meta"],
             keywords=[f"stock market holidays {yr}", f"NSE holidays {yr}", f"BSE holidays {yr}", "share market holiday list", "is market open today", "market holiday tomorrow", "NSE timings"],
             seo_title=f"Stock Market Holidays {yr}: NSE & BSE Holiday List | TotalMarket"))]


# ------------------------------------------------------------------ breadth card
def breadth_card(posts, ctx):
    e, base, url = ctx["e"], ctx["base"], ctx["url"]
    rep = next((p for p in posts if p.get("report")), None)
    b = (rep or {}).get("report", {}).get("breadth") or {}
    def v(k):
        x = b.get(k)
        return e(x) if x not in (None, "") else '<i class="na">Unavailable</i>'
    if rep:
        r = rep["report"]
        dl = r.get("dateLabel") or ""
        src = ", ".join(s.get("name", "") for s in (rep.get("sources") or [])[:2])
        foot = (f'<p class="bnote">End of day · {e(dl)} · {e(b.get("exchange") or "NSE")} · figures as reported by {e(src)} in our '
                f'<a href="{url(rep)}">daily report</a> · <a href="{NSE_MARKET_STATS}" rel="nofollow noopener" target="_blank">Official figures on NSE</a></p>')
    else:
        foot = '<p class="bnote">No market report yet.</p>'
    adv, dec = b.get("advances"), b.get("declines")
    bar = ""
    try:
        a, d_, u = float(adv), float(dec), float(b.get("unchanged") or 0)
        tot = a + d_ + u
        bar = (f'<div class="bbar" role="img" aria-label="{int(a)} advances, {int(d_)} declines, {int(u)} unchanged">'
               f'<i class="up" style="width:{a / tot * 100:.1f}%"></i><i class="fl" style="width:{u / tot * 100:.1f}%"></i><i class="down" style="width:{d_ / tot * 100:.1f}%"></i></div>')
    except Exception:
        pass
    return (f'<section class="panel breadth wide" aria-label="Market breadth"><h2>Market breadth <span class="mstatus" data-mstatus>Market status</span></h2>'
            f'{bar}<div class="bgrid">'
            f'<div><span>Advances</span><b class="up">{v("advances")}</b></div><div><span>Declines</span><b class="down">{v("declines")}</b></div><div><span>Unchanged</span><b>{v("unchanged")}</b></div>'
            f'<div><span>52-week highs</span><b>{v("highs52")}</b></div><div><span>52-week lows</span><b>{v("lows52")}</b></div><div><span>Investor wealth</span><b>{v("wealth")}</b></div>'
            f'<div><span>Upper circuit</span><b>{v("upperCircuit")}</b></div><div><span>Lower circuit</span><b>{v("lowerCircuit")}</b></div>'
            f'<div><span>Next holiday</span><b class="small" data-nextholiday>—</b></div></div>{foot}</section>')


# ------------------------------------------------------------------ corporate events
TYPE_NOTES = {
    "Dividend": "A dividend is a share of the company's profit paid to shareholders. Since India moved to T+1 settlement, the ex-date and record date are usually the same day, so you must already own the shares before that day to be eligible.",
    "Financial results": "Quarterly results show the company's revenue and profit for the last three months. Share prices often move sharply on results day.",
    "Results date": "The day the company's board meets to approve and announce its quarterly results. Companies must tell the exchange this date in advance.",
    "Board meeting": "Companies must tell the exchange in advance when the board will meet to approve results, dividends, fund-raising or other big decisions.",
    "Bonus": "A bonus issue gives existing shareholders extra free shares. The share price adjusts down, so the total value of your holding does not change on that day.",
    "Split": "A stock split divides each share into smaller ones, say 1 into 5. The price per share falls by the same ratio; your total value stays the same.",
    "Announcement": "Listed companies must tell the exchange about material news such as orders, acquisitions or management changes.",
}


def events_page(posts, results, ctx):
    page, e, base = ctx["page"], ctx["e"], ctx["base"]
    data = _load("corporate_events.json", {"events": []})
    off = data.get("officialPages", {})
    today = ctx["today"]
    evs = []
    for x in data.get("events", []):
        d = _d(x.get("date"))
        if d:
            evs.append(dict(x, _d=d))
    for r in results:  # confirmed results dates from the results calendar
        evs.append({"_d": r["date"], "date": r["date"].isoformat(), "company": r["company"], "type": "Results date",
                    "detail": r.get("note") or "Quarterly results", "source": {"name": "TotalMarket results calendar", "url": f"{base}results/"}, "noticeUrl": ""})
    evs.sort(key=lambda x: (x["_d"], x["type"], x["company"]))
    up = [x for x in evs if x["_d"] >= today]
    past = [x for x in evs if x["_d"] < today and (today - x["_d"]).days <= 14][::-1]
    types = sorted({x["type"] for x in evs})

    def row(x):
        src = x.get("source") or {}
        notice = (f'<a href="{e(x["noticeUrl"])}" rel="nofollow noopener" target="_blank">Official NSE notice</a>' if x.get("noticeUrl")
                  else f'<a href="{e(off.get("actions" if x["type"] in ("Dividend", "Bonus", "Split") else "boardMeetings" if x["type"] in ("Board meeting", "Results date") else "results" if x["type"] == "Financial results" else "announcements"))}" rel="nofollow noopener" target="_blank">Check on NSE</a>'
                  f' <small class="per">(per {e(src.get("name"))})</small>')
        srcl = f'<a href="{e(src.get("url"))}" rel="nofollow noopener">{e(src.get("name"))}</a>' if src.get("url") else e(src.get("name"))
        dates = " · ".join(t for t in [f'Ex-date {_fmt(_d(x["exDate"]))}' if x.get("exDate") else "", f'Record date {_fmt(_d(x["recordDate"]))}' if x.get("recordDate") else ""] if t)
        return (f'<tr data-type="{e(x["type"])}"><th scope="row"><b>{e(x["company"])}</b>{("<small>" + e(x["ticker"]) + "</small>") if x.get("ticker") else ""}</th>'
                f'<td><span class="evt">{e(x["type"])}</span></td><td>{e(x.get("detail"))}{("<small class=\"dates\">" + e(dates) + "</small>") if dates else ""}</td>'
                f'<td>{notice}<small class="per">Source: {srcl}</small></td></tr>')

    def table(items, title):
        if not items:
            return f'<section class="edition"><h2 class="edhead"><b>{e(title)}</b></h2><p class="empty">No events listed.</p></section>'
        by = {}
        for x in items:
            by.setdefault(x["_d"], []).append(x)
        out = [f'<section class="edition"><h2 class="edhead"><b>{e(title)}</b><span>{len(items)}</span></h2>']
        for d, xs in by.items():
            out.append(f'<h3 class="evday">{e(_fmt(d, True))}</h3><div class="tablewrap"><table class="dt evtable"><thead><tr><th>Company</th><th>Event</th><th>Details</th><th>Official notice</th></tr></thead>'
                       f'<tbody>{"".join(row(x) for x in xs)}</tbody></table></div>')
        out.append("</section>")
        return "".join(out)

    chips = '<div class="chips evchips" id="evchips"><button type="button" class="chipf on" data-cat="all">All</button>' + "".join(
        f'<button type="button" class="chipf" data-cat="{e(t)}">{e(t)}</button>' for t in types) + "</div>"
    notes = "".join(f'<details class="lessonq"><summary>What is a {e(t.lower())}?</summary><p>{e(TYPE_NOTES[t])}</p></details>' for t in types if t in TYPE_NOTES)
    host = ctx["piggy_host"]("Boss Piggy reads the notices", "Companies must tell the exchange about dividends, results dates, board meetings and other big news. I list each one with its date and a link to check it on NSE, and explain what each kind of event means below.", (f"{base}learn/", "More lessons"), "full")
    upd = datetime.fromisoformat(data["updatedAt"]).strftime("%-d %b %Y, %-I:%M %p IST") if data.get("updatedAt") else ""
    body = (f'<nav class="crumbs"><a href="{base}">Home</a> / <a href="{base}markets/">Markets</a></nav>'
            f'<div class="sechead"><h1>Corporate actions and events: dividends, results, board meetings</h1>'
            f'<p>Upcoming record dates, dividends, results dates and board meetings for listed Indian companies. Each item names its source; where an official NSE notice link is not yet confirmed, it links to the matching NSE filings page to check. Last updated {e(upd)}.</p></div>'
            + host + chips + f'<div id="evlist">{table(up, "Upcoming")}{table(past, "Last 14 days")}</div>'
            + f'<section class="lesson"><h2>What each event means</h2>{notes}</section>'
            + f'<p class="cm-note">Official sources: <a href="{e(off.get("announcements"))}" rel="nofollow noopener" target="_blank">NSE announcements</a> · <a href="{e(off.get("actions"))}" rel="nofollow noopener" target="_blank">NSE corporate actions</a> · <a href="{e(off.get("boardMeetings"))}" rel="nofollow noopener" target="_blank">NSE board meetings</a> · <a href="{base}results/">Results calendar</a></p>'
            + '<p class="disc">Dates and amounts come from company filings as reported by the sources named in each row and can change; check the official notice before acting. For information only, not investment advice.</p>')
    return [("corporate-events/index.html", page("Corporate Actions Today: Dividends, Record Dates, Board Meetings",
             "Upcoming corporate actions in India: dividend record dates, ex-dates, results dates and board meetings, with sources and links to official NSE filings.",
             f"{base}corporate-events/", body, ctx["meta"],
             keywords=["corporate actions", "dividend record date", "ex-dividend date", "upcoming dividends", "board meeting", "record date this week", "stocks going ex-dividend"],
             seo_title="Corporate Actions: Dividends, Record Dates, Board Meetings | TotalMarket"))]


# ------------------------------------------------------------------ archive + CSV
def index_csv(meta):
    h = meta.get("history") or {}
    dates = sorted({x["d"] for v in h.values() for x in v})
    names = list(h.keys())
    look = {n: {x["d"]: x["v"] for x in h[n]} for n in names}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date"] + names)
    for d in dates:
        w.writerow([d] + [look[n].get(d, "") for n in names])
    return buf.getvalue()


def archive_html(reps, meta, ctx):
    e, base, url = ctx["e"], ctx["base"], ctx["url"]
    if not reps:
        return ""
    by = {}
    for p in reps:
        d = _d((p.get("report") or {}).get("date")) or p["_dt"].date()
        by.setdefault(d.strftime("%B %Y"), []).append((d, p))
    months = "".join(
        f'<section class="edition arch" data-month="{e(m)}"><h2 class="edhead"><b>{e(m)}</b><span>{len(xs)}</span></h2><ul class="archlist">'
        + "".join(f'<li data-date="{d.isoformat()}"><time datetime="{d.isoformat()}">{e(_fmt(d))}</time><a href="{url(p)}">{e(p["title"])}</a></li>' for d, p in xs)
        + "</ul></section>" for m, xs in by.items())
    h = meta.get("history") or {}
    names = [n for n in ("Nifty 50", "Sensex", "Bank Nifty") if h.get(n)]
    dates = sorted({x["d"] for n in names for x in h[n]}, reverse=True)
    look = {n: {x["d"]: x["v"] for x in h[n]} for n in names}
    rows = "".join(f'<tr><th scope="row">{e(_fmt(_d(d)))}</th>' + "".join(f'<td class="num">{(f"{look[n][d]:,.2f}") if d in look[n] else "—"}</td>' for n in names) + "</tr>" for d in dates[:30])
    hist = (f'<section class="edition"><h2 class="edhead"><b>Index closing history</b></h2>'
            f'<div class="tablewrap"><table class="dt"><thead><tr><th>Date</th>{"".join(f"<th>{e(n)}</th>" for n in names)}</tr></thead><tbody>{rows}</tbody></table></div>'
            f'<p class="cm-note">Closing levels recorded by TotalMarket from the sources of each daily report. <a href="{base}data/index-closes.csv" download>Download CSV</a>. '
            f'This is TotalMarket\'s own record, not NSE\'s official data; for official history see <a href="https://www.nseindia.com/reports-indices-historical-index-data" rel="nofollow noopener" target="_blank">NSE historical index data</a>.</p></section>') if names else ""
    search = ('<div class="archsearch"><label for="archdate">Find a report by date</label><input type="date" id="archdate">'
              '<button type="button" id="archclear" class="chipf">Show all</button><span id="archmsg" class="cm-note" aria-live="polite"></span></div>')
    return search + f'<div id="archive">{months}</div>' + hist


def events_warnings(today):
    data = _load("corporate_events.json", {})
    try:
        upd = datetime.fromisoformat(data.get("updatedAt")).date()
    except Exception:
        return ["WARNING: data/corporate_events.json has no valid updatedAt; refresh corporate events."]
    age = (today - upd).days
    return [f"WARNING: corporate events last updated {upd.isoformat()} ({age} days ago); refresh data/corporate_events.json in this run."] if age >= 1 else []
