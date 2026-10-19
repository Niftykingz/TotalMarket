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
  "sources": [{"name": "Source", "url": "https://…"}]
}
```

### Results calendar

`data/results.json` is a list of `{"date": "2026-10-23", "company": "Infosys", "big": true, "note": "Q2 FY27 results"}`. The site shows upcoming dates on the home page and at `/results/`; past dates drop off automatically.
