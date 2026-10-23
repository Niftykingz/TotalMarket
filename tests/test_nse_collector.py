"""Offline tests: reject stale data and preserve partial results without fabrication."""
import unittest
from pipeline.market_data.collect_nse import collect


class MarketCollectionTests(unittest.TestCase):
    def test_stale_data_is_not_accepted(self):
        def fake(path):
            if path == "/api/allIndices":
                return {"data": [{"index": "NIFTY 50", "last": 22600,
                                  "percentChange": -0.39, "lastUpdateTime": "22-Oct-2026 15:30:00"}]}
            return []
        result = collect("2026-10-23", fetch=fake)
        self.assertNotIn("indices", result["datasets"])
        self.assertEqual(result["status"], "partial")

    def test_verified_date_index_and_flows(self):
        def fake(path):
            if path == "/api/allIndices":
                return {"data": [{"index": "NIFTY 50", "last": "22,600",
                                  "percentChange": -0.39, "lastUpdateTime": "23-Oct-2026 15:30:00"}]}
            if path == "/api/fiidiiTradeReact":
                return [{"date": "23-Oct-2026", "category": "FII", "netValue": "-200"},
                        {"date": "23-Oct-2026", "category": "DII", "netValue": "250"}]
            return {"data": []}
        result = collect("2026-10-23", fetch=fake)
        self.assertEqual(result["datasets"]["indices"]["rows"][0]["close"], 22600.0)
        self.assertEqual(len(result["datasets"]["institutionalFlows"]["rows"]), 2)
        self.assertNotIn("movers", result["datasets"])


if __name__ == "__main__":
    unittest.main()
