# TotalMarket AI newsroom — Phase 1

A private, local, multi-agent newsroom that researches, writes, verifies and illustrates
stories for TotalMarket, then **stops for the owner's decision**. It plugs into the existing
site code (`cover_templates.py`, `tmdate.py`, `data/company-logos.json`, `data/posts/`)
without changing how the website is built.

**Safe by default:**
- It uses a free deterministic mock AI provider (₹0).
- It does not fetch from the network.
- Production publishing is switched off in code.
- It writes nothing to `data/` or `docs/`.

## Quick start (Windows 11, Python 3.14)

```bat
cd C:\Users\mayur\TotalMarket
git checkout feature/company-logo-library
git pull
py -m pip install pillow numpy        &REM already installed for build.py
py -m newsroom demo
start newsroom\var\demo\review\demo-rbi-cuts-repo-rate-by-25-basis-points.html
py -m unittest discover -s tests
```

### Owner decision (optional)

```bat
set TM_NEWSROOM_OWNER_KEY=choose-a-long-secret
py -m newsroom status
py -m newsroom approve 1 --revision <full sha from the review page>
py -m newsroom publish 1              &REM always refused in Phase 1, and it lists why
```

### Other commands

- `py -m newsroom reject 1 --revision <sha> --note "..."` rejects a story.
- `py -m newsroom changes 1 --revision <sha> --note "..."` asks for changes.
- `py -m newsroom backup D:\backup\newsroom.db` makes an online copy of the database.

Linux and macOS use the same commands with `python3` instead of `py`.

## What the demo shows (fictional data, clearly labelled)

The demo story is *"RBI cuts repo rate by 25 basis points"*. It is test data, not a real RBI decision.

1. **Intake.** The Boss takes in 2 candidates. The second is caught as a **duplicate**. The first is ranked **BREAKING**, with an explained score.
2. **Research.** The Researcher stores the fictional statement as append-only evidence and extracts 5 facts, each with an exact excerpt.
3. **Write and design in parallel.** Once research is done, the Writer drafts about 180 words and the Designer builds the graphic at the same time.
4. **Designer mistake (failure demo).** On its first attempt the Designer prints **−3.58%** as the relative change. The correct figure is (6.25 − 6.50) / 6.50 × 100 = **−3.85%**.
5. **Fact check.** The Independent Fact Checker verifies all 16 article claims, including the quote, which it checks verbatim. It marks the graphic **NEEDS_CORRECTION** and records the formula, numerator and denominator.
6. **Correction loop.** The Boss returns the graphic to the Designer. The second attempt passes.
7. **No logo.** The graphic contains **no RBI logo**: none is approved in the registry, so "Reserve Bank of India" appears as plain text.
8. **Revision sealed.** The Boss seals revision 1 (SHA-256), writes an owner review page and moves the story to **OWNER_REVIEW**.
9. **Stops before publishing.** The page lists every reason publishing is blocked.

## Architecture

```
                         ┌──────────────────────────────┐
  fixtures / sources ──▶ │  BOSS (boss.py)              │  rank · dedupe · explain · assign
                         │  editor-in-chief             │  react to results · correction loops
                         └──────────────┬───────────────┘  prepare owner review
                                        │ tasks (SQLite queue, deps, priority, idempotency)
                         ┌──────────────▼───────────────┐
                         │ ORCHESTRATOR (orchestrator.py)│  bounded thread pool, retries,
                         │                              │  budget suspension, failure → Boss
                         └──┬──────────┬──────────┬─────┘
                ┌───────────▼┐   ┌─────▼─────┐   ┌▼──────────┐
                │ Researcher │──▶│  Writer   │   │ Designer  │  (Writer ∥ Designer)
                └────────────┘   └─────┬─────┘   └────┬──────┘
                                       └──────┬───────┘
                                     ┌────────▼─────────┐
                                     │ Fact Checker     │ deterministic verify.py + logo policy
                                     └────────┬─────────┘
                                              ▼
                     revision (sha256) → OWNER_REVIEW → owner approve/reject/changes
                                              ▼
                     publish_gate(): disabled in code · needs QA PASS · approval of exact revision
```

**Code-enforced guarantees.** No agent can change these:
- **Permissions:** `permissions.py` holds a frozen table, and `PRODUCTION_PUBLISHING = False`.
- **Approvals:** `approvals.py` ties each approval to a revision SHA. A new revision invalidates it, and the publish gate checks everything again.
- **Logos:** `services/logos.py` holds the logo policy. Its override argument is ignored on purpose.
- **Immutable records:** `database.py` uses triggers to make evidence, revisions, fact checks, QA reports, approvals, publications, budget changes and the audit log append-only.
- **Budget:** `providers.py` checks the cap before every call. Paid providers cannot be selected.

### Agent responsibility matrix

| Agent | Phase | Permitted tools | Input → output | Retries |
|---|---|---|---|---|
| Boss | 1 | rank, assign, move_stage, prepare_review | candidates → stories and tasks, with reasons | n/a (deterministic) |
| News Research | 1 | llm, source_fixtures, source_fetch (off), db_evidence | documents → EVIDENCE (facts with excerpts, quotes) | 2 (none for missing source) |
| Content Writer | 1 | llm, db_read | facts and quotes → DRAFT | 2, plus up to 2 correction rounds |
| Fact Checker | 1 | db_read, verify, logo_registry | draft and graphic → FACTCHECK ×2 | 2 |
| Graphic Designer | 1 | db_read, render, logo_registry | facts → GRAPHIC spec, PNG, WebP and JSON sidecar | 2, plus up to 2 correction rounds |
| Market Analyst | 3 | (prompt ready) | facts → context and scenarios | — |
| SEO Specialist | 3 | (prompt ready) | draft → metadata | — |
| Website Developer | 3 | (prompt ready) | package → `data/posts` preview and build check | — |
| Quality Assurance | 3 | (prompt ready) | package → PASS / RETURN / BLOCKED | — |
| Publishing | 4 | (prompt ready) | approved revision → commit | — |

Agent prompts are in `newsroom/prompts/`. In Phase 1 the Boss, Designer and Fact Checker are deterministic code. The Researcher and Writer call the provider, which is the mock.

### Workflow state machine (`workflow.py`)

The normal path is:

`DISCOVERED → DEDUPLICATED → PRIORITIZED → ASSIGNED → RESEARCHED → DRAFTED → FACT_CHECKED → GRAPHICS_READY → SEO_READY → INTEGRATED → QA_PASSED → OWNER_REVIEW → APPROVED → PUBLISHED`

Side states: `DUPLICATE`, `SKIPPED`, `BLOCKED`, `SUSPENDED` (budget), `REJECTED` (owner).

Correction loops:
- A failed article check sends the story back to the Writer, and a failed graphic check sends it back to the Designer.
- A missing or untraceable source blocks the story and returns it to the Researcher.
- "Request changes" from the owner sends it back to ASSIGNED.
- A new revision after approval moves the story to DRAFTED and invalidates the approval.

Phase 1 allows `GRAPHICS_READY → OWNER_REVIEW` only while the SEO, Developer and QA agents are disabled. Such a story has no QA PASS, so the publish gate refuses it.

### Database schema (SQLite, `newsroom/var/…/*.db`)

| Table | Purpose | Append-only |
|---|---|---|
| stories | slug, title, category, priority, score, reason, stage, demo, dedupe key, current revision | |
| source_documents | original evidence text, sha256, reliability, injection flags | ✔ |
| facts | key, label, value, unit, as-of, doc_id, verbatim excerpt, group | |
| tasks | agent, kind, status, dependencies, priority, attempts, idempotency key, input/output, timing | |
| revisions | full package snapshot and SHA-256 | ✔ |
| graphics | spec, file, sha256, status per attempt | |
| fact_checks | target, subject SHA, status, findings | ✔ |
| qa_reports | Phase 3 | ✔ |
| approvals | owner decisions and system invalidations, per revision SHA | ✔ |
| publications | one row per revision (UNIQUE): duplicate publishing impossible | ✔ |
| api_usage | tokens and ₹ cost per call | |
| errors | every failure and retry | |
| budget_changes | owner-approved cap changes | ✔ |
| audit_log | every stage move and decision | ✔ |

## How verification works (`services/verify.py`)

**A fact is traceable only if:**
- its excerpt occurs verbatim in a stored source document, and
- its value occurs in that excerpt.

**The checker reads the finished text itself.** It re-extracts every number, date and quotation, and ignores the Writer's own claim list.

**A number is verified only if:**
- it equals a traceable fact at the precision written, with a compatible unit (% ≠ percentage points), or
- it equals something the checker recomputes from facts: % change, absolute change or bps, with the formula, numerator and denominator recorded.

**What counts as a failure:**
- A near miss (−3.58% against −3.85%) is **NEEDS_CORRECTION**.
- A number with no support is **UNVERIFIED**.
- A quote not found verbatim is **REJECTED**.

**Graphics are checked item by item:**
- Every figure must cite a fact, and its label must match the fact's instrument (a Nifty value labelled "Sensex" is REJECTED).
- No digits may appear outside figure items.
- Logos must be approved original files whose hash still matches the registry.
- The image file itself must still match its hash.

## Logo policy

A logo may appear only if its entry in `data/company-logos.json` meets all of these:
- `status: "verified"`
- `source_url`
- `rights_reviewed: true`
- a `sha256` that matches the file's bytes

Anything generated or redrawn is rejected. Institutional marks (RBI, SEBI, NSE, BSE, government) are never drawn; their names appear as text. The registry is empty today, so no logos are used.

## Costs and approvals

- **Phase 1 costs ₹0:**
  - The provider is `mock`.
  - Daily and monthly caps default to ₹0 for paid calls.
  - Choosing any other provider raises `ProviderNotApproved`.
- **When the owner approves a provider later:**
  - The caps are raised with `Budget.raise_cap(owner_key, …)`, which is recorded as an append-only change.
  - When a cap is reached, jobs are suspended (stage `SUSPENDED`) until the owner raises it again.

## Tests (`tests/test_newsroom.py`, offline, free)

The tests cover the 17 required areas:
1. discovery and deduplication
2. task assignment
3. bounded parallel execution with dependencies
4. structured-output validation
5. percentage maths
6. independent verification, including ignoring the writer's claim mapping and catching invented quotes
7. missing sources, plus prompt injection
8. logo authenticity
9. graphic-number consistency, including the designer failure loop
10. revisions
11. owner approval
12. unauthorized publishing
13. budget caps, including suspend and resume
14. duplicate publication
15. failure recovery and idempotency
16. Windows compatibility (dates, paths with spaces, no `%-d`)
17. site build integration (`build.load_posts`, no writes to `data/` or `docs/`)

## Known limitations (Phase 1)

- **Not run on Windows yet.** Tests were run on Linux with Python 3.13. The code avoids Windows-specific pitfalls but needs a check on Windows 11 with Python 3.14.
- **No live sources.** Research uses fixtures only; live fetching from NSE, BSE, RBI or SEBI (respecting robots.txt and terms) comes in Phase 5.
- **Writer and Researcher are mocks.** They are deterministic templates, so writing quality only becomes representative once an approved LLM is connected.
- **Direction words are not checked in text.** The checker verifies magnitudes but does not yet read words such as "cut" or "rise" (signed figures and graphic signs are checked). For example, "rose 25 bps" would pass against a cut.
- **Not yet built:** the dashboard (Phase 2, FastAPI could not be installed in this workspace, though the standard library is enough), the Analyst, SEO, Developer and QA agents (Phase 3), and publishing (Phase 4).
- **Graphic templates are limited.** The Designer has two newsroom templates (`policy_rate`, `number_free`). The site's own `cover_templates.py` index, earnings and IPO covers are reused in Phase 3.
