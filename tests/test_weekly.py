"""Automatic weekly report from the archived NSE snapshot (offline)."""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import weekly  # noqa: E402

SNAP = ROOT / "data" / "market_snapshots" / "2026-10-23" / "api_allIndices.json.gz"


@unittest.skipUnless(SNAP.is_file(), "snapshot not in this checkout")
class Weekly(unittest.TestCase):
    def test_job_passes_offline_check(self):
        from pipeline import __main__ as cli
        job = weekly.build("2026-10-23", now=dt.datetime(2026, 10, 23, 16, 30, tzinfo=weekly.IST))
        job["slug"] = "2026-10-23-weekly-auto-test"
        self.assertIn("down 2.36%", job["article"]["title"])
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "j.json"
            p.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(cli.cmd_check([str(p)], root=ROOT), 0)

    def test_missing_snapshot_not_ready(self):
        with self.assertRaises(weekly.NotReady):
            weekly.build("2026-10-30")

    def test_week_end_detection(self):
        self.assertTrue(weekly.last_trading_day_of_week(dt.date(2026, 10, 23)))
        self.assertFalse(weekly.last_trading_day_of_week(dt.date(2026, 10, 22)))
        self.assertFalse(weekly.last_trading_day_of_week(dt.date(2026, 10, 24)))


if __name__ == "__main__":
    unittest.main()
