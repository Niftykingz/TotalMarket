"""IPO-stage covers: verified figures, stage artwork, blocked when data is missing or borrowed."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "pipeline" / "examples"))
from PIL import Image  # noqa: E402
from pipeline import core  # noqa: E402
from test_pipeline import Base  # noqa: E402
import make_ipo_dryrun_jobs as EX  # noqa: E402


class IpoCovers(Base):
    def run_job(self, j):
        p = self.root / "pipeline" / "inbox" / f"{j['slug']}.json"
        p.write_text(json.dumps(j, ensure_ascii=False), encoding="utf-8")
        return core.run_job(p, self.root)

    def test_each_stage_renders_from_verified_figures(self):
        for j in EX.JOBS:
            with self.subTest(job=j["slug"]):
                run = self.run_job(copy.deepcopy(j))
                self.assertEqual(core.status(run), "READY", core.status(run))
                self.assertEqual(run.load(3)["analysis"]["template"], j["graphic"]["chart"]["type"])
                with Image.open(run.dir / "cover.jpg") as im:
                    self.assertEqual(im.size, (1200, 675))

    def test_unverified_tile_blocked(self):
        j = copy.deepcopy(EX.OPENS)
        j["graphic"]["chart"]["items"].append({"label": "Lot size", "value": "21 shares"})
        self.assertIn("FAILED at GRAPHICS_GENERATION", core.status(self.run_job(j)))

    def test_missing_stage_blocked(self):
        j = copy.deepcopy(EX.LISTING)
        j["graphic"]["chart"].pop("stage")
        self.assertIn("MISSING_DATA", core.status(self.run_job(j)))


if __name__ == "__main__":
    unittest.main()
