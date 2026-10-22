"""Deterministic de-duplication plus a dependency-free similarity check.

1. Exact: canonical source URL, or the normalized-headline key, already seen.
2. Similar: word-set and character-trigram Jaccard similarity against stories in the
   newsroom database *and* stories already on the site (data/posts/*.json).
"""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

STOP = set("a an the of to in on for and or as at by with from is are be its it this that after amid over vs".split())
SIMILAR = 0.58


def canonical_url(u: str) -> str:
    p = urlsplit((u or "").strip())
    host = p.netloc.lower().removeprefix("www.")
    return urlunsplit(("https", host, p.path.rstrip("/"), "", ""))


def words(text):
    return [w for w in re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", (text or "").lower()) if w not in STOP]


def key(headline: str) -> str:
    return hashlib.sha1(" ".join(sorted(set(words(headline)))).encode()).hexdigest()[:16]


def _tri(text):
    t = " ".join(words(text))
    return {t[i:i + 3] for i in range(max(0, len(t) - 2))}


def similarity(a: str, b: str) -> float:
    wa, wb = set(words(a)), set(words(b))
    if not wa or not wb:
        return 0.0
    jw = len(wa & wb) / len(wa | wb)
    ta, tb = _tri(a), _tri(b)
    jt = len(ta & tb) / len(ta | tb) if ta and tb else 0.0
    return round(0.5 * jw + 0.5 * jt, 3)


def site_titles(root: Path):
    out = []
    for f in sorted((root / "data" / "posts").glob("*.json")):
        try:
            out.append((f.stem, json.loads(f.read_text(encoding="utf-8")).get("title", "")))
        except Exception:
            continue
    return out


def find_duplicate(candidate, db, root: Path):
    """Return (kind, ref, score) for a duplicate, or None. kind: url | key | similar | site."""
    cu, k, h = canonical_url(candidate["source_url"]), key(candidate["headline"]), candidate["headline"]
    for r in db.all("SELECT slug, title, source_url, dedupe_key FROM stories"):
        if r["source_url"] and canonical_url(r["source_url"]) == cu:
            return ("url", r["slug"], 1.0)
        if r["dedupe_key"] == k:
            return ("key", r["slug"], 1.0)
        s = similarity(h, r["title"])
        if s >= SIMILAR:
            return ("similar", r["slug"], s)
    for slug, title in site_titles(root):
        s = similarity(h, title)
        if s >= SIMILAR:
            return ("site", slug, s)
    return None


def related(headline, root: Path, limit=3):
    """Existing site stories that are related (for internal links / context), not duplicates."""
    scored = sorted(((similarity(headline, t), slug) for slug, t in site_titles(root)), reverse=True)
    return [slug for s, slug in scored if 0.18 <= s < SIMILAR][:limit]
