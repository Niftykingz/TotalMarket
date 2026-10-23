"""Offline regression tests for missing-config publishing bypass."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pipeline import gate

class FailClosedGateTests(unittest.TestCase):
    def test_missing_config_enforces(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = gate.config(tmp)
            self.assertTrue(gate.enforced({"publishedAt": "2026-10-23T19:00:00+05:30"}, cfg))

    def test_missing_config_cannot_bypass_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            post = {"id": "blocked-story", "publishedAt": "2026-10-23T19:00:00+05:30"}
            ok, reason = gate.allowed(post, tmp)
            self.assertFalse(ok)
            self.assertIn("no pipeline run", reason)

    def test_new_post_after_cutoff_is_enforced(self):
        cfg = {"enforce_from": "2026-10-23T18:00:00+05:30"}
        self.assertTrue(gate.enforced({"publishedAt": "2026-10-23T19:00:00+05:30"}, cfg))

    def test_older_post_retains_legacy_behavior(self):
        cfg = {"enforce_from": "2026-10-23T18:00:00+05:30"}
        self.assertFalse(gate.enforced({"publishedAt": "2026-10-22T19:00:00+05:30"}, cfg))

    def test_remote_audit_is_default_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pipeline").mkdir()
            (root / "pipeline" / "config.json").write_text('{"enforce_from":"2026-10-23T18:00:00+05:30"}')
            self.assertTrue(gate.config(root).get("require_live_evidence", True))

if __name__ == "__main__":
    unittest.main()
