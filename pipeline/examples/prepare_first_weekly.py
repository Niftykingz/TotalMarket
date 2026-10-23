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
    "title":"Indian Markets End Week Under Pressure: Nifty at 22,600, Sensex at 73,123.83",
    "dek":"On Friday 23 October 2026, Nifty 50 ended at 22,600.00 and Sensex at 73,123.83 as the market sell-off continued.",
    "category":"markets","lead":True,"readMins":3,
    "body":[
        "Indian stocks ended Friday 23 October under pressure. The Nifty 50 closed at 22,600.00, down 87.65 points (0.39%) in the session. The Sensex closed at 73,123.83, down 125.56 points (0.17%).",
        "Broader indices also fell on Friday: the Nifty Midcap 100 lost 2.21% and the Nifty Smallcap 100 declined 2.94%. These are Friday session moves, not weekly returns.",
        "The full weekly large-cap gainers and losers ranking is omitted because the available source dataset does not establish a verified five-session return for every constituent."
    ],
    "indiaImpact":"The sell-off extended beyond the headline indices to mid-cap and small-cap shares; daily declines should not be confused with full-week performance.",
    "seoTitle":"Nifty 50, Sensex Closing Review: 23 October 2026",
    "seoDescription":"Indian markets ended 23 October lower, with Nifty 50 at 22,600.00 and Sensex at 73,123.83. Midcap and smallcap indices also declined.",
    "sources":[{"name":s["name"],"url":s["url"]} for s in base["collection"]["sources"]],
    "publishedAt":"2026-10-23T19:00:00+05:30",
    "edition":"2026-10-23-weekly","editionLabel":"Fri 23 Oct · Weekly market review",
    "status":"new"
}
graphic=dict(base["graphic"])
graphic["headline"]=article["title"]
graphic["coverHeadline"]="NIFTY ENDS AT 22,600, DOWN 0.39%"
graphic["coverDate"]="2026-10-23"
job={"slug":"2026-10-23-weekly-market-review","collection":base["collection"],"graphic":graphic,"article":article}
out=root/"pipeline/inbox"/"2026-10-23-weekly-market-review.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(job,ensure_ascii=False,indent=2))
print("Prepared source-backed weekly-edition closing wrap; full weekly rankings pending evidence.")
