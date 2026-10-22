#!/usr/bin/env python3
"""Create original TotalMarket SVG news graphics from supplied verified data.
Usage: python graphics/original-infographic-generator.py --input graphics/example-story.json --output graphics/output/sample.svg
No web access, third-party images, trademarks, or external dependencies.
"""
import argparse, html, json, pathlib, re

PALETTES = {
    "markets": ("#101827", "#4B1D30"),
    "earnings": ("#102744", "#175C83"),
    "tech-ai": ("#081C36", "#2056A1"),
    "economy": ("#103B4A", "#177B82"),
    "ipo": ("#172B5B", "#5B48A5"),
    "commodities": ("#2B241C", "#7A5D2D"),
}
def esc(value):
    return html.escape(str(value), quote=True)
def generate(story):
    category = story.get("category", "markets")
    if category not in PALETTES:
        raise ValueError("Unsupported category")
    title = str(story.get("title", "")).strip()
    if not title or len(title) > 85:
        raise ValueError("Title required (1-85 chars)")
    metric = str(story.get("metric", "")).strip()
    if len(metric) > 30:
        raise ValueError("Metric too long")
    source = str(story.get("source", "")).strip()
    if metric and (not source or not story.get("as_of")):
        raise ValueError("Metrics require source and as_of timestamp")
    if len(source) > 85 or len(str(story.get("as_of",""))) > 60:
        raise ValueError("Source/date too long")
    words = title.split()
    lines = []
    line = ""
    for word in words:
        if len(line + " " + word) > 23 and line:
            lines.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    if line:
        lines.append(line)
    if len(lines) > 3:
        raise ValueError("Headline too long for this template")
    bg1, bg2 = PALETTES[category]
    tspans = "".join(f'<tspan x="68" dy="{0 if i == 0 else 78}">{esc(t)}</tspan>' for i,t in enumerate(lines))
    metric_y = 405 if len(lines) <= 2 else 475
    if metric_y > 475:
        metric_y = 475
    foot = (f'{source} · {story.get("as_of")}' if metric else "Original TotalMarket illustration")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675" role="img" aria-label="{esc(title)}">
<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="{bg1}"/><stop offset="1" stop-color="{bg2}"/></linearGradient><pattern id="dots" width="30" height="30" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#fff" opacity=".13"/></pattern></defs>
<rect width="1200" height="675" fill="url(#bg)"/><rect width="1200" height="675" fill="url(#dots)"/>
<circle cx="1040" cy="330" r="260" fill="none" stroke="#fff" stroke-opacity=".09" stroke-width="3"/>
<circle cx="1040" cy="330" r="175" fill="none" stroke="#fff" stroke-opacity=".15" stroke-width="3"/>
<path d="M690 470 L760 410 L815 440 L880 300 L950 350 L1020 200 L1120 240" fill="none" stroke="#7dd3fc" stroke-width="9" stroke-linecap="round" stroke-linejoin="round" opacity=".8"/>
<rect x="68" y="65" width="7" height="25" fill="#fb7185"/><text x="90" y="86" fill="#e2e8f0" font-family="Arial,sans-serif" font-size="25" font-weight="bold" letter-spacing="3">{esc(category.upper())}</text>
<text x="68" y="220" fill="white" font-family="Arial,sans-serif" font-size="67" font-weight="bold">{tspans}</text>
<text x="68" y="{metric_y}" fill="#7dd3fc" font-family="Arial,sans-serif" font-size="55" font-weight="bold">{esc(metric)}</text>
<path d="M68 583 H1132" stroke="#fff" stroke-opacity=".24"/>
<text x="68" y="624" fill="#cbd5e1" font-family="Arial,sans-serif" font-size="21">{esc(foot)}</text>
<text x="1132" y="624" text-anchor="end" fill="#fff" font-family="Arial,sans-serif" font-size="25" font-weight="bold">Total<tspan fill="#60a5fa">Market</tspan></text>
</svg>'''
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    data=json.loads(pathlib.Path(args.input).read_text(encoding="utf-8"))
    out=pathlib.Path(args.output)
    if out.suffix.lower()!=".svg":
        raise SystemExit("Output must be .svg")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(generate(data),encoding="utf-8")
    print(out)
if __name__=="__main__":
    main()
