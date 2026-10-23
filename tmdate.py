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
    # NUL sentinels truncate strftime output on some Linux libc builds.
    # Use printable sentinels that strftime preserves on Windows and Linux.
    out = d.strftime(pattern.replace("%-d", "__TM_DAY__").replace("%-I", "__TM_HOUR__"))
    return out.replace("__TM_DAY__", str(d.day)).replace("__TM_HOUR__", str(d.hour % 12 or 12))
