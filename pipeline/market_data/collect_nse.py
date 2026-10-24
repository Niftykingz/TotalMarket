"""Fetch exchange-origin market datasets without fabricating missing observations.

Outputs a dated JSON snapshot for independent verification. Never publishes directly.
NSE may deny automated access; that is recorded as an error, not bypassed.
"""
import argparse
import datetime as dt
import gzip
import hashlib
import http.cookiejar
import io
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


def request_raw(path, opener):
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
    return raw


def request_json(path, opener):
    return json.loads(request_raw(path, opener))


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
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M", "%d-%b-%Y", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y"):
        try:
            return dt.datetime.strptime(str(value).strip(), fmt).date().isoformat()
        except ValueError:
            pass
    return None


ARCHIVES = "https://nsearchives.nseindia.com"


def request_file(url, opener, max_bytes=40_000_000):
    """Official NSE end-of-day files (CSV, or a zip holding one CSV)."""
    import zipfile
    req = urllib.request.Request(url, headers=dict(HEADERS, Accept="*/*"))
    with opener.open(req, timeout=30) as response:
        if response.status != 200:
            raise ValueError("HTTP " + str(response.status))
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("file too large")
    if raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".csv")]
            if not names:
                raise ValueError("zip without a CSV")
            raw = z.read(names[0])
    if b"," not in raw[:2000]:
        raise ValueError("not a CSV file")
    return raw


def collect(asof=None, fetch=None, raw_sink=None, fetch_file=None):
    """raw_sink: optional dict filled with {path: raw response bytes} for the audit archive."""
    today = asof or dt.datetime.now(IST).date().isoformat()
    snap = {"schema": 1, "targetDate": today,
            "collectedAt": dt.datetime.now(IST).isoformat(),
            "provider": "NSE India", "status": "partial", "datasets": {}, "errors": []}
    # Keep the cookies NSE's home page sets, as any browser would (the old opener dropped them).
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    live = fetch is None
    if fetch is None:
        def fetch(path):
            raw = request_raw(path, opener)
            if raw_sink is not None:
                raw_sink[path] = raw
            return json.loads(raw)
    # Establish ordinary public-session cookies; no login or access bypass.
    if live:
        try:
            opener.open(urllib.request.Request(BASE + "/", headers=HEADERS), timeout=12).close()
        except Exception:
            pass

    snap["diagnostics"] = {}

    def shape(name, payload):
        """Record field names and timestamp strings only (never values) so format drift is visible."""
        d = {"type": type(payload).__name__}
        if isinstance(payload, dict):
            d["keys"] = sorted(payload)[:20]
            d["timestamp"] = str(payload.get("timestamp"))[:40] if "timestamp" in payload else None
            rows = payload.get("data") if isinstance(payload.get("data"), list) else []
        else:
            rows = payload if isinstance(payload, list) else []
        if rows and isinstance(rows[0], dict):
            d["rowKeys"] = sorted(rows[0])[:40]
            d["rowTimestamps"] = sorted({str(r.get(k))[:40] for r in rows[:60] if isinstance(r, dict)
                                         for k in ("lastUpdateTime", "timeVal", "date") if r.get(k)})[:5]
        d["rows"] = len(rows)
        snap["diagnostics"][name] = d

    def get(name, path):
        try:
            payload = fetch(path)
            if not isinstance(payload, (dict, list)):
                raise ValueError("unexpected payload shape")
            shape(name, payload)
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
            stamp = date_from_timestamp(x.get("lastUpdateTime") or x.get("timeVal") or idx.get("timestamp"))
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
    if stocks is None:  # NSE's own site requests this index with '+' for the space
        movers_path = "/api/equity-stockIndices?index=" + urllib.parse.quote_plus("NIFTY 50")
        stocks = get("nifty50_alt", movers_path)
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

    # Official end-of-day files for closing-price movers (used by pipeline/closing.py).
    if fetch_file is None and live:
        def fetch_file(url):
            return request_file(url, opener)
    if fetch_file is not None:
        ymd = today.replace("-", "")
        for key, url in (("bhavcopy", f"{ARCHIVES}/content/cm/BhavCopy_NSE_CM_0_0_0_{ymd}_F_0000.csv.zip"),
                         ("nifty50list", f"{ARCHIVES}/content/indices/ind_nifty50list.csv")):
            try:
                raw = fetch_file(url)
                if raw_sink is not None:
                    raw_sink[key] = raw
                lines = raw.decode("utf-8-sig", "replace").splitlines()
                snap["diagnostics"][key] = {"rows": len(lines) - 1, "header": lines[0][:300] if lines else ""}
                if key == "bhavcopy" and today not in "\n".join(lines[1:3]):
                    snap["errors"].append("bhavcopy: file does not carry the target date")
            except Exception as exc:
                snap["errors"].append(key + ": " + str(exc)[:180])

    snap["status"] = "complete" if len(snap["datasets"]) == 3 and not snap["errors"] else "partial"
    if snap["status"] == "complete" or "movers" in snap["datasets"]:
        snap["errors"] = [e for e in snap["errors"] if not e.startswith("nifty50:")]  # recovered by the alt path
    return snap


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=dt.datetime.now(IST).date().isoformat())
    parser.add_argument("--output", default="pipeline/market_data/latest.json")
    parser.add_argument("--archive", help="also keep the snapshot and raw responses under this folder")
    args = parser.parse_args()
    dt.date.fromisoformat(args.date)
    raw = {}
    result = collect(args.date, raw_sink=raw)
    result["raw"] = {p: {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)} for p, b in raw.items()}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    out.write_text(text, encoding="utf-8")
    if args.archive and result["datasets"]:
        base = Path(args.archive) / args.date
        base.mkdir(parents=True, exist_ok=True)
        # Archived files are evidence for published articles: never overwrite one. A re-run only
        # adds files that are not there yet, and keeps the earlier hash records.
        prev = json.loads((base / "snapshot.json").read_text(encoding="utf-8")) if (base / "snapshot.json").is_file() else None
        kept = dict((prev or {}).get("raw") or {})
        for p, b in raw.items():
            name = re.sub(r"[^A-Za-z0-9]+", "_", p).strip("_") + ".json.gz"
            if (base / name).is_file():
                continue
            (base / name).write_bytes(gzip.compress(b, mtime=0))
            kept[p] = result["raw"][p]
        merged = dict(prev, raw=kept, reruns=(prev.get("reruns") or []) + [{"collectedAt": result["collectedAt"], "added": sorted(set(kept) - set(prev.get("raw") or {})),
                                                                          "errors": result["errors"]}]) if prev else result
        (base / "snapshot.json").write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "datasets": list(result["datasets"]),
                      "errors": result["errors"]}))
    if not result["datasets"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
