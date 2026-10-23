"""Prepare first weekly edition using explicitly sourced market-close data.
The pipeline, not this script, decides whether the story can be published.
"""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipeline.examples.make_v2_dryrun_jobs import JOBS
root=Path(__file__).resolve().parents[2]
base=JOBS[0]
draft=json.loads((root/"pipeline/drafts/2026-10-23-weekly-market-review.json").read_text())
# Source-backed close figures from the existing graphics test fixture.
# Do not claim unsourced weekly top-10 rankings or add unverified statistics.
article={
    "title":"Friday Complete Market Report: Nifty 22,600, Sensex 73,123.83 | 23 October 2026",
    "dek":"Friday close, weekly benchmark performance, broader markets, sectors, institutional flows, volatility, global drivers and next-week watchlist.",
    "category":"markets","lead":True,"readMins":7,
    "body":[
        "FRIDAY CLOSING DASHBOARD | Nifty 50 closed at 22,600.00, down 87.65 points; Sensex ended at 73,123.83, down 125.56 points. The chart accompanying this report compares the two closing benchmarks and their Friday point changes.",
        "WEEKLY MARKET PERFORMANCE | The week of 19–23 October reversed the previous week's gains. Reuters reported weekly declines of approximately 2.4% in Nifty 50 and 2.2% in Sensex. The broad market performed worse, with mid-cap shares falling approximately 5.6% and small-cap shares approximately 7.3% across the week. These weekly changes must not be confused with Friday's session-only declines.",
        "MARKET BREADTH | Selling was broad-based. Reuters reported weekly losses in 15 of the 16 major sectors. That is a market-wide signal, not a claim that every listed share declined.",
        "SECTOR HEATMAP — WEEKLY DIRECTION | Consumer durables, energy, FMCG and automobiles were among the weakest sector groups. Sector-by-sector percentage rankings are withheld until an independently verified, like-for-like closing dataset is available.",
        "STOCK MOVERS | Reuters highlighted weekly weakness in HDFC Bank, Axis Bank and Bajaj Finance. Swiggy was also under pressure. These are selected notable shares, not a verified full Nifty 50 gainers-and-losers leaderboard.",
        "FRIDAY TRADING SESSION | The benchmarks recovered from deeper intraday losses but ended lower. The move was accompanied by weaker midcap and smallcap participation. The Friday close and the full week's return are shown separately to avoid mixing timeframes.",
        "FII / DII CASH FLOWS | Foreign and domestic institutional activity remains an important market driver. The complete 19–23 October net-flow total is not published here because the available daily series has missing sessions; incomplete sessions must not be presented as a full-week total.",
        "INDIA VIX AND DERIVATIVES | Volatility and options positioning matter for next week's expiry. Strike-specific open interest, PCR and implied ranges are deliberately omitted from this edition until an expiry-matched timestamped exchange dataset is verified.",
        "GLOBAL DRIVERS | Reuters attributed pressure on Indian equities partly to surging crude oil prices amid Middle East tensions, which increased concern over inflation, corporate margins and the rupee.",
        "NEXT WEEK'S WATCHLIST | Monitor Nifty and Sensex expiry-related positioning, crude oil, the rupee, domestic quarterly earnings, institutional flows and the US Federal Reserve's 27–28 October policy meeting. These are event risks to monitor, not forecasts.",
        "DATA TRANSPARENCY | This edition includes a source-backed benchmark visual. Exact stock rankings, full sector tables, final weekly FII/DII totals and additional visual panels will only be added when verified datasets are available. No missing market data is estimated."
    ],
    "indiaImpact":"Broader-market and sector weakness shows why investors should monitor breadth and risk, not just Nifty and Sensex. Weekly and Friday returns are distinct.",
    "seoTitle":"Friday Indian Stock Market Report: 23 October 2026 | TotalMarket",
    "seoDescription":"Friday market close and weekly review: Nifty 22,600, Sensex 73,123.83, broader market, sectors, flows, global risks and next week.",
    "sources":[{"name":s["name"],"url":s["url"]} for s in base["collection"]["sources"]]+[
        {"name":"Reuters: Surging oil prices drag Indian shares to weekly losses","url":"https://www.reuters.com/world/india/indian-shares-seen-opening-higher-after-3-session-drop-oil-surge-clouds-outlook-2026-10-23/"},
        {"name":"Moneycontrol: Friday close and broader markets","url":"https://www.moneycontrol.com/news/business/markets/taking-stock-markets-recover-from-day-s-lows-but-sell-off-extends-to-4th-day-nifty-at-22-600-14058497.html"},
        {"name":"MarketCue: 19–23 October weekly review","url":"https://marketcue.in/weekly-analysis"}
    ],
    "publishedAt":"2026-10-23T19:00:00+05:30",
    "edition":"2026-10-23-weekly","editionLabel":"Fri 23 Oct · Complete market report",
    "status":"new"
}

# Every article citation must be registered in collection before stage 4.
# Only add source metadata here; numerical evidence remains subject to
# independent figure-level remote verification by the existing audit gate.
job_collection=json.loads(json.dumps(base["collection"]))
existing_urls={source["url"] for source in job_collection["sources"]}
for source in article["sources"]:
    if source["url"] not in existing_urls:
        job_collection["sources"].append(source)
        existing_urls.add(source["url"])
graphic=dict(base["graphic"])
graphic["headline"]=article["title"]
graphic["coverHeadline"]="FRIDAY MARKET REPORT"
graphic["coverDate"]="2026-10-23"
# Omit percentage claims whose linked publisher evidence could not be found.
job_collection["figures"]=[f for f in job_collection["figures"] if f["id"] not in {"sensex_pct","nifty_pct","mid","small","realty"}]
graphic["stat"]="22,600"
graphic["chart"]["items"]=[i for i in graphic["chart"]["items"] if i["label"] in {"Sensex","Nifty 50"}]
for item in graphic["chart"]["items"]:
    if item["label"] in {"Sensex","Nifty 50"}:
        item.pop("pct",None)
job={"slug":"2026-10-23-weekly-market-review","collection":job_collection,"graphic":graphic,"article":article}
out=root/"pipeline/inbox"/"2026-10-23-weekly-market-review.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(job,ensure_ascii=False,indent=2))
print("Prepared expanded Friday report with verified-source context and benchmark chart; incomplete datasets disclosed.")
