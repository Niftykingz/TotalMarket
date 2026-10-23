"""Fail-closed remote evidence audit for financial figures.

Network access is only to public HTTPS hosts. It does not treat a job's
self-supplied evidence string as proof. This is an additional source check,
not a guarantee that a publisher's claim is true.
"""
import gzip
import hashlib
import html
import ipaddress
import json
import re
from pathlib import Path
import socket
import urllib.parse
import urllib.request
from html.parser import HTMLParser

MAX_BYTES = 1_500_000
ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = "data/market_snapshots/"

class EvidenceError(ValueError):
    pass

class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.skip:
            self.skip -= 1
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

def clean(value):
    return re.sub(r"\s+", " ", html.unescape(str(value)).replace("\u00a0", " ")).strip().casefold()

def safe_url(url):
    u = urllib.parse.urlsplit(str(url))
    if u.scheme != "https" or not u.hostname or u.username or u.password or u.port not in (None, 443):
        raise EvidenceError("source must be public HTTPS")
    host = u.hostname
    if host == "localhost" or host.endswith(".local"):
        raise EvidenceError("private host")
    try:
        addrs = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise EvidenceError(f"DNS failed: {exc}") from exc
    if not addrs:
        raise EvidenceError("no DNS records")
    for addr in addrs:
        ip = ipaddress.ip_address(addr[4][0])
        if not ip.is_global:
            raise EvidenceError("private or reserved IP")
    return u.geturl()

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise EvidenceError("redirect not allowed; use canonical final source URL")

def fetch_public_text(url, timeout=10):
    url = safe_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": "TotalMarketEvidenceAudit/1.0", "Accept": "text/html,text/plain"})
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req, timeout=timeout) as resp:
            typ = resp.headers.get_content_type()
            if typ not in ("text/html", "text/plain"):
                raise EvidenceError("unsupported source content type")
            raw = resp.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise EvidenceError("source exceeds maximum size")
            charset = resp.headers.get_content_charset() or "utf-8"
    except Exception as exc:
        raise EvidenceError(f"source fetch failed: {exc}") from exc
    doc = raw.decode(charset, errors="replace")
    if typ == "text/html":
        parser = TextOnly()
        parser.feed(doc)
        doc = " ".join(parser.parts)
    return clean(doc)

# ------------------------------------------------------------ exchange datasets
# A source with "dataset" points at a raw exchange response archived by the collector workflow
# (.github/workflows/collect-nse-market-data.yml). Its "page text" is rebuilt here from those raw
# bytes, so an evidence quote can only match what the exchange actually returned.

def _fmt(v):
    return "" if v is None else str(v)


def _lines_all_indices(d):
    ts = d.get("timestamp", "")
    out = []
    for x in d.get("data") or []:
        if not isinstance(x, dict) or not x.get("index"):
            continue
        out.append(f"{x['index']}: last {_fmt(x.get('last'))}, change {_fmt(x.get('variation'))} points, "
                   f"{_fmt(x.get('percentChange'))}% (previous close {_fmt(x.get('previousClose'))}; open {_fmt(x.get('open'))}, "
                   f"high {_fmt(x.get('high'))}, low {_fmt(x.get('low'))}; advances {_fmt(x.get('advances'))}, "
                   f"declines {_fmt(x.get('declines'))}, unchanged {_fmt(x.get('unchanged'))}; "
                   f"one week ago {_fmt(x.get('oneWeekAgoVal'))} on {_fmt(x.get('oneWeekAgo'))}) as of {ts}")
    return out


def _lines_fii_dii(d):
    return [f"{x.get('category')} {x.get('date')}: bought {x.get('buyValue')} crore, sold {x.get('sellValue')} crore, "
            f"net {x.get('netValue')} crore" for x in d if isinstance(x, dict)]


DATASET_FORMATS = {"api_allIndices": _lines_all_indices, "api_fiidiiTradeReact": _lines_fii_dii}


def dataset_lines(source, root=None):
    """Human-readable lines rebuilt from the archived raw exchange response (fail closed)."""
    root = Path(root or ROOT)
    rel = str(source.get("dataset") or "")
    if not rel.startswith(SNAPSHOT_DIR) or ".." in rel or not rel.endswith(".json.gz"):
        raise EvidenceError("dataset must be an archived file under " + SNAPSHOT_DIR)
    f = root / rel
    if not f.is_file():
        raise EvidenceError(f"dataset {rel} is not in the repository")
    raw = gzip.decompress(f.read_bytes())
    digest = hashlib.sha256(raw).hexdigest()
    if digest != source.get("sha256"):
        raise EvidenceError(f"dataset {rel} sha256 does not match the source record")
    snap = f.parent / "snapshot.json"
    recorded = {v.get("sha256") for v in (json.loads(snap.read_text(encoding="utf-8")).get("raw") or {}).values()} if snap.is_file() else set()
    if digest not in recorded:
        raise EvidenceError(f"dataset {rel} is not the response the collector recorded")
    fmt = DATASET_FORMATS.get(f.name[:-len(".json.gz")])
    if not fmt:
        raise EvidenceError(f"no reader for dataset {f.name}")
    return fmt(json.loads(raw))


def dataset_text(source, root=None):
    return clean(" | ".join(dataset_lines(source, root)))


def _page_for(source, fetcher, root):
    return dataset_text(source, root) if source.get("dataset") else fetcher(source.get("url", ""))


def audit_datasets(collected, root=None):
    """Offline part of the audit: figures from archived exchange datasets only."""
    ds = {s["id"] for s in collected.get("sources", []) if s.get("dataset")}
    figs = [f for f in collected.get("figures", []) if f.get("source") in ds]
    if not figs:
        return True, []
    return _audit(dict(collected, figures=figs), fetcher=lambda url: (_ for _ in ()).throw(EvidenceError("not a dataset")), root=root)


def audit(collected, fetcher=fetch_public_text, root=None):
    return _audit(collected, fetcher, root)


def _audit(collected, fetcher=fetch_public_text, root=None):
    """Return (success, errors). Every figure's quoted evidence must exist on
    the linked source page; unreachable/paywalled/JS-only sources fail closed.
    """
    sources = {s["id"]: s for s in collected.get("sources", [])}
    cache = {}
    errors = []
    for fig in collected.get("figures", []):
        fid = fig.get("id", "?")
        source = sources.get(fig.get("source"))
        if not source:
            errors.append(f"{fid}: missing source")
            continue
        url = source.get("dataset") or source.get("url", "")
        if url not in cache:
            try:
                cache[url] = _page_for(source, fetcher, root)
            except Exception as exc:
                cache[url] = exc
        page = cache[url]
        if isinstance(page, Exception):
            errors.append(f"{fid}: {page}")
            continue
        quote = clean(fig.get("evidence", ""))
        if len(quote) < 12 or quote not in page:
            errors.append(f"{fid}: evidence quote not found on source page")
    return not errors, errors


def recover_evidence(collected, fetcher=fetch_public_text, root=None):
    """Repair stale/incorrect quotations from the linked original source.

    Retain a figure only when its *existing* value, change and pct occur
    together in a single source-text window. Never invent or change numbers.
    Return a new collection plus errors for figures needing human/source
    recollection. This is deliberately narrower than AI article rewriting.
    """
    from . import numbers as N
    import copy
    result = copy.deepcopy(collected)
    sources = {s.get("id"): s for s in result.get("sources", [])}
    cache = {}
    unresolved = []
    for fig in result.get("figures", []):
        sid = fig.get("source")
        src = sources.get(sid)
        if not src:
            unresolved.append(f"{fig.get('id')}: missing original source")
            continue
        url = src.get("dataset") or src.get("url", "")
        if url not in cache:
            try:
                cache[url] = _page_for(src, fetcher, root)
            except Exception as exc:
                cache[url] = exc
        page = cache[url]
        if isinstance(page, Exception):
            unresolved.append(f"{fig.get('id')}: original source unavailable: {page}")
            continue
        quote = clean(fig.get("evidence", ""))
        values = [str(fig[k]) for k in ("value", "change", "pct") if fig.get(k) not in (None, "")]
        if len(quote) >= 12 and quote in page and all(N.in_evidence(v, quote) for v in values):
            continue
        # Search only for contiguous original-source text. Do not synthesize a quote.
        found = None
        for match in re.finditer(re.escape(clean(values[0])), page):
            lo = max(0, match.start() - 160)
            hi = min(len(page), match.end() + 160)
            window = page[lo:hi]
            if all(N.in_evidence(v, window) for v in values):
                found = window
                break
        if found is None:
            unresolved.append(f"{fig.get('id')}: values not supported together by original source")
        else:
            fig["evidence"] = found
    return result, unresolved
