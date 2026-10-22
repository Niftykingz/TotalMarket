"""Data-driven TotalMarket cover templates (1600x900), drawn deterministically with Pillow.

Every number on these covers comes from `graphics_selector.analyze()` figures, which are
verified structured data (recorded closes, the story's `figures`, the IPO register).
Text is rendered with Inter fonts, never by an image generator.

Templates:
  index_chart   Indian index close: Sensex and Nifty 50 labelled separately + real closes chart
  earnings_card company result: metric, value, change and period (light editorial card)
  ipo_card      IPO listing: issue price -> listing price and % gain/loss
"""
import os, re
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import tmdate

W, H = 1600, 900
HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, "fonts")
F = lambda name, size: ImageFont.truetype(os.path.join(FD, name), int(size))
BLACK, XB, SEMI, MED = "InterDisplay-Black.otf", "InterDisplay-ExtraBold.otf", "Inter-SemiBold.otf", "Inter-Medium.otf"

NAVY, MIDNIGHT, BLUE, GOLD = (18, 59, 129), (8, 27, 54), (37, 99, 235), (212, 168, 67)
UP, DOWN, INK, MUTED, PAPER, LINE = (34, 197, 94), (239, 68, 68), (15, 23, 42), (100, 116, 139), (248, 250, 252), (226, 232, 240)
UP_D, DOWN_D = (21, 128, 61), (220, 38, 38)


def _grad(c1, c2, angle_mix=.55):
    import numpy as np
    yy, xx = np.mgrid[0:H, 0:W].astype("float32")
    t = (xx / W * angle_mix + yy / H * (1 - angle_mix))[..., None]
    a, b = np.array(c1, "float32"), np.array(c2, "float32")
    return Image.fromarray((a * (1 - t) + b * t).clip(0, 255).astype("uint8"), "RGB").convert("RGBA")


def _brand(dr, dark=True, accent=GOLD):
    bf = F(XB, 32)
    w = dr.textlength("TotalMarket", font=bf)
    x, y = W - 72 - w, H - 78
    dr.rectangle([x - 24, y + 6, x - 13, y + 32], fill=accent)
    dr.text((x, y), "Total", font=bf, fill=(255, 255, 255) if dark else NAVY)
    dr.text((x + dr.textlength("Total", font=bf), y), "Market", font=bf, fill=accent if dark else BLUE)


def _kicker(dr, text, x=84, y=92, dark=True, accent=GOLD):
    dr.rectangle([x, y, x + 10, y + 34], fill=accent)
    dr.text((x + 26, y + 17), text.upper(), font=F(SEMI, 28), fill=(255, 255, 255) if dark else NAVY, anchor="lm")


def _date_line(p, a):
    d = (a.get("figures") or [{}])[0].get("date") or str(p.get("publishedAt") or "")[:10]
    try:
        return tmdate.fmt(d, "%-d %b %Y").upper()
    except Exception:
        return ""


def _fit(dr, text, font_name, size, max_w, min_size=20):
    f = F(font_name, size)
    while dr.textlength(text, font=f) > max_w and size > min_size:
        size -= 2; f = F(font_name, size)
    return f


def _rrect(im, box, radius, fill=None, outline=None, width=2):
    """Rounded rectangle composited with real alpha (ImageDraw would overwrite pixels)."""
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    im.alpha_composite(lay)


def _tint(c, k=.14, base=(255, 255, 255)):
    return tuple(int(base[i] * (1 - k) + c[i] * k) for i in range(3))


def _line_chart(im, box, pts, col, dark=False, label="", fmt=lambda v: f"{v:,.0f}", base=None):
    """Point-labelled line chart of verified values. `pts` = [[x_label, value], ...] (2+ points).
    `base` draws a dashed reference line (e.g. IPO issue price). Scale starts near the data, labelled."""
    x0, y0, x1, y1 = box
    vals = [float(v) for _, v in pts]
    allv = vals + ([float(base)] if base is not None else [])
    lo, hi = min(allv), max(allv)
    pad = (hi - lo) * .25 or max(1, hi * .05)
    lo, hi = lo - pad, hi + pad
    n = len(vals)
    X = lambda i: x0 + 40 + i * (x1 - x0 - 80) / max(1, n - 1)
    Y = lambda v: y1 - 46 - (v - lo) / (hi - lo) * (y1 - y0 - 110)
    txt, sub, grid = ((255, 255, 255), (203, 213, 225), (255, 255, 255, 40)) if dark else (INK, MUTED, LINE + (255,))
    S = 2
    lay = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    ld.line([(x0 * S, (y1 - 46) * S), (x1 * S, (y1 - 46) * S)], fill=grid, width=2)
    if base is not None:
        yb = Y(float(base)) * S
        for xx in range(int(x0 * S), int(x1 * S), 28):
            ld.line([(xx, yb), (xx + 14, yb)], fill=(212, 168, 67, 230), width=4)
    P = [(X(i) * S, Y(v) * S) for i, v in enumerate(vals)]
    ld.polygon([(P[0][0], (y1 - 46) * S)] + P + [(P[-1][0], (y1 - 46) * S)], fill=col + (40,))
    ld.line(P, fill=col + (255,), width=10, joint="curve")
    for i, (px, py) in enumerate(P):
        r = 16 if i == n - 1 else 11
        ld.ellipse([px - r, py - r, px + r, py + r], fill=(255, 255, 255, 255))
        ld.ellipse([px - r + 6, py - r + 6, px + r - 6, py + r - 6], fill=col + (255,))
    im.alpha_composite(lay.resize((W, H), Image.LANCZOS))
    dr = ImageDraw.Draw(im)
    if label:
        dr.text((x0, y0), label.upper(), font=F(SEMI, 22), fill=sub)
    vf, xf = F(XB, 28), F(MED, 22)
    for i, (xl, v) in enumerate(pts):
        dr.text((X(i), Y(float(v)) - 24), fmt(float(v)), font=vf, fill=txt, anchor="mb")
        dr.text((X(i), y1 - 14), str(xl), font=xf, fill=sub, anchor="mb")
    if base is not None:
        dr.text((x1, Y(float(base)) - 8), "Issue price", font=F(MED, 20), fill=(212, 168, 67), anchor="rb")


def _save(im, path_webp, path_jpg):
    rgb = im.convert("RGB")
    rgb.save(path_webp, "WEBP", quality=80, method=6)
    rgb.resize((1200, 675), Image.LANCZOS).save(path_jpg, "JPEG", quality=84, optimize=True, progressive=True)


# ------------------------------------------------------------------ index chart
def index_chart(p, a, path_webp, path_jpg):
    figs = {f["label"]: f for f in a["figures"]}
    down = a["direction"] == "down"
    col = DOWN if down else UP
    im = _grad((7, 19, 41), (16, 44, 92) if not down else (40, 18, 30))
    dr = ImageDraw.Draw(im)
    _kicker(dr, p.get("coverLabel") or "Indian markets · close", accent=col)
    # left: labelled index figures (Sensex and Nifty 50 never share a number)
    x0_left_limit = 1010
    y = 190
    for name in ("Sensex", "Nifty 50", "Bank Nifty"):
        f = figs.get(name)
        if not f:
            continue
        big = name in ("Sensex", "Nifty 50")
        dr.text((84, y), name.upper(), font=F(SEMI, 30 if big else 24), fill=(203, 213, 225))
        vf = F(BLACK, 92 if big else 54)
        dr.text((84, y + 34), f["value"], font=vf, fill=(255, 255, 255))
        vw = dr.textlength(f["value"], font=vf)
        cf = _fit(dr, "x", XB, 38 if big else 28, 9999)
        while 84 + vw + 26 + dr.textlength(f'▼ {f["change"].lstrip("+")}  ({f["pct"]})', font=cf) > x0_left_limit and cf.size > 22:
            cf = F(XB, cf.size - 2)
        ch = f'{"▼" if f["change"].startswith("-") else "▲"} {f["change"].lstrip("+")}  ({f["pct"]})'
        c = DOWN if f["change"].startswith("-") else UP
        dr.text((84 + vw + 26, y + 34 + (92 if big else 54) * .38), ch, font=cf, fill=c)
        y += 150 if big else 100
    # right: real closing-level chart (Nifty 50), scale labelled
    ser = a["series"]
    x0, x1, y0, y1 = 1060, 1420, 230, 640
    vals = [s["v"] for s in ser]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * .12 or 1
    lo, hi = lo - pad, hi + pad
    X = lambda i: x0 + i * (x1 - x0) / (len(vals) - 1)
    Y = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
    S = 2
    lay = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    for k in range(4):
        v = lo + pad + (hi - lo - 2 * pad) * k / 3
        ld.line([(x0 * S, Y(v) * S), (x1 * S, Y(v) * S)], fill=(255, 255, 255, 34), width=2)
    pts = [(X(i) * S, Y(v) * S) for i, v in enumerate(vals)]
    ld.polygon([(x0 * S, y1 * S)] + pts + [(x1 * S, y1 * S)], fill=col + (46,))
    ld.line(pts, fill=col + (255,), width=10, joint="curve")
    ex, ey = pts[-1]
    ld.ellipse([ex - 16, ey - 16, ex + 16, ey + 16], fill=(255, 255, 255, 255))
    ld.ellipse([ex - 10, ey - 10, ex + 10, ey + 10], fill=col + (255,))
    lay = lay.resize((W, H), Image.LANCZOS)
    im.alpha_composite(lay)
    dr = ImageDraw.Draw(im)
    sf = F(MED, 22)
    for k in range(4):
        v = lo + pad + (hi - lo - 2 * pad) * k / 3
        dr.text((x1 + 16, Y(v)), f"{v:,.0f}", font=sf, fill=(148, 163, 184), anchor="lm")
    dr.text((x0, y1 + 24), tmdate.fmt(ser[0]["d"], "%-d %b"), font=sf, fill=(148, 163, 184))
    dr.text((x1, y1 + 24), tmdate.fmt(ser[-1]["d"], "%-d %b"), font=sf, fill=(148, 163, 184), anchor="ra")
    dr.text((x0, y0 - 44), f"NIFTY 50 · LAST {len(vals)} CLOSES", font=F(SEMI, 22), fill=(203, 213, 225))
    src = ", ".join(sorted({f.get("source") for f in a["figures"] if f.get("source")}))
    dr.text((84, H - 74), f"Close · {_date_line(p, a)}" + (f" · Source: {src}" if src else ""), font=F(MED, 24), fill=(148, 163, 184))
    _brand(dr, accent=col)
    _save(im, path_webp, path_jpg)


# ------------------------------------------------------------------ earnings card (light)
def earnings_card(p, a, path_webp, path_jpg):
    im = Image.new("RGBA", (W, H), PAPER + (255,))
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, W, 14], fill=NAVY)
    _kicker(dr, p.get("coverLabel") or "Quarterly results", dark=False, accent=GOLD)
    figs = a["figures"]
    companies = [c for c in a["companies"] if c] or [""]
    multi = len({f.get("company") for f in figs if f.get("company")}) > 1
    if not multi:
        name = figs[0].get("company") or companies[0]
        # neutral initial badge (no imitation logos)
        dr.rounded_rectangle([84, 170, 204, 290], radius=26, fill=NAVY)
        dr.text((144, 230), name[:1].upper(), font=F(BLACK, 72), fill=(255, 255, 255), anchor="mm")
        nf = _fit(dr, name, XB, 64, 1250)
        dr.text((236, 196), name, font=nf, fill=INK)
        per = figs[0].get("period") or ""
        dr.text((238, 270), per, font=F(MED, 30), fill=MUTED)
        x, y = 84, 360
        ser = next((f for f in figs if isinstance(f.get("series"), list) and len(f["series"]) >= 2), None)
        for f in figs[:2]:
            card_w = 470 if ser else 680
            dr.rounded_rectangle([x, y, x + card_w, y + 330], radius=24, fill=(255, 255, 255), outline=LINE, width=3)
            dr.text((x + 40, y + 36), f["label"].upper(), font=F(SEMI, 26), fill=MUTED)
            vf = _fit(dr, f["value"], BLACK, 96 if card_w > 600 else 74, card_w - 80)
            dr.text((x + 40, y + 82), f["value"], font=vf, fill=INK)
            ch = f.get("change") or ""
            if ch:
                neg = ch.strip()[:1] in "-−"
                c = DOWN_D if neg else UP_D
                cf = F(XB, 40 if card_w > 600 else 34)
                tw = dr.textlength(ch, font=cf)
                dr.rounded_rectangle([x + 40, y + 222, x + 40 + tw + 44, y + 288], radius=14, fill=_tint(c))
                dr.text((x + 62, y + 255), ch, font=cf, fill=c, anchor="lm")
                note = f.get("vs") or ""
                if note:
                    dr.text((x + 40 + tw + 64, y + 255), note, font=F(MED, 26), fill=MUTED, anchor="lm")
            x += card_w + 40
        if ser:
            pts = ser["series"]
            c = DOWN_D if float(pts[-1][1]) < float(pts[0][1]) else UP_D
            _rrect(im, [1084, 330, W - 84, 720], 24, fill=(255, 255, 255, 255), outline=LINE + (255,), width=3)
            _line_chart(im, (1112, 356, W - 112, 712), pts, c, dark=False, label=ser.get("seriesLabel") or ser["label"],
                        fmt=lambda v: f"₹{v:,.0f}")
            dr = ImageDraw.Draw(im)
    else:
        dr.text((84, 180), "Q2 RESULTS SCORECARD", font=F(BLACK, 64), fill=INK)
        dr.text((86, 262), figs[0].get("period") or "", font=F(MED, 30), fill=MUTED)
        y = 330
        for f in figs[:4]:
            dr.line([(84, y), (W - 84, y)], fill=LINE, width=3)
            dr.rounded_rectangle([84, y + 26, 154, y + 96], radius=16, fill=NAVY)
            dr.text((119, y + 61), (f.get("company") or "?")[:1], font=F(BLACK, 40), fill=(255, 255, 255), anchor="mm")
            dr.text((180, y + 30), f.get("company") or "", font=F(XB, 40), fill=INK)
            dr.text((180, y + 80), f["label"], font=F(MED, 24), fill=MUTED)
            dr.text((1080, y + 60), f["value"], font=F(BLACK, 46), fill=INK, anchor="rm")
            ch = f.get("change") or ""
            if ch:
                neg = ch.strip()[:1] in "-−"
                dr.text((W - 84, y + 60), ch, font=F(XB, 38), fill=DOWN_D if neg else UP_D, anchor="rm")
            y += 118
    dr.text((84, H - 74), f'{_date_line(p, a)} · Figures as reported; see sources in the story', font=F(MED, 24), fill=MUTED)
    _brand(dr, dark=False, accent=GOLD)
    _save(im, path_webp, path_jpg)


# ------------------------------------------------------------------ IPO listing card
def ipo_card(p, a, path_webp, path_jpg):
    """Left: company, issue -> listing price, gain/loss. Right: listing-day price chart (when verified points exist)."""
    f = a["figures"][0]
    neg = f["pct"].startswith("-")
    col = DOWN if neg else UP
    im = _grad((22, 12, 60), (40, 22, 96))
    dr = ImageDraw.Draw(im)
    _kicker(dr, "IPO listing", accent=GOLD)
    has_chart = isinstance(f.get("series"), list) and len(f["series"]) >= 2
    L = 860 if has_chart else W - 168  # width of the left column
    nf = _fit(dr, f["label"], BLACK, 96, L)
    dr.text((84, 166), f["label"], font=nf, fill=(255, 255, 255))
    dr.text((86, 282), f'Listed {tmdate.fmt(f["date"], "%-d %b %Y") if f.get("date") else ""} · {f.get("exchange", "NSE")}', font=F(MED, 30), fill=(196, 181, 253))
    # issue -> listing price boxes
    bw = (L - 60) // 2
    y = 350
    for i, (lab, val) in enumerate((("ISSUE PRICE", f["issue"]), ("LISTING PRICE", f["listing"]))):
        x = 84 + i * (bw + 60)
        _rrect(im, [x, y, x + bw, y + 190], 24, fill=(255, 255, 255, 24), outline=(255, 255, 255, 70), width=2)
        dr = ImageDraw.Draw(im)
        dr.text((x + 32, y + 30), lab, font=F(SEMI, 24), fill=(203, 213, 225))
        dr.text((x + 32, y + 74), val, font=_fit(dr, val, BLACK, 84, bw - 64), fill=(255, 255, 255))
    ax = 84 + bw + 14
    dr.polygon([(ax, y + 82), (ax + 32, y + 95), (ax, y + 108)], fill=GOLD)
    # gain / loss band
    gy = y + 230
    _rrect(im, [84, gy, 84 + L, gy + 150], 24, fill=col + (55,), outline=col + (255,), width=3)
    dr = ImageDraw.Draw(im)
    dr.text((116, gy + 75), "LISTING GAIN" if not neg else "LISTING LOSS", font=F(SEMI, 28), fill=(255, 255, 255), anchor="lm")
    dr.text((84 + L - 32, gy + 75), f["pct"], font=F(BLACK, 88), fill=(255, 255, 255), anchor="rm")
    if has_chart:
        cx0 = 84 + L + 50
        _rrect(im, [cx0, 166, W - 84, 730], 26, fill=(255, 255, 255, 16), outline=(255, 255, 255, 50), width=2)
        _line_chart(im, (cx0 + 30, 196, W - 114, 712), f["series"], col, dark=True, label=f.get("seriesLabel") or "Price, ₹",
                    fmt=lambda v: f"₹{v:,.2f}".replace(".00", ""), base=float(re.sub(r"[^\d.]", "", f["issue"])))
        dr = ImageDraw.Draw(im)
    src = f.get("seriesSource")
    dr.text((84, H - 60), "Source: TotalMarket IPO register" + (f", {src}" if src else ""), font=F(MED, 24), fill=(196, 181, 253))
    _brand(dr, accent=GOLD)
    _save(im, path_webp, path_jpg)


TEMPLATES = {"index_chart": index_chart, "earnings_card": earnings_card, "ipo_card": ipo_card}
