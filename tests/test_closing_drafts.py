"""Daily closing drafts from the archived NSE files (offline)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from PIL import Image  # noqa: E402
from pipeline import closing  # noqa: E402

DAY = ROOT / "data" / "market_snapshots" / "2026-10-23" / "bhavcopy.json.gz"


@unittest.skipUnless(DAY.is_file(), "snapshot not in this checkout")
class ClosingDrafts(unittest.TestCase):
    def test_dataset_is_exchange_data_only(self):
        d = closing.dataset("2026-10-23")
        self.assertEqual(float(d["indices"]["NIFTY 50"]["close"]), 22600.0)
        self.assertEqual(d["movers"]["count"], 50)
        self.assertEqual(d["movers"]["gainers"][0]["name"], "ETERNAL")
        self.assertEqual(float(d["indices"]["SENSEX"]["close"]), 73123.83)   # from BSE's own archive
        self.assertEqual(d["indices"]["SENSEX"]["source"], "bse")
        self.assertEqual(d["flows"]["fii"], "887.65")

    def test_mover_pct_recomputed_from_close_and_previous_close(self):
        for r in closing.dataset("2026-10-23")["movers"]["gainers"]:
            self.assertAlmostEqual(r["pct"], round((r["close"] - r["prev"]) / r["prev"] * 100, 2))

    def test_four_pngs_and_draft_files(self):
        with tempfile.TemporaryDirectory() as t:
            out, files, missing = closing.make_drafts("2026-10-23", t)
            for f in files:
                with Image.open(f) as im:
                    self.assertEqual(im.size, (1536, 1024))
            self.assertIn("EDITOR:", (out / "article.md").read_text(encoding="utf-8"))
            self.assertTrue((out / "sources.json").is_file())

    def test_no_snapshot_not_ready(self):
        with self.assertRaises(closing.NotReady):
            closing.dataset("2026-10-30")


if __name__ == "__main__":
    unittest.main()
