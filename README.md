# TotalMarket

Indian markets, IPOs, tech and AI news, explained. Live at **https://totalmarket.co.in/**

Stories are researched and written automatically by Boss Piggy AI, TotalMarket's AI market desk, four times every market day, with one roundup on weekends and market holidays. News and explanation only, not investment advice.

## How it works

- `data/posts/<id>.json` – one file per story (title, dek, category, body, why, sources, publishedAt …)
- `data/meta.json` – latest update label and the market snapshot strip
- `build.py` – turns the data into the static site in `docs/` (Python 3.12+ with Pillow)
- `covers.py` – the premium cover engine: draws a 1600×900 cover per story (`docs/covers/*.webp` for the site, a 1200×675 `.jpg` for share previews). See **Cover graphics** below.
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
  "coverHeadline": "SENSEX FALLS 876 PTS",
  "coverContext": "Optional small line under the headline (defaults to statLabel)",
  "seoTitle": "How people search it, e.g. Gold Rate Today 21 Oct 2026: 24K ₹…, 22K ₹… (optional)",
  "tags": ["Gold rate today", "MCX gold"],
  "flags": ["IN", "US"],
  "symbol": "candles | gold | silver | oil | rupee | dollar | euro | yen | bitcoin | yield | globe | bank | chip | neural | servers | shield | growth | coins | diya",
  "palette": "festive (optional, saffron festival look)",
  "coverLabel": "Dussehra special (optional pill text)",
  "companies": [{"name": "Infosys", "ticker": "INFY"}],
  "people": [{"name": "Mukesh Ambani", "role": "Chairman, Reliance Industries", "commonsFile": "Mukesh_Ambani.jpg"}],
  "sources": [{"name": "Source", "url": "https://…"}]
}
```

`flags` (ISO country codes: IN US CN JP GB EU SA RU UA FR DE IT CA IL IR AE KR BR CH AU SG PK), `symbol` and `companies` decide the cover artwork; if left out they are detected from the headline. Companies appear as ticker badges. `tags` become topic pages at `/tag/<slug>/` and page keywords.

### Results calendar

`data/results.json` is a list of `{"date": "2026-10-23", "company": "Infosys", "big": true, "note": "Q2 FY27 results"}`. The site shows upcoming dates on the home page and at `/results/`; past dates drop off automatically.

### Daily market report

A story with a `report` object renders as the full evening report (see `report.py`) and appears on `/market-report/` and as the gold banner on the home page. Fields: `date`, `dateLabel`, `mood` (Bullish/Bearish/Mixed), `kpis` [{label, value, change, dir: up|down}], `takeaways` [..], `indices` [{name, open, high, low, close, change, pct}], `caps` [{name, pct}], `sectors` [{name, pct}], `moversIndex`, `gainers`/`losers` [{name, price, pct}], `movers` {title, up, down}, `breadth` {exchange, advances, declines, unchanged, highs52, lows52, upperCircuit, lowerCircuit, wealth}, `fiiDii` {asOf, fii {buy, sell, net}, dii {…}, mtd {fii, dii}, note}, `ipos` [{name, exchange, segment, issuePrice, listingPrice, listingGainPct, close, closeVsIssuePct, note}], `ipoUpcoming` [..], `levels` [{index, support, resistance, source}], `watch` [..]. Leave out anything you could not verify.

### Charts and sparklines

`data/meta.json` → `history` holds daily closes per index label, e.g. `{"Nifty 50": [{"d": "2026-10-19", "v": 22888.95}, …], "Sensex": […], "Bank Nifty": […]}`. The nightly report appends that day's close (keep the last 30). The home page draws the index chart from it, and any ticker whose label has history gets a sparkline.


### Keywords

Every story page gets meta keywords = its tags + the section's financial keyword set + core market keywords (see `CAT_KEYWORDS` / `CORE_KEYWORDS` in build.py); `news_keywords` uses the story's top 10 tags.

### People photos and company logos

- `people`: up to 4 people named in the story. Photos load only from **Wikimedia Commons** (`commonsFile` = the exact Commons file name, e.g. `Mukesh_Ambani.jpg`, found as `commons.wikimedia.org/wiki/File:<name>`), with a credit link to the file page. Never use photos from news sites, agencies, Google Images or social media. Skip the photo if no Commons file is found.
- Company logos: the site owner uploads files to `logos/<ticker>.png` (see `logos/README.md`). When a story's `companies` ticker has a logo file, it appears on the story page and on the cover badge. Never download or draw logos automatically.

### Cover graphics (TotalMarket graphics brief)

Every cover follows one system: dark category background, one rendered focal object on the right, one dominant headline on the left, small kicker (section + country flags), thin accent rule, one short context line with the date, company ticker badges bottom-left, TotalMarket branding bottom-right.

- `coverHeadline`: 3–6 words, uppercase, built around the single most important verified number or phrase from the story (e.g. `SENSEX FALLS 876 PTS`, `GOLD ₹1.48 LAKH`, `RUPEE AT 94.92`, `FED HIKE ODDS ~90%`, `JIO IPO WATCH`). Never the full article title, never a number that is not in the story. Words matching `stat` are drawn in the accent colour.
- `symbol` picks the focal object: `candles` (Indian market moves; red for falls, green for gains), `gold`, `silver`, `oil`, `rupee`/`dollar`/`euro`/`yen` (currency coins), `bitcoin`, `yield` (bond-yield curve), `globe` (global markets), `bank` (RBI, SEBI, Fed, regulators), `chip` (semiconductors, hardware), `neural` (AI models), `servers` (data centres, cloud), `shield` (hacks, bans, privacy, security), `growth` (IPOs, listings), `coins` (funding rounds, valuations), `diya` (festivals; use with `palette: "festive"`). Pick the most specific one so covers stay varied.
- No cartoons, emojis, photos of people or logos inside covers.

### Target visual style (owner reference: `design/style-reference.jpg`)

The owner's preferred look is cinematic, photo-realistic editorial imagery with clean data overlays:
- **Market crash / big falls:** a dark stormy scene, a dramatic red falling chart, and a large negative figure.
- **Gold and commodities:** realistic close-up gold bars ("Fine Gold 999.9" style) with premium warm lighting.
- **Global markets / central banks:** a real-world institution building at night with blue lighting and a candlestick chart overlay.
- **Startups and IPOs:** a modern city or corporate setting at golden hour with screens showing a rising chart, plus stacks of coins.

The current covers render this style in code (lit objects, dark backgrounds). Photo-realistic backgrounds need an image-generation service. If one is enabled, generate the background without text, then overlay the headline, numbers and branding with covers.py so every figure stays exact. Never generate real company logos, real people or text inside the image.

### Likes and comments

Every story page has a highlighted "Did this story help you?" card with a **Like** button and a **Comment** button, plus a floating like/comment bar while reading.
- Likes use the free, no-login Abacus counter (`abacus.jasoncameron.dev`, namespace `totalmarket`, one key per story). One like per browser.
- Comments use giscus (GitHub Discussions, free, no ads). Set `GISCUS["categoryId"]` in build.py (from https://giscus.app) to switch the comments box on; until then a "Comments are opening soon" note shows. Moderate comments in the repository's Discussions tab.


### IPO hub and company pages

- `data/ipos.json` feeds **/ipo/** (open, upcoming, closed and listed IPOs with subscription bars and an "IPO school" FAQ) and one page per IPO at **/ipo/<slug>/**. Status is computed from the dates. See RUNBOOK.md for the fields.
- **/stock/<slug>/** pages are built for every company in any story's `companies` field, with its next results date from `data/results.json`; **/stock/** lists them A–Z. Company badges on stories link to these pages.

### Editorial fields

- `updatedAt` + `changeNote`: shows "Updated …" and a "What changed" box when a story is revised.
- `status`: `"developing"` or `"update"` shows a badge next to the section chip.
- `coverAlt`: alt text for the cover image (defaults to headline + title).
- `seoDescription`: meta description (defaults to the dek).

### Boss Piggy (site guide)

Boss Piggy, a cartoon pig in black glasses and a navy suit, is TotalMarket's market guide. He appears in a small intro on the home page, as the host of the IPO hub and the Learn page, and in a "Boss Piggy explains" box on stories that have a `piggy` field (`happened`, `matters`, `watch`). Images: `assets/piggy/` (head avatars and a 360 px full figure, WebP with transparency); the original is kept in `design/`. He is not shown on story covers or cards.

### Market status, holidays, breadth, corporate events, archive

- `data/market_calendar.json` → header "Market open/closed" pill (computed in the browser from NSE hours and holidays, schedule-based, not live data) and **/stock-market-holidays-2026/**.
- Home **Market breadth** card reads the newest report's `breadth` (end of day, with source and an NSE link; missing values show "Unavailable").
- `data/corporate_events.json` + results calendar → **/corporate-events/** (dividends, record dates, results dates, board meetings; filter by type; official NSE notice links when confirmed).
- **/market-report/** has a date-searchable archive and an index-closing history table; `docs/data/index-closes.csv` is TotalMarket's own record of closes (not NSE official data).
