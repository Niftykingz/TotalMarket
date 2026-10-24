"""TotalMarket data-driven cover layouts, v2 (1600×900, Pillow, deterministic).

Every number drawn here comes from the story's `chart` spec, whose items the strict
pipeline has verified against source evidence (pipeline/core.py, stage 3). No layout
invents, rounds or estimates a figure; text is rendered with Inter, never generated.

Kept in a separate module from cover_templates.py so that previously published covers
(whose file names hash cover_templates.py) never change.

chart = {"type": <layout>, "title"?: str, "asOf"?: str, "source"?: str,
         "items": [{"label", "value", "change"?, "pct"?, "prev"?, "note"?, "role"?}]}

Layouts
  index_board       market index: Sensex/Nifty tiles + breadth / mid / small-cap chips
  global_bars       global markets: diverging % bars for each index, GIFT Nifty tile
  commodity_card    gold, silver, crude: price hero + comparison tiles (+ prev → now bar)
  forex_card        rupee: previous close → today step, paise change, direction
  policy_rate       RBI policy: previous rate → new rate columns + change in bps
  stock_move        single stock: price, change and a ladder of verified reference levels
  ipo_subscription  IPO demand: times-subscribed bars by investor category + total
  earnings_v2       results: revenue and profit cards with YoY, year-ago vs now bars
"""
import re

from PIL import Image, ImageDraw

import cover_templates as ct

W, H = ct.W, ct.H
F, BLACK, XB, SEMI, MED = ct.F, ct.BLACK, ct.XB, ct.SEMI, ct.MED
UP, DOWN, UP_D, DOWN_D, INK, MUTED, LINE, NAVY, BLUE, GOLD = ct.UP, ct.DOWN, ct.UP_D, ct.DOWN_D, ct.INK, ct.MUTED, ct.LINE, ct.NAVY, ct.BLUE, ct.GOLD
WHITE = (255, 255, 255)

# minimum verified content each layout needs (checked by graphics_selector before choosing it)
REQUIRES = {
    "index_board": "2+ items with value and change or pct",
    "global_bars": "3+ items with pct",
    "commodity_card": "1+ item with value and change, pct or prev",
    "forex_card": "1 item with value and prev or change",
    "policy_rate": "items with role 'before' and 'after'",
    "stock_move": "1 item with value and change or pct",
    "ipo_subscription": "item with role 'total' and 2+ category items",
    "earnings_v2": "2+ items with value and change",
}


def num(s):
    try:
        return float(re.sub(r"[^\d.\-]", "", str(s).replace("−", "-").replace(",", "")))
    except ValueError:
        return None


def neg(s):
    return str(s or "").strip()[:1] in "-−"


def sign_col(s, dark=True):
    if not s:
        return (203, 213, 225) if dark else MUTED
    return (DOWN if dark else DOWN_D) if neg(s) else (UP if dark else UP_D)


def ok(chart):
    """'' if the chart has what its layout needs, else what is missing."""
    t, items = chart.get("type"), chart.get("items") or []
    has = lambda i, *ks: any(i.get(k) not in (None, "") for k in ks)
    if t == "index_board":
        return "" if sum(1 for i in items if has(i, "value") and has(i, "change", "pct")) >= 2 else REQUIRES[t]
    if t == "global_bars":
        return "" if sum(1 for i in items if has(i, "pct") and num(i["pct"]) is not None) >= 3 else REQUIRES[t]
    if t == "commodity_card":
        return "" if any(has(i, "value") and has(i, "change", "pct", "prev") for i in items) else REQUIRES[t]
    if t == "forex_card":
        return "" if items and has(items[0], "value") and has(items[0], "prev", "change") else REQUIRES[t]
    if t == "policy_rate":
        roles = {i.get("role") for i in items if has(i, "value")}
        return "" if {"before", "after"} <= roles else REQUIRES[t]
    if t == "stock_move":
        return "" if items and has(items[0], "value") and has(items[0], "change", "pct") else REQUIRES[t]
    if t == "ipo_subscription":
        tot = [i for i in items if i.get("role") == "total" and num(i.get("value")) is not None]
        cats = [i for i in items if i.get("role") != "total" and num(i.get("value")) is not None]
        return "" if tot and len(cats) >= 2 else REQUIRES[t]
    if t == "earnings_v2":
        return "" if sum(1 for i in items if has(i, "value") and has(i, "change")) >= 2 else REQUIRES[t]
    return f"unknown layout {t!r}"


# ------------------------------------------------------------------ shared pieces
def _head(im, dr, p, chart, dark=True, accent=GOLD, max_w=1440, y=150, size=76):
    ct._kicker(dr, chart.get("title") or p.get("coverLabel") or "TotalMarket", dark=dark, accent=accent)
    text = str(p.get("coverHeadline") or p.get("title") or "")
    f = ct._fit(dr, text, BLACK, size, max_w, min_size=44)
    dr.text((84, y), text, font=f, fill=WHITE if dark else INK)
    return y + f.size + 24


def _foot(dr, p, chart, dark=True, accent=GOLD):
    bits = [chart.get("asOf") or "", ("Source: " + chart["source"]) if chart.get("source") else ""]
    line = " · ".join(b for b in bits if b)
    if line:
        f = ct._fit(dr, line, MED, 24, 1050, min_size=18)
        dr.text((84, H - 74), line, font=f, fill=(148, 163, 184) if dark else MUTED)
    ct._brand(dr, dark=dark, accent=accent)


def _pill(im, x, y, text, col, size=34, light_bg=False):
    dr = ImageDraw.Draw(im)
    f = F(XB, size)
    w = dr.textlength(text, font=f)
    fill = ct._tint(col, .16) + (255,) if light_bg else col + (60,)
    ct._rrect(im, [x, y, x + w + 40, y + size + 26], (size + 26) // 2, fill=fill)
    ImageDraw.Draw(im).text((x + 20, y + (size + 26) / 2), text, font=f, fill=col if light_bg else WHITE, anchor="lm")
    return w + 40


def _chg(i):
    parts = [str(i.get("change") or "").strip(), str(i.get("pct") or "").strip()]
    parts = [x for x in parts if x]
    if len(parts) == 2:
        return f"{parts[0]} ({parts[1]})"
    return parts[0] if parts else ""


# ------------------------------------------------------------------ 1 index board
def index_board(p, a, wp, jp):
    ch = a["chart"]
    items = ch["items"]
    main = [i for i in items if i.get("value") and (i.get("change") or i.get("pct"))][:2]
    rest = [i for i in items if i not in main][:4]
    down = neg(main[0].get("change") or main[0].get("pct"))
    acc = DOWN if down else UP
    im = ct._grad((6, 18, 40), (34, 16, 28) if down else (10, 46, 52))
    import market_art
    art_id = market_art.choice(p, "down" if down else "up")
    if art_id:  # approved bull / bear artwork, dimmed behind the data tiles (new stories only)
        im.alpha_composite(market_art.layer(art_id, W, H, strength=.75, text_width=1000))
    dr = ImageDraw.Draw(im)
    y = _head(im, dr, p, ch, accent=acc, size=70)
    tw = (W - 168 - 40) // 2
    for k, i in enumerate(main):
        x = 84 + k * (tw + 40)
        ct._rrect(im, [x, y + 10, x + tw, y + 300], 28, fill=(10, 8, 14, 170) if art_id else (255, 255, 255, 20), outline=(255, 255, 255, 46), width=2)
        dr = ImageDraw.Draw(im)
        dr.text((x + 36, y + 40), str(i["label"]).upper(), font=F(SEMI, 28), fill=(203, 213, 225))
        dr.text((x + 36, y + 84), str(i["value"]), font=ct._fit(dr, str(i["value"]), BLACK, 96, tw - 72), fill=WHITE)
        c = sign_col(i.get("change") or i.get("pct"))
        arrow = "▼ " if neg(i.get("change") or i.get("pct")) else "▲ "
        dr.text((x + 36, y + 214), arrow + _chg(i), font=ct._fit(dr, arrow + _chg(i), XB, 40, tw - 72), fill=c)
        if i.get("note"):
            dr.text((x + tw - 36, y + 48), str(i["note"]), font=F(MED, 22), fill=(148, 163, 184), anchor="ra")
    cy = y + 340
    if rest:
        cw = (W - 168 - 30 * (len(rest) - 1)) // len(rest)
        for k, i in enumerate(rest):
            x = 84 + k * (cw + 30)
            c = sign_col(i.get("change") or i.get("pct") or i.get("value") if i.get("role") == "move" else i.get("change") or i.get("pct"))
            if art_id:
                ct._rrect(im, [x, cy, x + cw, cy + 150], 22, fill=(10, 8, 14, 170))
            ct._rrect(im, [x, cy, x + cw, cy + 150], 22, fill=c + (40,), outline=c + (150,), width=2)
            dr = ImageDraw.Draw(im)
            dr.text((x + 26, cy + 24), str(i["label"]).upper(), font=ct._fit(dr, str(i["label"]).upper(), SEMI, 22, cw - 52), fill=(226, 232, 240))
            val = " ".join(v for v in (str(i.get("value") or ""), _chg(i)) if v)
            dr.text((x + 26, cy + 70), val, font=ct._fit(dr, val, XB, 46, cw - 52), fill=WHITE)
    if art_id:
        market_art.brand_backing(im, W, H)
    _foot(ImageDraw.Draw(im), p, ch, accent=acc)
    ct._save(im, wp, jp)


# ------------------------------------------------------------------ 2 global bars
def global_bars(p, a, wp, jp):
    ch = a["chart"]
    items = [i for i in ch["items"] if num(i.get("pct")) is not None][:7]
    im = Image.new("RGBA", (W, H), (247, 249, 252, 255))
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, W, 12], fill=BLUE)
    y0 = _head(im, dr, p, ch, dark=False, accent=BLUE, size=64)
    rows = len(items)
    top, bottom = y0 + 10, H - 120
    rh = min(84, (bottom - top) / max(1, rows))
    zx, half = 1060, 300                     # zero line and max bar length each side
    span = max(abs(num(i["pct"])) for i in items) or 1
    for k, i in enumerate(items):
        yy = top + k * rh
        if k % 2 == 0:
            ct._rrect(im, [70, yy, W - 70, yy + rh], 12, fill=(238, 242, 247, 255))
        dr = ImageDraw.Draw(im)
        v = num(i["pct"])
        c = DOWN_D if v < 0 else UP_D
        dr.text((96, yy + rh / 2), str(i["label"]), font=ct._fit(dr, str(i["label"]), SEMI, 32, 420), fill=INK, anchor="lm")
        if i.get("value"):
            dr.text((530, yy + rh / 2), str(i["value"]), font=ct._fit(dr, str(i["value"]), MED, 28, 200), fill=MUTED, anchor="lm")
        L = max(6, abs(v) / span * half)
        x0, x1 = (zx - L, zx) if v < 0 else (zx, zx + L)
        ct._rrect(im, [x0, yy + rh * .22, x1, yy + rh * .78], 10, fill=c + (255,))
        dr = ImageDraw.Draw(im)
        txt = str(i["pct"]) if "%" in str(i["pct"]) else f"{i['pct']}%"
        dr.text((W - 96, yy + rh / 2), txt, font=F(XB, 32), fill=c, anchor="rm")
    dr.line([(zx, top - 6), (zx, top + rows * rh + 6)], fill=(148, 163, 184), width=3)
    _foot(dr, p, ch, dark=False, accent=BLUE)
    ct._save(im, wp, jp)


# ------------------------------------------------------------------ 3 commodity card
PALETTES = {"gold": ((46, 30, 6), (92, 62, 12), (240, 196, 92)), "silver": ((28, 32, 40), (70, 78, 92), (209, 213, 219)),
            "oil": ((12, 12, 14), (52, 36, 16), (245, 158, 11)), "default": ((20, 28, 44), (52, 40, 20), GOLD)}


def commodity_card(p, a, wp, jp):
    ch = a["chart"]
    items = ch["items"]
    hero = next(i for i in items if i.get("value") and (i.get("change") or i.get("pct") or i.get("prev")))
    others = [i for i in items if i is not hero][:3]
    c1, c2, acc = PALETTES.get(p.get("symbol") if p.get("symbol") in PALETTES else "default")
    im = ct._grad(c1, c2, .4)
    dr = ImageDraw.Draw(im)
    y = _head(im, dr, p, ch, accent=acc, size=66, max_w=1440)
    dr.text((84, y + 10), str(hero["label"]).upper(), font=F(SEMI, 30), fill=(229, 231, 235))
    vf = ct._fit(dr, str(hero["value"]), BLACK, 150, 900)
    dr.text((80, y + 48), str(hero["value"]), font=vf, fill=acc)
    cy = y + 60 + vf.size + 10
    if _chg(hero):
        _pill(im, 84, cy, ("▼ " if neg(hero.get("change") or hero.get("pct")) else "▲ ") + _chg(hero), sign_col(hero.get("change") or hero.get("pct")), 34)
    if hero.get("prev"):
        dr = ImageDraw.Draw(im)
        dr.text((84 + 520, cy + 30), f"Previous: {hero['prev']}", font=F(MED, 30), fill=(229, 231, 235), anchor="lm")
    if others:
        x0, yy = 1060, y + 20
        th = min(170, (H - 140 - yy) // len(others) - 18)
        for i in others:
            ct._rrect(im, [x0, yy, W - 84, yy + th], 22, fill=(255, 255, 255, 26), outline=(255, 255, 255, 60), width=2)
            dr = ImageDraw.Draw(im)
            dr.text((x0 + 28, yy + 22), str(i["label"]).upper(), font=ct._fit(dr, str(i["label"]).upper(), SEMI, 22, W - 84 - x0 - 56), fill=(229, 231, 235))
            dr.text((x0 + 28, yy + 58), str(i["value"]), font=ct._fit(dr, str(i["value"]), XB, 48, W - 84 - x0 - 56), fill=WHITE)
            if _chg(i) and th > 130:
                dr.text((x0 + 28, yy + 118), _chg(i), font=F(SEMI, 26), fill=sign_col(i.get("change") or i.get("pct")))
            yy += th + 18
    _foot(ImageDraw.Draw(im), p, ch, accent=acc)
    ct._save(im, wp, jp)


# ------------------------------------------------------------------ 4 forex card
def forex_card(p, a, wp, jp):
    ch = a["chart"]
    i = ch["items"][0]
    extra = ch["items"][1:3]
    up = not neg(i.get("change") or i.get("pct")) if (i.get("change") or i.get("pct")) else (num(i["value"]) or 0) > (num(i.get("prev")) or 0)
    acc = DOWN if up else UP     # USD/INR up = rupee weaker
    im = ct._grad((4, 32, 36), (8, 62, 66), .5)
    dr = ImageDraw.Draw(im)
    y = _head(im, dr, p, ch, accent=acc, size=70)
    dr.text((84, y + 6), str(i["label"]).upper(), font=F(SEMI, 30), fill=(204, 251, 241))
    if i.get("prev"):
        bx = [(84, "PREVIOUS", str(i["prev"]), (148, 163, 184)), (640, "NOW", str(i["value"]), WHITE)]
        for x, lab, val, col in bx:
            ct._rrect(im, [x, y + 54, x + 480, y + 300], 26, fill=(255, 255, 255, 22), outline=(255, 255, 255, 60), width=2)
            dr = ImageDraw.Draw(im)
            dr.text((x + 32, y + 80), lab, font=F(SEMI, 24), fill=(204, 251, 241))
            dr.text((x + 32, y + 124), val, font=ct._fit(dr, val, BLACK, 110, 416), fill=col)
        dr.polygon([(578, y + 160), (616, y + 177), (578, y + 194)], fill=acc)
    else:
        dr.text((80, y + 50), str(i["value"]), font=F(BLACK, 170), fill=WHITE)
    cy = y + 340
    if _chg(i):
        _pill(im, 84, cy, _chg(i), acc, 36)
    dr = ImageDraw.Draw(im)
    dr.text((84, cy + 96), "Rupee weaker against the dollar" if up else "Rupee stronger against the dollar", font=F(SEMI, 30), fill=(204, 251, 241))
    yy = y + 54
    for e in extra:
        ct._rrect(im, [1190, yy, W - 84, yy + 150], 22, fill=(255, 255, 255, 22), outline=(255, 255, 255, 50), width=2)
        dr = ImageDraw.Draw(im)
        dr.text((1216, yy + 22), str(e["label"]).upper(), font=ct._fit(dr, str(e["label"]).upper(), SEMI, 22, 280), fill=(204, 251, 241))
        val = " ".join(v for v in (str(e.get("value") or ""), _chg(e)) if v)
        dr.text((1216, yy + 64), val, font=ct._fit(dr, val, XB, 42, 280), fill=WHITE)
        yy += 170
    _foot(ImageDraw.Draw(im), p, ch, accent=acc)
    ct._save(im, wp, jp)


# ------------------------------------------------------------------ 5 policy rate
def policy_rate(p, a, wp, jp):
    ch = a["chart"]
    by = {i.get("role"): i for i in ch["items"]}
    old, new = by["before"], by["after"]
    chg = by.get("change")
    ov, nv = num(old["value"]), num(new["value"])
    im = ct._grad((236, 243, 255), (255, 255, 255), .35)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    for k, r in enumerate(range(260, 900, 90)):
        ld.arc([1180 - r, 520 - r, 1180 + r, 520 + r], 180, 360, fill=(37, 99, 235, 26 - k * 2), width=3)
    im.alpha_composite(lay)
    dr = ImageDraw.Draw(im)
    _head(im, dr, p, ch, dark=False, accent=BLUE, size=72, max_w=1440)
    base, max_h, hi = 700, 270, max(ov, nv) or 1
    cols = [(110, old, ov, (148, 163, 184)), (430, new, nv, BLUE)]
    for x, it, v, col in cols:
        h = v / hi * max_h
        ct._rrect(im, [x, base - h, x + 230, base], 22, fill=col + (255,))
    dr = ImageDraw.Draw(im)
    for x, it, v, col in cols:
        h = v / hi * max_h
        dr.text((x + 115, base - h - 18), str(it["value"]), font=F(XB, 54), fill=INK, anchor="mb")
        dr.text((x + 115, base + 18), str(it["label"]), font=ct._fit(dr, str(it["label"]), MED, 26, 300), fill=MUTED, anchor="ma")
    ay = base - ov / hi * max_h / 2
    dr.line([(358, ay), (412, ay)], fill=NAVY, width=8)
    dr.polygon([(412, ay - 16), (436, ay), (412, ay + 16)], fill=NAVY)
    if chg:
        c = DOWN_D if neg(chg["value"]) else UP_D
        ct._rrect(im, [860, 400, 1500, 580], 28, fill=(255, 255, 255, 255), outline=LINE + (255,), width=3)
        dr = ImageDraw.Draw(im)
        dr.text((900, 430), str(chg["label"]).upper(), font=F(SEMI, 24), fill=MUTED)
        dr.text((900, 470), str(chg["value"]), font=F(BLACK, 76), fill=c)
    _foot(ImageDraw.Draw(im), p, ch, dark=False, accent=BLUE)
    ct._save(im, wp, jp)


# ------------------------------------------------------------------ 6 stock move
def stock_move(p, a, wp, jp):
    ch = a["chart"]
    i = ch["items"][0]
    refs = [r for r in ch["items"][1:5] if num(r.get("value")) is not None]
    c = sign_col(i.get("change") or i.get("pct"), dark=False)
    im = Image.new("RGBA", (W, H), (248, 250, 252, 255))
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, 18, H], fill=c)
    ct._kicker(dr, ch.get("title") or "Stock move", dark=False, accent=c)
    name = str(i["label"])
    dr.rounded_rectangle([84, 166, 196, 278], radius=24, fill=NAVY)
    dr.text((140, 222), name[:1].upper(), font=F(BLACK, 66), fill=WHITE, anchor="mm")
    dr.text((224, 172), name, font=ct._fit(dr, name, XB, 60, 760), fill=INK)
    head = str(p.get("coverHeadline") or "")
    dr.text((226, 246), head, font=ct._fit(dr, head, SEMI, 30, 760, min_size=20), fill=MUTED)
    dr.text((80, 330), str(i["value"]), font=ct._fit(dr, str(i["value"]), BLACK, 150, 820), fill=INK)
    _pill(im, 84, 520, ("▼ " if neg(i.get("change") or i.get("pct")) else "▲ ") + _chg(i), c, 40, light_bg=True)
    if refs:
        vals = [num(i["value"])] + [num(r["value"]) for r in refs]
        lo, hi = min(vals), max(vals)
        pad = (hi - lo) * .15 or max(1, hi * .05)
        lo, hi = lo - pad, hi + pad
        x0, x1, y0, y1 = 1010, 1516, 180, 760
        ct._rrect(im, [x0 - 30, y0 - 30, x1 + 20, y1 + 30], 26, fill=(255, 255, 255, 255), outline=LINE + (255,), width=3)
        dr = ImageDraw.Draw(im)
        Y = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
        dr.line([(x0 + 120, y0), (x0 + 120, y1)], fill=LINE, width=6)
        for r in refs:
            yy = Y(num(r["value"]))
            dr.line([(x0 + 100, yy), (x0 + 140, yy)], fill=MUTED, width=4)
            dr.text((x0 + 160, yy), f'{r["label"]}  {r["value"]}', font=ct._fit(dr, f'{r["label"]}  {r["value"]}', MED, 26, x1 - x0 - 170), fill=MUTED, anchor="lm")
        yy = Y(num(i["value"]))
        dr.ellipse([x0 + 104, yy - 16, x0 + 136, yy + 16], fill=c)
        dr.text((x0 + 160, yy), f'Now  {i["value"]}', font=F(XB, 30), fill=c, anchor="lm")
        dr.text((x0 - 6, y0 - 4), "VERIFIED REFERENCE LEVELS", font=F(SEMI, 20), fill=MUTED)
    else:  # no reference levels: a move gauge built from the verified % change only
        x0, y0, x1, y1 = 1000, 180, W - 84, 740
        ct._rrect(im, [x0, y0, x1, y1], 26, fill=ct._tint(c, .08) + (255,), outline=ct._tint(c, .35) + (255,), width=3)
        dr = ImageDraw.Draw(im)
        dr.text((x0 + 40, y0 + 36), "MOVE ON THE DAY", font=F(SEMI, 24), fill=MUTED)
        dr.text((x0 + 40, y0 + 80), _chg(i), font=ct._fit(dr, _chg(i), BLACK, 110, x1 - x0 - 80), fill=c)
        if i.get("note"):
            dr.text((x0 + 40, y0 + 260), str(i["note"]), font=ct._fit(dr, str(i["note"]), MED, 30, x1 - x0 - 80), fill=INK)
        if ch.get("asOf"):
            dr.text((x0 + 40, y1 - 70), str(ch["asOf"]), font=ct._fit(dr, str(ch["asOf"]), MED, 26, x1 - x0 - 80), fill=MUTED)
    _foot(dr, p, ch, dark=False, accent=BLUE)
    ct._save(im, wp, jp)


# ------------------------------------------------------------------ 7 IPO subscription
def ipo_subscription(p, a, wp, jp):
    ch = a["chart"]
    tot = next(i for i in ch["items"] if i.get("role") == "total")
    cats = [i for i in ch["items"] if i.get("role") != "total" and num(i.get("value")) is not None][:6]
    im = ct._grad((24, 10, 56), (58, 22, 104), .45)
    dr = ImageDraw.Draw(im)
    y = _head(im, dr, p, ch, accent=GOLD, size=66, max_w=1440)
    dr.text((84, y + 6), str(tot["label"]).upper(), font=F(SEMI, 28), fill=(221, 214, 254))
    tv = str(tot["value"]) if "x" in str(tot["value"]).lower() else f'{tot["value"]}x'
    dr.text((80, y + 44), tv, font=F(BLACK, 150), fill=GOLD)
    if tot.get("note"):
        dr.text((84, y + 230), str(tot["note"]), font=F(MED, 28), fill=(221, 214, 254))
    mx = max(num(c["value"]) for c in cats) or 1
    x0, x1 = 760, W - 200
    rh = min(130, (H - 150 - (y + 10)) / len(cats))
    for k, c in enumerate(cats):
        yy = y + 10 + k * rh
        v = num(c["value"])
        dr.text((x0, yy + 4), str(c["label"]), font=F(SEMI, 26), fill=WHITE)
        L = max(8, v / mx * (x1 - x0))
        ct._rrect(im, [x0, yy + 40, x0 + L, yy + rh - 14], 10, fill=(196, 181, 253, 235) if v >= 1 else (251, 146, 60, 235))
        dr = ImageDraw.Draw(im)
        lbl = str(c["value"]) if "x" in str(c["value"]).lower() else f'{c["value"]}x'
        dr.text((x0 + L + 16, yy + (rh + 26) / 2), lbl, font=F(XB, 30), fill=WHITE, anchor="lm")
    _foot(ImageDraw.Draw(im), p, ch, accent=GOLD)
    ct._save(im, wp, jp)


# ------------------------------------------------------------------ 8 earnings v2
def earnings_v2(p, a, wp, jp):
    ch = a["chart"]
    items = [i for i in ch["items"] if i.get("value") and i.get("change")][:3]
    im = Image.new("RGBA", (W, H), (248, 250, 252, 255))
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, W, 14], fill=NAVY)
    ct._kicker(dr, ch.get("title") or "Quarterly results", dark=False, accent=GOLD)
    head = str(p.get("coverHeadline") or "")
    dr.text((84, 150), head, font=ct._fit(dr, head, BLACK, 70, 1440), fill=INK)
    if ch.get("period"):
        dr.text((86, 240), str(ch["period"]), font=F(MED, 30), fill=MUTED)
    cw = 470 if any(i.get("prev") for i in items) else 680
    x, y = 84, 310
    for i in items[:2]:
        ct._rrect(im, [x, y, x + cw, y + 360], 24, fill=(255, 255, 255, 255), outline=LINE + (255,), width=3)
        dr = ImageDraw.Draw(im)
        dr.text((x + 36, y + 32), str(i["label"]).upper(), font=ct._fit(dr, str(i["label"]).upper(), SEMI, 24, cw - 72), fill=MUTED)
        dr.text((x + 36, y + 80), str(i["value"]), font=ct._fit(dr, str(i["value"]), BLACK, 88, cw - 72), fill=INK)
        _pill(im, x + 36, y + 216, ("▼ " if neg(i["change"]) else "▲ ") + str(i["change"]), sign_col(i["change"], dark=False), 34, light_bg=True)
        dr = ImageDraw.Draw(im)
        if i.get("note"):
            dr.text((x + 36, y + 300), str(i["note"]), font=F(MED, 24), fill=MUTED)
        x += cw + 36
    bars = [i for i in items if i.get("prev") and num(i["prev"]) is not None and num(i["value"]) is not None][:2]
    if bars:
        bx0, by0, bx1, by1 = 1100, 330, W - 84, 680
        ct._rrect(im, [bx0 - 20, by0 - 40, bx1 + 10, by1 + 70], 24, fill=(255, 255, 255, 255), outline=LINE + (255,), width=3)
        dr = ImageDraw.Draw(im)
        dr.text((bx0, by0 - 24), str(ch.get("compareLabel") or "Year ago vs now").upper(), font=F(SEMI, 22), fill=MUTED)
        gw = (bx1 - bx0) / len(bars)
        for k, i in enumerate(bars):
            pv, nv = num(i["prev"]), num(i["value"])
            mx = max(abs(pv), abs(nv)) or 1
            gx = bx0 + k * gw + 20
            for j, (v, col, t) in enumerate(((pv, (203, 213, 225), str(i["prev"])), (nv, BLUE, str(i["value"])))):
                h = abs(v) / mx * (by1 - by0 - 60)
                xx = gx + j * (gw / 2 - 10)
                ct._rrect(im, [xx, by1 - h, xx + gw / 2 - 30, by1], 10, fill=col + (255,))
                dr = ImageDraw.Draw(im)
                dr.text((xx + (gw / 2 - 30) / 2, by1 - h - 8), t, font=ct._fit(dr, t, SEMI, 20, gw / 2 - 20, min_size=14), fill=INK, anchor="mb")
            dr.text((gx, by1 + 14), str(i["label"]), font=ct._fit(dr, str(i["label"]), MED, 20, gw - 30, min_size=14), fill=MUTED)
    _foot(ImageDraw.Draw(im), p, ch, dark=False, accent=GOLD)
    ct._save(im, wp, jp)


TEMPLATES = {"index_board": index_board, "global_bars": global_bars, "commodity_card": commodity_card, "forex_card": forex_card,
             "policy_rate": policy_rate, "stock_move": stock_move, "ipo_subscription": ipo_subscription, "earnings_v2": earnings_v2}
