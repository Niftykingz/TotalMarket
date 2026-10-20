# TotalMarket automation runbook

Updates run inside the owner's Claude chat. Each scheduled message names a slot; follow that slot below, publish, then **schedule the next slot** (step 9) so the chain never breaks.

Slots (IST): `premarket` 08:45 · `midday` 12:45 · `close` 15:45 · `report` 20:10 · `evening` 20:45.
On weekends and NSE holidays only `midday` runs, as a "Weekend roundup" or "Market holiday briefing"; every other slot is skipped (still do step 9).

## 1. Prepare
- `cd /home/claude/totalmarket && git pull --rebase origin main` (if the folder is missing, clone `https://github.com/Niftykingz/TotalMarket` there).
- Check the IST time and whether NSE is open today.

## 2. Scope and rules
Indian retail investors and traders who follow global markets and tech. `category` is one of: markets, tech, startups, policy, global, commodities (see README). Politics only where it moves money; neutral.
Never recommend buying, selling or holding anything; no price targets or tips. Write in your own words (no copied sentences; at most one short quote under 15 words per source). Never invent numbers; omit what you can't verify; give ranges if sources conflict. No logos, no photos of people except Wikimedia Commons files via `people`, no downloaded images.

## 3. What each slot publishes
- **premarket**: lead with "Overnight global wrap" (category global, lead true) with a `table` of overnight moves (Dow, S&P 500, Nasdaq, US 10Y, DXY, USD/INR, USD/JPY or EUR/USD, gold, silver, Brent, WTI, copper, Nikkei/Hang Seng, GIFT Nifty, Bitcoin; omit unverified rows). Add separate stories for gold & silver (global + Indian rates), crude, rupee, key US news/data, and "Results today and what to watch".
- **midday**: market mid-session, rupee, gold/crude moves, results so far.
- **close**: Sensex/Nifty close (points, %), top gainers/losers, sectors and why, results reported today, rupee close, MCX gold/silver.
- **report**: the full Daily market report story (`data/posts/<date>-stock-market-today-sensex-nifty-closing-report.json`) with the `report` object as documented in README (indices with open/high/low/close, caps, sectors, gainers/losers, movers, breadth, FII/DII, IPO listings and what happened after listing, levels with source, what to watch). Append today's closes to `meta.history` for Nifty 50, Sensex and Bank Nifty (keep last 30).
- **evening**: tech and startup news, IPO subscription status, Europe/US open, commodity moves; refresh `data/results.json` for the next 7–10 days (remove entries >2 days old).
- **Festivals**: on major festivals, one festive educational piece (`palette: "festive"`, `coverLabel`, `symbol: "diya"`).

## 4. Research
Several WebSearch calls in one turn ("standard", "extended" if thin) plus WebFetch. Prefer NSE/BSE, SEBI, RBI, PIB, filings, Economic Times, Business Standard, Moneycontrol, Mint, Reuters, CNBC, Kitco, CME FedWatch, Trendlyne/NiftyTrader for FII/DII. Check the newest ~60 posts so you don't repeat stories.

## 5. Write stories (5–9 per slot; one file for `report`)
File `data/posts/<YYYY-MM-DD>-<keyword-slug>.json`. Fields per README: title, dek, category, lead (exactly one true per update; unset older ones), edition `<date>-<slot>`, editionLabel `Wed 21 Oct · Pre-market brief`, publishedAt (now, +05:30, one minute apart), readMins, body (array), indiaImpact (required), globalImpact, optional table, **coverHeadline** (3–6 words on a verified number), stat, statLabel, symbol (most specific; vary), flags, companies, optional people (Commons only), seoTitle (search-style, dated for daily prices), tags (6–10 real search phrases), sources.

## 6. Meta
Update `data/meta.json`: editionLabel, updatedAt, nextUpdate (next slot that will actually run), ticker (Sensex, Nifty 50, Bank Nifty, USD/INR, Gold, Silver, Brent, US 10Y, Nasdaq, DXY; verified only), tickerAsOf. Keep `history`.

## 7. Build and check
`python3 build.py` → "Built N stories", no WARNING for new files. Open every new cover in `docs/covers/` and check: short readable headline, numbers match the story, no overlap with the object, covers not identical. Fix and rebuild.

## 8. Publish
`git add -A && git -c user.name="TotalMarket Bot" -c user.email="noreply@anthropic.com" commit -m "<editionLabel>: <N> stories" && git push origin HEAD` (on rejection: pull --rebase, rebuild, commit, push once more). Post a one-line summary in the chat.

## 9. Schedule the next slot (always, even when skipping)
Use `send_later` with `at` = the next slot time in UTC (IST − 5:30) and the message:
`TotalMarket scheduled run: <slot> slot for <Ddd D Mon>. Follow RUNBOOK.md.`
Order: premarket → midday → close → report → evening → next day's premarket. On weekends/holidays you may jump straight to that day's midday and then the next market day's premarket.
