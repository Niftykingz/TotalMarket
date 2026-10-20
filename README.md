# TotalMarket

Indian markets, IPOs, tech and AI news, explained. Live at **https://niftykingz.github.io/TotalMarket/**

Stories are researched and written automatically by Claude (an AI model from Anthropic) four times every market day, with one roundup on weekends and market holidays. News and explanation only, not investment advice.

## How it works

- `data/posts/<id>.json` – one file per story (title, dek, category, body, why, sources, publishedAt …)
- `data/meta.json` – latest update label and the market snapshot strip
- `build.py` – turns the data into the static site in `docs/` (Python 3.12+ with Pillow)
- `covers.py` – draws a 1200×630 cover image for each story (`docs/covers/`), also used as the share preview. `stat` is the big number on the cover (start with `-` for a fall, `+` for a rise); `statLabel` explains it. Both are optional.
- `docs/` – the published site, served by GitHub Pages (Settings → Pages → branch `main`, folder `/docs`)

Rebuild locally with `python3 build.py`.

### Story format

```json
{
  "title": "Headline under 90 characters",
  "dek": "One-line subhead",
  "category": "markets | tech | startups | policy | global | commodities",
  "lead": false,
  "edition": "2026-10-21-close",
  "editionLabel": "Wed 21 Oct · Closing wrap",
  "publishedAt": "2026-10-21T15:44:00+05:30",
  "readMins": 2,
  "body": ["Paragraph one.", "Paragraph two."],
  "why": "Why it matters for an Indian investor or tech reader.",
  "globalImpact": "How this move affects markets worldwide (optional).",
  "indiaImpact": "How it affects India: Sensex/Nifty, rupee, inflation, sectors.",
  "table": {"title": "Overnight snapshot", "rows": [{"label": "Gold (spot)", "value": "$4,160", "change": "-0.6%", "note": "Strong dollar"}]},
  "stat": "-876 pts",
  "statLabel": "Sensex closes at 73,852.90",
  "seoTitle": "How people search it, e.g. Gold Rate Today 21 Oct 2026: 24K ₹…, 22K ₹… (optional)",
  "tags": ["Gold rate today", "MCX gold"],
  "flags": ["IN", "US"],
  "symbol": "gold | silver | oil | dollar | rupee | euro | yen | bitcoin | yield | bank | chip | rocket | bow | diya | chart-up | chart-down | bull | bear | ravan",
  "palette": "festive (optional, saffron festival look)",
  "coverLabel": "Dussehra special (optional pill text)",
  "companies": [{"name": "Infosys", "ticker": "INFY"}],
  "people": [{"name": "Mukesh Ambani", "role": "Chairman, Reliance Industries", "commonsFile": "Mukesh_Ambani.jpg"}],
  "sources": [{"name": "Source", "url": "https://…"}]
}
```

`flags` (ISO country codes: IN US CN JP GB EU SA RU UA FR DE IT CA IL IR AE KR BR CH AU SG PK), `symbol` and `companies` decide the cover artwork; if left out they are detected from the headline. Companies appear as ticker badges, never logos. `tags` become topic pages at `/tag/<slug>/` and page keywords.

### Results calendar

`data/results.json` is a list of `{"date": "2026-10-23", "company": "Infosys", "big": true, "note": "Q2 FY27 results"}`. The site shows upcoming dates on the home page and at `/results/`; past dates drop off automatically.

### Daily market report

A story with a `report` object renders as the full evening report (see `report.py`) and appears on `/market-report/` and as the gold banner on the home page. Fields: `date`, `dateLabel`, `mood` (Bullish/Bearish/Mixed), `kpis` [{label, value, change, dir: up|down}], `takeaways` [..], `indices` [{name, open, high, low, close, change, pct}], `caps` [{name, pct}], `sectors` [{name, pct}], `moversIndex`, `gainers`/`losers` [{name, price, pct}], `movers` {title, up, down}, `breadth` {exchange, advances, declines, unchanged, highs52, lows52, upperCircuit, lowerCircuit, wealth}, `fiiDii` {asOf, fii {buy, sell, net}, dii {…}, mtd {fii, dii}, note}, `ipos` [{name, exchange, segment, issuePrice, listingPrice, listingGainPct, close, closeVsIssuePct, note}], `ipoUpcoming` [..], `levels` [{index, support, resistance, source}], `watch` [..]. Leave out anything you could not verify.

### Charts and sparklines

`data/meta.json` → `history` holds daily closes per index label, e.g. `{"Nifty 50": [{"d": "2026-10-19", "v": 22888.95}, …], "Sensex": […], "Bank Nifty": […]}`. The nightly report appends that day's close (keep the last 30). The home page draws the index chart from it, and any ticker whose label has history gets a sparkline.

### Cartoon characters

`characters.py` draws original cartoon characters for covers: `bull` (rising market), `bear` (falling market), `ravan` (Dussehra). Market stories without a symbol get the bull or bear automatically. Add new festival or mascot characters there. Never draw real people or company logos.

### Keywords

Every story page gets meta keywords = its tags + the section's financial keyword set + core market keywords (see `CAT_KEYWORDS` / `CORE_KEYWORDS` in build.py); `news_keywords` uses the story's top 10 tags.

### People photos and company logos

- `people`: up to 4 people named in the story. Photos load only from **Wikimedia Commons** (`commonsFile` = the exact Commons file name, e.g. `Mukesh_Ambani.jpg`, found as `commons.wikimedia.org/wiki/File:<name>`), with a credit link to the file page. Never use photos from news sites, agencies, Google Images or social media. Skip the photo if no Commons file is found.
- Company logos: the site owner uploads files to `logos/<ticker>.png` (see `logos/README.md`). When a story's `companies` ticker has a logo file, it appears on the story page and on the cover badge. Never download or draw logos automatically.
