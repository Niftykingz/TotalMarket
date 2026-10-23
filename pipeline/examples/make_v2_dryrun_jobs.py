"""Dry-run jobs for the eight v2 graphic layouts, built only from real figures collected on
22–23 Oct 2026 (sources and evidence below). Writes job files to the folder given; never
into pipeline/inbox. Usage: python3 pipeline/examples/make_v2_dryrun_jobs.py <out_dir>"""
import json
import sys
from pathlib import Path

S = {
 "cm": ("ChiniMandi: Sensex down 125 points, Nifty at 22,600", "https://www.chinimandi.com/sensex-down-125-points-nifty-at-22600/", "2026-10-23T15:45:00+05:30"),
 "bs": ("Business Standard: Market close, 23 Oct", "https://www.business-standard.com/markets/news/stock-market-live-october-23-nse-bse-sensex-today-nifty50-gift-nifty-crude-oil-prices-jio-ipo-q2-results-today-126102300078_1.html", "2026-10-23T15:41:00+05:30"),
 "ap": ("AP via ABC News: How US indexes fared 22 Oct", "https://abcnews.com/Business/wireStory/major-us-stock-indexes-fared-thursday-10222026-137490327", "2026-10-22T16:30:00-04:00"),
 "rtr": ("Reuters via Business Standard: Asian shares, 23 Oct", "https://www.business-standard.com/markets/news/asian-shares-slip-as-tech-rout-boosts-bonds-dents-rate-hike-bets-126102300074_1.html", "2026-10-23T08:30:00+05:30"),
 "capp": ("CappNotes: Closing Look, 22 Oct", "https://cappnotes.substack.com/p/closing-look-thursday-october-22", "2026-10-22T18:00:00-04:00"),
 "pti": ("PTI via The Sen Times: Rupee closes at 94.82", "https://thesentimes.com/rupee-slumps-44-paise-to-close-at-94-82-against-us-dollar/", "2026-10-22T16:45:00+05:30"),
 "gk": ("GKToday: RBI hikes repo rate by 25 basis points to 5.50%", "https://www.gktoday.in/rbi-hikes-repo-rate-by-25-basis-points-to-5-50/", "2026-10-07T12:00:00+05:30"),
 "adda": ("Adda247: RBI raises repo rate by 25 bps", "https://currentaffairs.adda247.com/bi-monthly-monetary-policy-rbi-raises-repo-rate-by-25-bps-after-over-3-years/", "2026-10-07T12:00:00+05:30"),
 "jsw": ("Business Standard: JSW Steel Q2FY27 result", "https://www.business-standard.com/amp/companies/quarterly-results/jsw-steel-q2fy27-result-net-profit-rises-14-1-to-5-359-crore-126102300833_1.html", "2026-10-23T15:35:00+05:30"),
}


def src(*ids):
    return [{"id": i, "name": S[i][0], "url": S[i][1], "published": S[i][2]} for i in ids]


def fig(i, label, value, s, ev, as_of="2026-10-23", **k):
    return dict(id=i, label=label, value=value, source=s, evidence=ev, as_of=as_of, **k)


def article(title, dek, body, cat, ids, edition="2026-10-23-dryrun", label="Fri 23 Oct · Dry run (not published)"):
    return {"title": title, "dek": dek, "category": cat, "lead": False, "readMins": 2, "body": body,
            "indiaImpact": "Shown for the graphics dry run only; this job is never placed in the publishing inbox.",
            "seoTitle": title[:58], "seoDescription": (dek + " " + body[0])[:158],
            "sources": [{"name": S[i][0], "url": S[i][1]} for i in ids], "edition": edition, "editionLabel": label,
            "publishedAt": "2026-10-23T19:45:00+05:30", "status": "new"}


JOBS = []

# 1 index_board — today's close
JOBS.append({"slug": "2026-10-23-v2-index-board", "collection": {"sources": src("cm", "bs"), "examples": [], "figures": [
  fig("sensex", "Sensex close", "73,123.83", "cm", "Sensex: closed at 73,123.83, down 125.56 points", change="-125.56", key=True),
  fig("sensex_pct", "Sensex change %", "-0.17", "bs", "Fell 125.56 points (0.17%) to 73,123.83"),
  fig("nifty", "Nifty 50 close", "22,600.00", "cm", "Nifty 50: ended at 22,600.00, down 87.65 points", change="-87.65", key=True),
  fig("nifty_pct", "Nifty 50 change %", "-0.39", "bs", "Settled at 22,600, down 87.65 points (0.39%)"),
  fig("mid", "Nifty Midcap 100 change %", "-2.21", "bs", "The Nifty Midcap 100 fell 2.21%"),
  fig("small", "Nifty Smallcap 100 change %", "-2.94", "bs", "the Nifty Smallcap 100 fell 2.94%"),
  fig("realty", "Realty index change %", "-3", "cm", "Realty and Consumer Durables fell 3% each")]},
 "graphic": {"headline": "Sensex, Nifty fall for a fourth day", "coverHeadline": "NIFTY ENDS AT 22,600, DOWN 0.39%", "stat": "-0.39%",
  "statLabel": "Nifty 50 close", "symbol": "candles", "flags": ["IN"], "coverDate": "2026-10-23",
  "chart": {"type": "index_board", "title": "Indian markets · close", "asOf": "Close, Fri 23 Oct 2026", "source": "ChiniMandi, Business Standard",
            "items": [{"label": "Sensex", "value": "73,123.83", "change": "-125.56", "pct": "-0.17%"},
                      {"label": "Nifty 50", "value": "22,600.00", "change": "-87.65", "pct": "-0.39%"},
                      {"label": "Midcap 100", "pct": "-2.21%"}, {"label": "Smallcap 100", "pct": "-2.94%"}, {"label": "Realty", "pct": "-3%"}]}},
 "article": article("Sensex, Nifty fall for a fourth day: Nifty ends at 22,600, down 0.39%", "Small caps fell 2.94%.",
  ["The Sensex closed at 73,123.83, down 125.56 points (0.17%), and the Nifty 50 at 22,600.00, down 87.65 points (0.39%).",
   "The Nifty Midcap 100 fell 2.21% and the Smallcap 100 2.94%; realty fell 3%."], "markets", ["cm", "bs"])})

# 2 global_bars — overnight session
JOBS.append({"slug": "2026-10-23-v2-global-bars", "collection": {"sources": src("ap", "rtr"), "examples": [], "figures": [
  fig("dow", "Dow Jones close", "52,867.98", "ap", "Dow Jones Industrial Average: closed at 52,867.98, up 11.89 points (less than 0.1%)", as_of="2026-10-22", key=True),
  fig("dow_pct", "Dow change %", "0.02", "rtr", "Dow Jones +0.02%", as_of="2026-10-22"),
  fig("spx", "S&P 500 close", "7,663.43", "ap", "S&P 500: closed at 7,663.43, down 93.74 points (1.2%)", as_of="2026-10-22"),
  fig("spx_pct", "S&P 500 change %", "-1.21", "rtr", "S&P 500 -1.21%", as_of="2026-10-22"),
  fig("ndq", "Nasdaq close", "26,008.86", "ap", "Nasdaq Composite: closed at 26,008.86, down 694 points (2.6%)", as_of="2026-10-22", key=True),
  fig("ndq_pct", "Nasdaq change %", "-2.60", "rtr", "Nasdaq Composite -2.60% at 26,008.86", as_of="2026-10-22"),
  fig("rus_pct", "Russell 2000 change %", "0.11", "ap", "Russell 2000: closed at 2,784.03, up 3.01 points (0.11%)", as_of="2026-10-22"),
  fig("nik", "Nikkei change % (Fri morning)", "-1.3", "rtr", "Nikkei -1.3% Friday"),
  fig("kos", "Kospi change % (Fri morning)", "-1.7", "rtr", "KOSPI -1.7% Friday"),
  fig("hsi", "Hang Seng change % (Fri morning)", "0.1", "rtr", "Hang Seng +0.1% Friday, after -3% Thursday")]},
 "graphic": {"headline": "Overnight: Nasdaq sinks 2.6% on AI-spending fears", "coverHeadline": "NASDAQ −2.60% ON AI FEARS", "stat": "-2.60%",
  "symbol": "globe", "flags": ["US", "JP", "KR"], "coverDate": "2026-10-22",
  "chart": {"type": "global_bars", "title": "Global markets", "asOf": "US: Thu 22 Oct close · Asia: Fri 23 Oct morning", "source": "AP, Reuters",
            "items": [{"label": "Dow Jones", "value": "52,867.98", "pct": "+0.02%"}, {"label": "S&P 500", "value": "7,663.43", "pct": "-1.21%"},
                      {"label": "Nasdaq", "value": "26,008.86", "pct": "-2.60%"}, {"label": "Russell 2000", "pct": "+0.11%"},
                      {"label": "Nikkei (Fri am)", "pct": "-1.3%"}, {"label": "Kospi (Fri am)", "pct": "-1.7%"}, {"label": "Hang Seng (Fri am)", "pct": "+0.1%"}]}},
 "article": article("Overnight: Nasdaq sinks 2.60% on AI-spending fears; Dow flat", "The S&P 500 lost 1.21%.",
  ["The Nasdaq fell 2.60% to 26,008.86, the S&P 500 1.21% to 7,663.43, while the Dow rose 0.02% to 52,867.98.",
   "On Friday morning the Nikkei was 1.3% lower and the Kospi 1.7% lower; the Hang Seng rose 0.1%."], "global", ["ap", "rtr"])})

# 3 commodity_card — crude
JOBS.append({"slug": "2026-10-23-v2-commodity-card", "collection": {"sources": src("capp", "bs"), "examples": [], "figures": [
  fig("brent", "Brent settle", "113.17", "capp", "Brent (December settle): +4.00% to $113.17", as_of="2026-10-22", pct="4.00", key=True),
  fig("wti", "WTI settle", "99.47", "capp", "WTI (December settle): +2.39% to $99.47", as_of="2026-10-22", pct="2.39"),
  fig("brent_am", "Brent 8:12 am IST", "114.16", "bs", "Brent crude (December futures, 8:12 AM): 114.16, up 0.94%", pct="0.94")]},
 "graphic": {"headline": "Brent settles at $113.17, up 4%", "coverHeadline": "BRENT $113.17, UP 4.00%", "stat": "+4.00%", "symbol": "oil", "flags": ["SA", "US"],
  "coverDate": "2026-10-22",
  "chart": {"type": "commodity_card", "title": "Crude oil", "asOf": "Settle, Thu 22 Oct · Asia, Fri 23 Oct 8:12 am IST", "source": "CappNotes, Business Standard",
            "items": [{"label": "Brent, $/barrel (settle)", "value": "$113.17", "pct": "+4.00%"},
                      {"label": "WTI, $/barrel (settle)", "value": "$99.47", "pct": "+2.39%"},
                      {"label": "Brent, 8:12 am IST Fri", "value": "$114.16", "pct": "+0.94%"}]}},
 "article": article("Brent crude settles at $113.17, up 4.00%", "WTI rose 2.39% to $99.47.",
  ["Brent settled at $113.17, up 4.00%, and WTI at $99.47, up 2.39%.", "At 8:12 am IST on Friday Brent was at $114.16, up 0.94%."],
  "commodities", ["capp", "bs"])})

# 4 forex_card — rupee
JOBS.append({"slug": "2026-10-23-v2-forex-card", "collection": {"sources": src("pti"), "examples": [], "figures": [
  fig("inr", "USD/INR close 22 Oct", "94.82", "pti", "Close: 94.82 per dollar (provisional)", as_of="2026-10-22", key=True),
  fig("inr_prev", "USD/INR previous close", "94.38", "pti", "Down 44 paise from the previous close of 94.38", as_of="2026-10-21"),
  fig("inr_low", "Rupee intraday low", "94.94", "pti", "Opened at 94.47 and hit a low of 94.94", as_of="2026-10-22"),
  fig("dxy", "Dollar index", "101.60", "pti", "A softer dollar index (down 0.17% to 101.60)", as_of="2026-10-22", pct="-0.17")]},
 "graphic": {"headline": "Rupee falls 44 paise to 94.82", "coverHeadline": "RUPEE 94.82 PER DOLLAR", "stat": "94.82", "symbol": "rupee", "flags": ["IN", "US"],
  "coverDate": "2026-10-22",
  "chart": {"type": "forex_card", "title": "Rupee vs dollar", "asOf": "Close, Thu 22 Oct 2026 (provisional)", "source": "PTI",
            "items": [{"label": "USD/INR", "value": "94.82", "prev": "94.38", "change": "+0.44"},
                      {"label": "Day's weakest", "value": "94.94"}, {"label": "Dollar index", "value": "101.60", "pct": "-0.17%"}]}},
 "article": article("Rupee falls 44 paise to 94.82 per dollar", "The previous close was 94.38.",
  ["The rupee closed at 94.82 against the dollar (provisional), 44 paise weaker than 94.38.", "It touched 94.94 during the day; the dollar index was 101.60."],
  "commodities", ["pti"])})

# 5 policy_rate — RBI, 7 Oct 2026
JOBS.append({"slug": "2026-10-23-v2-policy-rate", "collection": {"sources": src("gk", "adda"), "examples": [], "figures": [
  fig("old", "Repo rate before", "5.25", "gk", "voted unanimously to increase the policy rate from 5.25%", as_of="2026-10-07", historical=True, key=True),
  fig("new", "Repo rate after", "5.50", "adda", "unanimously decided to increase the policy repo rate by 25 basis points to 5.50%", as_of="2026-10-07", historical=True, key=True),
  fig("bps", "Change in bps", "25", "adda", "increase the policy repo rate by 25 basis points to 5.50%", as_of="2026-10-07", historical=True)]},
 "graphic": {"headline": "RBI raised the repo rate by 25 bps to 5.50%", "coverHeadline": "REPO RATE 5.25% → 5.50%", "stat": "+25 bps", "symbol": "bank",
  "flags": ["IN"], "coverDate": "2026-10-07",
  "chart": {"type": "policy_rate", "title": "RBI policy · 7 Oct 2026", "asOf": "MPC decision, 7 Oct 2026", "source": "GKToday, Adda247",
            "items": [{"label": "Repo rate (before)", "value": "5.25%", "role": "before"}, {"label": "Repo rate (after)", "value": "5.50%", "role": "after"},
                      {"label": "Change", "value": "+25 bps", "role": "change", "figures": ["bps"]}]}},
 "article": article("RBI raised the repo rate by 25 bps to 5.50% from 5.25%", "The MPC raised the rate by 25 basis points on 7 October.",
  ["On 7 October the RBI's MPC raised the repo rate by 25 basis points, from 5.25% to 5.50%."], "policy", ["gk", "adda"])})

# 6 stock_move — Hatsun Agro
JOBS.append({"slug": "2026-10-23-v2-stock-move", "collection": {"sources": src("bs"), "examples": [], "figures": [
  fig("hatsun", "Hatsun Agro price 2:31 pm", "964.10", "bs", "Hatsun Agro: Shares fell 10.14% to ₹964.10 at 2:31 PM", pct="-10.14", key=True)]},
 "graphic": {"headline": "Hatsun Agro shares fall 10.14% after results", "coverHeadline": "HATSUN AGRO −10.14%", "stat": "-10.14%", "symbol": "candles",
  "flags": ["IN"], "companies": [{"name": "Hatsun Agro Product", "ticker": "HATSUN"}], "coverDate": "2026-10-23",
  "chart": {"type": "stock_move", "title": "Stock move", "asOf": "23 Oct 2026, 2:31 pm IST", "source": "Business Standard",
            "items": [{"label": "Hatsun Agro", "value": "₹964.10", "pct": "-10.14%"}]}},
 "article": article("Hatsun Agro shares fall 10.14% to ₹964.10 after results", "Its operating margin narrowed.",
  ["Hatsun Agro fell 10.14% to ₹964.10 at 2:31 pm after its results."], "markets", ["bs"])})

# 7 ipo_subscription — Jio
JOBS.append({"slug": "2026-10-23-v2-ipo-subscription", "collection": {"sources": src("bs"), "examples": [], "figures": [
  fig("tot", "Jio IPO total subscription 2:10 pm", "9.81", "bs", "9.81 times subscribed at 2:10 PM", key=True),
  fig("qib", "Jio IPO QIB", "23.47", "bs", "QIBs: 23.47 times"), fig("nii", "Jio IPO NII", "11.97", "bs", "NIIs: 11.97 times"),
  fig("rii", "Jio IPO retail", "2.28", "bs", "RIIs: 2.28 times")]},
 "graphic": {"headline": "Jio Platforms IPO subscribed 9.81 times on the final day", "coverHeadline": "JIO IPO 9.81X SUBSCRIBED", "stat": "9.81x",
  "symbol": "growth", "flags": ["IN"], "coverDate": "2026-10-23",
  "chart": {"type": "ipo_subscription", "title": "IPO demand · final day", "asOf": "23 Oct 2026, 2:10 pm IST", "source": "Business Standard",
            "items": [{"label": "Total", "value": "9.81x", "role": "total", "note": "Times subscribed, Jio Platforms"},
                      {"label": "Institutions (QIB)", "value": "23.47x"}, {"label": "Wealthy individuals (NII)", "value": "11.97x"},
                      {"label": "Retail", "value": "2.28x"}]}},
 "article": article("Jio Platforms IPO subscribed 9.81 times on the final day", "QIBs bid 23.47 times their quota.",
  ["Jio Platforms' IPO was subscribed 9.81 times at 2:10 pm: QIBs 23.47 times, NIIs 11.97 times, retail 2.28 times."], "startups", ["bs"])})

# 8 earnings_v2 — JSW Steel (vs previous quarter, as reported)
JOBS.append({"slug": "2026-10-23-v2-earnings", "collection": {"sources": src("jsw"), "examples": [], "figures": [
  fig("pat", "JSW Steel consolidated PAT", "5,359", "jsw", "consolidated profit after tax of ₹5,359 crore, up 14.1% from ₹4,696 crore in the preceding quarter", change="14.1", key=True),
  fig("pat_prev", "JSW Steel PAT Q1 FY27", "4,696", "jsw", "up 14.1% from ₹4,696 crore in the preceding quarter", as_of="2026-10-23"),
  fig("rev", "JSW Steel revenue from operations", "54,486", "jsw", "Revenue from operations: ₹54,486 crore, up 15% QoQ from ₹47,364 crore", change="15", key=True),
  fig("rev_prev", "JSW Steel revenue Q1 FY27", "47,364", "jsw", "up 15% QoQ from ₹47,364 crore")]},
 "graphic": {"headline": "JSW Steel Q2 profit ₹5,359 crore, up 14.1% from Q1", "coverHeadline": "JSW STEEL PROFIT ₹5,359 CR", "stat": "+14.1%",
  "symbol": "coins", "flags": ["IN"], "companies": [{"name": "JSW Steel", "ticker": "JSWSTEEL"}], "coverDate": "2026-10-23",
  "chart": {"type": "earnings_v2", "title": "Quarterly results · JSW Steel", "period": "Q2 FY27 (Jul–Sep 2026) · consolidated", "compareLabel": "Previous quarter vs now",
            "asOf": "Results declared 23 Oct 2026", "source": "Business Standard (exchange filing pending)",
            "items": [{"label": "Net profit", "value": "₹5,359 cr", "change": "+14.1%", "prev": "₹4,696 cr", "note": "vs Q1 FY27"},
                      {"label": "Revenue from operations", "value": "₹54,486 cr", "change": "+15%", "prev": "₹47,364 cr", "note": "vs Q1 FY27"}]}},
 "article": article("JSW Steel Q2 profit ₹5,359 crore, up 14.1% from the previous quarter", "Revenue rose 15% to ₹54,486 crore.",
  ["JSW Steel's consolidated profit was ₹5,359 crore, up 14.1% from ₹4,696 crore in Q1; revenue rose 15% to ₹54,486 crore from ₹47,364 crore."],
  "markets", ["jsw"])})


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for j in JOBS:
        (out / f"{j['slug']}.json").write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(JOBS), "jobs written to", out)
