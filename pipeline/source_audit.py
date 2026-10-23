"""Fail-closed remote evidence audit for financial figures.

Network access is only to public HTTPS hosts. It does not treat a job's
self-supplied evidence string as proof. This is an additional source check,
not a guarantee that a publisher's claim is true.
"""
import html
import ipaddress
import re
import socket
import urllib.parse
import urllib.request
from html.parser import HTMLParser

MAX_BYTES = 1_500_000

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

def audit(collected, fetcher=fetch_public_text):
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
        url = source.get("url", "")
        if url not in cache:
            try:
                cache[url] = fetcher(url)
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
