"""Prepare the 19–23 Oct 2026 weekly review from sourced closes plus NSE exchange data.

Exchange figures are read from the raw NSE responses the collector workflow archived in
data/market_snapshots/2026-10-23/ (sha256-recorded). Each figure's evidence is the line
source_audit rebuilds from those raw bytes, so the pipeline can re-check every number.
The pipeline, not this script, decides whether the story can be published.
"""
import datetime as dt
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
from pipeline import source_audit  # noqa: E402
from pipeline.examples.make_v2_dryrun_jobs import JOBS  # noqa: E402

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
DAY = "data/market_snapshots/2026-10-23"
base = JOBS[0]


def dataset_source(sid, name, api, published):
    rel = f"{DAY}/{api}.json.gz"
    raw = gzip.decompress((root / rel).read_bytes())
    return {"id": sid, "name": name, "url": "https://www.nseindia.com/" + api.replace("_", "/", 1),
            "published": published, "dataset": rel, "sha256": hashlib.sha256(raw).hexdigest()}, json.loads(raw)


nse, idx_raw = dataset_source("nse", "NSE India: all indices (closing data, 23 Oct 2026, 3:30 pm)",
                              "api_allIndices", "2026-10-23T15:30:00+05:30")
nsef, flow_raw = dataset_source("nsef", "NSE India: FII/FPI and DII provisional cash-market activity, 23 Oct 2026",
                                "api_fiidiiTradeReact", "2026-10-23T18:00:00+05:30")
lines = {ln.split(":", 1)[0]: ln for ln in source_audit.dataset_lines(nse, root)}
rows = {x["index"]: x for x in idx_raw["data"]}
if idx_raw.get("timestamp") != "23-Oct-2026 15:30":
    raise SystemExit("NSE snapshot is not the 23 Oct close; refusing to prepare")

# (key, NSE index name, display label)
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

figures = []


def add_index(key, name, label):
    x, ev = rows[name], lines[name]
    figures.extend([
        {"id": f"nse_{key}", "label": f"{label} close", "value": str(x["last"]), "change": str(x["variation"]),
         "source": "nse", "evidence": ev, "as_of": "2026-10-23"},
        {"id": f"nse_{key}_pct", "label": f"{label} change %", "value": str(x["percentChange"]),
         "source": "nse", "evidence": ev, "as_of": "2026-10-23"},
        {"id": f"nse_{key}_wk", "label": f"{label} close a week earlier", "value": str(x["oneWeekAgoVal"]),
         "source": "nse", "evidence": ev, "as_of": "2026-10-16", "historical": True}])


for k, n, l in INDEXES + SECTORS:
    add_index(k, n, l)
b = rows["NIFTY 500"]
for k in ("advances", "declines", "unchanged"):
    figures.append({"id": f"nse_n500_{k}", "label": f"Nifty 500 stocks: {k}", "value": str(b[k]),
                    "source": "nse", "evidence": lines["NIFTY 500"], "as_of": "2026-10-23"})
flow_lines = {ln.split(" ", 1)[0]: ln for ln in source_audit.dataset_lines(nsef, root)}
for who, cat in (("fii", "FII/FPI"), ("dii", "DII")):
    x = next(r for r in flow_raw if r["category"] == cat)
    if x["date"] != "23-Oct-2026":
        raise SystemExit("flow data is not for 23 Oct")
    for k, f in (("Net", "netValue"), ("Buy", "buyValue"), ("Sell", "sellValue")):
        figures.append({"id": f"nse_{who}_{k.lower()}", "label": f"{cat} {k.lower()} value, cash market",
                        "value": x[f], "source": "nsef", "evidence": flow_lines[cat], "as_of": "2026-10-23"})

idx_spec = lambda k, label, kpi=True: {"id": f"nse_{k}", "label": label, "pct": f"nse_{k}_pct", "weekAgo": f"nse_{k}_wk", "kpi": kpi}
pct_spec = lambda k, label: {"id": f"nse_{k}_pct", "label": label, "close": f"nse_{k}", "weekAgo": f"nse_{k}_wk"}

article = {
    "title": "Friday Complete Market Report: Nifty 22,600, Sensex 73,123.83 | 23 October 2026",
    "dek": "The Nifty 50 lost 2.36% this week while mid and small caps fell much harder. NSE sector heatmap, breadth and institutional flows inside.",
    "category": "markets", "lead": True, "readMins": 3,
    "reportType": "weekly_market",
    # Declarative slots: only verified figure IDs are rendered; week % is recomputed from two verified closes.
    "visualSpec": {
        "dateLabel": "Week of 19–23 October 2026 · Friday close",
        "weekLabel": "Change from the close on Fri 16 Oct to Fri 23 Oct (NSE)",
        "indices": [idx_spec("n50", "Nifty 50"),
                    {"id": "sensex", "label": "Sensex"},
                    idx_spec("bank", "Nifty Bank"), idx_spec("n500", "Nifty 500"),
                    idx_spec("vix", "India VIX")],
        "caps": [pct_spec("n50", "Nifty 50"), pct_spec("next50", "Nifty Next 50"),
                 pct_spec("mid", "Nifty Midcap 100"), pct_spec("small", "Nifty Smallcap 100")],
        "sectors": [pct_spec(k, l) for k, _, l in SECTORS],
        "global": [], "gainers": [], "losers": [],
        "breadth": {"advances": "nse_n500_advances", "declines": "nse_n500_declines", "unchanged": "nse_n500_unchanged"},
        "breadthExchange": "NSE, Nifty 500 stocks on Friday",
        "fiiDii": {"fiiNet": "nse_fii_net", "diiNet": "nse_dii_net", "fiiBuy": "nse_fii_buy", "fiiSell": "nse_fii_sell",
                   "diiBuy": "nse_dii_buy", "diiSell": "nse_dii_sell"},
        "fiiDiiNote": "NSE provisional figures for the cash market on Friday, in ₹ crore.",
    },
    "reportTakeaways": [
        "The Nifty 50 ended the week 2.36% lower; the Midcap 100 lost 5.63% and the Smallcap 100 7.27%.",
        "Only IT, among the NSE sector indices shown, gained over the week (+0.22%).",
        "Foreign portfolio investors and domestic institutions were both net buyers in Friday's cash market.",
    ],
    "reportWatch": ["Crude oil and the rupee", "Second-quarter earnings from large companies",
                    "Whether institutional buying continues", "India VIX, which rose 6.32% on Friday"],
    "body": [
        "What moved | The Nifty 50 closed the week at 22,600.00, down 2.36% from the previous Friday's 23,146.15, and fell 0.39% on Friday itself. The damage was far worse below the top 50 stocks: the Nifty Next 50 lost 4.58% over the week, the Midcap 100 5.63% and the Smallcap 100 7.27%.",
        "Breadth | On Friday 450 stocks in the Nifty 500 fell and 50 rose, according to NSE. India VIX, which measures the volatility traders expect, rose 6.32% to 16.76.",
        "Sectors | Every sector index in the heatmap fell on Friday. Over the week consumer durables (−6.42%), metal (−5.40%), media (−5.15%) and realty (−5.04%) fell most; IT edged up 0.22%.",
        "Flows | NSE's provisional data show foreign portfolio investors bought a net ₹887.65 crore of shares on Friday and domestic institutions a net ₹3,235.36 crore, even as prices fell.",
        "Why it mattered | Reuters linked the week's losses to surging oil prices amid Middle East tensions, which raise concerns about inflation, company margins and the rupee.",
    ],
    "indiaImpact": "Losses were concentrated in mid and small caps, so many portfolios fell more than the Nifty 50 suggests. Check breadth and sector moves, not just the headline indices.",
    "seoTitle": "Friday Indian Stock Market Report: 23 October 2026 | TotalMarket",
    "seoDescription": "Week to 23 Oct 2026: Nifty 50 down 2.36%, Smallcap 100 down 7.27%. NSE sector heatmap, Nifty 500 breadth and FII/DII flows.",
    "changeNote": "Updated on 23 Oct, 11:55 pm IST: added NSE index, sector, breadth and FII/DII data, week-on-week changes and a shorter analysis.",
    "updatedAt": dt.datetime.now(IST).replace(microsecond=0).isoformat(),
    "sources": [{"name": s["name"], "url": s["url"]} for s in base["collection"]["sources"]] + [
        {"name": nse["name"], "url": nse["url"]},
        {"name": nsef["name"], "url": nsef["url"]},
        {"name": "Reuters: Surging oil prices drag Indian shares to weekly losses", "url": "https://www.reuters.com/world/india/indian-shares-seen-opening-higher-after-3-session-drop-oil-surge-clouds-outlook-2026-10-23/"},
        {"name": "Moneycontrol: Friday close and broader markets", "url": "https://www.moneycontrol.com/news/business/markets/taking-stock-markets-recover-from-day-s-lows-but-sell-off-extends-to-4th-day-nifty-at-22-600-14058497.html"},
    ],
    "publishedAt": "2026-10-23T19:00:00+05:30",
    "edition": "2026-10-23-weekly", "editionLabel": "Fri 23 Oct · Complete market report",
    "status": "new",
}

# Every article citation must be registered in the collection before stage 4.
job_collection = json.loads(json.dumps(base["collection"]))
job_collection["sources"] += [nse, nsef]
existing_urls = {s["url"] for s in job_collection["sources"]}
for source in article["sources"]:
    if source["url"] not in existing_urls:
        job_collection["sources"].append({"id": "report_extra_" + str(len(existing_urls) + 1), "name": source["name"],
                                          "url": source["url"], "published": "2026-10-23T19:00:00+05:30"})
        existing_urls.add(source["url"])
# Publisher percentages whose quotes could not be found are dropped; NSE now supplies those numbers.
job_collection["figures"] = [f for f in job_collection["figures"] if f["id"] not in {"sensex_pct", "nifty_pct", "mid", "small", "realty", "nifty"}]
job_collection["figures"] += figures

graphic = dict(base["graphic"])
graphic["headline"] = article["title"]
graphic["coverHeadline"] = "FRIDAY MARKET REPORT"
graphic["coverDate"] = "2026-10-23"
graphic["stat"] = "22,600"
graphic["chart"] = dict(graphic["chart"], source="ChiniMandi, NSE")
graphic["chart"]["items"] = [dict(i) for i in graphic["chart"]["items"] if i["label"] in {"Sensex", "Nifty 50"}]
for item in graphic["chart"]["items"]:
    item.pop("pct", None)
    if item["label"] == "Nifty 50":
        item["figures"] = ["nse_n50"]
article["visualSpec"]["indices"][0]["id"] = "nse_n50"
job = {"slug": "2026-10-23-weekly-market-review", "collection": job_collection, "graphic": graphic, "article": article}
out = root / "pipeline/inbox" / "2026-10-23-weekly-market-review.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Prepared weekly report: {len(figures)} NSE exchange figures + sourced Sensex close.")
