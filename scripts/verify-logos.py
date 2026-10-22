#!/usr/bin/env python3
"""Validate TotalMarket's company-logo registry and local PNG assets."""
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
registry = json.loads((ROOT / "data/company-logos.json").read_text(encoding="utf-8"))
seen_isins = set()
errors = []
for entry in registry["companies"]:
    symbol = entry.get("symbol", "")
    isin = entry.get("isin", "")
    path = entry.get("logo", "")
    if not symbol or not entry.get("company_name") or not re.fullmatch(r"[A-Z0-9]{12}", isin):
        errors.append(f"Invalid identity: {entry}")
    if isin in seen_isins:
        errors.append(f"Duplicate ISIN: {isin}")
    seen_isins.add(isin)
    if not re.fullmatch(r"logos/[a-z0-9-]+\.png", path):
        errors.append(f"Unsafe logo path: {path}")
        continue
    logo = ROOT / path
    if not logo.is_file():
        errors.append(f"Missing PNG: {path}")
        continue
    raw = logo.read_bytes()
    if len(raw) < 24 or raw[:8] != b"\x89PNG\r\n\x1a\n":
        errors.append(f"Not a PNG: {path}")
        continue
    width, height = struct.unpack(">II", raw[16:24])
    if (width, height) != (256, 256):
        errors.append(f"Expected 256x256 PNG: {path}")
    if entry.get("status") == "verified" and not entry.get("source_url"):
        errors.append(f"Verified logo missing source: {path}")
if errors:
    raise SystemExit("\n".join(errors))
print(f"Validated {len(registry['companies'])} company records")
