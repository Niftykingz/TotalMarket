"""Strict publishing pipeline tests. Offline; each test uses a temporary site root.
Run: py -m unittest discover -s tests   (Windows)   /   python3 -m unittest discover -s tests
"""
import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import core, gate  # noqa: E402
from pipeline import __main__ as cli  # noqa: E402

BS = "https://www.business-standard.com/markets/news/stock-market-live-october-23-nse-bse-sensex-today-nifty50-gift-nifty-crude-oil-prices-jio-ipo-q2-results-today-126102300078_1.html"
CM = "https://www.chinimandi.com/sensex-down-125-points-nifty-at-22600/"

JOB = {
 "slug": "2026-10-23-test-close-story",
 "collection": {
  "sources": [{"id": "bs", "name": "Business Standard: Market close, 23 Oct", "url": BS, "published": "2026-10-23T15:41:00+05:30"},
              {"id": "cm", "name": "ChiniMandi: Sensex down 125 points", "url": CM, "published": "2026-10-23T15:45:00+05:30"}],
  "figures": [
   {"id": "sensex", "label": "Sensex close", "value": "73,123.83", "change": "-125.56", "as_of": "2026-10-23", "source": "cm", "key": True,
    "evidence": "Sensex closed at 73,123.83, down 125.56 points"},
   {"id": "nifty", "label": "Nifty 50 close", "value": "22,600.00", "change": "-87.65", "as_of": "2026-10-23", "source": "cm", "key": True,
    "evidence": "Nifty 50 ended at 22,600.00, down 87.65 points"},
   {"id": "nifty_pct", "label": "Nifty 50 change %", "value": "-0.39", "as_of": "2026-10-23", "source": "bs", "evidence": "down 87.65 points (0.39%)"},
   {"id": "small", "label": "Nifty Smallcap 100 change %", "value": "-2.94", "as_of": "2026-10-23", "source": "bs", "evidence": "the Nifty Smallcap 100 fell 2.94%"}],
  "examples": [{"id": "ex1", "value": "10,000", "note": "illustrative ₹10,000 investment"}, {"id": "ex2", "value": "9,706", "note": "₹10,000 after a 2.94% fall"}]
 },
 "graphic": {"headline": "Sensex, Nifty fall for a fourth day", "coverHeadline": "NIFTY ENDS AT 22,600", "stat": "-0.39%",
             "statLabel": "Nifty 50 closes at 22,600.00", "symbol": "candles", "flags": ["IN"], "coverDate": "2026-10-23",
             "chart": {"type": "index_board", "title": "Indian markets · close", "asOf": "Close, 23 Oct 2026", "source": "ChiniMandi, Business Standard",
                       "items": [{"label": "Sensex", "value": "73,123.83", "change": "-125.56"},
                                 {"label": "Nifty 50", "value": "22,600.00", "change": "-87.65", "pct": "-0.39%"},
                                 {"label": "Smallcap 100", "pct": "-2.94%"}]}},
 "article": {
  "title": "Sensex, Nifty fall for a fourth day: Nifty ends at 22,600, small caps drop 2.94%",
  "dek": "The Sensex closed 125.56 points lower at 73,123.83.",
  "category": "markets", "lead": True, "readMins": 2,
  "body": ["The Sensex ended at 73,123.83, down 125.56 points, and the Nifty 50 at 22,600.00, down 87.65 points (0.39%).",
           "Worked example: ₹10,000 in a small-cap index fund would be about ₹9,706 after a 2.94% fall.",
           "Key takeaway: smaller stocks fell harder than the index."],
  "indiaImpact": "Small-cap investors had a worse day than the Nifty suggests.",
  "seoTitle": "Sensex, Nifty Close: Nifty Ends at 22,600",
  "seoDescription": "Stock market close 23 Oct 2026: Sensex falls 125.56 points to 73,123.83 and Nifty 87.65 points to 22,600.00; Smallcap 100 −2.94%.",
  "sources": [{"name": "ChiniMandi", "url": CM}, {"name": "Business Standard", "url": BS}],
  "edition": "2026-10-23-close", "editionLabel": "Fri 23 Oct · Closing wrap", "publishedAt": "2026-10-23T15:52:00+05:30", "status": "new"
 }
}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="tm pipe ")
        self.root = Path(self.tmp.name)
        for d in ("data/posts", "logos", "pipeline/inbox"):
            (self.root / d).mkdir(parents=True)
        for f in ("meta.json", "ipos.json", "company-logos.json"):
            shutil.copy(ROOT / "data" / f, self.root / "data" / f)
        (self.root / "pipeline" / "config.json").write_text(json.dumps({"enforce_from": "2026-10-23T15:00:00+05:30"}))
        self._log, core.LOG = core.LOG, self.root / "pipeline" / "log.jsonl"
        # Legacy stage tests exercise numeric/graphics/QA logic; independent
        # source fetching is tested separately with deterministic offline fixtures.
        self._remote_patch = patch("pipeline.source_audit.audit", return_value=(True, []))
        self._remote_patch.start()

    def tearDown(self):
        self._remote_patch.stop()
        core.LOG = self._log
        self.tmp.cleanup()

    def job(self, mutate=None):
        j = copy.deepcopy(JOB)
        if mutate:
            mutate(j)
        p = self.root / "pipeline" / "inbox" / f"{j['slug']}.json"
        p.write_text(json.dumps(j, ensure_ascii=False), encoding="utf-8")
        return p, j

    def run_(self, mutate=None):
        p, j = self.job(mutate)
        return core.run_job(p, self.root), j

    def post_path(self, j):
        return self.root / "data" / "posts" / f"{j['slug']}.json"

    def failed_at(self, run):
        return core.status(run)


class HappyPath(Base):
    def test_all_stages_pass_and_save_artifacts_in_order(self):
        run, j = self.run_()
        self.assertEqual(core.status(run), "READY")
        times = []
        for i, s in enumerate(core.STAGES[:5], 1):
            st = run.m["stages"][s]
            self.assertEqual(st["status"], "PASS")
            self.assertEqual(core.sha_file(run.artifact(i, s)), st["sha256"])
            times.append(st["finished"])
        self.assertEqual(times, sorted(times))
        self.assertTrue((run.dir / "cover.jpg").is_file())
        self.assertTrue(self.post_path(j).is_file())
        ok, why = gate.allowed(dict(json.loads(self.post_path(j).read_text()), id=j["slug"]), self.root)
        self.assertTrue(ok, why)

    def test_log_records_every_stage(self):
        self.run_()
        lines = [json.loads(l) for l in core.LOG.read_text(encoding="utf-8").splitlines()[-5:]]
        self.assertEqual([l["stage"] for l in lines], core.STAGES[:5])


class Verification(Base):
    def test_value_not_in_evidence_rejected_and_blocks_article(self):
        def m(j):
            j["collection"]["figures"][3]["evidence"] = "small caps fell sharply"
        run, j = self.run_(m)
        rej = run.load(2)["rejected"]
        self.assertEqual([r["id"] for r in rej], ["small"])
        self.assertIn("FAILED at GRAPHICS_GENERATION", core.status(run))   # the chart shows the rejected figure
        self.assertFalse(self.post_path(j).exists())

    def test_key_figure_rejection_fails_verification(self):
        def m(j):
            j["collection"]["figures"][1]["evidence"] = "Nifty ended lower"
        run, _ = self.run_(m)
        self.assertIn("FAILED at DATA_VERIFICATION", core.status(run))

    def test_conflicting_values_rejected(self):
        def m(j):
            j["collection"]["figures"].append({"id": "sensex2", "label": "Sensex close", "value": "73,100.00", "as_of": "2026-10-23",
                                               "source": "bs", "evidence": "Sensex at 73,100.00"})
        run, _ = self.run_(m)
        self.assertIn("FAILED at DATA_VERIFICATION", core.status(run))   # sensex is a key figure
        self.assertEqual(sorted(r["id"] for r in run.load(2)["rejected"]), ["sensex", "sensex2"])

    def test_stale_figure_rejected(self):
        def m(j):
            j["collection"]["figures"][3]["as_of"] = "2026-10-10"
        run, _ = self.run_(m)
        self.assertIn("small", [r["id"] for r in run.load(2)["rejected"]])

    def test_collection_requires_https_sources_and_evidence(self):
        def m(j):
            j["collection"]["sources"][0]["url"] = "http://insecure.example/x"
            j["collection"]["figures"][0]["evidence"] = ""
        run, _ = self.run_(m)
        self.assertIn("FAILED at DATA_COLLECTION", core.status(run))


class Graphics(Base):
    def test_unverified_number_on_graphic_fails(self):
        def m(j):
            j["graphic"]["coverHeadline"] = "NIFTY CRASHES 3.5%"
        run, j = self.run_(m)
        self.assertIn("FAILED at GRAPHICS_GENERATION", core.status(run))
        self.assertFalse(self.post_path(j).exists())

    def test_worked_example_never_allowed_on_graphic(self):
        def m(j):
            j["graphic"]["statLabel"] = "₹10,000 becomes ₹9,706"
        run, _ = self.run_(m)
        self.assertIn("FAILED at GRAPHICS_GENERATION", core.status(run))

    def test_unapproved_logo_file_fails(self):
        (self.root / "logos" / "infy.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")

        def m(j):
            j["graphic"]["companies"] = [{"name": "Infosys", "ticker": "INFY"}]
        run, _ = self.run_(m)
        self.assertIn("FAILED at GRAPHICS_GENERATION", core.status(run))
        self.assertIn("logo", core.status(run))


class Article(Base):
    def test_unverified_number_in_article_fails(self):
        def m(j):
            j["article"]["body"].append("Analysts expect the Nifty to reach 24,000 by Diwali.")
        run, j = self.run_(m)
        self.assertIn("FAILED at ARTICLE_WRITING", core.status(run))
        self.assertFalse(self.post_path(j).exists())

    def test_example_number_not_allowed_in_headline(self):
        def m(j):
            j["article"]["title"] += " — ₹10,000 becomes ₹9,706"
        run, _ = self.run_(m)
        self.assertIn("FAILED at ARTICLE_WRITING", core.status(run))

    def test_uncollected_source_fails(self):
        def m(j):
            j["article"]["sources"].append({"name": "Random blog", "url": "https://blog.example/x"})
        run, _ = self.run_(m)
        self.assertIn("FAILED at ARTICLE_WRITING", core.status(run))

    def test_derived_numbers_are_recomputed(self):
        def m(j):  # 73,123.83 + 125.56 = previous close 73,249.39 (a derivation of verified figures)
            j["collection"]["figures"].append({"id": "sx_prev", "label": "Sensex previous close", "value": "73,249.39", "as_of": "2026-10-22",
                                               "source": "cm", "evidence": "previous close 73,249.39"})
            j["article"]["body"].insert(1, "That is a fall of 125.56 points from 73,249.39.")
        run, _ = self.run_(m)
        self.assertEqual(core.status(run), "READY")


class QA(Base):
    def test_placeholder_text_fails_qa(self):
        def m(j):
            j["article"]["body"].append("TODO add rupee figure.")
        run, _ = self.run_(m)
        self.assertIn("FAILED at FINAL_QA", core.status(run))

    def test_demo_text_fails_qa(self):
        def m(j):
            j["article"]["dek"] += " This is demonstration data."
        run, _ = self.run_(m)
        self.assertIn("FAILED at FINAL_QA", core.status(run))

    def test_date_mismatch_fails_qa(self):
        def m(j):
            j["article"]["publishedAt"] = "2026-10-24T09:00:00+05:30"
        run, _ = self.run_(m)
        self.assertIn("FAILED at FINAL_QA", core.status(run))


class Gate(Base):
    def post(self, j):
        return dict(json.loads(self.post_path(j).read_text(encoding="utf-8")), id=j["slug"])

    def test_edit_after_pass_blocks(self):
        run, j = self.run_()
        p = self.post(j)
        p["title"] += " (edited)"
        p.pop("id")
        self.post_path(j).write_text(json.dumps(p, ensure_ascii=False))
        ok, why = gate.allowed(dict(p, id=j["slug"]), self.root)
        self.assertFalse(ok)
        self.assertIn("differs", why)

    def test_tampered_artifact_blocks(self):
        run, j = self.run_()
        a = run.artifact(2, core.STAGES[1])
        a.write_text(a.read_text().replace("73,123.83", "74,000.00"))
        self.assertFalse(gate.allowed(self.post(j), self.root)[0])

    def test_forged_manifest_cannot_unlock(self):
        def m(j):
            j["article"]["body"].append("Analysts expect 24,000.")
        run, j = self.run_(m)
        self.assertIn("FAILED", core.status(run))
        # forge: write the post anyway and mark every stage PASS with matching hashes
        art = run.load(4)
        self.post_path(j).write_text(json.dumps(art["post"], ensure_ascii=False))
        art["post_sha256"] = core.sha_file(self.post_path(j))
        sha4 = run.save(4, art)
        run.m["stages"]["ARTICLE_WRITING"] = {"status": "PASS", "sha256": sha4, "errors": [], "started": core.now(), "finished": core.now()}
        sha5 = run.save(5, {"forged": True})
        run.m["stages"]["FINAL_QA"] = {"status": "PASS", "sha256": sha5, "errors": [], "started": core.now(), "finished": core.now()}
        run.save_manifest()
        ok, why = gate.allowed(self.post(j), self.root)
        self.assertFalse(ok)
        self.assertIn("QA re-check failed", why)

    def test_no_run_blocks_enforced_post_but_legacy_allowed(self):
        p = {"id": "2026-10-23-no-run", "publishedAt": "2026-10-23T16:00:00+05:30"}
        self.assertFalse(gate.allowed(p, self.root)[0])
        old = {"id": "2026-10-22-old", "publishedAt": "2026-10-22T16:00:00+05:30"}
        self.assertTrue(gate.allowed(old, self.root)[0])
        old["updatedAt"] = "2026-10-23T16:00:00+05:30"   # updating an old story after enforcement needs a run
        self.assertFalse(gate.allowed(old, self.root)[0])

    def test_stage_cannot_run_out_of_order(self):
        run, j = self.run_()
        run.m["stages"].pop("DATA_VERIFICATION")
        run.save_manifest()
        with self.assertRaises(core.StageError):
            run.require(4)

    def test_retry_after_fix_restarts_cleanly(self):
        def bad(j):
            j["article"]["body"].append("Analysts expect 24,000.")
        run, j = self.run_(bad)
        self.assertIn("FAILED", core.status(run))
        run, j = self.run_()           # fixed job file → restarts from stage 1
        self.assertEqual(core.status(run), "READY")

    def test_gate_pins_verified_graphic_and_respects_disabled_enforcement(self):
        run, j = self.run_()
        p = self.post(j)
        ok, _ = gate.allowed(p, self.root)
        self.assertTrue(ok)
        self.assertEqual(p["_analysis"]["template"], run.load(3)["analysis"]["template"])
        (self.root / "pipeline" / "config.json").write_text(json.dumps({"enforce_from": None}))
        self.assertFalse(gate.allowed({"id": "2026-10-23-x", "publishedAt": "2026-10-23T16:00:00+05:30"}, self.root)[0])

    def test_built_checks(self):
        out = self.root / "out"
        (out / "news" / "a").mkdir(parents=True)
        (out / "covers").mkdir()
        (out / "news" / "a" / "index.html").write_text('<img src="/covers/a-1.webp">')
        (out / "covers" / "a-1.webp").write_bytes(b"x")
        (out / "news" / "b").mkdir()
        (out / "news" / "b" / "index.html").write_text("blocked page")
        errs = cli.built_checks(out, [("a", True, "pipeline PASS"), ("b", False, "no run"), ("c", True, "pipeline PASS")])
        self.assertEqual(len(errs), 2)


if __name__ == "__main__":
    unittest.main()
