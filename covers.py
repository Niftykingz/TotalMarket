"""Draw a 1200x630 cover image for each story (used on the site and as the share preview)."""
import hashlib, json, math, os, re
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import art

VERSION = "6"
W, H = 1200, 630
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = lambda name, size: ImageFont.truetype(os.path.join(HERE, "fonts", name), size)

PAL = {  # bg start, bg end, accent
    "markets":  ("#062A20", "#0B6E4F", "#7CF5C8"),
    "tech":     ("#0E1647", "#2B4BD8", "#A9BBFF"),
    "startups": ("#22103F", "#7A4CC2", "#E6D2FF"),
    "policy":   ("#3D1904", "#C25E14", "#FFD7AE"),
    "global":   ("#042629", "#0E7C86", "#93F2F7"),
    "commodities": ("#2B1D02", "#A87708", "#FFE28A"),
    "down":     ("#33060F", "#B42D41", "#FFC0CA"),
}
LABEL = {"markets": "MARKETS", "tech": "TECH & AI", "startups": "STARTUPS & IPOs", "policy": "POLICY & ECONOMY", "global": "GLOBAL MARKETS", "commodities": "COMMODITIES & FOREX"}
DOWN_WORDS = re.compile(r"\b(drops?|falls?|fell|slides?|slips?|plunges?|crash(es)?|tumbles?|sinks?|down|loses?|sheds?)\b", re.I)
STAT_RES = [
    re.compile(r"[₹$]\s?\d[\d,.]*(?:\s?[–-]\s?[\d,.]+)?(?:\s?(?:lakh crore|crore|cr|billion|bn|million|trillion|[MBK]\b))?", re.I),
    re.compile(r"[+-]?\d[\d,.]*\s?%"),
    re.compile(r"\d[\d,]*(?:\.\d+)?\s?(?:points|pts)\b", re.I),
    re.compile(r"\d[\d,]*\+?\s?(?:crore|billion|million)\b", re.I),
]


def hexrgb(h, a=255):
    h = h.lstrip("#"); return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def pick_stat(p):
    if p.get("stat"):
        return str(p["stat"]), str(p.get("statLabel") or "")
    for rx in STAT_RES:
        m = rx.search(p.get("title", ""))
        if m:
            return m.group(0).strip(), str(p.get("statLabel") or "")
    return "", ""


def is_down(p, stat):
    return stat.startswith("-") or bool(DOWN_WORDS.search(p.get("title", "")))


def fit(draw, text, font_name, max_w, start, min_size):
    size = start
    while size > min_size:
        f = FONT(font_name, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return FONT(font_name, min_size)


def wrap(draw, text, font, max_w, max_lines):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            lines.append(cur); cur = w
            if len(lines) == max_lines:
                break
    if len(lines) < max_lines and cur:
        lines.append(cur)
    if len(lines) == max_lines and " ".join(lines) != text:
        last = lines[-1]
        while draw.textlength(last + "…", font=font) > max_w and " " in last:
            last = last.rsplit(" ", 1)[0]
        lines[-1] = last + "…"
    return lines


def glyph(d, cat, cx, cy, s, col):
    """Big line-art icon for the section."""
    lw = max(6, int(s * 0.035))
    if cat in ("markets", "down"):
        xs = [cx - s * .42 + i * s * .17 for i in range(6)]
        hs = [.30, .45, .35, .60, .50, .75]
        for i, x in enumerate(xs):
            top = cy + s * .35 - s * hs[i]; bot = top + s * .28
            d.line([(x, top - s * .08), (x, bot + s * .08)], fill=col, width=lw // 2)
            d.rectangle([x - s * .05, top, x + s * .05, bot], outline=col, width=lw)
    elif cat == "tech":
        r = s * .32
        d.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], radius=s * .06, outline=col, width=lw)
        d.rounded_rectangle([cx - r * .45, cy - r * .45, cx + r * .45, cy + r * .45], radius=s * .03, outline=col, width=lw)
        for i in range(-2, 3):
            o = i * r * .38
            for a, b in (((cx + o, cy - r), (cx + o, cy - r - s * .12)), ((cx + o, cy + r), (cx + o, cy + r + s * .12)),
                         ((cx - r, cy + o), (cx - r - s * .12, cy + o)), ((cx + r, cy + o), (cx + r + s * .12, cy + o))):
                d.line([a, b], fill=col, width=lw)
    elif cat == "startups":
        # rocket
        body = [(cx, cy - s * .48), (cx + s * .14, cy - s * .22), (cx + s * .14, cy + s * .2), (cx - s * .14, cy + s * .2), (cx - s * .14, cy - s * .22)]
        d.polygon(body, outline=col, width=lw)
        d.ellipse([cx - s * .06, cy - s * .2, cx + s * .06, cy - s * .08], outline=col, width=lw)
        d.polygon([(cx - s * .14, cy), (cx - s * .28, cy + s * .26), (cx - s * .14, cy + s * .2)], outline=col, width=lw)
        d.polygon([(cx + s * .14, cy), (cx + s * .28, cy + s * .26), (cx + s * .14, cy + s * .2)], outline=col, width=lw)
        for dx, ln in ((-.07, .2), (0, .3), (.07, .2)):
            d.line([(cx + s * dx, cy + s * .26), (cx + s * dx, cy + s * (.26 + ln))], fill=col, width=lw)
    elif cat == "policy":
        w = s * .42
        d.polygon([(cx - w - s * .04, cy - s * .18), (cx, cy - s * .42), (cx + w + s * .04, cy - s * .18)], outline=col, width=lw)
        d.line([(cx - w, cy - s * .12), (cx + w, cy - s * .12)], fill=col, width=lw)
        for i in range(5):
            x = cx - w * .8 + i * w * .4
            d.line([(x, cy - s * .08), (x, cy + s * .28)], fill=col, width=lw * 2)
        d.line([(cx - w - s * .06, cy + s * .34), (cx + w + s * .06, cy + s * .34)], fill=col, width=lw)
        d.line([(cx - w - s * .1, cy + s * .42), (cx + w + s * .1, cy + s * .42)], fill=col, width=lw)
    elif cat == "commodities":
        bw, bh = s * .3, s * .14
        def bar(x, y):
            d.polygon([(x - bw / 2, y + bh / 2), (x - bw / 2 + s * .05, y - bh / 2), (x + bw / 2 - s * .05, y - bh / 2), (x + bw / 2, y + bh / 2)], outline=col, width=lw)
        base_y = cy + s * .3
        for dx in (-.32, 0, .32):
            bar(cx + s * dx, base_y)
        for dx in (-.16, .16):
            bar(cx + s * dx, base_y - bh * 1.1)
        bar(cx, base_y - bh * 2.2)
        r = s * .16
        ox, oy = cx + s * .16, cy - s * .24
        d.ellipse([ox, oy, ox + 2 * r, oy + 2 * r], outline=col, width=lw)
        f = FONT("DejaVuSans-Bold.ttf", int(r * 1.1))
        d.text((ox + r, oy + r), "₹", font=f, fill=col, anchor="mm")
    elif cat == "global":
        r = s * .42
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=lw)
        for k in (.35, .7):
            d.ellipse([cx - r * k, cy - r, cx + r * k, cy + r], outline=col, width=lw // 2 + 1)
        d.line([(cx - r, cy), (cx + r, cy)], fill=col, width=lw // 2 + 1)
        for k in (-.55, .55):
            hw = r * math.sqrt(1 - k * k)
            d.line([(cx - hw, cy + r * k), (cx + hw, cy + r * k)], fill=col, width=lw // 2 + 1)


def render(p, path):
    cat = p["category"]
    stat, stat_label = pick_stat(p)
    down = cat in ("markets", "global", "commodities") and is_down(p, stat)
    a, b, acc = PAL["down" if down else cat]
    A, B, ACC = hexrgb(a), hexrgb(b), hexrgb(acc)

    # diagonal gradient
    base = Image.new("RGBA", (W, H))
    px = base.load()
    for y in range(H):
        for x in range(0, W, 4):
            t = min(1, max(0, (x * .6 + y * .9) / (W * .6 + H * .9)))
            c = tuple(int(A[i] + (B[i] - A[i]) * t) for i in range(3)) + (255,)
            for k in range(4):
                px[x + k, y] = c
    # glow
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([700, -200, 1400, 500], fill=ACC[:3] + (70,))
    base.alpha_composite(glow.filter(ImageFilter.GaussianBlur(120)))

    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    for x in range(0, W, 60):
        d.line([(x, 0), (x, H)], fill=(255, 255, 255, 14), width=1)
    for y in range(0, H, 60):
        d.line([(0, y), (W, y)], fill=(255, 255, 255, 14), width=1)

    # chart line along the bottom
    seed = int(hashlib.md5(p["id"].encode()).hexdigest()[:8], 16)
    pts, n = [], 14
    for i in range(n + 1):
        trend = (i / n) * 70
        wob = math.sin(i * 1.7 + seed % 7) * 14 + math.sin(i * .9 + seed % 5) * 10
        y = (H - 70 - trend) if not down else (H - 140 + trend)
        pts.append((i * W / n, y - wob))
    d.polygon(pts + [(W, H), (0, H)], fill=ACC[:3] + (34,))
    d.line(pts, fill=ACC[:3] + (210,), width=7, joint="curve")
    ex, ey = pts[-2]
    d.ellipse([ex - 12, ey - 12, ex + 12, ey + 12], fill=ACC[:3] + (255,))

    flags, sym, comps = art.detect(p)
    if not sym and cat == "markets":
        sym = "chart-down" if down else "chart-up"
    hero = art.symbol(sym, 300) if sym else None
    if hero is None:
        glyph(d, "down" if down and cat == "markets" else cat, 960, 300, 380, (255, 255, 255, 60))
    base.alpha_composite(over)
    if hero is not None:
        halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(halo).ellipse([800, 170, 1120, 490], fill=(255, 255, 255, 46))
        base.alpha_composite(halo.filter(ImageFilter.GaussianBlur(18)))
        base.alpha_composite(hero, (810, 180))
    # flags, top right, overlapping
    x = W - 56
    for code in reversed(flags[:3]):
        fb = art.flag_badge(code, 92)
        if fb is not None:
            x -= fb.width - 26 if x != W - 56 else fb.width
            base.alpha_composite(fb, (int(x), 44))
    d = ImageDraw.Draw(base)

    # section pill
    pf = FONT("DejaVuSansMono-Bold.ttf", 26)
    label = LABEL[cat]
    tw = d.textlength(label, font=pf)
    d.rounded_rectangle([64, 60, 64 + tw + 44, 112], radius=26, fill=ACC)
    d.text((86, 70), label, font=pf, fill=A[:3])
    if down or (stat.startswith("+")):
        arrow = "▼" if down else "▲"
        af = FONT("DejaVuSans-Bold.ttf", 30)
        d.text((64 + tw + 64, 70), arrow, font=af, fill=ACC)

    if stat:
        sf = fit(d, stat, "DejaVuSansCondensed-Bold.ttf", 720, 168, 70)
        d.text((60, 150), stat, font=sf, fill=(255, 255, 255))
        sb = d.textbbox((60, 150), stat, font=sf)
        y = sb[3] + 22
        if stat_label:
            lf = fit(d, stat_label, "DejaVuSans-Bold.ttf", 700, 40, 26)
            d.text((64, y), stat_label, font=lf, fill=ACC); y += 60
        hf = FONT("DejaVuSans-Bold.ttf", 34)
        for line in wrap(d, p.get("title", ""), hf, 700, 2):
            d.text((64, y), line, font=hf, fill=(255, 255, 255, 230)); y += 46
    else:
        hf = FONT("DejaVuSansCondensed-Bold.ttf", 72)
        y = 160
        for line in wrap(d, p.get("title", ""), hf, 720, 3):
            d.text((60, y), line, font=hf, fill=(255, 255, 255)); y += 84

    # company ticker badges, bottom left
    bx = 58
    for t in comps:
        bd = art.company_badge(t, 54)
        if bx + bd.width > 760:
            break
        base.alpha_composite(bd, (bx, H - 100))
        bx += bd.width + 10
    d = ImageDraw.Draw(base)
    # wordmark (bottom right)
    wf = FONT("DejaVuSans-Bold.ttf", 30)
    ww = d.textlength("TotalMarket", font=wf)
    d.rounded_rectangle([W - 84 - ww, H - 84, W - 44, H - 34], radius=14, fill=(0, 0, 0, 110))
    d.text((W - 64 - ww, H - 76), "Total", font=wf, fill=(255, 255, 255))
    d.text((W - 64 - ww + d.textlength("Total", font=wf), H - 76), "Market", font=wf, fill=ACC)
    base.convert("RGB").save(path, "JPEG", quality=84, optimize=True, progressive=True)


def cover_name(p):
    stat, lbl = pick_stat(p)
    h = hashlib.md5(json.dumps([VERSION, p["id"], p["title"], p["category"], stat, lbl, art.detect(p)], ensure_ascii=False).encode()).hexdigest()[:8]
    return f"{p['id']}-{h}.jpg"


def ensure_covers(posts, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    keep = set()
    for p in posts:
        name = cover_name(p)
        keep.add(name)
        path = os.path.join(out_dir, name)
        if not os.path.exists(path):
            render(p, path)
        p["_cover"] = name
    for f in os.listdir(out_dir):
        if f.endswith((".png", ".jpg")) and f not in keep:
            os.remove(os.path.join(out_dir, f))
