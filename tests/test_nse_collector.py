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

    def test_top_level_timestamp_without_seconds(self):
        # NSE allIndices rows carry no per-row time; the payload has "timestamp": "23-Oct-2026 15:30"
        def fake(path):
            if path == "/api/allIndices":
                return {"timestamp": "23-Oct-2026 15:30", "data": [
                    {"index": "NIFTY 50", "last": 22600.0, "percentChange": -0.39}]}
            return {"data": []}
        result = collect("2026-10-23", fetch=fake)
        self.assertEqual(result["datasets"]["indices"]["rows"][0]["asOf"], "2026-10-23")
        self.assertEqual(result["diagnostics"]["indices"]["timestamp"], "23-Oct-2026 15:30")
        self.assertNotIn("22600", str(result["diagnostics"]))  # diagnostics never carry values

    def test_stale_top_level_timestamp_rejected(self):
        def fake(path):
            if path == "/api/allIndices":
                return {"timestamp": "22-Oct-2026 15:30", "data": [
                    {"index": "NIFTY 50", "last": 22600.0, "percentChange": -0.39}]}
            return {"data": []}
        self.assertNotIn("indices", collect("2026-10-23", fetch=fake)["datasets"])

    def test_movers_alternate_encoding(self):
        rows = [{"symbol": f"S{i}", "lastPrice": 100 + i, "pChange": i / 10,
                 "lastUpdateTime": "23-Oct-2026 16:00:00"} for i in range(50)]
        def fake(path):
            if path.endswith("NIFTY%2050"):
                raise ValueError("HTTP Error 404: Not Found")
            if path.endswith("NIFTY+50"):
                return {"data": rows}
            return {"data": []}
        result = collect("2026-10-23", fetch=fake)
        self.assertEqual(result["datasets"]["movers"]["count"], 50)
        self.assertFalse([e for e in result["errors"] if e.startswith("nifty50:")])


if __name__ == "__main__":
    unittest.main()
