"""Daily market-close drafts: verified closing dataset -> four graphics + draft article + source record.

    python3 -m pipeline.closing --date 2026-10-23 [--out drafts/closing]

Data comes only from the raw NSE responses archived by the collector workflow in
data/market_snapshots/<date>/ (sha256-checked against the collector's record):
  api_allIndices         Nifty 50, Bank Nifty, India VIX, sector indices, Nifty 500 breadth
  api_fiidiiTradeReact   provisional FII/FPI and DII cash-market activity (same date only)
  bhavcopy + nifty50list top movers by closing price (when the collector has archived them)
  bse_sensex_arch        Sensex close, change and % from BSE's own daily index archive
If BSE's file is missing, a named secondary source may be supplied in data/closing_inputs/<date>.json
({"sensex": {"close", "change", "pct", "source": {name, url}}}); otherwise Sensex is AWAITING.
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
    sraw, ssrc = _raw(root, day, "bse_sensex_arch")
    if sraw:
        t = next((r for r in json.loads(sraw).get("Table") or [] if str(r.get("tdate", ""))[:10] == day
                  and str(r.get("I_name", "")).strip() == "SENSEX"), None)
        if t and t.get("I_close") is not None:
            out["indices"]["SENSEX"] = {"close": t["I_close"], "change": t["Chg"], "pct": round(float(t["ChgPer"]), 2), "source": "bse"}
            out["sources"].append(dict(ssrc, name="BSE India: Sensex daily index archive",
                                       url="https://api.bseindia.com/BseIndiaAPI/api/IndexArchDaily/w"))
            out["sourceNames"].append("BSE")
    extra = Path(root) / "data" / "closing_inputs" / f"{day}.json"
    if extra.is_file():
        sx = json.loads(extra.read_text(encoding="utf-8")).get("sensex")
        if sx and sx.get("source", {}).get("url") and "SENSEX" not in out["indices"]:  # fallback: named source
            out["indices"]["SENSEX"] = {k: sx[k] for k in ("close", "change", "pct") if k in sx}
            out["indices"]["SENSEX"]["source"] = "secondary"
            out["indices"]["SENSEX"]["sourceInfo"] = sx["source"]
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
        out["missing"].append("FII/DII (same-date figures unavailable in the archived NSE response)")

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
        L += ["*Awaiting verified data: Same-date FII/DII figures are unavailable in the archived NSE response.*", ""]
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


# ------------------------------------------------------------------ approved draft -> pipeline job
CAPS = [("n50", "NIFTY 50", "Nifty 50"), ("next50", "NIFTY NEXT 50", "Nifty Next 50"),
        ("mid", "NIFTY MIDCAP 100", "Nifty Midcap 100"), ("small", "NIFTY SMALLCAP 100", "Nifty Smallcap 100")]


def to_job(day, editor=None, root=ROOT, now=None):
    """Build the publishable job for an approved closing draft. Every number is a figure whose evidence
    is a line rebuilt from the archived exchange files. editor (optional, from the founder/research):
    {"drivers": [paragraphs], "watch": [items], "sources": [{id, name, url, published}], "figures": [...]}"""
    from closing_graphics import inr
    d = dataset(day, root)
    D = dt.date.fromisoformat(day)
    stamp = D.strftime("%d-%b-%Y")
    nse = next(s for s in d["sources"] if s["name"].startswith("NSE India: all indices"))
    nse_src = {"id": "nse", "name": "NSE India: all indices (closing data)", "url": nse["url"], "published": f"{day}T15:30:00+05:30",
               "dataset": nse["dataset"], "sha256": nse["sha256"]}
    lines = {ln.split(":", 1)[0]: ln for ln in source_audit.dataset_lines(nse_src, root)}
    idx = {x["index"]: x for x in json.loads(_raw(root, day, "api_allIndices")[0])["data"]}
    sources, figs = [nse_src], []

    def add(k, name, label):
        x, ev = idx[name], lines[name]
        figs.extend([{"id": f"nse_{k}", "label": f"{label} close", "value": str(x["last"]), "change": str(x["variation"]),
                      "source": "nse", "evidence": ev, "as_of": day, **({"key": True} if k == "n50" else {})},
                     {"id": f"nse_{k}_pct", "label": f"{label} change %", "value": str(x["percentChange"]), "source": "nse", "evidence": ev, "as_of": day}])
    for k, n, l in [("bank", "NIFTY BANK", "Nifty Bank"), ("vix", "INDIA VIX", "India VIX")] + CAPS:
        if n in idx:
            add(k, n, l)
    sec_ids = []
    for n, label in SECTORS:
        if n in idx and n != "NIFTY BANK":
            k = "s_" + "".join(c for c in label.lower() if c.isalnum())
            add(k, n, label)
            sec_ids.append((k, label))
    b = idx.get("NIFTY 500")
    if b:
        for k in ("advances", "declines", "unchanged"):
            figs.append({"id": f"nse_n500_{k}", "label": f"Nifty 500 stocks: {k}", "value": str(b[k]), "source": "nse",
                         "evidence": lines["NIFTY 500"], "as_of": day})
    sx = d["indices"].get("SENSEX")
    if sx and sx.get("source") == "bse":
        s_ = next(s for s in d["sources"] if s["name"].startswith("BSE India"))
        bse = {"id": "bse", "name": "BSE India: Sensex daily index archive", "url": s_["url"], "published": f"{day}T15:30:00+05:30",
               "dataset": s_["dataset"], "sha256": s_["sha256"]}
        sources.append(bse)
        ev = source_audit.dataset_lines(bse, root)[0]
        figs += [{"id": "bse_sx", "label": "Sensex close", "value": str(sx["close"]), "change": str(sx["change"]), "source": "bse", "evidence": ev, "as_of": day},
                 {"id": "bse_sx_pct", "label": "Sensex change %", "value": f"{float(sx['pct']):.2f}", "source": "bse", "evidence": ev, "as_of": day}]
    fl = d.get("flows")
    if fl:
        s_ = next(s for s in d["sources"] if "FII" in s["name"])
        nsef = {"id": "nsef", "name": "NSE India: FII/FPI and DII provisional cash-market activity", "url": s_["url"],
                "published": f"{day}T18:00:00+05:30", "dataset": s_["dataset"], "sha256": s_["sha256"]}
        sources.append(nsef)
        fls = {ln.split(" ", 1)[0]: ln for ln in source_audit.dataset_lines(nsef, root)}
        for who, cat, net, buy, sell in (("fii", "FII/FPI", fl["fii"], fl["fiiBuy"], fl["fiiSell"]), ("dii", "DII", fl["dii"], fl["diiBuy"], fl["diiSell"])):
            for k, v in (("net", net), ("buy", buy), ("sell", sell)):
                figs.append({"id": f"nse_{who}_{k}", "label": f"{cat} {k} value, cash market", "value": str(v), "source": "nsef", "evidence": fls[cat], "as_of": day})
    mv = d.get("movers")
    mover_specs = {"gainers": [], "losers": []}
    if mv:
        s_ = next(s for s in d["sources"] if "bhavcopy" in s["name"])
        bh = {"id": "bhav", "name": "NSE India: capital-market bhavcopy (end of day)",
              "url": f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{day.replace('-', '')}_F_0000.csv.zip",
              "published": f"{day}T18:00:00+05:30", "dataset": s_["dataset"], "sha256": s_["sha256"]}
        sources.append(bh)
        bl = {ln.split(" EQ ", 1)[0]: ln for ln in source_audit.dataset_lines(bh, root)}
        for side in ("gainers", "losers"):
            for r in mv[side]:
                k = "st_" + "".join(c for c in r["name"].lower() if c.isalnum())
                ev = bl[r["name"]]
                figs += [{"id": k, "label": f"{r['name']} close", "value": f"{r['close']:.2f}", "source": "bhav", "evidence": ev, "as_of": day},
                         {"id": k + "_prev", "label": f"{r['name']} previous close", "value": f"{r['prev']:.2f}", "source": "bhav", "evidence": ev, "as_of": day}]
                mover_specs[side].append({"id": k, "label": r["name"], "prev": k + "_prev"})
    editor = editor or {}
    for s_ in editor.get("sources") or []:
        sources.append(s_)
    figs += editor.get("figures") or []

    n50 = d["indices"]["NIFTY 50"]
    p50 = float(n50["pct"])
    word = "rises" if p50 > 0 else "falls" if p50 < 0 else "flat at"
    title = f"Sensex, Nifty today: Nifty 50 {word} {abs(p50):.2f}% to {inr(n50['close'])}"
    if sx:
        title += f", Sensex {'up' if float(sx['pct']) > 0 else 'down'} {abs(float(sx['pct'])):.2f}%"
    title += f" | {D.day} {D.strftime('%B %Y')}"
    # Prose stays short: the structured report above already shows every table, so the body only
    # summarises the close and adds the verified drivers (no duplicated figure lists).
    body = [_body_from_article(article(d))[0]]
    if editor.get("drivers"):
        body += ["Why the market moved | " + editor["drivers"][0]] + list(editor["drivers"][1:])
    body.append("More data | Scroll up for the full NSE index scoreboard, sector heatmap, Nifty 500 breadth, top gainers and "
                "losers and FII/DII flows. For more, see the Nifty 50 page and the FII/DII data page on TotalMarket.")
    spec = lambda k, label: {"id": f"nse_{k}", "label": label, "pct": f"nse_{k}_pct"}
    idx_specs = [spec("n50", "Nifty 50")] + ([{"id": "bse_sx", "label": "Sensex", "pct": "bse_sx_pct"}] if sx and sx.get("source") == "bse" else []) \
        + [spec("bank", "Nifty Bank"), spec("vix", "India VIX")]
    figs_by_id = {f["id"] for f in figs}
    figs.insert(0, {"id": "nse_n50", "label": "Nifty 50 close", "value": str(idx["NIFTY 50"]["last"]), "change": str(idx["NIFTY 50"]["variation"]),
                    "source": "nse", "evidence": lines["NIFTY 50"], "as_of": day, "key": True})
    figs.insert(1, {"id": "nse_n50_pct", "label": "Nifty 50 change %", "value": str(idx["NIFTY 50"]["percentChange"]), "source": "nse",
                    "evidence": lines["NIFTY 50"], "as_of": day})
    figs = list({f["id"]: f for f in figs}.values())
    pub = (now or dt.datetime.now(IST)).replace(microsecond=0)
    items = [{"label": "NIFTY 50", "value": str(n50["close"]), "change": str(n50["change"]), "pct": f"{n50['pct']}%", "figures": ["nse_n50", "nse_n50_pct"]}]
    if sx and sx.get("source") == "bse":
        items.append({"label": "SENSEX", "value": str(sx["close"]), "change": str(sx["change"]), "pct": f"{float(sx['pct']):.2f}%", "figures": ["bse_sx", "bse_sx_pct"]})
    for k, n, lab in (("bank", "NIFTY BANK", "NIFTY BANK"), ("vix", "INDIA VIX", "INDIA VIX")):
        if n in idx:
            items.append({"label": lab, "value": str(idx[n]["last"]), "change": str(idx[n]["variation"]), "pct": f"{idx[n]['percentChange']}%", "figures": [f"nse_{k}", f"nse_{k}_pct"]})
    if b:
        items += [{"label": f"Nifty 500 {k}", "value": str(b[k]), "role": k, "figures": [f"nse_n500_{k}"]} for k in ("advances", "declines", "unchanged")]
    job = {
        "slug": f"{day}-market-close-sensex-nifty",
        "collection": {"sources": sources, "figures": figs, "examples": []},
        "graphic": {"headline": title, "coverHeadline": "MARKET CLOSE", "flags": ["IN"], "coverDate": day, "symbol": "candles",
                    "chart": {"type": "market_close", "title": "Indian markets · close", "asOf": f"Close, {D.strftime('%a')} {D.day} {D.strftime('%b %Y')}",
                              "dateLabel": d["dateLabel"], "summary": d["bottomLine"], "source": ", ".join(dict.fromkeys(d["sourceNames"])),
                              "breadthUniverse": "Nifty 500", "items": items}},
        "article": {
            "title": title,
            "dek": f"The Nifty 50 closed at {inr(n50['close'])}. NSE index scoreboard, sector heatmap, breadth, top movers and FII/DII flows.",
            "category": "markets", "lead": True, "readMins": 3, "reportType": "weekly_market",
            "visualSpec": {
                "dateLabel": f"Market close · {d['dateLabel']}", "outlookTitle": "What to watch next session",
                "indices": idx_specs,
                "caps": [{"id": f"nse_{k}_pct", "label": l} for k, n, l in CAPS if n in idx],
                "sectors": [{"id": f"nse_{k}_pct", "label": l} for k, l in sec_ids],
                "gainers": mover_specs["gainers"], "losers": mover_specs["losers"], "moversIndex": "Nifty 50",
                "global": [],
                **({"breadth": {"advances": "nse_n500_advances", "declines": "nse_n500_declines", "unchanged": "nse_n500_unchanged"},
                    "breadthExchange": "NSE, Nifty 500 stocks"} if b else {}),
                **({"fiiDii": {"fiiNet": "nse_fii_net", "diiNet": "nse_dii_net", "fiiBuy": "nse_fii_buy", "fiiSell": "nse_fii_sell",
                               "diiBuy": "nse_dii_buy", "diiSell": "nse_dii_sell"},
                    "fiiDiiNote": "NSE provisional figures for the cash market, in ₹ crore."} if fl else {}),
            },
            "reportTakeaways": [d["bottomLine"]] if d["bottomLine"] else [],
            "reportWatch": editor.get("watch") or [],
            "body": body,
            "indiaImpact": "Breadth, sector moves and institutional flows show how widely the day's move spread beyond the headline indices.",
            **seo(d, D, sx, inr),
            "sources": [{"name": s_["name"], "url": s_["url"]} for s_ in sources],
            "publishedAt": pub.isoformat(), "edition": f"{day}-close", "editionLabel": f"{D.strftime('%a')} {D.day} {D.strftime('%b')} · Market close",
            "status": "new",
        },
    }
    return job


def apply_data(day, root=ROOT):
    """Update the site's market data files from the verified closing dataset (official NSE/BSE files):
    meta.json history + ticker cards for Nifty 50, Sensex, Bank Nifty, India VIX, and fii_dii.json."""
    d = dataset(day, root)
    D = dt.date.fromisoformat(day)
    mp = Path(root) / "data" / "meta.json"
    meta = json.loads(mp.read_text(encoding="utf-8"))
    if max((c.get("asOf", "") for c in meta.get("ticker", []) if c.get("label") in ("Nifty 50", "Bank Nifty")), default="") > day:
        raise NotReady("refusing to replace newer market cards with an older session")
    hist = meta.setdefault("history", {})
    names = {"NIFTY 50": "Nifty 50", "SENSEX": "Sensex", "NIFTY BANK": "Bank Nifty", "INDIA VIX": "India VIX"}
    src = {"nse": {"name": "NSE India: index closing data", "url": "https://www.nseindia.com/market-data/live-market-indices"},
           "bse": {"name": "BSE India: Sensex daily index archive", "url": "https://www.bseindia.com/indices/IndexArchiveData.html"}}
    changed = []
    for key, label in names.items():
        x = d["indices"].get(key)
        if not x:
            continue
        s_ = x.get("source") or "nse"
        if label != "India VIX":
            rows = [r for r in hist.get(label, []) if r.get("d") != day]
            rows.append({"d": day, "v": round(float(x["close"]), 2), "s": x.get("sourceInfo", {}).get("name") or ("BSE" if s_ == "bse" else "NSE")})
            hist[label] = sorted(rows, key=lambda r: r["d"])[-30:]
        card = {"label": label, "value": f"{float(x['close']):,.2f}", "change": f"{float(x['pct']):+.2f}%", "asOf": day, "kind": "close",
                "asOfText": f"{D.day} {D.strftime('%b')} close", "source": x.get("sourceInfo") or src["bse" if s_ == "bse" else "nse"]}
        t = meta.setdefault("ticker", [])
        k = next((i for i, c in enumerate(t) if c.get("label") == label), None)
        if k is None:
            t.append(card)
        else:
            t[k] = card
        changed.append(label)
    meta["tickerAsOf"] = f"{D.day} {D.strftime('%b')} close"
    meta["updatedAt"] = dt.datetime.now(IST).replace(microsecond=0).isoformat()
    mp.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    f = d.get("flows")
    if f:
        fp = Path(root) / "data" / "fii_dii.json"
        fd = json.loads(fp.read_text(encoding="utf-8"))
        n = lambda v: round(float(v), 2)
        row = {"date": day, "fii": {"buy": n(f["fiiBuy"]), "sell": n(f["fiiSell"]), "net": n(f["fii"])},
               "dii": {"buy": n(f["diiBuy"]), "sell": n(f["diiSell"]), "net": n(f["dii"])}}
        update_flow_rows(fd, row)
        fd["days"][0]["source"] = {"name": "NSE India: FII/FPI and DII provisional cash-market activity", "url": "https://www.nseindia.com/reports/fii-dii"}
        fd["source"] = {"name": "NSE India: FII/FPI and DII provisional cash-market activity", "url": "https://www.nseindia.com/reports/fii-dii"}
        fd["updatedAt"] = dt.datetime.now(IST).replace(microsecond=0).isoformat()
        fp.write_text(json.dumps(fd, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        changed.append("FII/DII")
    gp = Path(root) / "data" / "global.json"
    if gp.is_file():
        g = json.loads(gp.read_text(encoding="utf-8"))
        for region in g.get("regions", []):
            if region.get("region") != "India":
                continue
            for row in region.get("rows", []):
                key = next((k for k, v in names.items() if v == row.get("name")), None)
                x = d["indices"].get(key)
                if not x:
                    continue
                row.update(value=f"{float(x['close']):,.2f}", change=f"{float(x['change']):+.2f}",
                           pct=f"{float(x['pct']):+.2f}", asOf=f"{D.strftime('%a')} {D.day} {D.strftime('%b')}, close",
                           date=day, type="close", source=x.get("sourceInfo") or src.get(x.get("source"), src["nse"]))
        # Foreign rows retain their own original dates; this is not a global refresh.
        g["indiaUpdatedAt"] = day + "T15:30:00+05:30"
        gp.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return changed


def update_flow_rows(fd, row):
    """Idempotent daily upsert; preserve supplied MTD totals and apply correction deltas."""
    day = row["date"]
    old = next((x for x in fd.get("days", []) if x.get("date") == day), None)
    fd["days"] = sorted([x for x in fd.get("days", []) if x.get("date") != day] + [row],
                        key=lambda x: x["date"], reverse=True)
    D = dt.date.fromisoformat(fd["days"][0]["date"])
    mo = fd.get("month") or {}
    prefix = D.strftime("%B %Y")
    if day[:7] != D.isoformat()[:7]:
        return
    if str(mo.get("label", "")).startswith(prefix):
        for who in ("fii", "dii"):
            for k in ("buy", "sell", "net"):
                mo[who][k] = round(float(mo[who][k]) + row[who][k] - (old[who][k] if old else 0), 2)
    else:
        # Label an incomplete stored history as such instead of inventing an MTD total.
        mo = {who: {k: round(sum(x[who][k] for x in fd["days"] if x["date"][:7] == day[:7]), 2)
                    for k in ("buy", "sell", "net")} for who in ("fii", "dii")}
        mo["partial"] = True
    mo["label"] = f"{prefix} (to {D.day} {D.strftime('%b')})" + (" · available sessions only" if mo.get("partial") else "")
    fd["month"] = mo


def seo(d, D, sx, inr):
    """Search metadata: dated search-style title, a description with the verified closes, real search phrases
    as tags (meta keywords, news_keywords, JSON-LD), descriptive image alt text and a Hindi edition."""
    n50 = d["indices"]["NIFTY 50"]
    p = float(n50["pct"])
    move = "Higher" if p > 0 else "Lower" if p < 0 else "Flat"
    day_txt, day_short = f"{D.day} {D.strftime('%B %Y')}", f"{D.day} {D.strftime('%b %Y')}"
    desc = f"Nifty 50 closed at {inr(n50['close'])} ({p:+.2f}%)"
    if sx:
        desc += f", Sensex at {inr(sx['close'])} ({float(sx['pct']):+.2f}%)"
    desc += f" on {day_short}. Top gainers and losers, sector heatmap, breadth and FII/DII data."
    mon = D.strftime("%B").lower()
    tags = ["stock market today", "share market today", "Sensex today", "Nifty today", "Nifty 50 closing",
            "Bank Nifty today", "top gainers and losers today", "FII DII data today", "sector performance today",
            f"stock market {D.day} {mon} {D.year}"]
    alt = f"Market close graphic for {day_txt}: Nifty 50 {inr(n50['close'])} ({p:+.2f}%)" + (f", Sensex {inr(sx['close'])}" if sx else "")
    return {"seoTitle": f"Stock Market Today {day_short}: Sensex, Nifty Close {move}"[:70],
            "seoDescription": desc[:160], "tags": tags, "coverAlt": alt, "hi": hindi_edition(d, D, sx, inr)}


HI_MONTHS = ["जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]


def hindi_edition(d, D, sx, inr):
    """Hindi edition with exactly the same verified numbers (Hindi search: शेयर बाजार आज, सेंसेक्स निफ्टी)."""
    n50, bank = d["indices"]["NIFTY 50"], d["indices"].get("NIFTY BANK")
    p = float(n50["pct"])
    dt_hi = f"{D.day} {HI_MONTHS[D.month - 1]} {D.year}"
    v = "चढ़कर" if p > 0 else "गिरकर" if p < 0 else "स्थिर रहकर"
    title = f"शेयर बाजार आज: निफ्टी 50 {abs(p):.2f}% {v} {inr(n50['close'])} पर बंद"
    if sx:
        title += f", सेंसेक्स {abs(float(sx['pct'])):.2f}% {'ऊपर' if float(sx['pct']) > 0 else 'नीचे'}"
    title += f" | {dt_hi}"
    body = [f"NSE के क्लोजिंग आंकड़ों के मुताबिक {dt_hi} को निफ्टी 50 {inr(abs(float(n50['change'])))} अंक यानी {abs(p):.2f}% {v} "
            f"{inr(n50['close'])} पर बंद हुआ।" + (f" सेंसेक्स {inr(sx['close'])} पर बंद हुआ ({float(sx['pct']):+.2f}%)।" if sx else "")
            + (f" बैंक निफ्टी {inr(bank['close'])} पर रहा ({float(bank['pct']):+.2f}%)।" if bank else "")]
    b = d.get("breadth")
    if b:
        body.append(f"बाजार की चौड़ाई | निफ्टी 500 में {int(b['advances'])} शेयर चढ़े और {int(b['declines'])} गिरे।")
    f = d.get("flows")
    if f:
        body.append(f"संस्थागत निवेश | NSE के अस्थायी आंकड़ों के मुताबिक FII/FPI का नेट {'खरीद' if float(f['fii']) > 0 else 'बिकवाली'} "
                    f"₹{inr(abs(float(f['fii'])))} करोड़ और DII का नेट {'खरीद' if float(f['dii']) > 0 else 'बिकवाली'} ₹{inr(abs(float(f['dii'])))} करोड़ रहा।")
    body.append("पूरी जानकारी | सेक्टर हीटमैप, टॉप गेनर्स-लूजर्स और FII/DII के पूरे आंकड़े इसी पेज पर ऊपर रिपोर्ट में देखें।")
    return {"title": title, "dek": f"निफ्टी 50 {inr(n50['close'])} पर बंद। सेक्टर, बाजार की चौड़ाई, टॉप शेयर और FII/DII आंकड़े।",
            "body": body, "indiaImpact": "सेक्टर और बाजार की चौड़ाई बताती है कि गिरावट या तेजी कितनी व्यापक थी।",
            "seoTitle": f"शेयर बाजार आज {dt_hi}: सेंसेक्स, निफ्टी क्लोजिंग"[:70],
            "seoDescription": f"{dt_hi} को निफ्टी 50 {inr(n50['close'])} पर बंद ({p:+.2f}%)। टॉप गेनर्स-लूजर्स, सेक्टर और FII/DII आंकड़े।"[:160],
            "tags": ["शेयर बाजार आज", "सेंसेक्स आज", "निफ्टी आज", "स्टॉक मार्केट न्यूज़", "FII DII डेटा", "टॉप गेनर्स लूजर्स"]}


def _body_from_article(md):
    """Prose paragraphs from the draft article, without the title, editor slots or source list."""
    out, head = [], None
    for ln in md.splitlines():
        if ln.startswith("# ") or ln.startswith("---") or ln.startswith("Sources:") or not ln.strip():
            continue
        if ln.startswith("## "):
            head = ln[3:].strip()
            continue
        if ln.startswith("*"):
            continue  # editor / awaiting notes never reach the article
        out.append(f"{head} | {ln}" if head else ln)
        head = None
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.datetime.now(IST).date().isoformat())
    ap.add_argument("--out", default=str(ROOT / "drafts" / "closing"))
    ap.add_argument("--job", action="store_true", help="write the publishable job for an APPROVED draft to pipeline/inbox")
    ap.add_argument("--editor", help="JSON file with the approved drivers / watch list and their sources")
    ap.add_argument("--apply-data", action="store_true", help="update data/meta.json and data/fii_dii.json from the verified close")
    a = ap.parse_args(argv)
    ap_data = "--apply-data" in (argv or sys.argv[1:])
    if ap_data:
        print("updated:", ", ".join(apply_data(a.date)))
        if not a.job:
            return 0
    if a.job:
        editor = json.loads(Path(a.editor).read_text(encoding="utf-8")) if a.editor else None
        job = to_job(a.date, editor)
        out = ROOT / "pipeline" / "inbox" / f"{job['slug']}.json"
        out.write_text(json.dumps(job, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"approved closing job written to {out}")
        return 0
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
