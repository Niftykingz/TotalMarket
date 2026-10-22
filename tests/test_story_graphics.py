"""Story analysis and cover-template tests. Run: py -m unittest discover -s tests  (Windows) / python3 -m unittest discover -s tests"""
import os, sys, unittest, tempfile, json
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import graphics_selector as g
import tmdate

META = {"history": {
    "Sensex": [{"d": "2026-10-21", "v": 73709.69}, {"d": "2026-10-22", "v": 73249.39, "s": "HDFC Sky"}],
    "Nifty 50": [{"d": "2026-10-19", "v": 22888.95}, {"d": "2026-10-21", "v": 22811.35}, {"d": "2026-10-22", "v": 22687.65, "s": "IIFL"}],
    "Bank Nifty": [{"d": "2026-10-21", "v": 54976.90}, {"d": "2026-10-22", "v": 54832.35}]}}
IPOS = [{"name": "Fusion CX", "issuePrice": "₹289", "listingPrice": "₹305 (NSE), ₹292 (BSE)", "listing": "2026-10-22"},
        {"name": "Weak Co", "issuePrice": "₹100", "listingPrice": "₹92", "listing": "2026-10-22"},
        {"name": "Jio Platforms", "priceBand": "₹1,065–1,119"}]


def story(**kw):
    p = {"id": "t", "category": "markets", "title": "", "publishedAt": "2026-10-22T15:55:00+05:30"}
    p.update(kw)
    return p


class EventSelection(unittest.TestCase):
    def test_index_close_gets_index_chart_not_oil(self):
        p = story(title="Sensex falls 460 pts, Nifty ends near 22,688 as oil, West Asia weigh", editionLabel="Thu 22 Oct · Closing wrap")
        a = g.analyze(p, META, IPOS)
        self.assertEqual(a["event"], "index_move")
        self.assertEqual(a["template"], "index_chart")
        self.assertEqual(a["object"], "candles")  # never the oil barrel for an index story

    def test_daily_report_with_brent_in_title(self):
        p = story(title="Stock market today: Sensex sheds 460 pts, Nifty 22,687.65 as oil jumps to $112", report={"date": "2026-10-22"})
        self.assertEqual(g.analyze(p, META, IPOS)["template"], "index_chart")

    def test_earnings_needs_structured_figures(self):
        p = story(title="Adani Green Q2: profit ₹747 crore, down 24%", companies=[{"name": "Adani Green Energy"}])
        a = g.analyze(p, META, IPOS)
        self.assertEqual(a["event"], "earnings")
        self.assertEqual(a["template"], "illustration")  # no `figures` -> no numbers drawn
        p["figures"] = [{"company": "Adani Green Energy", "label": "Net profit", "value": "₹747 cr", "change": "−24%"}]
        a = g.analyze(p, META, IPOS)
        self.assertEqual(a["template"], "earnings_card")
        self.assertEqual(a["direction"], "down")

    def test_earnings_growth(self):
        p = story(title="Eternal Q2 results: profit up 92%", companies=[{"name": "Eternal"}],
                  figures=[{"label": "Net profit", "value": "₹125 cr", "change": "+92%"}])
        self.assertEqual(g.analyze(p)["direction"], "up")

    def test_rbi_and_tech_and_global(self):
        self.assertEqual(g.analyze(story(category="policy", title="RBI keeps repo rate unchanged"))["object"], "bank")
        self.assertEqual(g.analyze(story(category="tech", title="Critical PHP flaws found with AI help"))["object"], "shield")
        self.assertEqual(g.analyze(story(category="global", title="Evening markets: Nasdaq slides on AI jitters"))["object"], "globe")

    def test_ipo_roundup_is_not_a_single_listing_card(self):
        p = story(category="startups", title="IPO today (22 Oct): Jio 5.51x, Fusion CX lists at 5.5% premium")
        self.assertEqual(g.analyze(p, META, IPOS)["template"], "illustration")


class Figures(unittest.TestCase):
    def test_sensex_and_nifty_are_separate(self):
        p = story(title="Sensex falls 460 pts; Nifty ends near 22,688", editionLabel="Thu 22 Oct · Closing wrap")
        f = {x["label"]: x for x in g.analyze(p, META, IPOS)["figures"]}
        self.assertEqual(f["Sensex"]["value"], "73,249.39")
        self.assertEqual(f["Nifty 50"]["value"], "22,687.65")
        self.assertEqual(f["Sensex"]["change"], "-460.30")
        self.assertEqual(f["Nifty 50"]["pct"], "-0.54%")

    def test_bank_nifty_not_counted_as_nifty(self):
        self.assertEqual(g.instruments_in("Bank Nifty slips 0.26%"), ["Bank Nifty"])
        self.assertEqual(g.instruments_in("Sensex and Nifty 50 fall; Brent at $112"), ["Nifty 50", "Sensex", "Brent"])

    def test_midday_story_gets_no_closing_figures(self):
        p = story(title="Sensex down 471 pts, Nifty at 22,636 by noon", editionLabel="Thu 22 Oct · Midday check")
        a = g.analyze(p, META, IPOS)
        self.assertEqual(a["figures"], [])
        self.assertEqual(a["template"], "illustration")

    def test_missing_history_falls_back(self):
        p = story(title="Sensex falls; Nifty ends lower", editionLabel="Thu 22 Oct · Closing wrap", publishedAt="2026-10-23T16:00:00+05:30")
        self.assertEqual(g.analyze(p, META, IPOS)["template"], "illustration")

    def test_ipo_gain_and_loss(self):
        up = g.analyze(story(category="startups", title="Fusion CX lists at ₹305 on NSE, 5.5% above its ₹289 IPO price"), META, IPOS)
        self.assertEqual(up["template"], "ipo_card")
        self.assertEqual(up["figures"][0]["pct"], "+5.54%")
        self.assertEqual(up["direction"], "up")
        down = g.analyze(story(category="startups", title="Weak Co lists at ₹92, below its IPO price"), META, IPOS)
        self.assertEqual(down["figures"][0]["pct"], "-8.00%")
        self.assertEqual(down["direction"], "down")

    def test_ipo_without_listing_price(self):
        a = g.analyze(story(category="startups", title="Jio Platforms IPO listing: GMP hints at premium"), META, IPOS)
        self.assertEqual(a["template"], "illustration")


class Dates(unittest.TestCase):
    def test_date_and_datetime(self):
        self.assertEqual(tmdate.fmt(date(2026, 10, 2), "%a %-d %b"), "Fri 2 Oct")
        self.assertEqual(tmdate.fmt(datetime(2026, 10, 22, 15, 5), "%-d %b %Y, %-I:%M %p"), "22 Oct 2026, 3:05 PM")
        self.assertEqual(tmdate.fmt("2026-10-22T09:15:00+05:30", "%-I:%M"), "9:15")
        self.assertEqual(tmdate.fmt("2026-10-22", "%-d %B"), "22 October")


class CoverRendering(unittest.TestCase):
    def test_templates_render(self):
        import cover_templates as ct
        with tempfile.TemporaryDirectory() as d:
            cases = [(story(title="Sensex falls; Nifty ends lower", editionLabel="x · Closing wrap"), "index_chart"),
                     (story(title="Fusion CX lists at ₹305 on NSE", category="startups"), "ipo_card"),
                     (story(title="X Q2 results", companies=[{"name": "X"}], figures=[{"company": "X", "label": "Net profit", "value": "₹1 cr", "change": "+1%"}]), "earnings_card")]
            for i, (p, tpl) in enumerate(cases):
                a = g.analyze(p, META, IPOS)
                self.assertEqual(a["template"], tpl)
                w, j = os.path.join(d, f"{i}.webp"), os.path.join(d, f"{i}.jpg")
                ct.TEMPLATES[tpl](p, a, w, j)
                from PIL import Image
                self.assertEqual(Image.open(w).size, (1600, 900))
                self.assertEqual(Image.open(j).size, (1200, 675))


class PageGeneration(unittest.TestCase):
    def test_build_outputs_exist(self):
        out = os.path.join(ROOT, "docs")
        for rel in ("index.html", "markets/index.html", "tech/index.html", "hi/index.html", "sitemap.xml", "news-sitemap.xml"):
            self.assertTrue(os.path.exists(os.path.join(out, rel)), rel)
        html = open(os.path.join(out, "index.html"), encoding="utf-8").read()
        self.assertIn('class="trow"', html)          # responsive ticker present
        self.assertNotIn(">LIVE<", html)              # never labelled live
        self.assertIn('rel="canonical"', html)


if __name__ == "__main__":
    unittest.main()
