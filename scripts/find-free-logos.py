#!/usr/bin/env python3
"""Free-only Wikimedia Commons candidate discovery; preserve originals.

Usage: python scripts/find-free-logos.py --limit 5
       python scripts/find-free-logos.py --limit 5 --download

Never marks assets as approved. Requires human verification of identity, license,
trademark status and intended usage before production publication.
"""
import argparse
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "logo-source-queue.json"
OUTPUT = ROOT / "data" / "wikimedia-logo-candidates.json"
USER_AGENT = "TotalMarketEditorialLogoResearch/1.0 (open-source editorial asset discovery)"
API = "https://commons.wikimedia.org/w/api.php"
ALLOWED = {".svg", ".png", ".jpg", ".jpeg", ".webp"}

def request(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.read()

def search(query, limit):
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query + " logo", "gsrnamespace": "6",
        "gsrlimit": str(limit), "prop": "imageinfo",
        "iiprop": "url|mime|size|extmetadata", "iilimit": "1",
    }
    result = json.loads(request(API + "?" + urllib.parse.urlencode(params)))
    return result.get("query", {}).get("pages", {}).values()

def clean(value):
    return re.sub(r"<[^>]*>", "", str(value or "")).strip()

def candidate(page):
    info = (page.get("imageinfo") or [{}])[0]
    metadata = info.get("extmetadata") or {}
    def field(name):
        return clean((metadata.get(name) or {}).get("value"))
    url = info.get("url", "")
    ext = Path(urllib.parse.urlsplit(url).path).suffix.lower()
    return {
        "commons_title": page.get("title"), "description_page": info.get("descriptionurl"),
        "original_url": url, "original_format": ext,
        "original_width": info.get("width"), "original_height": info.get("height"),
        "license_short_name": field("LicenseShortName"),
        "license_url": field("LicenseUrl"),
        "usage_terms": field("UsageTerms"),
        "artist": field("Artist"),
        "attribution_required": field("AttributionRequired"),
        "copyrighted": field("Copyrighted"),
        "restrictions": field("Restrictions"),
        "status": "candidate_only_manual_rights_and_identity_review",
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--download", action="store_true", help="Save original bytes to quarantined review folder, never published logo registry")
    args = parser.parse_args()
    if not 1 <= args.limit <= 20:
        parser.error("--limit must be between 1 and 20")
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    output = {"source": "Wikimedia Commons", "purpose": "candidate discovery only", "companies": []}
    quarantine = ROOT / "logo-review" / "originals"
    if args.download:
        quarantine.mkdir(parents=True, exist_ok=True)
    for company in queue["items"]:
        symbol = company["symbol"]
        name = company["company_name"]
        record = {"symbol": symbol, "company_name": name, "candidates": [], "errors": []}
        try:
            for page in search(name, args.limit):
                item = candidate(page)
                if item["original_format"] not in ALLOWED or not item["original_url"]:
                    continue
                if args.download:
                    try:
                        data = request(item["original_url"])
                        if len(data) > 8_000_000:
                            raise ValueError("asset exceeds 8 MB")
                        if item["original_format"] == ".png" and not data.startswith(bytes.fromhex("89504e470d0a1a0a")):
                            raise ValueError("invalid PNG signature")
                        if item["original_format"] == ".svg" and b"<svg" not in data[:4096].lower():
                            raise ValueError("invalid SVG")
                        # Store original bytes unchanged; never render unreviewed SVG in public site.
                        dest = quarantine / (symbol.lower() + "-" + hashlib.sha256(data).hexdigest()[:12] + item["original_format"])
                        dest.write_bytes(data)
                        item["quarantine_path"] = str(dest.relative_to(ROOT))
                        item["sha256"] = hashlib.sha256(data).hexdigest()
                    except Exception as exc:
                        item["download_error"] = str(exc)
                record["candidates"].append(item)
        except Exception as exc:
            record["errors"].append(str(exc))
        output["companies"].append(record)
        print(symbol, len(record["candidates"]), "candidate(s)", file=sys.stderr)
        time.sleep(0.2)
    OUTPUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Wrote", OUTPUT, "(unapproved candidate list)")

if __name__ == "__main__":
    main()
