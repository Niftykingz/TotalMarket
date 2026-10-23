"""IPO timeline in IST: opens 10 am, bidding closes 5 pm, allotment day, trading from 10 am on listing day."""
import os
import sys
import unittest
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import hubs  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
JIO = {"name": "Jio Platforms", "open": "2026-10-21", "close": "2026-10-23", "allotment": "2026-10-26", "listing": "2026-10-28"}


def at(d, h, m=0):
    return datetime(2026, 10, d, h, m, tzinfo=IST)


class Timeline(unittest.TestCase):
    def test_status_through_the_ipo_week(self):
        cases = [((21, 9, 59), "upcoming"), ((21, 10, 0), "open"), ((23, 16, 59), "open"), ((23, 17, 0), "closed"),
                 ((23, 22, 56), "closed"), ((26, 12), "closed"), ((27, 18), "closed"), ((28, 9, 30), "listing"), ((28, 10, 30), "listing")]
        for (d, h, *m), want in cases:
            with self.subTest(at=(d, h, *m)):
                self.assertEqual(hubs.ipo_status(JIO, at(d, h, *m)), want)

    def test_reader_phase_lines(self):
        self.assertEqual(hubs.ipo_phase(JIO, at(21, 9)), "Opens today, 10 am")
        self.assertEqual(hubs.ipo_phase(JIO, at(23, 11)), "Bidding closes today, 5 pm")
        self.assertEqual(hubs.ipo_phase(JIO, at(22, 11)), "Bidding closes tomorrow, 5 pm")
        self.assertTrue(hubs.ipo_phase(JIO, at(23, 17, 30)).startswith("Bidding closed · allotment Mon 26 Oct"))
        self.assertTrue(hubs.ipo_phase(JIO, at(26, 12)).startswith("Allotment today"))
        self.assertEqual(hubs.ipo_phase(JIO, at(27, 12)), "Allotment done · lists tomorrow, 10 am")
        self.assertEqual(hubs.ipo_phase(JIO, at(28, 9)), "Lists today, trading from 10 am")
        self.assertEqual(hubs.ipo_phase(JIO, at(28, 11)), "Listing today · trading now")

    def test_listed_once_listing_price_recorded(self):
        x = dict(JIO, listingPrice=1200, listed=True)
        self.assertEqual(hubs.ipo_status(x, at(28, 10, 5)), "listed")

    def test_custom_close_time_override(self):
        x = dict(JIO, closeTime="16:00")
        self.assertEqual(hubs.ipo_status(x, at(23, 16, 30)), "closed")

    def test_date_only_input_still_works(self):
        self.assertEqual(hubs.ipo_status(JIO, date(2026, 10, 22)), "open")
        self.assertEqual(hubs.ipo_status(JIO, date(2026, 10, 24)), "closed")

    def test_browser_attributes(self):
        a = hubs.ipo_data_attrs(JIO)
        self.assertIn('data-ipo-close="2026-10-23T17:00:00+05:30"', a)
        self.assertIn('data-ipo-open="2026-10-21T10:00:00+05:30"', a)
        self.assertIn('data-ipo-list="2026-10-28T10:00:00+05:30"', a)


if __name__ == "__main__":
    unittest.main()
