"""Offline tests for source provenance gate; never access the internet."""
import unittest
from pipeline import source_audit

SAMPLE = {
    "sources": [{"id": "official", "url": "https://example.org/release"}],
    "figures": [
        {"id": "price", "source": "official",
         "evidence": "The reported closing price was 123.45 rupees."}
    ],
}

class EvidenceAuditTests(unittest.TestCase):
    def test_matching_quote(self):
        ok, errors = source_audit.audit(
            SAMPLE, fetcher=lambda url: source_audit.clean(
                "Press release: The reported closing price was 123.45 rupees."))
        self.assertTrue(ok, errors)

    def test_invented_quote_rejected(self):
        ok, errors = source_audit.audit(
            SAMPLE, fetcher=lambda url: "There is no financial price in this page.")
        self.assertFalse(ok)
        self.assertIn("not found", errors[0])

    def test_unavailable_source_rejected(self):
        def unavailable(url):
            raise source_audit.EvidenceError("offline")
        ok, errors = source_audit.audit(SAMPLE, fetcher=unavailable)
        self.assertFalse(ok)
        self.assertIn("offline", errors[0])

    def test_private_hosts_rejected_before_network(self):
        for url in ("http://example.org", "https://localhost/x",
                    "https://127.0.0.1/x", "https://user:pass@example.org/x"):
            with self.subTest(url=url), self.assertRaises(source_audit.EvidenceError):
                source_audit.safe_url(url)

    def test_source_fetched_once_for_multiple_figures(self):
        job = {"sources": SAMPLE["sources"],
               "figures": SAMPLE["figures"] * 2}
        calls = []
        def fetch(url):
            calls.append(url)
            return source_audit.clean(SAMPLE["figures"][0]["evidence"])
        ok, errors = source_audit.audit(job, fetcher=fetch)
        self.assertTrue(ok, errors)
        self.assertEqual(len(calls), 1)

if __name__ == "__main__":
    unittest.main()
