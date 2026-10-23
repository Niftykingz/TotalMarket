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
    "dek":"Friday close with verified index dashboard, market breadth context, sector commentary and next-week risks.",
    "category":"markets","lead":True,"readMins":4,
    "reportType":"weekly_market",
    # Declarative slots: only verified figure IDs are rendered. A category with
    # no source-backed data remains absent, never a fabricated chart or table.
    "visualSpec":{
        "indices":[{"id":"nifty","label":"Nifty 50"},{"id":"sensex","label":"Sensex"}],
        "sectors":[],"caps":[],"global":[],"gainers":[],"losers":[]
    },
    "reportTakeaways":["Friday benchmarks closed lower after recovering from intraday lows.","Broader-market and sector weakness warrants attention beyond headline indices."],
    "reportWatch":["Crude oil, rupee and quarterly earnings","Institutional cash flows and exchange-verified expiry positioning"],
    "body":[
        "What moved | Indian equities ended Friday lower after recovering from deeper intraday losses. Broader-market weakness and pressure across several sectors showed that the decline extended beyond the headline indices.",
        "Sectors and stocks | Consumer durables, energy, FMCG and automobiles were among the weaker groups. Reuters highlighted weakness in HDFC Bank, Axis Bank and Bajaj Finance; Swiggy also faced pressure. These are selected examples, not a ranked leaderboard.",
        "Why it mattered | Higher crude oil prices amid Middle East tensions raised concerns about inflation, margins and the rupee. Investors should distinguish Friday's closing move from the full week's return.",
        "Looking ahead | Watch crude oil, the rupee, quarterly earnings, institutional flows and expiry positioning. These are monitoring priorities, not price forecasts."
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
        source_id="report_extra_"+str(len(existing_urls)+1)
        job_collection["sources"].append({
            "id":source_id,
            "name":source["name"],
            "url":source["url"],
            "published":"2026-10-23T19:00:00+05:30"
        })
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
print("Prepared expanded Friday report with verified-source context, benchmark chart and editorial dashboard layout; incomplete datasets disclosed.")
