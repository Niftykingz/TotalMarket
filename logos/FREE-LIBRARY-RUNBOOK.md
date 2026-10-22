# Run the free-only 15-company logo discovery

On Windows 11, from the repository root:

```powershell
py scripts/find-free-logos.py --limit 5
```

This searches Wikimedia Commons for each of the 15 tracked companies and writes `data/wikimedia-logo-candidates.json`, including original image URL, original dimensions, original format, license metadata, and file-description page.

To download **unchanged original bytes** into a quarantined, git-ignored review folder:

```powershell
py scripts/find-free-logos.py --limit 5 --download
```

Review the Commons file page for each result: correct company and current branding, creator, licensing, trademark limitations, editorial/public website permissions, and attribution. A Commons logo may be ineligible despite being downloadable. Never publish candidates or use unknown SVG directly on the website. Quarantine SVG files should be security-reviewed.

Only move a permitted reviewed original into `logos/` and update `data/company-logos.json` with verified symbol, legal name, ISIN, source and permission. The source file is never resized, cropped, recolored, or converted. Run `py scripts/verify-logos.py`.

**Important:** This workflow is free but not a promise that every company's logo is licensed for redistribution. Missing logos must remain neutral text placeholders. No API key or payment is needed.
