"""Publish queue: failure isolation, archiving, live check, offline mode and published-article stability."""
import copy
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from pipeline import core, gate, queue  # noqa: E402
from pipeline import __main__ as cli  # noqa: E402
from test_pipeline import Base, JOB  # noqa: E402


def offline(root):
    p = root / "pipeline" / "config.json"
    cfg = json.loads(p.read_text())
    cfg["require_live_evidence"] = False
    p.write_text(json.dumps(cfg))


class Queue(Base):
    def setUp(self):
        super().setUp()
        offline(self.root)

    def test_failed_job_does_not_block_good_job(self):
        good = copy.deepcopy(JOB)
        bad = copy.deepcopy(JOB)
        bad["slug"] = "2026-10-23-broken-story"
        bad["article"]["body"].append("Analysts expect 24,000.")
        for j in (good, bad):
            (self.root / "pipeline" / "inbox" / f"{j['slug']}.json").write_text(json.dumps(j), encoding="utf-8")
        (self.root / "pipeline" / "inbox" / "zz-not-json.json").write_text("{oops", encoding="utf-8")
        st = queue.run_jobs(self.root)
        self.assertEqual(st[good["slug"]], "READY")
        self.assertIn("FAILED", st[bad["slug"]])
        self.assertIn("unreadable", st["zz-not-json"])

    def test_only_published_jobs_are_archived(self):
        p = self.root / "pipeline" / "inbox" / f"{JOB['slug']}.json"
        p.write_text(json.dumps(JOB), encoding="utf-8")
        run = core.run_job(p, self.root)
        self.assertEqual(queue.archive_published(self.root), [])          # READY but not published yet
        sha = run.save(6, {"commit": "abc", "post_sha256": run.load(4)["post_sha256"]})
        run.record(6, "PASS", sha=sha)
        self.assertEqual(queue.archive_published(self.root), [JOB["slug"]])
        self.assertTrue((self.root / "pipeline" / "archive" / p.name).is_file())

    def test_live_check_waits_for_the_page(self):
        calls = {"n": 0}

        class R:
            def __init__(self, body): self.status, self.body = 200, body
            def read(self, n): return self.body
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def opener(req, timeout):
            calls["n"] += 1
            return R(b"<html>2026-10-23-test-close-story</html>" if calls["n"] > 1 else b"old")
        with mock.patch.object(queue.time, "sleep", lambda s: None):
            self.assertEqual(queue.live_check(["2026-10-23-test-close-story"], timeout_s=60, opener=opener), [])

    def test_offline_check_never_writes_to_repo_and_publish_refuses_offline(self):
        before = sorted(str(x) for x in (ROOT / "data" / "posts").glob("*.json"))
        job = self.root / "job.json"
        job.write_text(json.dumps(JOB), encoding="utf-8")
        self.assertEqual(cli.cmd_check([str(job)], root=self.root), 0)
        self.assertEqual(sorted(str(x) for x in (ROOT / "data" / "posts").glob("*.json")), before)
        self.assertFalse((self.root / "data" / "posts" / f"{JOB['slug']}.json").exists())
        with mock.patch.dict(os.environ, {"TM_PIPELINE_OFFLINE": "1"}):
            self.assertEqual(cli.main(["publish"]), 4)


class PublishedStability(Base):
    def test_published_article_survives_source_drift_but_new_ones_do_not(self):
        p = self.root / "pipeline" / "inbox" / f"{JOB['slug']}.json"
        p.write_text(json.dumps(JOB), encoding="utf-8")
        with mock.patch("pipeline.source_audit.audit", return_value=(True, [])):
            run = core.run_job(p, self.root)
        self.assertEqual(core.status(run), "READY")
        post = dict(json.loads((self.root / "data" / "posts" / f"{JOB['slug']}.json").read_text()), id=JOB["slug"])
        drift = mock.patch("pipeline.source_audit.audit", return_value=(False, ["x: evidence quote not found on source page"]))
        with drift:
            self.assertFalse(gate.allowed(dict(post), self.root)[0])     # not yet published: blocked
        sha = run.save(6, {"commit": "abc", "post_sha256": run.load(4)["post_sha256"]})
        run.record(6, "PASS", sha=sha)
        with drift:
            self.assertTrue(gate.allowed(dict(post), self.root)[0])      # published: stays live


if __name__ == "__main__":
    unittest.main()


class HindiDates(unittest.TestCase):
    def test_hindi_dates_and_times_are_not_figures(self):
        from pipeline import numbers as N
        got = [raw for raw, _, _ in N.mentions("allotment 26 अक्टूबर, ट्रेडिंग सुबह 10 बजे से; 23 अक्टूबर 2026 को ₹26 करोड़")]
        self.assertEqual(got, ["₹26"])
