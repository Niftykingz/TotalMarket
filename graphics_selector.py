"""Deterministic, original cover-illustration selector for TotalMarket.

Uses only existing art objects, never external images or fabricated chart data.
An explicit story symbol other than generic 'candles' remains authoritative.
"""
import re

RULES = (
    (r"\b(quarterly|q[1-4]|earnings|net profit|revenue|results|ebitda)\b", "coins"),
    (r"\b(rbi|repo rate|central bank|monetary policy|inflation|cpi|sebi)\b", "bank"),
    (r"\b(ipo|listing|funding|startup|fundraise|unicorn)\b", "growth"),
    (r"\b(artificial intelligence|ai|chip|semiconductor|nvidia|gpu)\b", "chip"),
    (r"\b(cloud|data cent(er|re)|servers?)\b", "servers"),
    (r"\b(cybersecurity|data breach|security)\b", "shield"),
    (r"\b(fii|dii|institutional flows|investment inflows|mutual fund)\b", "coins"),
    (r"\b(us market|wall street|global markets|nasdaq|dow jones)\b", "globe"),
    (r"\b(rupee|usd.?inr|forex|currency)\b", "forex"),
    (r"\b(gold|bullion)\b", "gold"),
    (r"\b(silver)\b", "silver"),
    (r"\b(crude|brent|oil)\b", "oil"),
)

def choose_cover_object(story, fallback="candles"):
    """Choose a fitting illustration from already-original cover primitives."""
    title = str(story.get("title") or "")
    category = str(story.get("category") or "")
    text = title.lower()
    for pattern, obj in RULES:
        if re.search(pattern, text, re.I):
            return obj
    category_defaults = {
        "tech": "chip", "startups": "growth", "policy": "bank",
        "global": "globe", "commodities": "gold",
    }
    if category == "markets":
        # Keep generic market wraps on the chart artwork, while distinguishing
        # corporate and economic stories via the title-based rules above.
        return fallback
    return category_defaults.get(category, fallback)
