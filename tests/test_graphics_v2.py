"""Data-driven graphics v2: every layout, missing data, wrong figures, and publishing rules.
Offline; uses the real-figure dry-run jobs in pipeline/examples. Run: python3 -m unittest discover -s tests"""
import copy
import glob
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "pipeline" / "examples"))
import covers  # noqa: E402
import graphics_selector as gs  # noqa: E402
from PIL import Image  # noqa: E402
from pipeline import core, gate  # noqa: E402
from test_pipeline import Base  # noqa: E402
import make_v2_dryrun_jobs as EX  # noqa: E402

JOBS = {j["graphic"]["chart"]["type"]: j for j in EX.JOBS}
LAYOUTS = ["index_board", "global_bars", "commodity_card", "forex_card", "policy_rate", "stock_move", "ipo_subscription", "earnings_v2"]


class V2(Base):
    def run_job(self, j):
        p = self.root / "pipeline" / "inbox" / f"{j['slug']}.json"
        p.write_text(json.dumps(j, ensure_ascii=False), encoding="utf-8")
        return core.run_job(p, self.root)

    def mutated(self, layout, fn):
        j = copy.deepcopy(JOBS[layout])
        fn(j)
        return self.run_job(j)


class AllLayouts(V2):
    def test_every_layout_renders_from_verified_figures(self):
        seen = set()
        for layout in LAYOUTS:
            with self.subTest(layout=layout):
                run = self.run_job(copy.deepcopy(JOBS[layout]))
                self.assertEqual(core.status(run), "READY", core.status(run))
                a = run.load(3)["analysis"]
                self.assertEqual(a["template"], layout)
                img = run.dir / "cover.jpg"
                with Image.open(img) as im:
                    self.assertEqual(im.size, (1200, 675))
                seen.add(core.sha_file(img))
        self.assertEqual(len(seen), len(LAYOUTS))  # eight different graphics

    def test_example_jobs_never_in_inbox(self):
        self.assertFalse([f for f in glob.glob(str(ROOT / "pipeline" / "inbox" / "*.json")) if "-v2-" in f])


class MissingData(V2):
    def test_financial_story_without_chart_is_blocked_not_illustrated(self):
        for layout in ("commodity_card", "forex_card", "global_bars", "ipo_subscription", "earnings_v2", "policy_rate", "stock_move"):
            with self.subTest(layout=layout):
                run = self.mutated(layout, lambda j: j["graphic"].pop("chart"))
                st = core.status(run)
                self.assertIn("FAILED at GRAPHICS_GENERATION", st)
                self.assertIn("MISSING_DATA", st)
                self.assertIn("retry", run.m)

    def test_chart_missing_required_items_is_blocked(self):
        def m(j):
            j["graphic"]["chart"]["items"][0].pop("prev"); j["graphic"]["chart"]["items"][0].pop("change")
        st = core.status(self.mutated("forex_card", m))
        self.assertIn("MISSING_DATA", st)
        self.assertIn("forex_card needs", st)

    def test_wrong_layout_for_story_type_is_blocked(self):
        def m(j):
            j["graphic"]["chart"]["type"] = "ipo_subscription"
        st = core.status(self.mutated("commodity_card", m))
        self.assertIn("does not fit a commodity story", st)

    def test_closing_story_needs_closes_saved_before_the_wrap(self):
        j = copy.deepcopy(JOBS["index_board"])
        j["graphic"].pop("chart")
        j["article"]["editionLabel"] = "Fri 23 Oct · Closing wrap"
        j["graphic"]["headline"] = "Sensex, Nifty close lower"
        st = core.status(self.run_job(j))
        self.assertIn("MISSING_DATA", st)            # no 23 Oct closes in meta.history yet
        meta = json.loads((self.root / "data" / "meta.json").read_text(encoding="utf-8"))
        h = meta.setdefault("history", {})
        for name, v in (("Sensex", 73123.83), ("Nifty 50", 22600.00)):
            h.setdefault(name, []).append({"d": "2026-10-23", "v": v, "s": "ChiniMandi"})
        (self.root / "data" / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        j["collection"]["figures"] += [  # the index chart also shows the previous closes' changes
            {"id": "sx_prev", "label": "Sensex previous close", "value": "73,249.39", "as_of": "2026-10-22", "source": "cm",
             "evidence": "Sensex: closed at 73,123.83, down 125.56 points (previous close 73,249.39)"},
            {"id": "nf_prev", "label": "Nifty previous close", "value": "22,687.65", "as_of": "2026-10-22", "source": "cm",
             "evidence": "Nifty 50: ended at 22,600.00, down 87.65 points (previous close 22,687.65)"}]
        j["collection"]["sources"][0]["url"] = j["collection"]["sources"][0]["url"]
        run = self.run_job(j)
        a = run.load(3)["analysis"] if (run.dir / "03_graphics_generation.json").is_file() else {}
        self.assertEqual(a.get("template"), "index_chart", core.status(run))


class WrongFigures(V2):
    def test_unverified_chart_value_blocked(self):
        def m(j):
            j["graphic"]["chart"]["items"][0]["value"] = "$115.00"
        st = core.status(self.mutated("commodity_card", m))
        self.assertIn("FAILED at GRAPHICS_GENERATION", st)
        self.assertIn("115", st)

    def test_headline_number_not_in_chart_blocked(self):
        def m(j):  # 99.47 is verified (WTI) but the headline must match what the chart shows
            j["graphic"]["chart"]["items"] = [j["graphic"]["chart"]["items"][0]]
            j["graphic"]["coverHeadline"] = "WTI AT $99.47"
        st = core.status(self.mutated("commodity_card", m))
        self.assertIn("not shown in the chart", st)

    def test_article_headline_must_match_graphic(self):
        def m(j):
            j["article"]["title"] = "WTI crude settles at $99.47"
            j["article"]["dek"] = "Oil prices moved again."
            j["graphic"]["chart"]["items"] = [j["graphic"]["chart"]["items"][0]]
        st = core.status(self.mutated("commodity_card", m))
        self.assertIn("FAILED at FINAL_QA", st)

    def test_sign_flip_in_chart_blocked(self):
        def m(j):
            j["graphic"]["chart"]["items"][1]["pct"] = "-1.21%x"  # malformed / unverifiable token
            j["graphic"]["chart"]["items"][1]["value"] = "7,700.00"
        st = core.status(self.mutated("global_bars", m))
        self.assertIn("FAILED at GRAPHICS_GENERATION", st)


class ChartLabels(V2):
    def _items(self, layout):
        return [i["label"] for i in JOBS[layout]["graphic"]["chart"]["items"]]

    def test_value_borrowed_from_another_figure_blocked(self):
        def m(j):  # smallcap's verified -2.94% drawn on the Midcap 100 bar
            for i in j["graphic"]["chart"]["items"]:
                if i["label"] == "Midcap 100":
                    i["pct"] = "-2.94%"
        st = core.status(self.mutated("index_board", m))
        self.assertIn("FAILED at GRAPHICS_GENERATION", st)
        self.assertIn("Midcap 100", st)

    def test_rescaled_figure_blocked_on_chart(self):
        def m(j):  # 7,663.43 ÷ 1,00,000 ≈ 0.08 used to pass as a "scaled" figure
            j["graphic"]["chart"]["items"][0]["pct"] = "+0.08%"
        st = core.status(self.mutated("global_bars", m))
        self.assertIn("FAILED at GRAPHICS_GENERATION", st)
        self.assertIn("Dow Jones", st)

    def test_unmatched_label_needs_explicit_figure_link(self):
        def m(j):
            j["graphic"]["chart"]["items"][0]["label"] = "Benchmark"
        st = core.status(self.mutated("stock_move", m))
        self.assertIn("no verified figure with a matching label", st)

        def linked(j):
            j["graphic"]["chart"]["items"][0]["label"] = "Benchmark"
            j["graphic"]["chart"]["items"][0]["figures"] = ["hatsun"]
        self.assertNotIn("matching label", core.status(self.mutated("stock_move", linked)))


class Publishing(V2):
    def test_passed_v2_story_is_published_with_its_pinned_graphic(self):
        run = self.run_job(copy.deepcopy(JOBS["ipo_subscription"]))
        post = json.loads((self.root / "data" / "posts" / f"{run.slug}.json").read_text(encoding="utf-8"))
        post["id"] = run.slug
        ok, why = gate.allowed(post, self.root)
        self.assertTrue(ok, why)
        self.assertEqual(post["_analysis"]["template"], "ipo_subscription")

    def test_financial_story_published_by_hand_is_blocked(self):
        j = JOBS["forex_card"]
        p = dict(j["article"], **{k: v for k, v in j["graphic"].items() if k != "headline"})
        p.update(id="2026-10-23-hand-written", publishedAt="2026-10-23T20:00:00+05:30")
        ok, why = gate.allowed(p, self.root)
        self.assertFalse(ok)

    def test_previously_published_covers_keep_their_files(self):
        live = {os.path.basename(x)[:-5] for x in glob.glob(str(ROOT / "docs" / "covers" / "*.webp")) if "-800" not in x}
        if not live:
            self.skipTest("no built covers in this checkout")
        changed = []
        for f in sorted(glob.glob(str(ROOT / "data" / "posts" / "*.json"))):
            p = json.loads(open(f, encoding="utf-8").read())
            p["id"] = os.path.basename(f)[:-5]
            # The build publishes only eligible posts. A post omitted by the
            # source gate has no built news page and must not be checked for a
            # newly generated cover. This does not relax the publication gate.
            if not (ROOT / "docs" / "news" / p["id"] / "index.html").is_file():
                continue
            if p.get("chart"):
                continue
            if covers.cover_name(p) not in live:
                changed.append(p["id"])
        self.assertEqual(changed, [])

    def test_explainer_and_tech_may_still_use_illustrations(self):
        a = gs.analyze({"id": "x", "title": "What is a repo rate? Explained", "category": "policy"})
        self.assertFalse(a.get("data_required", False))
        a = gs.analyze({"id": "y", "title": "OpenAI launches a new coding agent", "category": "tech"})
        self.assertFalse(a.get("data_required", False))


if __name__ == "__main__":
    unittest.main()
