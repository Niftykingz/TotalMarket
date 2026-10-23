"""Exchange-dataset evidence: figures quoted from raw NSE responses archived by the collector.
Offline; uses the real 23 Oct 2026 snapshot committed by the collector workflow."""
import copy
import gzip
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import source_audit as SA  # noqa: E402

DAY = "data/market_snapshots/2026-10-23"
IDX = f"{DAY}/api_allIndices.json.gz"
FLOW = f"{DAY}/api_fiidiiTradeReact.json.gz"
REALTY = ("NIFTY REALTY: last 784.35, change -19.1 points, -2.38% (previous close 803.45; open 802.15, "
          "high 802.2, low 770.95; advances 0, declines 10, unchanged 0; one week ago 825.95 on 16-Oct-2026) "
          "as of 23-Oct-2026 15:30")
FII = "FII/FPI 23-Oct-2026: bought 14445.54 crore, sold 13557.89 crore, net 887.65 crore"


def sha(rel, root=ROOT):
    import hashlib
    return hashlib.sha256(gzip.decompress((Path(root) / rel).read_bytes())).hexdigest()


@unittest.skipUnless((ROOT / IDX).is_file(), "snapshot not in this checkout")
class DatasetEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / DAY, self.root / DAY)
        self.col = {
            "sources": [
                {"id": "nse", "name": "NSE India", "url": "https://www.nseindia.com/api/allIndices",
                 "published": "2026-10-23T15:30:00+05:30", "dataset": IDX, "sha256": sha(IDX)},
                {"id": "nsef", "name": "NSE India", "url": "https://www.nseindia.com/api/fiidiiTradeReact",
                 "published": "2026-10-23T18:00:00+05:30", "dataset": FLOW, "sha256": sha(FLOW)}],
            "figures": [
                {"id": "realty", "label": "Nifty Realty change %", "value": "-2.38", "as_of": "2026-10-23",
                 "source": "nse", "evidence": REALTY},
                {"id": "fii", "label": "FII net", "value": "887.65", "as_of": "2026-10-23", "source": "nsef",
                 "evidence": FII}]}

    def tearDown(self):
        self.tmp.cleanup()

    def test_real_exchange_lines_pass(self):
        ok, errs = SA.audit_datasets(self.col, root=self.root)
        self.assertTrue(ok, errs)

    def test_changed_number_in_quote_fails(self):
        c = copy.deepcopy(self.col)
        c["figures"][0]["evidence"] = REALTY.replace("-2.38%", "-3%")
        self.assertFalse(SA.audit_datasets(c, root=self.root)[0])

    def test_edited_raw_file_fails(self):
        f = self.root / IDX
        raw = gzip.decompress(f.read_bytes()).replace(b"784.35", b"794.35")
        f.write_bytes(gzip.compress(raw))
        ok, errs = SA.audit_datasets(self.col, root=self.root)
        self.assertFalse(ok)
        self.assertIn("sha256", " ".join(errs))

    def test_raw_file_and_source_hash_edited_together_still_fails(self):
        f = self.root / IDX
        raw = gzip.decompress(f.read_bytes()).replace(b"784.35", b"794.35")
        f.write_bytes(gzip.compress(raw))
        c = copy.deepcopy(self.col)
        c["sources"][0]["sha256"] = sha(IDX, self.root)
        c["figures"][0]["evidence"] = REALTY.replace("784.35", "794.35")
        ok, errs = SA.audit_datasets(c, root=self.root)
        self.assertFalse(ok)
        self.assertIn("collector recorded", " ".join(errs))

    def test_dataset_outside_archive_rejected(self):
        c = copy.deepcopy(self.col)
        c["sources"][0]["dataset"] = "data/meta.json"
        self.assertFalse(SA.audit_datasets(c, root=self.root)[0])
        c["sources"][0]["dataset"] = "data/market_snapshots/../meta.json.gz"
        self.assertFalse(SA.audit_datasets(c, root=self.root)[0])

    def test_missing_snapshot_fails_closed(self):
        shutil.rmtree(self.root / DAY)
        self.assertFalse(SA.audit_datasets(self.col, root=self.root)[0])

    def test_web_sources_untouched_by_offline_check(self):
        c = copy.deepcopy(self.col)
        c["sources"].append({"id": "web", "url": "https://example.com/x", "published": "2026-10-23T16:00:00+05:30"})
        c["figures"].append({"id": "w", "value": "1", "source": "web", "evidence": "nothing to see"})
        self.assertTrue(SA.audit_datasets(c, root=self.root)[0])


@unittest.skipUnless((ROOT / IDX).is_file(), "snapshot not in this checkout")
class DatasetJobEndToEnd(unittest.TestCase):
    """A job mixing a news source and an NSE dataset figure, through the offline pre-check."""
    def job(self, realty_quote=REALTY):
        sys.path.insert(0, str(ROOT / "pipeline" / "examples"))
        import make_v2_dryrun_jobs as EX
        j = copy.deepcopy([x for x in EX.JOBS if x["graphic"]["chart"]["type"] == "index_board"][0])
        j["slug"] = "2026-10-23-dataset-e2e"
        j["collection"]["sources"].append({"id": "nse", "name": "NSE India: all indices", "url": "https://www.nseindia.com/api/allIndices",
                                           "published": "2026-10-23T15:30:00+05:30", "dataset": IDX, "sha256": sha(IDX)})
        for f in j["collection"]["figures"]:
            if f["id"] == "realty":
                f.update(label="Nifty Realty change %", value="-2.38", source="nse", evidence=realty_quote)
        for i in j["graphic"]["chart"]["items"]:
            if i["label"] == "Realty":
                i["pct"] = "-2.38%"
        j["article"]["body"][1] = "The Nifty Midcap 100 fell 2.21% and the Smallcap 100 2.94%; the Nifty Realty index fell 2.38%."
        return j

    def check(self, j):
        from pipeline import __main__ as cli
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "job.json"
            p.write_text(json.dumps(j, ensure_ascii=False), encoding="utf-8")
            return cli.cmd_check([str(p)], root=ROOT)

    def test_exchange_figure_passes_offline_check(self):
        self.assertEqual(self.check(self.job()), 0)

    def test_misquoted_exchange_figure_blocked(self):
        self.assertNotEqual(self.check(self.job(REALTY.replace("high 802.2", "high 812.2"))), 0)


if __name__ == "__main__":
    unittest.main()
