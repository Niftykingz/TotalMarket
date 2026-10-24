"""IPO-stage cover dry-run jobs built from real, previously verified figures (never placed in the inbox).

Used by tests/test_ipo_covers.py. Figures: Paras Healthcare (HDFC Sky, 23 Oct 2026),
Tonbo Imaging listing (Upstox, 23 Oct 2026), next week's IPO list (Choice, 24 Oct 2026).
"""
HDFC = {"id": "hdfc", "name": "HDFC Sky: Paras Healthcare IPO subscription status, day 3",
        "url": "https://hdfcsky.com/news/paras-healthcare-ipo-subscription-status-day-3", "published": "2026-10-23T17:21:00+05:30"}
UPSTOX = {"id": "upt", "name": "Upstox: Tonbo lists at 66% premium",
          "url": "https://upstox.com/news/market-news/ipo/tonbo-imaging-india-shares-list-at-66-premium-on-nse-here-s-how-much-investors-made-per-lot/article-202269/",
          "published": "2026-10-23T10:05:00+05:30"}
CHOICE = {"id": "ch", "name": "Choice: upcoming IPOs, October 2026", "url": "https://choiceindia.com/ipo/upcoming-ipo-october-2026",
          "published": "2026-10-24T09:00:00+05:30"}


def fig(i, label, value, src, ev, as_of="2026-10-23", key=False):
    return dict({"id": i, "label": label, "value": value, "source": src, "evidence": ev, "as_of": as_of}, **({"key": True} if key else {}))


def article(title, dek, body, when, edition, label, sources):
    return {"title": title, "dek": dek, "category": "startups", "lead": False, "readMins": 2, "body": body,
            "indiaImpact": "Shown for the IPO graphics dry run only; this job is never placed in the publishing inbox.",
            "seoTitle": title[:60], "seoDescription": (dek + " " + body[0])[:155], "sources": [{"name": s["name"], "url": s["url"]} for s in sources],
            "publishedAt": when, "edition": edition, "editionLabel": label, "status": "new"}


OPENS = {
    "slug": "2026-10-24-ipo-v2-opens",
    "collection": {"sources": [HDFC], "examples": [], "figures": [
        fig("lo", "Paras Healthcare IPO price band lower end", "660", "hdfc", "The price band is ₹660 to ₹693 per share.", key=True),
        fig("hi", "Paras Healthcare IPO price band upper end", "693", "hdfc", "The price band is ₹660 to ₹693 per share."),
        fig("size", "Paras Healthcare IPO issue size", "1,450", "hdfc", "The book-built issue has a total size of ₹1,450 crore")]},
    "graphic": {"headline": "Paras Healthcare IPO: price band ₹660–693", "coverHeadline": "PARAS HEALTHCARE IPO", "flags": ["IN"], "coverDate": "2026-10-23",
                "chart": {"type": "ipo_facts", "stage": "opens", "title": "IPO opens · key details", "dates": "Opens Tue 21 Oct · closes Thu 23 Oct",
                          "source": "HDFC Sky", "asOf": "23 Oct 2026",
                          "items": [{"label": "Price band", "value": "₹660–693", "role": "main", "note": "per share"},
                                    {"label": "Issue size", "value": "₹1,450 cr"}]}},
    "article": article("Paras Healthcare IPO: price band ₹660–693, issue size ₹1,450 crore", "The issue size is ₹1,450 crore.",
                       ["The price band is ₹660 to ₹693 a share and the issue size ₹1,450 crore, according to HDFC Sky."],
                       "2026-10-24T13:00:00+05:30", "2026-10-24-ipo", "Sat 24 Oct · IPO", [HDFC]),
}

LISTING = {
    "slug": "2026-10-24-ipo-v2-listing",
    "collection": {"sources": [UPSTOX], "examples": [], "figures": [
        fig("issue", "Tonbo issue price", "700", "upt", "Final issue price: ₹700 per share", key=True),
        fig("listing", "Tonbo NSE listing price", "1,160", "upt", "NSE listing price: ₹1,160 (65.71% premium)", key=True),
        fig("gain", "Tonbo listing gain %", "65.71", "upt", "NSE listing price: ₹1,160 (65.71% premium)")]},
    "graphic": {"headline": "Tonbo Imaging lists at ₹1,160", "coverHeadline": "TONBO LISTS 65.71% HIGHER", "flags": ["IN"], "coverDate": "2026-10-23",
                "chart": {"type": "ipo_facts", "stage": "listing", "title": "IPO listing · NSE", "dates": "Listed Fri 23 Oct 2026, 10:00 am",
                          "source": "Upstox", "asOf": "23 Oct 2026",
                          "items": [{"label": "Listing gain", "value": "+65.71%", "role": "main", "note": "vs issue price", "figures": ["gain"]},
                                    {"label": "Issue price", "value": "₹700"}, {"label": "NSE listing price", "value": "₹1,160"}]}},
    "article": article("Tonbo Imaging lists at ₹1,160, 65.71% above its ₹700 issue price", "The shares listed at ₹1,160 on NSE.",
                       ["Tonbo Imaging listed at ₹1,160 on NSE against an issue price of ₹700, a premium of 65.71%, according to Upstox."],
                       "2026-10-24T13:00:00+05:30", "2026-10-24-ipo", "Sat 24 Oct · IPO", [UPSTOX]),
}

CALENDAR = {
    "slug": "2026-10-24-ipo-v2-calendar",
    "collection": {"sources": [CHOICE], "examples": [], "figures": [
        fig("e_lo", "EDELALTS price band lower", "1,585", "ch", 'Price range "₹1585 - ₹1665"', "2026-10-24", key=True),
        fig("e_hi", "EDELALTS price band upper", "1,665", "ch", 'Price range "₹1585 - ₹1665"', "2026-10-24"),
        fig("s_lo", "SFC Environmental price band lower", "313", "ch", 'Price range "₹313 - ₹330"', "2026-10-24"),
        fig("s_hi", "SFC Environmental price band upper", "330", "ch", 'Price range "₹313 - ₹330"', "2026-10-24")]},
    "graphic": {"headline": "IPOs opening next week", "coverHeadline": "IPOS OPENING NEXT WEEK", "flags": ["IN"], "coverDate": "2026-10-24",
                "chart": {"type": "ipo_calendar", "title": "IPO calendar · next week", "source": "Choice", "asOf": "24 Oct 2026",
                          "items": [{"label": "EDELALTS", "note": "26–28 Oct", "value": "₹1,585–1,665"},
                                    {"label": "SFC Environmental", "note": "27–29 Oct", "value": "₹313–330"},
                                    {"label": "Carver Roboweld", "note": "28–30 Oct"}]}},
    "article": article("IPOs opening next week: EDELALTS, SFC Environmental and Carver Roboweld", "EDELALTS has a price band of ₹1,585–1,665.",
                       ["EDELALTS opens on 26 October with a price band of ₹1,585 to ₹1,665, and SFC Environmental on 27 October at ₹313 to ₹330, according to Choice."],
                       "2026-10-24T13:00:00+05:30", "2026-10-24-ipo", "Sat 24 Oct · IPO", [CHOICE]),
}

JOBS = [OPENS, LISTING, CALENDAR]
