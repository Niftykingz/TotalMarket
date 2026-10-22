#!/usr/bin/env python3
"""Discover free Wikimedia Commons logo candidates and optionally download original bytes.
Candidates are NOT approved for public redistribution. Python standard library only.
"""
import argparse
import hashlib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://commons.wikimedia.org/w/api.php"
QUEUE = ROOT / "data/logo-source-queue.json"
OUTPUT = ROOT / "data/wikimedia-logo-candidates.json"
QUARANTINE = ROOT / "logo-review/originals"
UA = "TotalMarketLogoResearch/1.1 (editorial candidate review; contact via GitHub Niftykingz/TotalMarket)"
ALLOWED = {".svg", ".png", ".jpg", ".jpeg", ".webp"}
SEARCHES = {
    "RELIANCE": ["Reliance Industries", "Reliance Industries Limited"],
    "JIO": ["Jio", "Reliance Jio"],
    "HDFCBANK": ["HDFC Bank"],
    "ICICIBANK": ["ICICI Bank"],
    "INFY": ["Infosys"],
    "TCS": ["Tata Consultancy Services", "TCS"],
    "SBIN": ["State Bank of India", "SBI"],
    "AXISBANK": ["Axis Bank"],
    "KOTAKBANK": ["Kotak Mahindra Bank", "Kotak Bank"],
    "BAJFINANCE": ["Bajaj Finance", "Bajaj Finserv"],
    "TATAMOTORS": ["Tata Motors", "Tata Motors Limited"],
    "ADANIENT": ["Adani Enterprises", "Adani Group"],
    "ETERNAL": ["Eternal Limited", "Zomato Eternal"],
    "SWIGGY": ["Swiggy", "Swiggy Limited"],
    "NVDA": ["NVIDIA"],
}

class RateLimited(Exception):
    pass

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            retry = exc.headers.get("Retry-After", "not specified")
            raise RateLimited("HTTP 429 from Wikimedia; stop and try again later (Retry-After: " + retry + ")") from exc
        raise

def metadata(info, key):
    return re.sub(r"<[^>]+>", "", html.unescape(str((info.get("extmetadata", {}).get(key) or {}).get("value", "")))).strip()

def discover(query, limit):
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query + " logo", "gsrnamespace": 6,
        "gsrlimit": limit, "prop": "imageinfo",
        "iiprop": "url|mime|size|extmetadata", "iilimit": 1,
    }
    result = json.loads(fetch(API + "?" + urllib.parse.urlencode(params)))
    for page in result.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("url", "")
        ext = Path(urllib.parse.urlsplit(url).path).suffix.lower()
        if ext not in ALLOWED or not url:
            continue
        yield {
            "commons_title": page.get("title"), "description_page": info.get("descriptionurl"),
            "original_url": url, "original_format": ext,
            "original_width": info.get("width"), "original_height": info.get("height"),
            "license_short_name": metadata(info, "LicenseShortName"),
            "license_url": metadata(info, "LicenseUrl"),
            "usage_terms": metadata(info, "UsageTerms"),
            "artist": metadata(info, "Artist"),
            "restrictions": metadata(info, "Restrictions"),
            "status": "candidate_only_manual_rights_and_identity_review",
        }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=3, help="Candidates per search (1-10)")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--delay", type=float, default=4.0, help="Minimum seconds between HTTP requests (>= 2)")
    args = parser.parse_args()
    if not 1 <= args.limit <= 10 or args.delay < 2:
        parser.error("--limit must be 1-10 and --delay >= 2")
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    previous = {}
    if OUTPUT.exists():
        try:
            previous = {x["symbol"]: x for x in json.loads(OUTPUT.read_text(encoding="utf-8")).get("companies", [])}
        except (ValueError, KeyError):
            pass
    if args.download:
        QUARANTINE.mkdir(parents=True, exist_ok=True)
    records = []
    last_request = [0.0]
    blocked = False
    def paced_fetch(url):
        remaining = args.delay - (time.monotonic() - last_request[0])
        if remaining > 0:
            time.sleep(remaining)
        try:
            return fetch(url)
        finally:
            last_request[0] = time.monotonic()

    # Discover uses the same rate-limited HTTP function as original downloads.
    global fetch
    original_fetch = fetch
    def paced(url):
        remaining = args.delay - (time.monotonic() - last_request[0])
        if remaining > 0:
            time.sleep(remaining)
        try:
            return original_fetch(url)
        finally:
            last_request[0] = time.monotonic()
    fetch = paced
    try:
        for company in queue["items"]:
            symbol = company["symbol"]
            prior = previous.get(symbol, {})
            record = {"symbol": symbol, "company_name": company["company_name"], "candidates": [], "errors": []}
            seen = set()
            # Keep previously discovered candidate URLs, avoiding unnecessary repeat API calls.
            for item in prior.get("candidates", []):
                if item.get("original_url") and item["original_url"] not in seen:
                    seen.add(item["original_url"])
                    record["candidates"].append(item)
            if not record["candidates"] and not blocked:
                for name in SEARCHES.get(symbol, [company["company_name"]]):
                    try:
                        for item in discover(name, args.limit):
                            if item["original_url"] not in seen:
                                seen.add(item["original_url"])
                                record["candidates"].append(item)
                    except RateLimited as exc:
                        blocked = True
                        record["errors"].append(str(exc))
                        break
                    except (OSError, ValueError) as exc:
                        record["errors"].append(str(exc))
                    if record["candidates"]:
                        break
            if args.download and not blocked:
                # One valid original candidate per company. Preserve any existing downloads.
                has_file = any(QUARANTINE.glob(symbol.lower() + "-*"))
                if not has_file:
                    for item in record["candidates"]:
                        try:
                            data = fetch(item["original_url"])
                            if len(data) > 8_000_000:
                                raise ValueError("original exceeds 8 MB")
                            ext = item["original_format"]
                            if ext == ".png" and not data.startswith(bytes.fromhex("89504e470d0a1a0a")):
                                raise ValueError("invalid PNG signature")
                            if ext == ".svg" and b"<svg" not in data[:8192].lower():
                                raise ValueError("invalid SVG")
                            if ext in (".jpg", ".jpeg") and not data.startswith(bytes.fromhex("ffd8ff")):
                                raise ValueError("invalid JPEG signature")
                            if ext == ".webp" and not (data[:4] == b"RIFF" and data[8:12] == b"WEBP"):
                                raise ValueError("invalid WebP signature")
                            digest = hashlib.sha256(data).hexdigest()
                            dest = QUARANTINE / (symbol.lower() + "-" + digest[:12] + ext)
                            dest.write_bytes(data)
                            item["quarantine_path"] = str(dest.relative_to(ROOT)).replace("\\", "/")
                            item["sha256"] = digest
                            item.pop("download_error", None)
                            break
                        except RateLimited as exc:
                            blocked = True
                            record["errors"].append(str(exc))
                            break
                        except (OSError, ValueError) as exc:
                            item["download_error"] = str(exc)
            records.append(record)
            print(symbol + ": " + str(len(record["candidates"])) + " candidates; " +
                  ("downloaded" if any(QUARANTINE.glob(symbol.lower() + "-*")) else "no local original") +
                  (" [rate-limited; stopping network requests]" if blocked else ""), file=sys.stderr)
            # Save partial results even when interrupted.
            OUTPUT.write_text(json.dumps({"source": "Wikimedia Commons", "purpose": "candidate discovery only", "companies": records}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if blocked:
            print("Wikimedia rate limit encountered. Stop and retry after the server's cooldown; do not loop.", file=sys.stderr)
    finally:
        fetch = original_fetch

if __name__ == "__main__":
    main()
