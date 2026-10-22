"""Safe handling of source material. Everything fetched is UNTRUSTED DATA.

* Only hosts on the allowlist may be used; the allowlist also gives reliability.
* Live network fetching is off in Phase 1 (fixtures only). When it is enabled later it must
  respect robots.txt and site terms, and never fetch login-protected or restricted endpoints.
* Text that looks like instructions to an AI ("ignore previous instructions", "approve and
  publish") is flagged. Flags lower reliability and are shown to the Boss and the owner;
  nothing in a source is ever executed or obeyed.
"""
import hashlib
import re
from urllib.parse import urlsplit

MAX_CHARS = 200_000
INJECTION = [
    r"ignore (all |any )?(previous|prior|above) instructions",
    r"\b(system|assistant|developer)\s*:",
    r"\byou are (now )?(an? )?(ai|assistant|chatgpt|claude)\b",
    r"\b(approve|publish|deploy|merge)\b.{0,40}\b(now|immediately|without)\b",
    r"\bdisregard\b.{0,30}\b(rules|policy|instructions)\b",
    r"<\s*/?\s*(script|iframe)\b",
]


class SourceRefused(ValueError):
    pass


def host(url):
    return urlsplit(url).netloc.lower().split(":")[0].removeprefix("www.")


def reliability(url, allowlist):
    h = host(url)
    for dom, rel in allowlist.items():
        if h == dom or h.endswith("." + dom):
            return rel
    return None


def check_url(url, allowlist):
    if urlsplit(url).scheme not in ("https", "http"):
        raise SourceRefused(f"unsupported scheme: {url}")
    rel = reliability(url, allowlist)
    if rel is None:
        raise SourceRefused(f"{host(url)} is not on the source allowlist")
    return rel


def injection_flags(text):
    return [p for p in INJECTION if re.search(p, text or "", re.I)]


def clean(text):
    """Bound size and strip control characters. The text stays data; it is not interpreted."""
    t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", str(text or ""))[:MAX_CHARS]
    return t


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch(url, settings):
    """Live fetch is disabled in Phase 1."""
    check_url(url, settings.allowlist)
    if not settings.network_fetch:
        raise SourceRefused("live source fetching is disabled in Phase 1; use fixtures")
    raise SourceRefused("live fetching not implemented yet")  # pragma: no cover
