# Remote source audit rollout (development only)

Branch: `feature/source-evidence-gate` (based on `feature/data-graphics`).

## What it does

`pipeline/source_audit.py` fetches public HTTPS HTML/text and checks whether
each figure's recorded evidence quotation appears on the linked publisher page.
Requests fail closed on network errors, unsupported formats, redirects,
private/reserved addresses, and missing quotations.

To enable the additional check for **enforced** posts, add
`"require_live_evidence": true` to `pipeline/config.json`.
**Do not enable production publishing until all sample stories have been
audited and the tests have been run.**

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
5. Verify `pipeline/config.json` has a valid `enforce_from` for all new posts:
   if it is missing, the legacy branch of `gate.allowed` permits publishing
   without any pipeline verification.
6. Run a site dry-run and verify scheduled jobs call the gated publisher.

No live activation, schedule changes, or publishing were performed.
