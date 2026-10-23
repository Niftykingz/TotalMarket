# TotalMarket strict publishing pipeline

Every news article goes through six stages in order. Each stage saves a SHA-256-hashed
artifact in `pipeline/runs/<slug>/` before the next stage may start. A FAILED or
INCOMPLETE stage blocks that article.

| # | Stage | Saved artifact | Blocks when |
|---|---|---|---|
| 1 | DATA_COLLECTION | `01_data_collection.json` | a source is missing or not https; a figure has no evidence, date or source |
| 2 | DATA_VERIFICATION | `02_data_verification.json` (verified + rejected) | a figure's value isn't in its own evidence quote; it is stale (more than 3 days old); two sources conflict; a `key` figure is rejected |
| 3 | GRAPHICS_GENERATION | `03_graphics_generation.json` + `cover.jpg` | any number on the cover isn't a verified figure (worked examples are never allowed on a graphic); an unapproved logo file exists for a company; the image is invalid |
| 4 | ARTICLE_WRITING | `04_article_writing.json` + `data/posts/<slug>.json` | any number in the headline, dek, SEO, table, Boss Piggy or Hindi text isn't verified (body may also use declared worked examples); a source wasn't collected |
| 5 | FINAL_QA | `05_final_qa.json` | the post changed after stage 4; graphic fields differ; there is placeholder or demo text; dates mismatch; the graphic is missing or invalid; the final article would render a different graphic |
| 6 | PUBLISH | `06_publish.json` (commit, URL) | only `python3 -m pipeline publish` publishes, and only after the gate passes, the build checks pass and the tests pass |

## How enforcement works

**`build.py` gate.** `build.py` calls `pipeline.gate.allowed()` for every post. An article published or updated at or after `enforce_from` (in `pipeline/config.json`) is left out of the site unless all of these hold:
- its stages 1–5 are PASS, in order;
- every artifact matches its hash;
- the post file is byte-identical to the stage-4 output;
- verification and QA still pass when they are re-run from the saved files.

So a hand-edited manifest, an edited post or a skipped stage cannot reach the site, whatever starts the build.

**Pinned graphic.** The site renders the graphic analysis saved by stage 3, so later market-data changes cannot alter a verified graphic.

**Publish checks.** `python3 -m pipeline publish` runs the gate and the build, then checks that:
- every passing article has a page and a cover;
- every blocked article has no page;
- the tests pass.

Only then does it commit and push. It then records stage 6 in each run and appends to `pipeline/log.jsonl`. Every stage result and publish attempt is logged there.

**Retries.** `python3 -m pipeline retry` re-runs failed jobs. A changed job file restarts from stage 1. Pushes that are rejected are logged and can be published again after `git pull --rebase`.

## How a number counts as verified

A number in an article or on a graphic passes if it is any of these:
- a verified figure, at the precision written;
- a verified figure scaled by ×/÷ 10, 100, 1,000, lakh or crore (per gram ↔ per 10 g);
- a difference or % change between two verified figures, which the checker recomputes;
- a declared worked example, allowed in the body only.

These are ignored: years, dates, clock times, Q2/FY27-style labels, index names (Nifty 50, S&P 500), and small counts up to 12 without a unit. Any number with %, ₹, $, crore, bps, "x" or "points" must always be verified.

## Job file (`pipeline/inbox/<slug>.json`)

```json
{
 "slug": "2026-10-23-sensex-nifty-close-...",
 "collection": {
  "sources": [{"id": "bs", "name": "...", "url": "https://...", "published": "2026-10-23T15:41:00+05:30"}],
  "figures": [{"id": "nifty", "label": "Nifty 50 close", "value": "22,600.00", "change": "-87.65",
               "as_of": "2026-10-23", "source": "bs", "evidence": "exact text from the source containing 22,600.00 and 87.65", "key": true}],
  "examples": [{"id": "ex1", "value": "10,000", "note": "worked example: ₹10,000 investment"}]
 },
 "graphic": {"headline": "...", "coverHeadline": "NIFTY ENDS AT 22,600", "stat": "-0.39%", "statLabel": "...", "symbol": "candles", "flags": ["IN"]},
 "article": {"title": "...", "dek": "...", "category": "markets", "body": ["..."], "indiaImpact": "...", "seoTitle": "...",
             "seoDescription": "...", "sources": [{"name": "...", "url": "https://..."}], "edition": "2026-10-23-close",
             "editionLabel": "Fri 23 Oct · Closing wrap", "publishedAt": "2026-10-23T15:52:00+05:30", "hi": {"...": "..."}}
}
```

There is a full real example in `examples/close-story-job.json`, made from the 23 Oct closing wrap.

## Commands

```
python3 -m pipeline run pipeline/inbox/<slug>.json    # stages 1–5
python3 -m pipeline status
python3 -m pipeline retry
python3 -m pipeline publish --dry-run                 # builds into a temp folder, no git
python3 -m pipeline publish                           # the only publish entry point
```

## Scope

The gate covers news articles (`data/posts`). Data files used by the data pages (`rates.json`, `ipos.json`, `fii_dii.json`, `global.json`, `meta.json`) are still updated directly by the runs. Their figures appear on article graphics only through verified job figures.
