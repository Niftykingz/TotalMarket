"""TotalMarket premium cover engine (1600x900, 16:9).

Follows the TotalMarket graphics brief: one dominant number or short phrase (3–6 words),
one rendered focal object per category, category colour identity, branding bottom-right,
no cartoons, no fake logos, no invented numbers (text comes only from the story's own
`coverHeadline` / `stat` / `statLabel` fields). Exports WebP (site) and JPG (share preview).
"""
import hashlib, json, math, os, re
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

VERSION = "p7-original-variety"
W, H = 1600, 900
HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, "fonts")
F_BLACK = os.path.join(FD, "InterDisplay-Black.otf")
F_XB = os.path.join(FD, "InterDisplay-ExtraBold.otf")
F_SEMI = os.path.join(FD, "Inter-SemiBold.otf")
F_MED = os.path.join(FD, "Inter-Medium.otf")
font = lambda path, size: ImageFont.truetype(path, int(size))

THEMES = {  # bg top-left, bg bottom-right, accent, kicker label
    "markets-up":   ("#07090B", "#121A16", "#10C47A", "INDIAN MARKETS"),
    "markets-down": ("#0A0809", "#1C1013", "#E5334B", "INDIAN MARKETS"),
    "markets":      ("#08090C", "#14171D", "#10C47A", "INDIAN MARKETS"),
    "global":       ("#040817", "#0A1D45", "#22D3EE", "GLOBAL MARKETS"),
    "gold":         ("#070605", "#1E1607", "#E8B64A", "COMMODITIES"),
    "silver":       ("#08090B", "#1B1E23", "#CBD2DC", "COMMODITIES"),
    "oil":          ("#090603", "#251507", "#F59E0B", "COMMODITIES"),
    "forex":        ("#04100D", "#0D2A23", "#34D399", "FOREX"),
    "startups":     ("#0D0521", "#24104D", "#60A5FA", "STARTUPS & IPOs"),
    "policy":       ("#050C22", "#0F1F47", "#C9A227", "ECONOMY & POLICY"),
    "tech":         ("#040A18", "#0D1C3D", "#38BDF8", "TECH & AI"),
    "festive":      ("#140406", "#3A0E10", "#F5B342", "FESTIVE SPECIAL"),
}
SYMBOL_OBJ = {"gold": "gold", "silver": "silver", "oil": "oil", "dollar": "forex", "rupee": "forex", "euro": "forex",
              "yen": "forex", "bitcoin": "bitcoin", "yield": "yield", "bank": "bank", "chip": "chip", "rocket": "growth",
              "bow": "diya", "diya": "diya", "ravan": "diya", "bull": "candles", "bear": "candles",
              "chart-up": "candles", "chart-down": "candles", "globe": "globe", "candles": "candles", "growth": "growth",
              "shield": "shield", "servers": "servers", "neural": "neural", "coins": "coins"}
CAT_OBJ = {"markets": "candles", "global": "globe", "commodities": "gold", "startups": "growth", "policy": "bank", "tech": "chip"}
DOWN_WORDS = re.compile(r"\b(drops?|falls?|fell|slides?|slips?|plunges?|crash(es)?|tumbles?|sinks?|loses?|sheds?|weak(er)?|bear(ish)?)\b", re.I)
UP_WORDS = re.compile(r"\b(jumps?|rises?|rose|gains?|surges?|rall(y|ies)|climbs?|soars?|bull(ish)?|record high|bounces?)\b", re.I)


def rgb(h):
    h = h.lstrip("#"); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def seed_of(p):
    return int(hashlib.md5(p["id"].encode()).hexdigest()[:8], 16)


def direction(p):
    stat = str(p.get("stat") or "")
    t = " ".join([p.get("title", ""), p.get("coverHeadline") or ""])
    if stat.startswith(("-", "−")) or (DOWN_WORDS.search(t) and not UP_WORDS.search(t)):
        return "down"
    if stat.startswith("+") or UP_WORDS.search(t):
        return "up"
    return "flat"


def pick(p):
    import art
    sym = p.get("symbol")
    if not sym:
        _, sym, _ = art.detect(p)
    obj = SYMBOL_OBJ.get(sym) or CAT_OBJ.get(p["category"], "candles")
    # Prefer an original, story-specific illustration over generic candles.
    # Explicit story symbols retain editorial priority.
    if not sym or sym == "candles":
        obj = analysis(p)["object"]
    d = direction(p)
    if p.get("palette") == "festive":
        theme, obj = "festive", "diya"
    elif obj in ("gold", "silver", "oil"):
        theme = obj
    elif obj in ("forex", "bitcoin"):
        theme = "forex"
    elif p["category"] == "markets":
        theme = "markets-down" if d == "down" else "markets-up"
    else:
        theme = p["category"] if p["category"] in THEMES else "markets"
    glyph = {"rupee": "₹", "dollar": "$", "euro": "€", "yen": "¥", "bitcoin": "₿"}.get(sym, "₹")
    return obj, theme, d, glyph


# ------------------------------------------------------------------ background
def background(theme, seed, d):
    c1, c2, acc, _ = THEMES[theme]
    A, B, C = rgb(c1), rgb(c2), rgb(acc)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    t = np.clip((xx / W) * .55 + (yy / H) * .45, 0, 1)[..., None]
    img = A * (1 - t) + B * t
    gx, gy = 1170 + (seed % 60) - 30, 430 + (seed // 7 % 40) - 20
    r = np.sqrt((xx - gx) ** 2 + ((yy - gy) * 1.15) ** 2)
    img = img + C * np.exp(-(r / 430) ** 2)[..., None] * .22
    r2 = np.sqrt((xx + 200) ** 2 + (yy + 260) ** 2)
    img = img + 255 * np.exp(-(r2 / 900) ** 2)[..., None] * .035
    vx, vy = (xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)
    img = img * (1 - .55 * np.clip((vx ** 2 * .8 + vy ** 2) - .25, 0, 1))[..., None]
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    ac = tuple(int(v) for v in C)
    style = seed % 4
    if style == 0:  # perspective floor grid
        vx0, vy0 = 1180, 470
        for i in range(-14, 15):
            ld.line([(vx0 + i * 18, vy0), (vx0 + i * 150, H + 40)], fill=ac + (18,), width=1)
        for k in range(1, 9):
            y = vy0 + (H - vy0) * (k / 8) ** 1.8
            ld.line([(560, y), (W, y)], fill=ac + (16,), width=1)
    elif style == 1:  # dot matrix
        for gy_ in range(40, H, 34):
            for gx_ in range(620, W, 34):
                a = int(28 * math.exp(-(((gx_ - 1180) / 520) ** 2 + ((gy_ - 440) / 380) ** 2)))
                if a > 3:
                    ld.ellipse([gx_ - 2, gy_ - 2, gx_ + 2, gy_ + 2], fill=ac + (a,))
    elif style == 2:  # concentric arcs
        for k in range(1, 9):
            rr = 120 * k
            ld.ellipse([1180 - rr, 440 - rr, 1180 + rr, 440 + rr], outline=ac + (max(4, 26 - k * 3),), width=1)
    else:  # light beams
        for k in range(5):
            x0 = 760 + k * 170 + seed % 50
            ld.polygon([(x0, 0), (x0 + 60, 0), (x0 + 260, H), (x0 + 120, H)], fill=ac + (7,))
    rng = np.random.default_rng(seed)
    n = 26
    base = np.cumsum(rng.normal(0, 1, n)); base = (base - base.min()) / (np.ptp(base) or 1)
    trend = np.linspace(0, 1, n) * (1 if d != "down" else -1)
    ys = 640 - (base * .35 + trend * .65) * 220 + (0 if d != "down" else -200)
    ld.line([(560 + i * (W - 560) / (n - 1), float(y)) for i, y in enumerate(ys)], fill=ac + (40,), width=3, joint="curve")
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.2)))
    return im, ac


def grain(im, seed, amt=2.5):
    rng = np.random.default_rng(seed + 7)
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    return Image.fromarray(np.clip(a + rng.normal(0, amt, (H, W, 1)).astype(np.int16), 0, 255).astype(np.uint8), "RGB")


# ------------------------------------------------------------------ object helpers
S2 = 2  # objects are drawn at 2x and downscaled for smooth edges


def shade_strip(w, h, base, light=1.0, spec=.55, center=.35):
    """Cylindrical shading (left-to-right) for a w x h tile."""
    x = np.linspace(-1, 1, max(1, w))
    lam = np.clip(np.cos((x - center * .6) * 1.45), 0, 1)
    s = np.exp(-((x + center) / .12) ** 2) * spec
    col = np.clip(np.asarray(base)[None, :] * ((.28 + .72 * lam) * light)[:, None] + 255 * s[:, None], 0, 255)
    return np.repeat(col[None, :, :], max(1, h), axis=0)


def vgrad(w, h, top, bottom):
    t = np.linspace(0, 1, max(1, int(h)))[:, None, None]
    return np.repeat(np.array(top, np.float32) * (1 - t) + np.array(bottom, np.float32) * t, max(1, int(w)), axis=1)


def paste_poly(layer, pts, arr):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, y0, x1, y1 = int(min(xs)), int(min(ys)), int(math.ceil(max(xs))), int(math.ceil(max(ys)))
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    if arr.shape[0] != h or arr.shape[1] != w:
        arr = np.asarray(Image.fromarray(arr).resize((w, h)))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon([(x - x0, y - y0) for x, y in pts], fill=255)
    layer.paste(Image.fromarray(arr, "RGB").convert("RGBA"), (x0, y0), mask)


def finish(obj, floor_y, shadow_w, reflect=True):
    obj = obj.resize((W, H), Image.LANCZOS)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bb = obj.getbbox() or (0, 0, W, H)
    cx = (bb[0] + bb[2]) / 2
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([cx - shadow_w / 2, floor_y - 18, cx + shadow_w / 2, floor_y + 22], fill=(0, 0, 0, 170))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    if reflect and bb[3] > bb[1]:
        crop = obj.crop((0, int(bb[1]), W, int(floor_y)))
        ref = crop.transpose(Image.FLIP_TOP_BOTTOM)
        a = np.asarray(ref).copy()
        a[..., 3] = (a[..., 3] * np.linspace(.3, 0, ref.height)[:, None]).astype(np.uint8)
        out.alpha_composite(Image.fromarray(a, "RGBA").filter(ImageFilter.GaussianBlur(3)), (0, int(floor_y)))
    out.alpha_composite(obj)
    return out


def blank():
    return Image.new("RGBA", (W * S2, H * S2), (0, 0, 0, 0))


def glow_line(L, pts, acc, width, blur):
    gl = Image.new("RGBA", L.size, (0, 0, 0, 0))
    ImageDraw.Draw(gl).line(pts, fill=tuple(acc) + (255,), width=width, joint="curve")
    L.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))


# ------------------------------------------------------------------ focal objects
def obj_candles(seed, d, acc):
    L = blank(); dr = ImageDraw.Draw(L)
    rng = np.random.default_rng(seed)
    n = 9
    up_c, dn_c = rgb("#10C47A"), rgb("#E5334B")
    closes = np.cumsum(rng.normal(.35 if d != "down" else -.35, .9, n))
    closes = (closes - closes.min()) / (np.ptp(closes) or 1)
    x0, x1, y_top, y_bot = 880, 1500, 190, 680
    cw = (x1 - x0) / n * .56
    prev = closes[0] - (.1 if d != "down" else -.1)
    Y = lambda v: y_bot - v * (y_bot - y_top)
    pts = []
    for i, c in enumerate(closes):
        o = prev
        hi, lo = max(o, c) + rng.uniform(.03, .12), min(o, c) - rng.uniform(.03, .12)
        cx = x0 + (i + .5) * (x1 - x0) / n
        col = up_c if c >= o else dn_c
        dr.line([(cx * S2, Y(hi) * S2), (cx * S2, Y(lo) * S2)], fill=tuple(int(v * .9) for v in col) + (255,), width=4 * S2)
        bt, bb_ = Y(max(o, c)), max(Y(min(o, c)), Y(max(o, c)) + 10)
        w, h = int(cw * S2), int((bb_ - bt) * S2)
        paste_poly(L, [(cx * S2 - w / 2, bt * S2), (cx * S2 + w / 2, bt * S2), (cx * S2 + w / 2, bb_ * S2), (cx * S2 - w / 2, bb_ * S2)], shade_strip(w, h, col, spec=.45))
        pts.append((cx * S2, Y(c) * S2)); prev = c
    glow_line(L, pts, acc, 6 * S2, 10 * S2)
    dr = ImageDraw.Draw(L)
    dr.line(pts, fill=(255, 255, 255, 230), width=3 * S2, joint="curve")
    ex, ey = pts[-1]
    dr.ellipse([ex - 9 * S2, ey - 9 * S2, ex + 9 * S2, ey + 9 * S2], fill=tuple(acc) + (255,), outline=(255, 255, 255, 255), width=2 * S2)
    return finish(L, 712, 620)


def _bar(L, cx, cy, w, h, pal):
    dark, mid, light, hi = pal
    inset = w * .14
    front = [(cx - w / 2, cy), (cx + w / 2, cy), (cx + w / 2 - inset, cy - h), (cx - w / 2 + inset, cy - h)]
    shine = np.exp(-((np.linspace(0, 1, int(h)) - .25) / .07) ** 2)[:, None, None] * 90
    paste_poly(L, front, vgrad(w, h, light, dark) + shine)
    dep = h * .28
    top = [(cx - w / 2 + inset, cy - h), (cx + w / 2 - inset, cy - h), (cx + w / 2 - inset * 1.6, cy - h - dep), (cx - w / 2 + inset * 1.6, cy - h - dep)]
    paste_poly(L, top, vgrad(w, dep + 1, hi, mid))


def obj_bullion(seed, metal):
    L = blank()
    pal = {"gold": ((120, 72, 8), (196, 134, 26), (246, 196, 82), (255, 236, 168)),
           "silver": ((88, 94, 104), (150, 158, 170), (214, 220, 230), (250, 252, 255))}[metal]
    bw, bh = 290 * S2, 96 * S2
    cx0, by = (1190 + seed % 40 - 20) * S2, 700 * S2
    for i in (-1, 0, 1):
        _bar(L, cx0 + i * bw * .96, by, bw, bh, pal)
    for i in (-.5, .5):
        _bar(L, cx0 + i * bw * .96, by - bh * 1.28, bw, bh, pal)
    _bar(L, cx0, by - bh * 2.56, bw, bh, pal)
    sp = Image.new("RGBA", L.size, (0, 0, 0, 0))
    ImageDraw.Draw(sp).ellipse([cx0 - 90 * S2, by - bh * 3.2 - 30 * S2, cx0 + 90 * S2, by - bh * 3.2 + 30 * S2], fill=(255, 255, 255, 110))
    L.alpha_composite(sp.filter(ImageFilter.GaussianBlur(26 * S2)))
    return finish(L, 712, 900)


def obj_oil(seed, acc):
    L = blank(); dr = ImageDraw.Draw(L)
    cx, top, bot, bw = (1220 + seed % 30) * S2, 200 * S2, 700 * S2, 330 * S2
    paste_poly(L, [(cx - bw / 2, top), (cx + bw / 2, top), (cx + bw / 2, bot), (cx - bw / 2, bot)], shade_strip(bw, bot - top, rgb("#2A2E34"), light=1.1, spec=.35))
    band = shade_strip(bw, 80 * S2, rgb("#E08A0B"), spec=.4)
    paste_poly(L, [(cx - bw / 2, 400 * S2), (cx + bw / 2, 400 * S2), (cx + bw / 2, 480 * S2), (cx - bw / 2, 480 * S2)], band)
    for k in (.16, .62, .9):
        y = top + (bot - top) * k
        paste_poly(L, [(cx - bw / 2 - 8 * S2, y - 8 * S2), (cx + bw / 2 + 8 * S2, y - 8 * S2), (cx + bw / 2 + 8 * S2, y + 8 * S2), (cx - bw / 2 - 8 * S2, y + 8 * S2)],
                   shade_strip(bw + 16 * S2, 16 * S2, rgb("#4A5058"), spec=.5))
    dr = ImageDraw.Draw(L)
    dr.ellipse([cx - bw / 2, top - 34 * S2, cx + bw / 2, top + 34 * S2], fill=(64, 68, 76, 255), outline=(30, 32, 36, 255), width=3 * S2)
    dr.ellipse([cx + bw * .12, top - 16 * S2, cx + bw * .3, top + 4 * S2], fill=(22, 24, 27, 255))
    dx, dy, r = cx - bw * .82, 540 * S2, 64 * S2
    dr.polygon([(dx, dy - r * 2.1), (dx - r * .92, dy - r * .2), (dx + r * .92, dy - r * .2)], fill=(22, 14, 6, 255))
    dr.ellipse([dx - r, dy - r, dx + r, dy + r], fill=(22, 14, 6, 255))
    hl = Image.new("RGBA", L.size, (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse([dx - r * .55, dy - r * .75, dx - r * .12, dy - r * .1], fill=tuple(acc) + (230,))
    L.alpha_composite(hl.filter(ImageFilter.GaussianBlur(6 * S2)))
    rim = Image.new("RGBA", L.size, (0, 0, 0, 0))
    ImageDraw.Draw(rim).arc([dx - r, dy - r, dx + r, dy + r], 20, 160, fill=tuple(acc) + (210,), width=5 * S2)
    L.alpha_composite(rim.filter(ImageFilter.GaussianBlur(2 * S2)))
    return finish(L, 712, 600)


def _coin(L, cx, cy, r, face, rim, glyph, gcol):
    r = int(r)
    yy, xx = np.mgrid[0:2 * r, 0:2 * r].astype(np.float32)
    rr = np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / r
    light = np.clip(1.15 - .6 * np.sqrt((xx - r * .6) ** 2 + (yy - r * .55) ** 2) / r, .35, 1.2)
    col = np.where((rr > .86)[..., None], np.array(rim, np.float32) * light[..., None] * 1.05, np.array(face, np.float32) * light[..., None])
    col = np.clip(col + np.exp(-((rr - .9) / .03) ** 2)[..., None] * 60, 0, 255)
    mask = Image.fromarray((np.clip((1 - rr) * r * .9, 0, 1) * 255).astype(np.uint8), "L")
    L.paste(Image.fromarray(col.astype(np.uint8), "RGB").convert("RGBA"), (int(cx - r), int(cy - r)), mask)
    f = font(F_BLACK, r * 1.15)
    dr = ImageDraw.Draw(L)
    dr.text((cx + r * .03, cy + r * .05), glyph, font=f, fill=tuple(int(v * .45) for v in face) + (255,), anchor="mm")
    dr.text((cx - r * .02, cy), glyph, font=f, fill=gcol, anchor="mm")


def obj_forex(seed, glyph):
    L = blank()
    if glyph == "₿":
        _coin(L, 1190 * S2, 430 * S2, 230 * S2, (247, 160, 40), (196, 112, 16), "₿", (255, 248, 230, 255))
    else:
        back = "$" if glyph == "₹" else "₹"
        _coin(L, 1340 * S2, 340 * S2, 165 * S2, (52, 168, 104), (24, 110, 64), back, (236, 255, 244, 255))
        _coin(L, 1120 * S2, 480 * S2, 215 * S2, (232, 178, 64), (176, 120, 22), glyph, (255, 250, 230, 255))
    return finish(L, 712, 640)


def obj_globe(seed, acc):
    L = blank()
    cx, cy, r = 1190 * S2, 430 * S2, 270 * S2
    yy, xx = np.mgrid[0:2 * r, 0:2 * r].astype(np.float32)
    rr = np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / r
    lam = np.clip(1.15 - np.sqrt((xx - r * .62) ** 2 + (yy - r * .55) ** 2) / r, .1, 1)
    col = np.array([12, 40, 90], np.float32) * lam[..., None] + np.array(acc, np.float32) * np.exp(-((rr - .98) / .05) ** 2)[..., None] * .9
    mask = Image.fromarray((np.clip((1 - rr) * r * .6, 0, 1) * 255).astype(np.uint8), "L")
    L.paste(Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), "RGB").convert("RGBA"), (int(cx - r), int(cy - r)), mask)
    grid = Image.new("RGBA", L.size, (0, 0, 0, 0)); g = ImageDraw.Draw(grid)
    for k in range(1, 6):
        w = r * math.cos(math.radians(k * 15 + seed % 10))
        g.ellipse([cx - w, cy - r, cx + w, cy + r], outline=tuple(acc) + (70,), width=2 * S2)
    for k in range(-3, 4):
        y = cy + r * math.sin(math.radians(k * 25)); hw = r * math.cos(math.radians(k * 25))
        g.ellipse([cx - hw, y - hw * .12, cx + hw, y + hw * .12], outline=tuple(acc) + (55,), width=2 * S2)
    L.alpha_composite(grid)
    rng = np.random.default_rng(seed)
    nodes = [(cx + r * .7 * math.cos(a), cy + r * .6 * math.sin(a)) for a in rng.uniform(0, 2 * math.pi, 6)]
    arcs = Image.new("RGBA", L.size, (0, 0, 0, 0)); a_ = ImageDraw.Draw(arcs)
    for (x1, y1), (x2, y2) in zip(nodes, nodes[1:]):
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - r * .35
        a_.line([((1 - t) ** 2 * x1 + 2 * (1 - t) * t * mx + t * t * x2, (1 - t) ** 2 * y1 + 2 * (1 - t) * t * my + t * t * y2) for t in np.linspace(0, 1, 30)],
                fill=(255, 255, 255, 170), width=2 * S2)
    for x, y in nodes:
        a_.ellipse([x - 8 * S2, y - 8 * S2, x + 8 * S2, y + 8 * S2], fill=tuple(acc) + (255,))
    L.alpha_composite(arcs.filter(ImageFilter.GaussianBlur(4 * S2))); L.alpha_composite(arcs)
    halo = Image.new("RGBA", L.size, (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse([cx - r * 1.08, cy - r * 1.08, cx + r * 1.08, cy + r * 1.08], outline=tuple(acc) + (120,), width=10 * S2)
    L.alpha_composite(halo.filter(ImageFilter.GaussianBlur(14 * S2)))
    return finish(L, 740, 520, reflect=False)


def obj_yield(seed, d, acc):
    L = blank()
    x0, y0, x1, y1 = 850 * S2, 200 * S2, 1520 * S2, 690 * S2
    panel = Image.new("RGBA", L.size, (0, 0, 0, 0)); pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle([x0, y0, x1, y1], radius=26 * S2, fill=(255, 255, 255, 18), outline=(255, 255, 255, 60), width=2 * S2)
    for k in range(1, 6):
        y = y0 + (y1 - y0) * k / 6
        pd.line([(x0 + 30 * S2, y), (x1 - 30 * S2, y)], fill=(255, 255, 255, 26), width=S2)
    L.alpha_composite(panel)
    rng = np.random.default_rng(seed)
    n = 9
    xs = np.linspace(x0 + 60 * S2, x1 - 60 * S2, n)
    base = 1 - np.exp(-np.linspace(0, 2.6, n)) + rng.normal(0, .03, n)
    if d == "down": base = base[::-1] * .9
    ys = y1 - 60 * S2 - base / base.max() * (y1 - y0 - 140 * S2)
    pts = list(zip(xs, ys))
    area = Image.new("RGBA", L.size, (0, 0, 0, 0))
    ImageDraw.Draw(area).polygon(pts + [(xs[-1], y1 - 40 * S2), (xs[0], y1 - 40 * S2)], fill=tuple(acc) + (40,))
    L.alpha_composite(area)
    glow_line(L, pts, acc, 8 * S2, 10 * S2)
    dr = ImageDraw.Draw(L)
    dr.line(pts, fill=(255, 255, 255, 240), width=4 * S2, joint="curve")
    for x, y in pts:
        dr.ellipse([x - 7 * S2, y - 7 * S2, x + 7 * S2, y + 7 * S2], fill=tuple(acc) + (255,), outline=(255, 255, 255, 255), width=2 * S2)
    return finish(L, 712, 680, reflect=False)


def obj_chip(seed, acc):
    L = blank(); dr = ImageDraw.Draw(L)
    cx, cy, r = 1190 * S2, 430 * S2, 200 * S2
    for i in range(-4, 5):
        o = i * r * .2
        for a, b in (((cx + o, cy - r), (cx + o, cy - r - 46 * S2)), ((cx + o, cy + r), (cx + o, cy + r + 46 * S2)),
                     ((cx - r, cy + o), (cx - r - 46 * S2, cy + o)), ((cx + r, cy + o), (cx + r + 46 * S2, cy + o))):
            dr.line([a, b], fill=(196, 170, 110, 255), width=9 * S2)
    paste_poly(L, [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)], vgrad(2 * r, 2 * r, (62, 70, 88), (20, 24, 34)))
    ir = r * .62
    paste_poly(L, [(cx - ir, cy - ir), (cx + ir, cy - ir), (cx + ir, cy + ir), (cx - ir, cy + ir)], vgrad(2 * ir, 2 * ir, (150, 160, 180), (70, 78, 96)))
    tr = Image.new("RGBA", L.size, (0, 0, 0, 0)); t = ImageDraw.Draw(tr)
    rng = np.random.default_rng(seed)
    for _ in range(14):
        x, y = cx + rng.uniform(-ir, ir) * .9, cy + rng.uniform(-ir, ir) * .9
        x2 = x + rng.choice([-1, 1]) * rng.uniform(30, 110) * S2
        t.line([(x, y), (x2, y), (x2, y + rng.choice([-1, 1]) * rng.uniform(20, 70) * S2)], fill=tuple(acc) + (255,), width=3 * S2)
    t.rectangle([cx - ir * .35, cy - ir * .35, cx + ir * .35, cy + ir * .35], outline=tuple(acc) + (255,), width=4 * S2)
    L.alpha_composite(tr.filter(ImageFilter.GaussianBlur(6 * S2))); L.alpha_composite(tr)
    return finish(L, 712, 560)


def obj_bank(seed, acc):
    L = blank(); dr = ImageDraw.Draw(L)
    cx, w = 1250 * S2, 540 * S2
    dr.polygon([(cx - w / 2 - 20 * S2, 300 * S2), (cx, 170 * S2), (cx + w / 2 + 20 * S2, 300 * S2)], fill=(214, 206, 188, 255))
    dr.polygon([(cx - w / 2 + 40 * S2, 290 * S2), (cx, 200 * S2), (cx + w / 2 - 40 * S2, 290 * S2)], fill=(150, 142, 126, 255))
    paste_poly(L, [(cx - w / 2, 300 * S2), (cx + w / 2, 300 * S2), (cx + w / 2, 340 * S2), (cx - w / 2, 340 * S2)], vgrad(w, 40 * S2, (236, 230, 214), (170, 162, 146)))
    for i in range(6):
        x = cx - w / 2 + 50 * S2 + i * (w - 100 * S2) / 5
        paste_poly(L, [(x - 27 * S2, 350 * S2), (x + 27 * S2, 350 * S2), (x + 27 * S2, 630 * S2), (x - 27 * S2, 630 * S2)], shade_strip(54 * S2, 280 * S2, rgb("#D9D4C7"), spec=.35))
    for dw, y in ((0, 632), (40, 660), (80, 688)):
        paste_poly(L, [(cx - w / 2 - dw * S2, y * S2), (cx + w / 2 + dw * S2, y * S2), (cx + w / 2 + dw * S2, (y + 26) * S2), (cx - w / 2 - dw * S2, (y + 26) * S2)],
                   vgrad(w + 2 * dw * S2, 26 * S2, (226, 220, 204), (150, 142, 126)))
    glow_line(L, [(cx - w / 2, 300 * S2), (cx + w / 2, 300 * S2)], acc, 6 * S2, 5 * S2)
    ImageDraw.Draw(L).line([(cx - w / 2, 300 * S2), (cx + w / 2, 300 * S2)], fill=tuple(acc) + (255,), width=4 * S2)
    return finish(L, 716, 820)


def obj_growth(seed, acc):
    L = blank()
    rng = np.random.default_rng(seed)
    hs = np.sort(rng.uniform(.25, .9, 5)); hs[-1] = 1
    x0, base, bw, gap, dpt = 900 * S2, 700 * S2, 92 * S2, 34 * S2, 28 * S2
    tops = []
    for i, hfr in enumerate(hs):
        x = x0 + i * (bw + gap); h = hfr * 430 * S2
        paste_poly(L, [(x, base - h), (x + bw, base - h), (x + bw, base), (x, base)], vgrad(bw, h, (96, 165, 250), (37, 70, 170)))
        paste_poly(L, [(x, base - h), (x + bw, base - h), (x + bw + dpt, base - h - dpt * .6), (x + dpt, base - h - dpt * .6)], vgrad(bw + dpt, dpt * .6 + 1, (200, 225, 255), (140, 180, 250)))
        paste_poly(L, [(x + bw, base - h), (x + bw + dpt, base - h - dpt * .6), (x + bw + dpt, base - dpt * .6), (x + bw, base)], vgrad(dpt + 1, h, (60, 100, 200), (20, 40, 110)))
        tops.append((x + bw / 2, base - h - 46 * S2))
    glow_line(L, tops, acc, 7 * S2, 8 * S2)
    a = ImageDraw.Draw(L)
    a.line(tops, fill=(255, 255, 255, 235), width=4 * S2, joint="curve")
    (px, py), (ex, ey) = tops[-2], tops[-1]
    ang = math.atan2(ey - py, ex - px)
    a.polygon([(ex + 30 * S2 * math.cos(ang), ey + 30 * S2 * math.sin(ang)),
               (ex + 22 * S2 * math.cos(ang + 2.4), ey + 22 * S2 * math.sin(ang + 2.4)),
               (ex + 22 * S2 * math.cos(ang - 2.4), ey + 22 * S2 * math.sin(ang - 2.4))], fill=(255, 255, 255, 255))
    return finish(L, 712, 700)


def obj_diya(seed, acc):
    L = blank()
    cx, cy = 1170 * S2, 580 * S2
    b = ImageDraw.Draw(L)
    b.chord([cx - 260 * S2, cy - 170 * S2, cx + 260 * S2, cy + 150 * S2], 0, 180, fill=(170, 74, 22, 255))
    b.polygon([(cx + 200 * S2, cy - 10 * S2), (cx + 330 * S2, cy - 70 * S2), (cx + 250 * S2, cy + 40 * S2)], fill=(150, 64, 18, 255))
    b.ellipse([cx - 260 * S2, cy - 46 * S2, cx + 260 * S2, cy + 30 * S2], fill=(214, 120, 40, 255))
    b.ellipse([cx - 220 * S2, cy - 34 * S2, cx + 220 * S2, cy + 18 * S2], fill=(120, 54, 14, 255))
    for k in range(5):
        an = math.radians(30 + k * 30)
        x, y = cx + math.cos(an) * 200 * S2, cy + 40 * S2 + math.sin(an) * 70 * S2
        b.ellipse([x - 9 * S2, y - 9 * S2, x + 9 * S2, y + 9 * S2], fill=tuple(acc) + (255,))
    fx, fy = cx + 300 * S2, cy - 90 * S2
    fl = Image.new("RGBA", L.size, (0, 0, 0, 0))
    ImageDraw.Draw(fl).ellipse([fx - 170 * S2, fy - 260 * S2, fx + 170 * S2, fy + 60 * S2], fill=tuple(acc) + (110,))
    L.alpha_composite(fl.filter(ImageFilter.GaussianBlur(50 * S2)))
    core = Image.new("RGBA", L.size, (0, 0, 0, 0)); c = ImageDraw.Draw(core)
    c.polygon([(fx, fy - 170 * S2), (fx - 44 * S2, fy - 30 * S2), (fx, fy + 10 * S2), (fx + 44 * S2, fy - 30 * S2)], fill=(255, 176, 40, 255))
    c.polygon([(fx, fy - 110 * S2), (fx - 20 * S2, fy - 26 * S2), (fx, fy), (fx + 20 * S2, fy - 26 * S2)], fill=(255, 246, 210, 255))
    L.alpha_composite(core.filter(ImageFilter.GaussianBlur(2 * S2)))
    return finish(L, 712, 640)


def obj_shield(seed, acc):
    L = blank()
    cx, top, r = 1190 * S2, 160 * S2, 250 * S2
    pts = [(cx, top), (cx + r, top + 70 * S2), (cx + r * .92, top + 330 * S2), (cx, top + 560 * S2), (cx - r * .92, top + 330 * S2), (cx - r, top + 70 * S2)]
    paste_poly(L, pts, vgrad(2 * r, 560 * S2, (58, 70, 96), (14, 18, 30)))
    inner = [(x * .78 + cx * .22, y * .8 + (top + 230 * S2) * .2) for x, y in pts]
    rim = Image.new("RGBA", L.size, (0, 0, 0, 0))
    ImageDraw.Draw(rim).polygon(inner, outline=tuple(acc) + (255,), width=8 * S2)
    L.alpha_composite(rim.filter(ImageFilter.GaussianBlur(10 * S2))); L.alpha_composite(rim)
    dr = ImageDraw.Draw(L)
    ly = top + 250 * S2
    dr.rounded_rectangle([cx - 80 * S2, ly, cx + 80 * S2, ly + 120 * S2], radius=14 * S2, fill=(235, 240, 248, 255))
    dr.arc([cx - 58 * S2, ly - 90 * S2, cx + 58 * S2, ly + 40 * S2], 180, 360, fill=(235, 240, 248, 255), width=20 * S2)
    dr.ellipse([cx - 16 * S2, ly + 36 * S2, cx + 16 * S2, ly + 68 * S2], fill=(20, 26, 40, 255))
    dr.rectangle([cx - 6 * S2, ly + 60 * S2, cx + 6 * S2, ly + 92 * S2], fill=(20, 26, 40, 255))
    return finish(L, 735, 520, reflect=False)


def obj_servers(seed, acc):
    L = blank(); dr = ImageDraw.Draw(L)
    rng = np.random.default_rng(seed)
    for k, (x, h) in enumerate(((930, 470), (1110, 520), (1290, 470))):
        x *= S2; w = 160 * S2; top = (700 - h) * S2; bot = 700 * S2
        paste_poly(L, [(x, top), (x + w, top), (x + w, bot), (x, bot)], vgrad(w, bot - top, (46, 54, 72), (16, 20, 30)))
        for u in range(int(h / 46)):
            y = top + 18 * S2 + u * 46 * S2
            dr.rounded_rectangle([x + 14 * S2, y, x + w - 14 * S2, y + 32 * S2], radius=4 * S2, fill=(28, 34, 48, 255), outline=(70, 80, 100, 255), width=S2)
            for j in range(3):
                on = rng.random() > .3
                dr.ellipse([x + 26 * S2 + j * 18 * S2, y + 11 * S2, x + 36 * S2 + j * 18 * S2, y + 21 * S2], fill=(tuple(acc) + (255,)) if on else (60, 66, 80, 255))
            dr.line([(x + 90 * S2, y + 16 * S2), (x + w - 26 * S2, y + 16 * S2)], fill=(80, 92, 116, 255), width=2 * S2)
    gl = Image.new("RGBA", L.size, (0, 0, 0, 0))
    ImageDraw.Draw(gl).rectangle([900 * S2, 690 * S2, 1480 * S2, 700 * S2], fill=tuple(acc) + (200,))
    L.alpha_composite(gl.filter(ImageFilter.GaussianBlur(14 * S2)))
    return finish(L, 712, 640)


def obj_neural(seed, acc):
    L = blank()
    rng = np.random.default_rng(seed)
    layers = [3, 5, 5, 3]
    xs = [920, 1080, 1260, 1420]
    nodes = []
    for x, n in zip(xs, layers):
        ys = np.linspace(430 - (n - 1) * 62, 430 + (n - 1) * 62, n)
        nodes.append([(x * S2, y * S2) for y in ys])
    ln = Image.new("RGBA", L.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ln)
    for a, b in zip(nodes, nodes[1:]):
        for p1 in a:
            for p2 in b:
                d.line([p1, p2], fill=tuple(acc) + (int(rng.uniform(40, 150)),), width=2 * S2)
    L.alpha_composite(ln)
    nd = Image.new("RGBA", L.size, (0, 0, 0, 0)); d = ImageDraw.Draw(nd)
    for layer in nodes:
        for x, y in layer:
            d.ellipse([x - 22 * S2, y - 22 * S2, x + 22 * S2, y + 22 * S2], fill=(14, 22, 44, 255), outline=tuple(acc) + (255,), width=5 * S2)
            d.ellipse([x - 8 * S2, y - 8 * S2, x + 8 * S2, y + 8 * S2], fill=(255, 255, 255, 255))
    L.alpha_composite(nd.filter(ImageFilter.GaussianBlur(8 * S2))); L.alpha_composite(nd)
    return finish(L, 740, 600, reflect=False)


def obj_coins(seed, acc):
    L = blank()
    rng = np.random.default_rng(seed)
    face, rimc = (232, 178, 64), (176, 120, 22)
    for k, n in enumerate((3, 5, 7, 10)):
        x = (930 + k * 150) * S2
        for j in range(n):
            y = 700 * S2 - j * 34 * S2
            dr = ImageDraw.Draw(L)
            dr.ellipse([x - 62 * S2, y - 20 * S2, x + 62 * S2, y + 20 * S2], fill=rimc + (255,))
            paste_poly(L, [(x - 62 * S2, y - 30 * S2), (x + 62 * S2, y - 30 * S2), (x + 62 * S2, y), (x - 62 * S2, y)], shade_strip(124 * S2, 30 * S2, np.array(face, np.float32), spec=.5))
            dr = ImageDraw.Draw(L)
            dr.ellipse([x - 62 * S2, y - 50 * S2, x + 62 * S2, y - 10 * S2], fill=(250, 210, 110, 255), outline=rimc + (255,), width=2 * S2)
    pts = [((930 + k * 150) * S2, (700 - n * 34 - 70) * S2) for k, n in enumerate((3, 5, 7, 10))]
    glow_line(L, pts, acc, 7 * S2, 8 * S2)
    a = ImageDraw.Draw(L)
    a.line(pts, fill=(255, 255, 255, 235), width=4 * S2, joint="curve")
    (px, py), (ex, ey) = pts[-2], pts[-1]
    ang = math.atan2(ey - py, ex - px)
    a.polygon([(ex + 30 * S2 * math.cos(ang), ey + 30 * S2 * math.sin(ang)), (ex + 22 * S2 * math.cos(ang + 2.4), ey + 22 * S2 * math.sin(ang + 2.4)),
               (ex + 22 * S2 * math.cos(ang - 2.4), ey + 22 * S2 * math.sin(ang - 2.4))], fill=(255, 255, 255, 255))
    return finish(L, 712, 700)


OBJECTS = {"candles": lambda s, d, a, g: obj_candles(s, d, a), "gold": lambda s, d, a, g: obj_bullion(s, "gold"),
           "silver": lambda s, d, a, g: obj_bullion(s, "silver"), "oil": lambda s, d, a, g: obj_oil(s, a),
           "forex": lambda s, d, a, g: obj_forex(s, g), "bitcoin": lambda s, d, a, g: obj_forex(s, "₿"),
           "globe": lambda s, d, a, g: obj_globe(s, a), "yield": lambda s, d, a, g: obj_yield(s, d, a),
           "chip": lambda s, d, a, g: obj_chip(s, a), "bank": lambda s, d, a, g: obj_bank(s, a),
           "growth": lambda s, d, a, g: obj_growth(s, a), "diya": lambda s, d, a, g: obj_diya(s, a),
           "shield": lambda s, d, a, g: obj_shield(s, a), "servers": lambda s, d, a, g: obj_servers(s, a),
           "neural": lambda s, d, a, g: obj_neural(s, a), "coins": lambda s, d, a, g: obj_coins(s, a)}


# ------------------------------------------------------------------ typography
def headline_text(p):
    h = (p.get("coverHeadline") or "").strip()
    if h:
        return h.upper()
    t = re.split(r"[;:,]| as | after | amid ", p.get("title", ""), maxsplit=1)[0]
    return " ".join(t.split()[:6]).upper()


def key_words(words, stat):
    st = [t.strip(".,~") for t in str(stat or "").upper().replace("−", "-").split()]
    hits = {i for i, w in enumerate(words) if st and any(x in st for x in w.strip(".,~").replace("−", "-").split("\u00a0"))}
    if not hits:
        hits = {next((i for i, w in enumerate(words) if re.search(r"\d", w)), -1)}
    return hits


def layout_headline(dr, text, max_w, max_lines=3):
    words = text.split(" ")
    for size in range(150, 70, -4):
        f = font(F_BLACK, size)
        lines, cur = [], []
        for w in words:
            if not cur or dr.textlength(" ".join(cur + [w]), font=f) <= max_w:
                cur.append(w)
            else:
                lines.append(cur); cur = [w]
        if cur: lines.append(cur)
        if len(lines) <= max_lines and all(dr.textlength(" ".join(l), font=f) <= max_w for l in lines):
            return f, lines, size
    return font(F_BLACK, 70), [words], 70


_CTX = {}


def _ctx():
    if not _CTX:
        def load(name, default):
            try:
                return json.load(open(os.path.join(HERE, "data", name), encoding="utf-8"))
            except Exception:
                return default
        _CTX["meta"] = load("meta.json", {})
        _CTX["ipos"] = load("ipos.json", {}).get("ipos", [])
    return _CTX


def analysis(p):
    """Story analysis (event, verified figures, template) from graphics_selector; cached per story."""
    if "_analysis" not in p:
        import graphics_selector
        c = _ctx()
        p["_analysis"] = graphics_selector.analyze(p, c["meta"], c["ipos"])
    return p["_analysis"]


def market_art_new(p):
    import market_art
    return market_art._new_enough(p)


def render(p, path_webp, path_jpg):
    import art
    a = analysis(p)
    if a["template"] != "illustration":
        import cover_templates, cover_templates_v2
        if a["template"] in cover_templates_v2.TEMPLATES:
            return cover_templates_v2.TEMPLATES[a["template"]](p, a, path_webp, path_jpg)
        return cover_templates.TEMPLATES[a["template"]](p, a, path_webp, path_jpg)
    seed = seed_of(p)
    obj, theme, d, glyph = pick(p)
    _, _, _, label = THEMES[theme]
    if p.get("coverLabel"):
        label = str(p["coverLabel"]).upper()
    base, acc = background(theme, seed, d)
    import market_art
    art_id = market_art.choice(p, d) if obj == "candles" else None
    if art_id:  # owner-approved bull / bear artwork instead of generic candles (new stories only)
        base.alpha_composite(market_art.layer(art_id, W, H))
    else:
        base.alpha_composite(OBJECTS.get(obj, OBJECTS["candles"])(seed, d, acc, glyph))
    scrim = np.zeros((H, W, 4), np.uint8)
    scrim[..., 3] = (np.clip((np.linspace(1, 0, W) - .35) / .65, 0, 1) ** 1.4 * 170).astype(np.uint8)[None, :]
    base.alpha_composite(Image.fromarray(scrim, "RGBA"))
    dr = ImageDraw.Draw(base)
    M = 84
    dr.rectangle([M, 92, M + 10, 128], fill=acc + (255,))
    kf = font(F_SEMI, 30)
    dr.text((M + 28, 110), label, font=kf, fill=(255, 255, 255, 235), anchor="lm")
    kx = M + 28 + dr.textlength(label, font=kf) + 22
    flags, _, comps = art.detect(p)
    if flags:
        dr.line([(kx, 96), (kx, 124)], fill=(255, 255, 255, 70), width=2)
        x = kx + 18
        for code in flags[:3]:
            fb = art.flag_badge(code, 40)
            if fb is not None:
                base.alpha_composite(fb, (int(x), 88)); x += fb.width + 6
    text = headline_text(p)
    stat = str(p.get("stat") or "")
    su = stat.upper().strip()
    if su and " " in su and su in text:
        text = text.replace(su, su.replace(" ", "\u00a0"))
    f, lines, size = layout_headline(dr, text, 700)
    flat = [w for l in lines for w in l]
    hot = key_words(flat, stat)
    lh = int(size * 1.02)
    y = max(190, 455 - lh * len(lines) // 2)
    k = 0
    for line in lines:
        x = M
        for w in line:
            dr.text((x, y), w, font=f, fill=(acc + (255,)) if k in hot else (255, 255, 255, 255))
            x += dr.textlength(w + " ", font=f); k += 1
        y += lh
    y += 22
    dr.rectangle([M, y, M + 120, y + 6], fill=acc + (255,))
    ctx = str(p.get("coverContext") or p.get("statLabel") or "").strip()
    try:
        from datetime import datetime
        ds = (p.get("report") or {}).get("date") or p.get("coverDate") or p.get("publishedAt")
        import tmdate
        date_s = tmdate.fmt(ds, "%-d %b %Y").upper()
    except Exception:
        date_s = ""
    line2 = " · ".join(s for s in (ctx, date_s) if s)
    if line2:
        cf = font(F_MED, 32)
        while dr.textlength(line2, font=cf) > 720 and cf.size > 22:
            cf = font(F_MED, cf.size - 2)
        dr.text((M, y + 28), line2, font=cf, fill=(214, 220, 230, 230))
    bx = M
    for t in comps[:3]:
        bd = art.company_badge(t, 44)
        base.alpha_composite(bd, (bx, H - 96)); bx += bd.width + 10
    if art_id:
        market_art.brand_backing(base, W, H)
    dr = ImageDraw.Draw(base)
    bf = font(F_XB, 34)
    bwid = dr.textlength("TotalMarket", font=bf)
    new_story = market_art_new(p)
    bx, by = W - 70 - bwid, H - (104 if new_story else 82)
    dr.rectangle([bx - 26, by + 6, bx - 14, by + 34], fill=acc + (255,))
    dr.text((bx, by), "Total", font=bf, fill=(255, 255, 255, 255))
    dr.text((bx + dr.textlength("Total", font=bf), by), "Market", font=bf, fill=acc + (255,))
    if new_story:
        import market_art
        market_art.cta(dr, W, H, font(F_SEMI, 21), y_off=54)
    out = grain(base, seed)
    out.save(path_webp, "WEBP", quality=78, method=6)
    out.resize((1200, 675), Image.LANCZOS).save(path_jpg, "JPEG", quality=82, optimize=True, progressive=True)


def cover_name(p):
    import art
    ld = os.path.join(HERE, "logos")
    logos = sorted(f for f in os.listdir(ld) if not f.endswith(".md")) if os.path.isdir(ld) else []
    key = [VERSION, p["id"], p.get("title"), p.get("coverHeadline"), p["category"], p.get("stat"), p.get("statLabel"), p.get("symbol"),
           p.get("palette"), p.get("coverLabel"), p.get("publishedAt"), art.detect(p), logos]
    an = analysis(p)
    key += [an["template"], an["object"], an["figures"], an["series"]]
    import market_art
    art_id = market_art.choice(p, direction(p))
    if art_id:  # only stories from market_art.ART_FROM: older cover names never change
        key.append("art:" + art_id)
    if an["template"] != "illustration":  # re-render data covers whenever their template code changes
        mod = "cover_templates_v2.py" if an.get("chart") else "cover_templates.py"
        key.append(hashlib.md5(open(os.path.join(HERE, mod), "rb").read()).hexdigest()[:8])
        if an.get("chart"):
            key.append(an["chart"])
    if p.get("coverDate") or p.get("coverContext"):
        key += [p.get("coverDate"), p.get("coverContext")]
    return f"{p['id']}-{hashlib.md5(json.dumps(key, ensure_ascii=False, default=str).encode()).hexdigest()[:8]}"


def ensure_covers(posts, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    keep = set()
    for p in posts:
        stem = cover_name(p)
        wp, jp = stem + ".webp", stem + ".jpg"
        keep.update((wp, jp))
        sm = stem + "-800.webp"
        keep.add(sm)
        if not (os.path.exists(os.path.join(out_dir, wp)) and os.path.exists(os.path.join(out_dir, jp))):
            render(p, os.path.join(out_dir, wp), os.path.join(out_dir, jp))
        if not os.path.exists(os.path.join(out_dir, sm)):  # responsive derivative for cards and phones
            Image.open(os.path.join(out_dir, wp)).convert("RGB").resize((800, 450), Image.LANCZOS).save(os.path.join(out_dir, sm), "WEBP", quality=80, method=6)
        p["_cover"], p["_cover_og"] = wp, jp
    for f in os.listdir(out_dir):
        if f.endswith((".png", ".jpg", ".webp")) and f not in keep:
            os.remove(os.path.join(out_dir, f))
