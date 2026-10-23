# Remote source audit rollout (development only)

Branch: `feature/source-evidence-gate` (based on `feature/data-graphics`).

## What it does

`pipeline/source_audit.py` fetches public HTTPS HTML/text and checks whether
each figure's recorded evidence quotation appears on the linked publisher page.
Requests fail closed on network errors, unsupported formats, redirects,
private/reserved addresses, and missing quotations.

The development branch now has `"require_live_evidence": true` in `pipeline/config.json`, and the gate defaults to requiring it when the flag is absent. Missing `enforce_from` configuration also fails closed. **This branch is not deployed.**

This check does **not** establish the truth of a publisher's claim, guarantee
the correct instrument/date, or independently validate arithmetic. It also
cannot validate dynamic pages, PDF releases or paywalled pages yet. In those
cases the story is held for better evidence rather than silently accepted.

## Rollout blockers

1. Run `py -m unittest discover -s tests -p "test_*.py" -v` on a clean checkout.
2. Obtain accessible authoritative primary-source records for each of the eight
   sample graphics; mark any missing/unavailable source as blocked.
3. Add explicit source timestamp, instrument, units, and as-of matching.
4. Test redirect/DNS-rebinding defenses and add trusted PDF support.
5. Establish an immutable legacy-post allowlist: posts backdated before `enforce_from` can still be treated as historical. Only genuinely pre-existing posts should qualify.
6. Run a site dry-run and verify scheduled jobs call the gated publisher.

No live activation, schedule changes, or publishing were performed.

## Verification status (23 Oct 2026)

- Code committed; offline regression tests added but **not executed** in this environment because a GitHub checkout cannot be fetched here.
- The eight sample jobs have not all passed independent source retrieval. Their quoted snippets in `make_v2_dryrun_jobs.py` are not proof by themselves.
- Do not merge, deploy, or enable automated production publishing on this branch yet.
