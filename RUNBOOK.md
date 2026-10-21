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
- **IPO daily (every market day, published in the `evening` slot; on weekends/holidays inside the `midday` roundup):** one story `data/posts/<date>-ipo-today-<main-names>.json`, category `startups`, `coverLabel: "IPO daily"`, symbol `growth`, editionLabel `<Ddd D Mon> · IPO daily`. Voice: a friendly finance teacher talking to beginners ("Namaste investors, welcome to today's IPO class") — warm and energetic, but education only: never say apply, skip, avoid, "good IPO" or give targets. Body in this order: (1) **Open now** – each mainboard IPO open today: price band, lot size and minimum amount, issue size split into fresh issue vs OFS, retail quota, day-wise subscription by category (QIB/NII/retail) with time and source, close and listing dates; (2) **Listed today** – issue price, listing price and %, how it traded after listing (high/low or latest, % vs issue) and the final subscription; (3) **Today's concept** – one IPO idea explained with a worked example using real numbers from today's IPOs (rotate: fresh vs OFS, GMP, anchor investors, QIB/NII/retail quotas, allotment lottery, price band and cut-off, lock-in expiry, P/E vs peers, use of proceeds, red flags in the RHP, ASBA/UPI mandate, SME vs mainboard); (4) **Coming up** – IPOs opening, closing, allotting and listing in the next 5 sessions; GMP only as a range with the warning that it is unofficial; (5) a "Key takeaway" line ending with "This is education, not a recommendation." Add a `table` "IPO dashboard" with one row per IPO (status, price band/lot, key dates, listing gain). SME IPOs only when unusually large or newsworthy. Tags include "IPO today", "Upcoming IPO", "IPO GMP today" and "<Name> IPO", "<Name> IPO subscription status", "<Name> IPO listing".
- **IPO hub data (`data/ipos.json`, every slot that has IPO news; always in `evening` and the IPO daily):** keep one entry per mainboard IPO from the day its dates are announced until about 10 sessions after listing (then delete it). Fields: name, slug, segment, exchange, business (one sentence), open, close, allotment, listing (ISO dates), priceBand, lot, minAmount (lot × upper band), issueSize, fresh, ofs, subscription {asOf, total, qib, nii, retail, employee, shareholder, source{name,url}}, gmp {value range, asOf}, issuePrice, listingPrice, listingGainPct, afterListing (one line: day-1 close or latest vs issue), note, sources. Status (open/upcoming/closed/listed) is computed from the dates, so keep dates correct. Set `listed: true` with listing price once a company lists. Update top-level `asOf` and `updatedAt`. Omit anything unverified. This feeds /ipo/, /ipo/<slug>/ pages and the "IPO watch" box.
- **Company pages** (/stock/<slug>/) are built automatically from every story's `companies` field and `data/results.json`. Always fill `companies` with the exact company name and NSE ticker (US tickers for US firms) so stories land on the right page; use the same spelling every time (e.g. "Eternal", "Reliance Industries", "HDFC Bank").
- **FII/DII data (`data/fii_dii.json`, every `report` slot; also premarket if the previous day's figures are newly out):** add the latest provisional cash-market day at the top of `days` as {date, fii{buy,sell,net}, dii{buy,sell,net}} in ₹ crore (never duplicate a date; keep last 30), refresh `month` (label like "October 2026 (to 21 Oct)") and `source`, set `updatedAt`. Feeds /fii-dii-data/. The /top-gainers-losers-today/ page reads the newest `report` story, and /live/ lists the day's stories automatically.
- **Festivals**: on major festivals, one festive educational piece (`palette: "festive"`, `coverLabel`, `symbol: "diya"`).

- **Gold & silver rates (premarket, midday, close, and the weekend/holiday midday):** refresh `data/rates.json`. `benchmark` = latest IBJA rates from https://ibjarates.com/ (gold 999/995/916/750/585 per 10 g, silver 999 per kg, `date`, `session` AM/PM; set `note` if IBJA skipped a day). Append the day's PM rates to `history` once per date (keep last 30). `cities` = shop rates per 10 g for 24K/22K from one same-day source, named in `citySource` with time; add cities only when that source covers them. `retailRange` = low–high 24K/22K shop rates across the day's sources, with links. Never copy an old or cached page: check the date on the source. Omit a field rather than guess. `updatedAt` = now.

## 4. Research
Several WebSearch calls in one turn ("standard", "extended" if thin) plus WebFetch. Prefer NSE/BSE, SEBI, RBI, PIB, filings, Economic Times, Business Standard, Moneycontrol, Mint, Reuters, CNBC, Kitco, CME FedWatch, Trendlyne/NiftyTrader for FII/DII. Check the newest ~60 posts so you don't repeat stories.

## 5. Write stories (5–9 per slot; one file for `report`)
File `data/posts/<YYYY-MM-DD>-<keyword-slug>.json`. Fields per README: title, dek, category, lead (exactly one true per update; unset older ones), edition `<date>-<slot>`, editionLabel `Wed 21 Oct · Pre-market brief`, publishedAt (now, +05:30, one minute apart), readMins, body (array), indiaImpact (required), globalImpact, optional table, **coverHeadline** (3–6 words on a verified number), stat, statLabel, symbol (most specific; vary), flags, companies, optional people (Commons only), seoTitle (search-style, dated for daily prices), tags (6–10 real search phrases), sources.

### Voice: teach, don't just report
Write like a friendly teacher walking a beginner through the news. Open with what happened in one plain sentence, then explain why it happened and what it means for an ordinary investor or saver. Define every piece of jargon the first time (e.g. "FII — foreign institutional investors, big overseas funds"). Where a number matters, add a short worked example with real figures ("a ₹10 lakh home loan at 8.5% means…"). End the body with a one-line "Key takeaway" paragraph. Still no tips or recommendations.

### Editorial rules (accuracy, freshness, transparency)
- **Record times separately:** `publishedAt` is when we publish; write the event time in the body ("at 3:00 pm", "on Monday"). Label every market figure with its as-of time and whether it is live, delayed, or a close. If markets are closed, say so and use the latest verified close with its date. Never mix today's live figures with an earlier close without dates.
- **Verify:** prefer primary sources (NSE/BSE, filings, RBI, SEBI, PIB, offer documents). For significant or disputed figures, confirm with a second credible source. Never invent prices, moves, subscription numbers, results, quotes, analyst views or links.
- **No near-duplicates:** before writing, check the newest ~60 posts. If a story on the same topic was published earlier the same day, **update that file** instead of adding a new one: refresh the facts, set `updatedAt` (now), `status: "update"` (or `"developing"` for a fast-moving event) and a one-line `changeNote` saying what changed. A new file is right only for a new day or a genuinely new development.
- **Label uncertainty:** grey market premium, social-media posts, forecasts and brokerage estimates must be named as such with their limitation. Mark preliminary or changing information in the text ("provisional", "as of 3 pm").
- **Every story needs** `seoDescription` (140–160 chars, plain summary with the key number), `coverAlt` (one sentence describing the cover, e.g. "Cover graphic: Nifty -0.34%, smallcaps sink 2.37%"), and the usual SEO fields. The AI-transparency footer is added automatically.
- **End-of-run report in chat:** after publishing, post a short edition status via SendUserMessage: edition date and slot, market status (pre-market/open/closed/holiday), research as-of time, lead headline, number of stories (new vs updated), and a **"Needs verification"** list of anything left out because it couldn't be confirmed (or "None"). Never say something is published unless the push succeeded.

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
