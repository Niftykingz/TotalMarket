# Official company logo acquisition — preserve originals

1. Confirm company identity using symbol, full legal name and ISIN from official exchange records.
2. Obtain an official, permitted logo asset from the company's press/brand resources or an authorized provider.
3. Record the original source URL, format, dimensions (if known), usage terms, retrieval date and review decision.
4. **Preserve the exact original asset.** Never resize, crop, stretch, recolor, add transparency, convert formats, or force 256×256. Rectangular and square logos both remain in their native proportions.
5. Keep original SVG, PNG, WebP or JPEG as supplied when safe and suitable. Sanitize/review SVG for security before website use; do not silently alter the archived source.
6. Add the approved original logo and company record to `data/company-logos.json` and run `python scripts/verify-logos.py`.
7. Display with CSS `object-fit: contain` in a responsive box; preserve aspect ratio and show natural padding if needed.
8. When rights or source are unclear, use a separate neutral text placeholder; never generate an imitation of the company's official logo.

Company marks remain the property of their owners. A publicly downloadable image does not automatically grant redistribution rights.
