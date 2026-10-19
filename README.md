# TotalMarket

Indian markets, IPOs, tech and AI news, explained. Live at **https://niftykingz.github.io/totalmarket/**

Stories are researched and written automatically by Claude (an AI model from Anthropic) four times every market day, with one roundup on weekends and market holidays. News and explanation only, not investment advice.

## How it works

- `data/posts/<id>.json` – one file per story (title, dek, category, body, why, sources, publishedAt …)
- `data/meta.json` – latest update label and the market snapshot strip
- `build.py` – turns the data into the static site in `docs/` (no dependencies, Python 3.9+)
- `docs/` – the published site, served by GitHub Pages (Settings → Pages → branch `main`, folder `/docs`)

Rebuild locally with `python3 build.py`.

### Story format

```json
{
  "title": "Headline under 90 characters",
  "dek": "One-line subhead",
  "category": "markets | tech | startups | policy | global",
  "lead": false,
  "edition": "2026-10-21-close",
  "editionLabel": "Wed 21 Oct · Closing wrap",
  "publishedAt": "2026-10-21T15:44:00+05:30",
  "readMins": 2,
  "body": ["Paragraph one.", "Paragraph two."],
  "why": "Why it matters for an Indian investor or tech reader.",
  "sources": [{"name": "Source", "url": "https://…"}]
}
```
