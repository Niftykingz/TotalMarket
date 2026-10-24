"""Daily market-close drafts: verified closing dataset -> four graphics + draft article + source record.

    python3 -m pipeline.closing --date 2026-10-23 [--out drafts/closing]

Data comes only from the raw NSE responses archived by the collector workflow in
data/market_snapshots/<date>/ (sha256-checked against the collector's record):
  api_allIndices         Nifty 50, Bank Nifty, India VIX, sector indices, Nifty 500 breadth
  api_fiidiiTradeReact   provisional FII/FPI and DII cash-market activity (same date only)
  bhavcopy + nifty50list top movers by closing price (when the collector has archived them)
Sensex is a BSE index: it is shown only when a sourced figure is supplied in
data/closing_inputs/<date>.json ({"sensex": {"close", "change", "pct", "source": {name, url}}}).
Anything missing becomes AWAITING VERIFIED DATA. Output is a draft for the founder's approval:
nothing here publishes.
"""
import argparse
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import source_audit  # noqa: E402

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
SECTORS = [("NIFTY AUTO", "Auto"), ("NIFTY FMCG", "FMCG"), ("NIFTY IT", "IT"), ("NIFTY METAL", "Metal"),
           ("NIFTY PHARMA", "Pharma"), ("NIFTY REALTY", "Realty"), ("NIFTY ENERGY", "Energy"),
           ("NIFTY PSU BANK", "PSU Bank"), ("NIFTY PRIVATE BANK", "Private Bank"), ("NIFTY MEDIA", "Media"),
           ("NIFTY CONSUMER DURABLES", "Consumer Durables"), ("NIFTY OIL & GAS", "Oil & Gas"),
           ("NIFTY HEALTHCARE INDEX", "Healthcare"), ("NIFTY FINANCIAL SERVICES", "Financial Services"),
           ("NIFTY BANK", "Bank"), ("NIFTY CHEMICALS", "Chemicals"), ("NIFTY CEMENT", "Cement")]


class NotReady(Exception):
    pass


def _raw(root, day, name):
    snap = Path(root) / "data" / "market_snapshots" / day
    f = snap / f"{name}.json.gz"
    if not f.is_file():
        return None, None
    raw = gzip.decompress(f.read_bytes())
    sha = hashlib.sha256(raw).hexdigest()
    rec = json.loads((snap / "snapshot.json").read_text(encoding="utf-8")).get("raw", {}) if (snap / "snapshot.json").is_file() else {}
    if sha not in {v.get("sha256") for v in rec.values()}:
        raise NotReady(f"{f.name} is not the response the collector recorded")
    return raw, {"dataset": str(f.relative_to(root)).replace("\\", "/"), "sha256": sha}


def dataset(day, root=ROOT):
    d = dt.date.fromisoformat(day)
    stamp = d.strftime("%d-%b-%Y")
    raw, idx_src = _raw(root, day, "api_allIndices")
    if raw is None:
        raise NotReady(f"no NSE snapshot for {day} (the collector runs at 16:15 IST on trading days)")
    idx = json.loads(raw)
    if idx.get("timestamp") != f"{stamp} 15:30":
        raise NotReady(f"NSE index data is not the {day} close (timestamp {idx.get('timestamp')!r})")
    rows = {x["index"]: x for x in idx.get("data") or []}
    out = {"date": day, "dateLabel": f"{d.strftime('%A')}, {d.day} {d.strftime('%B %Y')}", "status": "closing data, 3:30 pm IST",
           "indices": {}, "sources": [], "sourceNames": ["NSE"], "missing": []}
    out["sources"].append(dict(idx_src, name="NSE India: all indices", url="https://www.nseindia.com/api/allIndices",
                               timestamp=idx.get("timestamp")))
    for name in ("NIFTY 50", "NIFTY BANK", "INDIA VIX"):
        x = rows.get(name)
        if x:
            out["indices"][name] = {"close": x["last"], "change": x["variation"], "pct": x["percentChange"], "source": "nse"}
        else:
            out["missing"].append(name)
    extra = Path(root) / "data" / "closing_inputs" / f"{day}.json"
    if extra.is_file():
        sx = json.loads(extra.read_text(encoding="utf-8")).get("sensex")
        if sx and sx.get("source", {}).get("url"):
            out["indices"]["SENSEX"] = {k: sx[k] for k in ("close", "change", "pct") if k in sx}
            out["sources"].append(dict(sx["source"], what="Sensex close"))
            out["sourceNames"].append(sx["source"]["name"].split(":")[0])
    if "SENSEX" not in out["indices"]:
        out["missing"].append("SENSEX (BSE index: needs a sourced figure in data/closing_inputs)")
    b = rows.get("NIFTY 500")
    if b:
        out["breadth"] = {"advances": b["advances"], "declines": b["declines"], "unchanged": b.get("unchanged", 0), "universe": "Nifty 500"}
    out["sectors"] = [{"name": label, "pct": rows[n]["percentChange"]} for n, label in SECTORS if n in rows]
    out["broad"] = {k: rows[k]["percentChange"] for k in ("NIFTY MIDCAP 100", "NIFTY SMALLCAP 100") if k in rows}

    fraw, fsrc = _raw(root, day, "api_fiidiiTradeReact")
    if fraw:
        flows = {r.get("category"): r for r in json.loads(fraw) if isinstance(r, dict) and r.get("date") == stamp}
        if "FII/FPI" in flows and "DII" in flows:
            out["flows"] = {"fii": flows["FII/FPI"]["netValue"], "dii": flows["DII"]["netValue"], "status": "provisional",
                            "fiiBuy": flows["FII/FPI"]["buyValue"], "fiiSell": flows["FII/FPI"]["sellValue"],
                            "diiBuy": flows["DII"]["buyValue"], "diiSell": flows["DII"]["sellValue"]}
            out["sources"].append(dict(fsrc, name="NSE India: FII/FPI and DII provisional cash-market activity",
                                       url="https://www.nseindia.com/api/fiidiiTradeReact"))
            out["flowSources"] = ["NSE"]
    if "flows" not in out:
        out["missing"].append("FII/DII (not published by NSE for this date yet)")

    out["movers"] = movers(root, day, out)
    if not out["movers"]:
        out["missing"].append("Top movers (NSE end-of-day stock file not archived for this date)")
    out["bottomLine"] = bottom_line(out)
    return out


def movers(root, day, out):
    """Top 3 gainers / losers of the Nifty 50 by closing price vs previous close (official EOD file)."""
    braw, bsrc = _raw(root, day, "bhavcopy")
    lraw, lsrc = _raw(root, day, "nifty50list")
    if not (braw and lraw):
        return None
    members = {r["Symbol"].strip() for r in csv.DictReader(io.StringIO(lraw.decode("utf-8-sig"))) if r.get("Symbol")}
    rows = []
    for r in csv.DictReader(io.StringIO(braw.decode("utf-8-sig"))):
        sym, series = (r.get("TckrSymb") or "").strip(), (r.get("SctySrs") or "").strip()
        if sym in members and series == "EQ" and (r.get("TradDt") or "").strip() == day:
            c, p = float(r["ClsPric"]), float(r["PrvsClsgPric"])
            if p > 0:
                rows.append({"name": sym, "close": c, "prev": p, "pct": round((c - p) / p * 100, 2)})
    if len(rows) < 40:
        return None
    rows.sort(key=lambda x: x["pct"], reverse=True)
    out["sources"] += [dict(bsrc, name="NSE India: capital-market bhavcopy (end of day)"), dict(lsrc, name="NSE India: Nifty 50 constituents")]
    return {"universe": "Nifty 50", "count": len(rows), "gainers": rows[:3], "losers": rows[::-1][:3]}


def bottom_line(d):
    """One sentence from the numbers only: direction, breadth and broader-market comparison."""
    n = (d.get("indices") or {}).get("NIFTY 50")
    if not n:
        return ""
    p = float(n["pct"])
    word = "rose" if p > 0 else "fell" if p < 0 else "ended flat"
    s = f"The Nifty 50 {word}{'' if p == 0 else f' {abs(p):.2f}%'}"
    b = d.get("breadth")
    if b:
        a, dcl = int(b["advances"]), int(b["declines"])
        s += f"; {dcl if dcl > a else a} of {a + dcl + int(b.get('unchanged') or 0)} Nifty 500 stocks {'declined' if dcl > a else 'advanced'}"
    sm = (d.get("broad") or {}).get("NIFTY SMALLCAP 100")
    if sm is not None and p != 0 and abs(sm) > abs(p) * 2 and (sm > 0) == (p > 0):
        s += f", and small caps {'fell' if sm < 0 else 'rose'} more ({sm:+.2f}%)"
    return s + "."


def article(d):
    """Draft article (Markdown) built only from verified numbers; drivers left for verified reporting."""
    ix = d["indices"]
    n50, bank, vix, sx = ix.get("NIFTY 50"), ix.get("NIFTY BANK"), ix.get("INDIA VIX"), ix.get("SENSEX")
    from closing_graphics import inr
    pct = lambda v: f"{abs(float(v)):.2f}%"
    dirw = lambda v, up="rose", dn="fell": up if float(v) > 0 else dn
    L = [f"# Sensex, Nifty today: Nifty 50 {dirw(n50['pct'], 'rises', 'falls')} {pct(n50['pct'])} to {inr(n50['close'])} | {d['dateLabel']}", ""]
    open_ = (f"The Nifty 50 {dirw(n50['pct'])} {inr(abs(float(n50['change'])))} points, or {pct(n50['pct'])}, to close at "
             f"{inr(n50['close'])} on {d['dateLabel']}, according to NSE closing data.")
    if sx:
        open_ += f" The Sensex {dirw(sx['pct'])} {pct(sx['pct'])} to {inr(sx['close'])}."
    if bank:
        open_ += f" Bank Nifty {dirw(bank['pct'], 'gained', 'lost')} {pct(bank['pct'])} to {inr(bank['close'])}."
    L += [open_, ""]
    b = d.get("breadth")
    if b:
        L += ["## Market breadth", f"Across the Nifty 500, {int(b['advances'])} stocks advanced and {int(b['declines'])} declined "
              f"({int(b.get('unchanged') or 0)} unchanged)." + (f" India VIX {dirw(vix['pct'])} {pct(vix['pct'])} to {inr(vix['close'])}." if vix else ""), ""]
    secs = sorted(d.get("sectors") or [], key=lambda s: float(s["pct"]), reverse=True)
    if len(secs) >= 6:
        f3 = ", ".join(f"{s['name']} ({float(s['pct']):+.2f}%)" for s in secs[:3])
        l3 = ", ".join(f"{s['name']} ({float(s['pct']):+.2f}%)" for s in secs[-3:])
        L += ["## Sectors", f"Strongest NSE sector indices: {f3}. Weakest: {l3}.", ""]
    m = d.get("movers")
    L += ["## Top movers (Nifty 50, closing prices)"]
    if m:
        L += ["Gainers: " + ", ".join(f"{r['name']} ₹{inr(r['close'])} ({r['pct']:+.2f}%)" for r in m["gainers"]) + ".",
              "Losers: " + ", ".join(f"{r['name']} ₹{inr(r['close'])} ({r['pct']:+.2f}%)" for r in m["losers"]) + ".", ""]
    else:
        L += ["*Awaiting verified data: NSE's end-of-day stock file for this date is not archived yet.*", ""]
    f = d.get("flows")
    L += ["## Institutional activity"]
    if f:
        L += [f"NSE's provisional data show foreign portfolio investors were net {'buyers' if float(f['fii']) > 0 else 'sellers'} of "
              f"₹{inr(abs(float(f['fii'])))} crore in the cash market and domestic institutions net {'buyers' if float(f['dii']) > 0 else 'sellers'} "
              f"of ₹{inr(abs(float(f['dii'])))} crore.", ""]
    else:
        L += ["*Awaiting verified data: NSE has not published FII/DII figures for this date yet.*", ""]
    L += ["## Why the market moved", "*EDITOR: add the day's drivers from named sources (with links) before approving. "
          "Do not publish this section without verified reporting.*", "",
          "## What to watch next session", "*EDITOR: add confirmed events only (RBI, results calendar, data releases, global cues).*", "",
          "---", "Sources: " + "; ".join(f"{s.get('name')} ({s.get('url') or s.get('dataset')})" for s in d["sources"])]
    return "\n".join(L) + "\n"


def make_drafts(day, out_root, root=ROOT):
    import closing_graphics
    d = dataset(day, root)
    out = Path(out_root) / day
    files = closing_graphics.render_all(d, str(out))
    (out / "article.md").write_text(article(d), encoding="utf-8")
    rec = {"date": day, "generatedAt": dt.datetime.now(IST).replace(microsecond=0).isoformat(), "status": "DRAFT — awaiting founder approval",
           "missing": d["missing"], "sources": d["sources"], "data": {k: d.get(k) for k in ("indices", "breadth", "sectors", "movers", "flows", "bottomLine")}}
    (out / "sources.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    return out, files, d["missing"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.datetime.now(IST).date().isoformat())
    ap.add_argument("--out", default=str(ROOT / "drafts" / "closing"))
    a = ap.parse_args(argv)
    try:
        out, files, missing = make_drafts(a.date, a.out)
    except NotReady as ex:
        print(f"closing drafts not prepared: {ex}")
        return 2
    print(f"drafts in {out}: {', '.join(Path(f).name for f in files)}, article.md, sources.json")
    for m in missing:
        print("  awaiting:", m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
