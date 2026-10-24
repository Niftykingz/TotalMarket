"""Build the Friday (last trading day of the week) market report job from NSE exchange data.

    python3 -m pipeline.weekly --date 2026-10-30 [--out pipeline/inbox]

Every number comes from the raw NSE responses the collector archived in
data/market_snapshots/<date>/ (sha256-recorded); each figure's evidence is the line
source_audit rebuilds from those bytes. Week % values are recomputed by the pipeline from two
verified closes. Text is written from the numbers only: no causes, forecasts or tips.
The pipeline decides whether the job can be published; this script only prepares it.
"""
import argparse
import datetime as dt
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import source_audit  # noqa: E402

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
INDEXES = [("n50", "NIFTY 50", "Nifty 50"), ("bank", "NIFTY BANK", "Nifty Bank"),
           ("n500", "NIFTY 500", "Nifty 500"), ("next50", "NIFTY NEXT 50", "Nifty Next 50"),
           ("mid", "NIFTY MIDCAP 100", "Nifty Midcap 100"), ("small", "NIFTY SMALLCAP 100", "Nifty Smallcap 100"),
           ("vix", "INDIA VIX", "India VIX")]
SECTORS = [("it", "NIFTY IT", "IT"), ("cement", "NIFTY CEMENT", "Cement"), ("oilgas", "NIFTY OIL & GAS", "Oil & gas"),
           ("pharma", "NIFTY PHARMA", "Pharma"), ("health", "NIFTY HEALTHCARE INDEX", "Healthcare"),
           ("psub", "NIFTY PSU BANK", "PSU banks"), ("pvtb", "NIFTY PRIVATE BANK", "Private banks"),
           ("auto", "NIFTY AUTO", "Auto"), ("fmcg", "NIFTY FMCG", "FMCG"), ("energy", "NIFTY ENERGY", "Energy"),
           ("realty", "NIFTY REALTY", "Realty"), ("media", "NIFTY MEDIA", "Media"), ("metal", "NIFTY METAL", "Metal"),
           ("cdur", "NIFTY CONSUMER DURABLES", "Consumer durables")]


class NotReady(Exception):
    pass


def _source(root, day, sid, name, api, published):
    rel = f"data/market_snapshots/{day}/{api}.json.gz"
    f = Path(root) / rel
    if not f.is_file():
        raise NotReady(f"{rel} missing")
    raw = gzip.decompress(f.read_bytes())
    return {"id": sid, "name": name, "url": "https://www.nseindia.com/" + api.replace("_", "/", 1),
            "published": published, "dataset": rel, "sha256": hashlib.sha256(raw).hexdigest()}, json.loads(raw)


def fmt(v):
    """Indian grouping, 2 decimals, for numbers in prose (the checker ignores grouping)."""
    n = float(v)
    whole, frac = f"{abs(n):.2f}".split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        whole = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1]) + "," + tail
    return whole + "." + frac


def pct_word(p, up="rose", down="fell"):
    return (up if p > 0 else down if p < 0 else "was unchanged at"), f"{abs(p):.2f}%"


def build(day, root=ROOT, now=None):
    d = dt.date.fromisoformat(day)
    nse_stamp = d.strftime("%d-%b-%Y")
    label_day = f"{d.strftime('%a')} {d.day} {d.strftime('%b')}"
    nse, idx = _source(root, day, "nse", f"NSE India: all indices (closing data, {d.day} {d.strftime('%b %Y')}, 3:30 pm)",
                       "api_allIndices", f"{day}T15:30:00+05:30")
    if idx.get("timestamp") != f"{nse_stamp} 15:30":
        raise NotReady(f"NSE index snapshot is not the {day} close (timestamp {idx.get('timestamp')!r})")
    lines = {ln.split(":", 1)[0]: ln for ln in source_audit.dataset_lines(nse, root)}
    rows = {x["index"]: x for x in idx["data"]}
    missing = [n for _, n, _ in INDEXES + SECTORS if n not in rows]
    if missing:
        raise NotReady(f"indices missing from snapshot: {missing}")
    week_ago = {rows[n].get("oneWeekAgo") for _, n, _ in INDEXES + SECTORS}
    if len(week_ago) != 1:
        raise NotReady(f"indices disagree on the week-ago date: {week_ago}")
    week_ago = week_ago.pop()
    wk_date = dt.datetime.strptime(week_ago, "%d-%b-%Y").date()
    if not 5 <= (d - wk_date).days <= 9:
        raise NotReady(f"week-ago close {week_ago} is not about a week before {day}")

    figs = []
    for k, n, label in INDEXES + SECTORS:
        x, ev = rows[n], lines[n]
        figs += [{"id": f"nse_{k}", "label": f"{label} close", "value": str(x["last"]), "change": str(x["variation"]),
                  "source": "nse", "evidence": ev, "as_of": day, **({"key": True} if k == "n50" else {})},
                 {"id": f"nse_{k}_pct", "label": f"{label} change %", "value": str(x["percentChange"]),
                  "source": "nse", "evidence": ev, "as_of": day},
                 {"id": f"nse_{k}_wk", "label": f"{label} close a week earlier", "value": str(x["oneWeekAgoVal"]),
                  "source": "nse", "evidence": ev, "as_of": wk_date.isoformat(), "historical": True}]
    b = rows["NIFTY 500"]
    for k in ("advances", "declines", "unchanged"):
        figs.append({"id": f"nse_n500_{k}", "label": f"Nifty 500 stocks: {k}", "value": str(b[k]),
                     "source": "nse", "evidence": lines["NIFTY 500"], "as_of": day})
    sources = [nse]
    flows = None
    try:
        nsef, flow_raw = _source(root, day, "nsef", f"NSE India: FII/FPI and DII provisional cash-market activity, {d.day} {d.strftime('%b %Y')}",
                                 "api_fiidiiTradeReact", f"{day}T18:00:00+05:30")
        fl = {ln.split(" ", 1)[0]: ln for ln in source_audit.dataset_lines(nsef, root)}
        got = {}
        for who, cat in (("fii", "FII/FPI"), ("dii", "DII")):
            x = next((r for r in flow_raw if r.get("category") == cat and r.get("date") == nse_stamp), None)
            if x:
                got[who] = x
                for k, f in (("net", "netValue"), ("buy", "buyValue"), ("sell", "sellValue")):
                    figs.append({"id": f"nse_{who}_{k}", "label": f"{cat} {k} value, cash market", "value": x[f],
                                 "source": "nsef", "evidence": fl[cat], "as_of": day})
        if len(got) == 2:
            sources.append(nsef)
            flows = got
        else:
            figs = [f for f in figs if f["source"] != "nsef"]
    except NotReady:
        pass

    def wk(n):
        x = rows[n]
        return (x["last"] - x["oneWeekAgoVal"]) / x["oneWeekAgoVal"] * 100

    n50 = rows["NIFTY 50"]
    w50 = wk("NIFTY 50")
    wv, wa = pct_word(w50, "up", "down")
    dv, da = pct_word(n50["percentChange"])
    sect = sorted(((wk(n), label) for _, n, label in SECTORS), reverse=True)
    best, worst = sect[0], sect[-1]
    ups = [l for w, l in sect if w > 0]
    downs_day = sum(1 for _, n, _ in SECTORS if rows[n]["percentChange"] < 0)
    parts = [f"the {label} {('gained' if wk(n) > 0 else 'lost')} {abs(wk(n)):.2f}%"
             for _, n, label in INDEXES if n in ("NIFTY NEXT 50", "NIFTY MIDCAP 100", "NIFTY SMALLCAP 100")]
    broad = ", ".join(parts[:-1]) + " and " + parts[-1]
    vix = rows["INDIA VIX"]
    vv, va = pct_word(vix["percentChange"])
    sector_line = (f"Over the week {best[1]} did best ({best[0]:+.2f}%) and {worst[1]} worst ({worst[0]:+.2f}%) among the sector indices in the heatmap."
                   .replace("+-", "−").replace("-", "−"))
    if downs_day == len(SECTORS):
        sector_line = "Every sector index in the heatmap fell on the day. " + sector_line
    body = [
        f"What moved | The Nifty 50 closed the week at {fmt(n50['last'])}, {wv} {wa} from the previous week's close of "
        f"{fmt(n50['oneWeekAgoVal'])} on {wk_date.day} {wk_date.strftime('%b')}, and {dv} {da} on the day. Over the week {broad}.",
        f"Breadth | On the day {b['declines']} stocks in the Nifty 500 fell and {b['advances']} rose, according to NSE. "
        f"India VIX, which measures the volatility traders expect, {vv} {va} to {fmt(vix['last'])}.",
        f"Sectors | {sector_line}",
    ]
    if flows:
        def flow_sent(who, name):
            v = float(flows[who]["netValue"])
            return f"{name} were net {'buyers' if v > 0 else 'sellers'} of ₹{fmt(abs(v))} crore"
        body.append(f"Flows | NSE's provisional data show {flow_sent('fii', 'foreign portfolio investors')} in the cash market on the day, "
                    f"and {flow_sent('dii', 'domestic institutions')}.")
    takeaways = [f"The Nifty 50 ended the week {wa} {'higher' if w50 > 0 else 'lower'}; " + broad + ".",
                 (f"Sectors up over the week: {', '.join(ups)}." if ups else "No sector index in the heatmap gained over the week.")]
    title_dir = "up" if w50 > 0 else "down"
    pub = (now or dt.datetime.now(IST)).replace(microsecond=0)
    spec = lambda k, label: {"id": f"nse_{k}", "label": label, "pct": f"nse_{k}_pct", "weekAgo": f"nse_{k}_wk"}
    pspec = lambda k, label: {"id": f"nse_{k}_pct", "label": label, "close": f"nse_{k}", "weekAgo": f"nse_{k}_wk"}
    slug = f"{day}-weekly-market-review"
    article = {
        "title": f"Weekly market report: Nifty 50 closes at {fmt(n50['last'])}, {title_dir} {wa} this week | {d.day} {d.strftime('%B %Y')}",
        "dek": f"The Nifty 50 ended the week at {fmt(n50['last'])}. NSE index scoreboard, sector heatmap, breadth and institutional flows.",
        "category": "markets", "lead": True, "readMins": 3, "reportType": "weekly_market",
        "visualSpec": {
            "dateLabel": f"Week to {label_day} · close",
            "weekLabel": f"Change from the close on {wk_date.strftime('%a')} {wk_date.day} {wk_date.strftime('%b')} to {label_day} (NSE)",
            "indices": [spec("n50", "Nifty 50"), spec("bank", "Nifty Bank"), spec("n500", "Nifty 500"), spec("vix", "India VIX")],
            "caps": [pspec("n50", "Nifty 50"), pspec("next50", "Nifty Next 50"), pspec("mid", "Nifty Midcap 100"), pspec("small", "Nifty Smallcap 100")],
            "sectors": [pspec(k, label) for k, _, label in SECTORS], "global": [], "gainers": [], "losers": [],
            "breadth": {"advances": "nse_n500_advances", "declines": "nse_n500_declines", "unchanged": "nse_n500_unchanged"},
            "breadthExchange": "NSE, Nifty 500 stocks on the day",
            **({"fiiDii": {"fiiNet": "nse_fii_net", "diiNet": "nse_dii_net", "fiiBuy": "nse_fii_buy", "fiiSell": "nse_fii_sell",
                           "diiBuy": "nse_dii_buy", "diiSell": "nse_dii_sell"},
                "fiiDiiNote": "NSE provisional figures for the cash market, in ₹ crore."} if flows else {}),
        },
        "reportTakeaways": takeaways,
        "reportWatch": ["Crude oil and the rupee", "Quarterly earnings from large companies", "Institutional flows", "India VIX"],
        "body": body,
        "indiaImpact": "Index, sector and breadth moves together show how widely gains or losses spread beyond the Nifty 50.",
        "seoTitle": f"Weekly Stock Market Report {d.day} {d.strftime('%b %Y')}: Nifty, Sensex, Sectors",
        "seoDescription": f"Week to {d.day} {d.strftime('%b %Y')}: Nifty 50 at {fmt(n50['last'])}, {title_dir} {wa}. NSE sector heatmap, Nifty 500 breadth and FII/DII flows.",
        "tags": ["weekly market report", "Nifty 50 this week", "sector heatmap", "market breadth", "FII DII data", "stock market today"],
        "sources": [{"name": s["name"], "url": s["url"]} for s in sources],
        "publishedAt": pub.isoformat(), "edition": f"{day}-weekly", "editionLabel": f"{label_day} · Weekly market report",
        "status": "new",
    }
    graphic = {
        "headline": article["title"], "coverHeadline": "WEEKLY MARKET REPORT", "stat": fmt(n50["last"]), "statLabel": "Nifty 50 close",
        "symbol": "candles", "flags": ["IN"], "coverDate": day,
        "chart": {"type": "index_board", "title": "Indian markets · week close", "asOf": f"Close, {label_day} {d.year}", "source": "NSE",
                  "items": [{"label": "Nifty 50", "value": str(n50["last"]), "change": str(n50["variation"]), "pct": f"{n50['percentChange']}%"},
                            {"label": "Nifty Bank", "value": str(rows["NIFTY BANK"]["last"]), "change": str(rows["NIFTY BANK"]["variation"]),
                             "pct": f"{rows['NIFTY BANK']['percentChange']}%"},
                            {"label": "Midcap 100", "pct": f"{rows['NIFTY MIDCAP 100']['percentChange']}%"},
                            {"label": "Smallcap 100", "pct": f"{rows['NIFTY SMALLCAP 100']['percentChange']}%"}]},
    }
    return {"slug": slug, "collection": {"sources": sources, "figures": figs, "examples": []}, "graphic": graphic, "article": article}


def last_trading_day_of_week(d, root=ROOT):
    """True when no NSE session remains between d and the weekend."""
    cal = json.loads((Path(root) / "data" / "market_calendar.json").read_text(encoding="utf-8"))
    hol = {h["date"] for y in cal.get("years", []) for h in y.get("holidays", [])}
    nxt = d + dt.timedelta(days=1)
    while nxt.weekday() < 5:
        if nxt.isoformat() not in hol:
            return False
        nxt += dt.timedelta(days=1)
    return d.weekday() < 5 and d.isoformat() not in hol


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.datetime.now(IST).date().isoformat())
    ap.add_argument("--out", default=str(ROOT / "pipeline" / "inbox"))
    ap.add_argument("--only-if-week-end", action="store_true", help="do nothing unless DATE is the week's last session")
    a = ap.parse_args(argv)
    d = dt.date.fromisoformat(a.date)
    if a.only_if_week_end and not last_trading_day_of_week(d):
        print(f"{a.date} is not the last trading day of the week; no weekly report")
        return 0
    try:
        job = build(a.date)
    except NotReady as ex:
        print(f"weekly report not prepared: {ex}")
        return 2
    if (ROOT / "data" / "posts" / f"{job['slug']}.json").is_file() or (ROOT / "pipeline" / "archive" / f"{job['slug']}.json").is_file():
        print(f"{job['slug']} is already published; not preparing it again")
        return 0
    out = Path(a.out) / f"{job['slug']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(job, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"prepared {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
