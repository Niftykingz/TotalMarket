"""Fail (so GitHub e-mails the owner) when scheduled publishing has gone quiet.

Weekdays: the newest post must be under 9 hours old between 10:00 and 23:00 IST.
Weekends / NSE holidays: under 30 hours (one roundup a day).
"""
import datetime as dt
import glob
import json
import os
import sys

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
now = dt.datetime.now(IST)
newest = None
for f in glob.glob(os.path.join(root, "data", "posts", "*.json")):
    try:
        t = dt.datetime.fromisoformat(json.load(open(f, encoding="utf-8"))["publishedAt"])
    except Exception:
        continue
    if t <= now and (newest is None or t > newest[0]):
        newest = (t, os.path.basename(f))
holidays = set()
try:
    cal = json.load(open(os.path.join(root, "data", "market_calendar.json"), encoding="utf-8"))
    holidays = {h.get("date") for y in cal.get("years", []) for h in y.get("holidays", []) if isinstance(h, dict)}
except Exception:
    pass
quiet_day = now.weekday() >= 5 or now.date().isoformat() in holidays
limit = dt.timedelta(hours=30 if quiet_day else 9)
age = now - newest[0] if newest else None
msg = f"newest post: {newest[1] if newest else 'none'} ({age} old; limit {limit})"
print(msg)
if age is None or age > limit:
    print(f"::error title=Scheduled publishing looks stalled::{msg}")
    sys.exit(1)
