"""Official logo authenticity policy (cannot be overridden by the Boss or any agent).

A graphic may contain an organization's logo ONLY as an unmodified original file that is
listed in data/company-logos.json with status "verified", a source_url, rights_reviewed
true, and whose bytes still match the recorded sha256. Logos are composited as a separate
layer at their original aspect ratio (contain-fit, never squared, recoloured or redrawn).

Everything else is rejected, including any logo-like element produced by a generator.
When no approved logo exists, the organization's name is shown as plain text.
"""
import hashlib
import json
from pathlib import Path

from ..config import ROOT

# Institutional marks that must never be drawn or imitated. Text names are fine.
PROTECTED_MARKS = ("rbi", "reserve bank", "sebi", "nse", "bse", "government of india", "ashoka", "emblem", "seal")


def registry(root: Path = ROOT):
    p = root / "data" / "company-logos.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("companies", [])
    except FileNotFoundError:
        return []


def approved(logo_key, root: Path = ROOT):
    """(entry, reason). entry is None if this logo may not be used."""
    for e in registry(root):
        if str(e.get("symbol", "")).lower() != str(logo_key or "").lower():
            continue
        if e.get("status") != "verified" or not e.get("source_url") or e.get("rights_reviewed") is not True:
            return None, "logo not verified / rights not reviewed"
        f = root / e.get("logo", "")
        if not f.is_file():
            return None, "approved logo file missing"
        if e.get("sha256") and hashlib.sha256(f.read_bytes()).hexdigest() != e["sha256"]:
            return None, "logo file bytes changed since approval"
        if not e.get("sha256"):
            return None, "approved logo has no recorded sha256"
        return e, "ok"
    return None, "no approved logo in registry"


def check_items(items, root: Path = ROOT, override=None):
    """Findings for logo elements in a graphic spec. `override` is accepted and ignored on purpose."""
    out = []
    for it in items:
        txt = (it.get("text") or "").lower()
        if it.get("kind") == "logo":
            if it.get("generated"):
                out.append(("REJECTED", it.get("text", "logo"), "logo element was generated/redrawn, not an original file"))
                continue
            e, why = approved(it.get("logo_key"), root)
            if e is None:
                out.append(("REJECTED", it.get("text", "logo"), f"logo '{it.get('logo_key')}' refused: {why}"))
            else:
                out.append(("VERIFIED", it.get("text", "logo"), f"original file {e['logo']} sha256 {e['sha256'][:12]}… source {e['source_url']}"))
        elif it.get("generated") and any(m in txt for m in PROTECTED_MARKS):
            out.append(("REJECTED", it.get("text", ""), "generated element imitating institutional branding"))
    return out
