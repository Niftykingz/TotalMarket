"""Deterministic source-first recovery tests (no network)."""
import unittest
from pipeline.source_audit import recover_evidence

SOURCE = "https://example.com/story"
def collection(quote="outdated headline"):
    return {"sources":[{"id":"s","url":SOURCE,"name":"Example"}],
            "figures":[{"id":"nifty","source":"s","value":"25,600.00",
                        "change":"+120.00","evidence":quote}]}

class Recovery(unittest.TestCase):
    def test_replaces_bad_quote_with_actual_source_text(self):
        page="market close: nifty ended at 25,600.00, gaining +120.00 points on the day."
        repaired, errors = recover_evidence(collection(), fetcher=lambda _:page)
        self.assertEqual(errors, [])
        self.assertIn("25,600.00", repaired["figures"][0]["evidence"])
        self.assertIn("+120.00", repaired["figures"][0]["evidence"])
    def test_never_invents_missing_value(self):
        repaired, errors = recover_evidence(collection(), fetcher=lambda _:"market close: nifty 25,060.00")
        self.assertTrue(errors)
        self.assertEqual(repaired["figures"][0]["evidence"], "outdated headline")
    def test_unavailable_source_stays_unresolved(self):
        def fail(_):
            raise ValueError("publisher unavailable")
        _, errors = recover_evidence(collection(), fetcher=fail)
        self.assertTrue(errors)
if __name__=="__main__":
    unittest.main()
