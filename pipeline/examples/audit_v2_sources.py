"""Audit all eight graphics sample stories against their actual publisher pages.

Read-only, no publishing. Run from repository root:
    python -m pipeline.examples.audit_v2_sources
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from pipeline.examples.make_v2_dryrun_jobs import JOBS
from pipeline.source_audit import audit

def main():
    results = []
    for job in JOBS:
        ok, errors = audit(job["collection"])
        results.append({"slug": job["slug"], "status": "VERIFIED_QUOTATIONS" if ok else "BLOCKED",
                        "errors": errors})
        print(f'{results[-1]["status"]}: {job["slug"]} ({len(errors)} issues)')
    output = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "note": "Quotation presence only; not independent truth, timestamps or official filings.",
              "results": results}
    dest = Path("pipeline") / "audit-results.json"
    dest.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print("Report:", dest)
    return 0 if all(x["status"] == "VERIFIED_QUOTATIONS" for x in results) else 1

if __name__ == "__main__":
    raise SystemExit(main())
