"""Windows-safe date formatting shared by all TotalMarket modules.

`fmt(value, pattern)` accepts a datetime.date, datetime.datetime or ISO string and
supports the unpadded `%-d` (day) and `%-I` (12-hour) directives on every platform
(Windows strftime rejects them).
"""
from datetime import date, datetime


def to_dt(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    s = str(value or "").strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return datetime.fromisoformat(s[:10])


def fmt(value, pattern):
    d = to_dt(value)
    out = d.strftime(pattern.replace("%-d", "\x00D\x00").replace("%-I", "\x00I\x00"))
    return out.replace("\x00D\x00", str(d.day)).replace("\x00I\x00", str(d.hour % 12 or 12))
