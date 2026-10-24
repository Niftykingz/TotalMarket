"""Bull / bear cover artwork: approved files only, new market stories only."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import market_art  # noqa: E402

NEW = {"id": "2026-10-24-x", "category": "markets", "publishedAt": "2026-10-24T12:50:00+05:30"}


class MarketArt(unittest.TestCase):
    def setUp(self):
        market_art._CACHE.clear()

    def test_direction_picks_bear_or_bull(self):
        self.assertTrue(market_art.choice(NEW, "down").startswith("bear"))
        self.assertTrue(market_art.choice(NEW, "up").startswith("bull"))
        self.assertIsNone(market_art.choice(NEW, "flat"))

    def test_old_and_non_market_stories_untouched(self):
        self.assertIsNone(market_art.choice(dict(NEW, publishedAt="2026-10-23T15:52:00+05:30"), "down"))
        self.assertIsNone(market_art.choice(dict(NEW, category="startups"), "up"))

    def test_unapproved_or_altered_file_never_used(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            shutil.copytree(ROOT / "cover_art", tmp / "cover_art")
            (tmp / "data").mkdir()
            reg = json.loads((ROOT / "data" / "cover-art.json").read_text(encoding="utf-8"))
            reg["items"][0]["approved"] = False
            reg["items"][1]["sha256"] = "0" * 64
            (tmp / "data" / "cover-art.json").write_text(json.dumps(reg), encoding="utf-8")
            old = market_art.HERE
            market_art.HERE = str(tmp)
            try:
                self.assertEqual(market_art._registry(), [])
            finally:
                market_art.HERE = old
                market_art._CACHE.clear()
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
