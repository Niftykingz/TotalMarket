"""Fetch exchange-origin market datasets without fabricating missing observations.

Outputs a dated JSON snapshot for independent verification. Never publishes directly.
NSE may deny automated access; that is recorded as an error, not bypassed.
"""
import argparse
import datetime as dt
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
BASE = "https://www.nseindia.com"
UA = "Mozilla/5.0 (compatible; TotalMarketMarketData/1.0; editorial research)"
HEADERS = {"User-Agent": UA, "Accept": "application/json,text/plain,*/*",
           "Referer": BASE + "/", "Accept-Language": "en-IN,en;q=0.9"}
INDEXES = ("NIFTY 50", "NIFTY BANK", "NIFTY MIDCAP 100", "NIFTY SMALLCAP 100",
           "NIFTY AUTO", "NIFTY FMCG", "NIFTY IT", "NIFTY METAL", "NIFTY REALTY",
           "NIFTY PHARMA", "NIFTY ENERGY", "NIFTY FINANCIAL SERVICES")


def request_json(path, opener):
    url = BASE + path
    req = urllib.request.Request(url, headers=HEADERS)
    with opener.open(req, timeout=18) as response:
        if response.status != 200:
            raise ValueError("HTTP " + str(response.status))
        if "json" not in response.headers.get("Content-Type", "").lower():
            raise ValueError("response is not JSON")
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("response too large")
    return json.loads(raw)


def numeric(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        v = float(str(value).replace(",", ""))
        if not (-1e12 < v < 1e12):
            return None
        return v
    except (ValueError, TypeError):
        return None


def date_from_timestamp(value):
    if not value:
        return None
    # NSE commonly uses '23-Oct-2026 15:30:00'; never substitute collection date.
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y", "%d-%m-%Y %H:%M:%S"):
        try:
            return dt.datetime.strptime(str(value), fmt).date().isoformat()
        except ValueError:
            pass
    return None


def collect(asof=None, fetch=None):
    today = asof or dt.datetime.now(IST).date().isoformat()
    snap = {"schema": 1, "targetDate": today,
            "collectedAt": dt.datetime.now(IST).isoformat(),
            "provider": "NSE India", "status": "partial", "datasets": {}, "errors": []}
    opener = urllib.request.build_opener()
    live = fetch is None
    if fetch is None:
        def fetch(path):
            return request_json(path, opener)
    # Establish ordinary public-session cookies; no login or access bypass.
    if live:
        try:
            opener.open(urllib.request.Request(BASE + "/", headers=HEADERS), timeout=12).close()
        except Exception:
            pass

    def get(name, path):
        try:
            payload = fetch(path)
            if not isinstance(payload, (dict, list)):
                raise ValueError("unexpected payload shape")
            return payload
        except Exception as exc:
            snap["errors"].append(name + ": " + str(exc)[:180])
            return None

    idx_path = "/api/allIndices"
    idx = get("indices", idx_path)
    if isinstance(idx, dict) and isinstance(idx.get("data"), list):
        rows = []
        for x in idx["data"]:
            if not isinstance(x, dict) or x.get("index") not in INDEXES:
                continue
            stamp = date_from_timestamp(x.get("lastUpdateTime") or x.get("timeVal"))
            if stamp != today:
                continue
            value = numeric(x.get("last"))
            pct = numeric(x.get("percentChange"))
            if value is None or pct is None:
                continue
            rows.append({"name": x["index"], "close": value, "pct": pct,
                         "advances": numeric(x.get("advances")),
                         "declines": numeric(x.get("declines")),
                         "unchanged": numeric(x.get("unchanged")),
                         "asOf": stamp})
        if rows:
            snap["datasets"]["indices"] = {"sourceUrl": BASE + idx_path, "rows": rows}
        else:
            snap["errors"].append("indices: no rows matching target date and required fields")

    movers_path = "/api/equity-stockIndices?index=" + urllib.parse.quote("NIFTY 50")
    stocks = get("nifty50", movers_path)
    if isinstance(stocks, dict) and isinstance(stocks.get("data"), list):
        rows = []
        for x in stocks["data"]:
            if not isinstance(x, dict) or x.get("symbol") == "NIFTY 50":
                continue
            pct = numeric(x.get("pChange"))
            last = numeric(x.get("lastPrice"))
            stamp = date_from_timestamp(x.get("lastUpdateTime") or stocks.get("timestamp"))
            if stamp != today or pct is None or last is None:
                continue
            rows.append({"symbol": x["symbol"], "price": last, "pct": pct, "asOf": stamp})
        if len(rows) >= 40:
            snap["datasets"]["movers"] = {"sourceUrl": BASE + movers_path,
                                           "universe": "NIFTY 50", "count": len(rows),
                                           "gainers": sorted(rows, key=lambda x: x["pct"], reverse=True)[:5],
                                           "losers": sorted(rows, key=lambda x: x["pct"])[:5]}
        else:
            snap["errors"].append("movers: incomplete or stale NIFTY 50 universe")

    flow_path = "/api/fiidiiTradeReact"
    flows = get("institutionalFlows", flow_path)
    if isinstance(flows, list):
        rows = []
        for x in flows:
            if not isinstance(x, dict):
                continue
            date = date_from_timestamp(x.get("date"))
            category = str(x.get("category") or "").upper()
            net = numeric(x.get("netValue"))
            if date == today and net is not None and ("FII" in category or "DII" in category):
                rows.append({"category": category, "netCrore": net, "asOf": date})
        if any("FII" in r["category"] for r in rows) and any("DII" in r["category"] for r in rows):
            snap["datasets"]["institutionalFlows"] = {"sourceUrl": BASE + flow_path, "rows": rows}
        else:
            snap["errors"].append("institutionalFlows: matching-date FII and DII rows unavailable")

    snap["status"] = "complete" if len(snap["datasets"]) == 3 and not snap["errors"] else "partial"
    return snap


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=dt.datetime.now(IST).date().isoformat())
    parser.add_argument("--output", default="pipeline/market_data/latest.json")
    args = parser.parse_args()
    dt.date.fromisoformat(args.date)
    result = collect(args.date)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "datasets": list(result["datasets"]),
                      "errors": result["errors"]}))
    if not result["datasets"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
