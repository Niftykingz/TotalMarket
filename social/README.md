# TotalMarket social publishing — approval first

This is an **isolated draft preparation MVP**. It reads existing `data/posts/*.json` files, skips stories without an HTTPS source, and creates reviewable JSON in `social/drafts/`. It does **not** edit the website, call Meta/X, or publish anything.

Run locally: `python -m social.queue --limit 20`.

## Approval and release design
1. Verify original sources, numbers, publication dates and article canonical URL.
2. Generate branded Instagram portrait (1080×1350) and X landscape (1600×900) images from existing cover assets. Do not invent numbers in graphics.
3. Human reviewer inspects platform-specific text, images and linked source.
4. Reviewer explicitly approves each platform and version; editing invalidates approval.
5. Separate publisher (not yet implemented) checks signed authorization, approved immutable content hash, and platform credentials before attempting publication; logs platform IDs and deduplicates retries.
6. Failure must remain visible and retryable; no fallback auto-publishing.

## Required connections
- GitHub Actions permission to run workflow; no publishing secrets required for draft generation.
- Instagram Professional account linked to a Facebook Page, with a Meta app and the appropriate content publishing permissions/tokens (or approved scheduler).
- X developer/API access with write permission and OAuth authorization (or approved scheduler).
- Publicly reachable HTTPS images for platform media ingestion.
- Store secrets only in GitHub Actions Secrets or a secure external credential store, never in repository files.

Do not enable live posting until both integrations are verified and end-to-end approval checks are tested.
