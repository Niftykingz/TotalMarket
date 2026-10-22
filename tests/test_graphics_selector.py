"""Smoke tests: run with python3 -m unittest discover -s tests."""
import unittest
from graphics_selector import choose_cover_object

class CoverSelectorTests(unittest.TestCase):
    def test_earnings(self):
        self.assertEqual(choose_cover_object({"category":"markets","title":"Company quarterly earnings beat forecasts"}),"coins")
    def test_rbi(self):
        self.assertEqual(choose_cover_object({"category":"markets","title":"RBI monetary policy decision"}),"bank")
    def test_market_wrap(self):
        self.assertEqual(choose_cover_object({"category":"markets","title":"Nifty falls at closing"}),"candles")
    def test_ai(self):
        self.assertEqual(choose_cover_object({"category":"tech","title":"AI chip launch"}),"chip")
    def test_ipo(self):
        self.assertEqual(choose_cover_object({"category":"startups","title":"IPO subscription opens"}),"growth")
if __name__=="__main__": unittest.main()
