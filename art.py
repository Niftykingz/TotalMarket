"""Flags, symbols and company ticker badges for story covers, plus entity/tag detection.

Everything here is drawn from simple shapes. No trademarked logos and no likenesses
of real people: companies appear as ticker badges in neutral colours.
"""
import hashlib, math, os, re
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = lambda name, size: ImageFont.truetype(os.path.join(HERE, "fonts", name), size)

# ---------------------------------------------------------------- flags
R, W_, B = (206, 17, 38), (255, 255, 255), (0, 40, 104)


def _stripes_h(d, s, cols):
    h = s / len(cols)
    for i, c in enumerate(cols):
        d.rectangle([0, i * h, s, (i + 1) * h + 1], fill=c)


def _stripes_v(d, s, cols):
    w = s / len(cols)
    for i, c in enumerate(cols):
        d.rectangle([i * w, 0, (i + 1) * w + 1, s], fill=c)


def _star(d, cx, cy, r, fill, rot=-90):
    pts = []
    for i in range(10):
        a = math.radians(rot + i * 36)
        rr = r if i % 2 == 0 else r * .4
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)


def _flag(code, s):
    im = Image.new("RGB", (s, s), (255, 255, 255))
    d = ImageDraw.Draw(im)
    if code == "IN":
        _stripes_h(d, s, [(255, 153, 51), (255, 255, 255), (19, 136, 8)])
        r = s * .13; c = s / 2
        d.ellipse([c - r, c - r, c + r, c + r], outline=(0, 0, 128), width=max(2, s // 40))
        for i in range(24):
            a = math.radians(i * 15)
            d.line([(c, c), (c + r * math.cos(a), c + r * math.sin(a))], fill=(0, 0, 128), width=1)
    elif code == "US":
        for i in range(13):
            d.rectangle([0, i * s / 13, s, (i + 1) * s / 13 + 1], fill=R if i % 2 == 0 else W_)
        d.rectangle([0, 0, s * .5, s * 7 / 13], fill=(60, 59, 110))
        for row in range(5):
            for col in range(6):
                x = s * .05 + col * s * .08 + (s * .04 if row % 2 else 0)
                y = s * .06 + row * s * .1
                if x < s * .47:
                    _star(d, x, y, s * .022, W_)
    elif code == "CN":
        d.rectangle([0, 0, s, s], fill=(222, 41, 16))
        _star(d, s * .3, s * .32, s * .15, (255, 222, 0))
        for x, y in ((.52, .14), (.62, .26), (.62, .42), (.52, .54)):
            _star(d, s * x, s * y, s * .05, (255, 222, 0))
    elif code == "JP":
        d.ellipse([s * .25, s * .25, s * .75, s * .75], fill=(188, 0, 45))
    elif code == "GB":
        d.rectangle([0, 0, s, s], fill=(1, 33, 105))
        d.line([(0, 0), (s, s)], fill=W_, width=int(s * .18)); d.line([(s, 0), (0, s)], fill=W_, width=int(s * .18))
        d.line([(0, 0), (s, s)], fill=(200, 16, 46), width=int(s * .06)); d.line([(s, 0), (0, s)], fill=(200, 16, 46), width=int(s * .06))
        d.rectangle([s * .38, 0, s * .62, s], fill=W_); d.rectangle([0, s * .38, s, s * .62], fill=W_)
        d.rectangle([s * .43, 0, s * .57, s], fill=(200, 16, 46)); d.rectangle([0, s * .43, s, s * .57], fill=(200, 16, 46))
    elif code == "EU":
        d.rectangle([0, 0, s, s], fill=(0, 51, 153))
        for i in range(12):
            a = math.radians(i * 30)
            _star(d, s / 2 + s * .3 * math.cos(a), s / 2 + s * .3 * math.sin(a), s * .045, (255, 204, 0))
    elif code == "SA":
        d.rectangle([0, 0, s, s], fill=(0, 108, 53))
        d.rectangle([s * .25, s * .62, s * .75, s * .66], fill=W_)
        d.rectangle([s * .25, s * .36, s * .75, s * .5], outline=W_, width=max(2, s // 50))
    elif code == "RU":
        _stripes_h(d, s, [W_, (0, 57, 166), (213, 43, 30)])
    elif code == "UA":
        _stripes_h(d, s, [(0, 87, 183), (255, 215, 0)])
    elif code == "FR":
        _stripes_v(d, s, [(0, 85, 164), W_, (239, 65, 53)])
    elif code == "DE":
        _stripes_h(d, s, [(0, 0, 0), (221, 0, 0), (255, 206, 0)])
    elif code == "IT":
        _stripes_v(d, s, [(0, 146, 70), W_, (206, 43, 55)])
    elif code == "CA":
        _stripes_v(d, s, [(216, 6, 33), W_, W_, (216, 6, 33)])
        c = s / 2
        d.polygon([(c, s * .3), (c + s * .12, s * .45), (c + s * .08, s * .62), (c, s * .58), (c - s * .08, s * .62), (c - s * .12, s * .45)], fill=(216, 6, 33))
        d.rectangle([c - s * .015, s * .58, c + s * .015, s * .7], fill=(216, 6, 33))
    elif code == "IL":
        d.rectangle([0, s * .15, s, s * .25], fill=(0, 56, 184)); d.rectangle([0, s * .75, s, s * .85], fill=(0, 56, 184))
        c, r = s / 2, s * .16
        for rot in (-90, 90):
            pts = [(c + r * math.cos(math.radians(rot + k * 120)), c + r * math.sin(math.radians(rot + k * 120))) for k in range(3)]
            d.polygon(pts, outline=(0, 56, 184), width=max(2, s // 40))
    elif code == "IR":
        _stripes_h(d, s, [(35, 159, 64), W_, (218, 0, 0)])
    elif code == "AE":
        _stripes_h(d, s, [(0, 115, 47), W_, (0, 0, 0)])
        d.rectangle([0, 0, s * .28, s], fill=(255, 0, 0))
    elif code == "KR":
        c, r = s / 2, s * .2
        d.pieslice([c - r, c - r, c + r, c + r], 180, 360, fill=(205, 46, 58)); d.pieslice([c - r, c - r, c + r, c + r], 0, 180, fill=(0, 71, 160))
        for x, y in ((.2, .2), (.8, .2), (.2, .8), (.8, .8)):
            for k in range(3):
                d.rectangle([s * x - s * .07, s * y - s * .06 + k * s * .045, s * x + s * .07, s * y - s * .04 + k * s * .045], fill=(0, 0, 0))
    elif code == "BR":
        d.rectangle([0, 0, s, s], fill=(0, 156, 59))
        d.polygon([(s * .5, s * .12), (s * .9, s * .5), (s * .5, s * .88), (s * .1, s * .5)], fill=(255, 223, 0))
        d.ellipse([s * .3, s * .3, s * .7, s * .7], fill=(0, 39, 118))
    elif code == "CH":
        d.rectangle([0, 0, s, s], fill=(218, 41, 28))
        d.rectangle([s * .42, s * .22, s * .58, s * .78], fill=W_); d.rectangle([s * .22, s * .42, s * .78, s * .58], fill=W_)
    elif code == "AU":
        d.rectangle([0, 0, s, s], fill=(0, 0, 139))
        for x, y, r in ((.3, .72, .08), (.72, .28, .05), (.82, .48, .05), (.62, .5, .05), (.72, .75, .05)):
            _star(d, s * x, s * y, s * r, W_)
    elif code == "SG":
        _stripes_h(d, s, [(237, 41, 57), W_])
        d.ellipse([s * .12, s * .12, s * .42, s * .42], fill=W_); d.ellipse([s * .19, s * .12, s * .49, s * .42], fill=(237, 41, 57))
    elif code == "PK":
        d.rectangle([0, 0, s, s], fill=(1, 65, 28)); d.rectangle([0, 0, s * .25, s], fill=W_)
        d.ellipse([s * .38, s * .25, s * .82, s * .69], fill=W_); d.ellipse([s * .46, s * .22, s * .88, s * .64], fill=(1, 65, 28))
    else:
        return None
    return im


def flag_badge(code, size):
    im = _flag(code, size * 2)
    if im is None:
        return None
    im = im.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    out = Image.new("RGBA", (size + 8, size + 8), (0, 0, 0, 0))
    ImageDraw.Draw(out).ellipse([0, 0, size + 7, size + 7], fill=(255, 255, 255, 255))
    out.paste(im, (4, 4), mask)
    return out


# ---------------------------------------------------------------- symbols
def _coin(d, cx, cy, r, fill, ring, glyph, gcol, font="DejaVuSans-Bold.ttf"):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ring)
    d.ellipse([cx - r * .84, cy - r * .84, cx + r * .84, cy + r * .84], fill=fill)
    d.ellipse([cx - r * .84, cy - r * .84, cx + r * .84, cy + r * .84], outline=ring, width=max(3, int(r * .05)))
    f = FONT(font, int(r * 1.05))
    d.text((cx, cy + r * .04), glyph, font=f, fill=gcol, anchor="mm")


def symbol(name, size):
    """Full-colour hero symbol on a transparent square."""
    s = size
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = s / 2
    if name == "oil":
        bw, bh = s * .5, s * .68
        x0, y0 = c - bw / 2, c - bh / 2 + s * .04
        d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=s * .06, fill=(28, 28, 32))
        for k in (.18, .5, .82):
            y = y0 + bh * k
            d.rectangle([x0 - s * .02, y - s * .025, x0 + bw + s * .02, y + s * .025], fill=(70, 70, 78))
        d.ellipse([x0 + bw * .6, y0 - s * .01, x0 + bw * .82, y0 + s * .05], fill=(70, 70, 78))
        # drop
        dx, dy, r = c, y0 + bh * .52, s * .12
        d.polygon([(dx, dy - r * 1.9), (dx - r * .9, dy - r * .1), (dx + r * .9, dy - r * .1)], fill=(255, 196, 0))
        d.ellipse([dx - r, dy - r * .9, dx + r, dy + r * 1.1], fill=(255, 196, 0))
    elif name == "dollar":
        _coin(d, c, c, s * .42, (46, 160, 90), (22, 110, 60), "$", (255, 255, 255))
    elif name == "rupee":
        _coin(d, c, c, s * .42, (255, 153, 51), (200, 100, 20), "₹", (255, 255, 255))
    elif name == "euro":
        _coin(d, c, c, s * .42, (0, 51, 153), (0, 30, 100), "€", (255, 204, 0))
    elif name == "yen":
        _coin(d, c, c, s * .42, (188, 0, 45), (130, 0, 30), "¥", (255, 255, 255))
    elif name == "bitcoin":
        _coin(d, c, c, s * .42, (247, 147, 26), (190, 105, 10), "₿", (255, 255, 255))
    elif name == "silver":
        _coin(d, c, c, s * .42, (200, 205, 214), (140, 146, 156), "Ag", (90, 96, 108))
    elif name == "gold":
        bw, bh = s * .34, s * .16
        def bar(x, y):
            d.polygon([(x - bw / 2, y + bh / 2), (x - bw / 2 + s * .06, y - bh / 2), (x + bw / 2 - s * .06, y - bh / 2), (x + bw / 2, y + bh / 2)], fill=(255, 196, 37))
            d.polygon([(x - bw / 2 + s * .06, y - bh / 2), (x + bw / 2 - s * .06, y - bh / 2), (x + bw / 2 - s * .1, y - bh / 2 + s * .03), (x - bw / 2 + s * .1, y - bh / 2 + s * .03)], fill=(255, 230, 140))
            d.line([(x - bw / 2, y + bh / 2), (x + bw / 2, y + bh / 2)], fill=(190, 130, 0), width=max(3, s // 80))
        by = c + s * .22
        for dx in (-.35, 0, .35): bar(c + s * dx, by)
        for dx in (-.175, .175): bar(c + s * dx, by - bh * 1.05)
        bar(c, by - bh * 2.1)
    elif name == "yield":
        d.rounded_rectangle([s * .12, s * .16, s * .88, s * .84], radius=s * .05, fill=(255, 255, 255))
        pts = [(s * .2, s * .7), (s * .36, s * .6), (s * .5, s * .64), (s * .66, s * .42), (s * .8, s * .3)]
        d.line(pts, fill=(196, 55, 74), width=max(6, s // 30), joint="curve")
        d.polygon([(s * .8, s * .22), (s * .86, s * .36), (s * .72, s * .32)], fill=(196, 55, 74))
        f = FONT("DejaVuSans-Bold.ttf", int(s * .16))
        d.text((s * .2, s * .2), "%", font=f, fill=(20, 32, 60))
    elif name == "chip":
        r = s * .26
        d.rounded_rectangle([c - r, c - r, c + r, c + r], radius=s * .05, fill=(30, 40, 90))
        for i in range(-2, 3):
            o = i * r * .38
            for a, b in (((c + o, c - r), (c + o, c - r - s * .1)), ((c + o, c + r), (c + o, c + r + s * .1)),
                         ((c - r, c + o), (c - r - s * .1, c + o)), ((c + r, c + o), (c + r + s * .1, c + o))):
                d.line([a, b], fill=(180, 190, 220), width=max(4, s // 50))
        f = FONT("DejaVuSans-Bold.ttf", int(s * .16))
        d.text((c, c), "AI", font=f, fill=(140, 230, 255), anchor="mm")
    elif name == "rocket":
        d.polygon([(c, s * .08), (c + s * .14, s * .32), (c + s * .14, s * .66), (c - s * .14, s * .66), (c - s * .14, s * .32)], fill=(245, 245, 250))
        d.ellipse([c - s * .07, s * .3, c + s * .07, s * .44], fill=(80, 140, 255))
        d.polygon([(c - s * .14, s * .5), (c - s * .28, s * .74), (c - s * .14, s * .66)], fill=(230, 60, 80))
        d.polygon([(c + s * .14, s * .5), (c + s * .28, s * .74), (c + s * .14, s * .66)], fill=(230, 60, 80))
        d.polygon([(c - s * .1, s * .66), (c + s * .1, s * .66), (c, s * .92)], fill=(255, 170, 30))
        d.polygon([(c - s * .05, s * .66), (c + s * .05, s * .66), (c, s * .82)], fill=(255, 235, 120))
    elif name == "bank":
        col = (245, 245, 250)
        d.polygon([(s * .12, s * .34), (c, s * .12), (s * .88, s * .34)], fill=col)
        d.rectangle([s * .16, s * .36, s * .84, s * .41], fill=col)
        for i in range(5):
            x = s * .22 + i * s * .14
            d.rectangle([x - s * .03, s * .44, x + s * .03, s * .74], fill=col)
        d.rectangle([s * .12, s * .76, s * .88, s * .82], fill=col)
        d.rectangle([s * .08, s * .84, s * .92, s * .9], fill=col)
    elif name == "chart-up" or name == "chart-down":
        up = name == "chart-up"
        col = (40, 200, 120) if up else (240, 80, 100)
        hs = [.35, .5, .42, .62, .55, .78] if up else [.78, .6, .66, .45, .5, .3]
        for i, hh in enumerate(hs):
            x = s * .14 + i * s * .14
            top = s * (.9 - hh); bot = top + s * .2
            d.line([(x, top - s * .05), (x, bot + s * .05)], fill=(240, 240, 245), width=max(3, s // 90))
            d.rectangle([x - s * .04, top, x + s * .04, bot], fill=col if (i % 2 == 0) == up or i == 5 else (240, 240, 245))
    else:
        return None
    return im


# ---------------------------------------------------------------- company badges
BADGE_COLS = [(37, 99, 235), (124, 58, 237), (219, 39, 119), (234, 88, 12), (5, 150, 105), (8, 145, 178), (79, 70, 229), (190, 18, 60)]


def company_badge(ticker, height=58):
    t = ticker.upper()[:12]
    f = FONT("DejaVuSansMono-Bold.ttf", int(height * .48))
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    w = int(tmp.textlength(t, font=f) + height * .7)
    col = BADGE_COLS[int(hashlib.md5(t.encode()).hexdigest(), 16) % len(BADGE_COLS)]
    im = Image.new("RGBA", (w + 6, height + 6), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w + 5, height + 5], radius=height * .3, fill=(255, 255, 255, 255))
    d.rounded_rectangle([3, 3, w + 2, height + 2], radius=height * .27, fill=col)
    d.text(((w + 6) / 2, (height + 6) / 2), t, font=f, fill=(255, 255, 255), anchor="mm")
    return im


# ---------------------------------------------------------------- detection
COUNTRIES = [
    ("IN", ["india", "indian", "sensex", "nifty", "rbi", "sebi", "rupee"]), ("US", ["us ", "u.s.", "united states", "america", "wall street", "fed ", "federal reserve", "nasdaq", "dow", "s&p", "treasury", "washington", "trump"]),
    ("CN", ["china", "chinese", "beijing", "deepseek"]), ("JP", ["japan", "nikkei", "yen", "boj"]), ("GB", ["uk ", "britain", "british", "london", "bank of england"]),
    ("EU", ["europe", "eu ", "euro ", "ecb", "eurozone"]), ("SA", ["saudi"]), ("RU", ["russia", "moscow"]), ("UA", ["ukraine", "zelenskyy", "kyiv"]),
    ("FR", ["france", "french", "paris", "macron"]), ("DE", ["germany", "german"]), ("CA", ["canada", "canadian", "alberta"]), ("IL", ["israel"]), ("IR", ["iran", "hormuz"]),
    ("AE", ["uae", "dubai"]), ("KR", ["korea", "kospi"]), ("BR", ["brazil"]), ("CH", ["swiss", "switzerland"]), ("AU", ["australia", "rba"]), ("SG", ["singapore"]), ("PK", ["pakistan"]),
]
COUNTRY_NAMES = {"IN": "India", "US": "US", "CN": "China", "JP": "Japan", "GB": "UK", "EU": "Europe", "SA": "Saudi Arabia", "RU": "Russia", "UA": "Ukraine", "FR": "France", "DE": "Germany",
                 "CA": "Canada", "IL": "Israel", "IR": "Iran", "AE": "UAE", "KR": "South Korea", "BR": "Brazil", "CH": "Switzerland", "AU": "Australia", "SG": "Singapore", "PK": "Pakistan"}
SYMBOLS = [("gold", ["gold"]), ("silver", ["silver"]), ("oil", ["crude", "oil", "brent", "wti", "opec"]), ("bitcoin", ["bitcoin", "crypto", "btc"]),
           ("rupee", ["rupee", "usd/inr", "inr"]), ("yen", ["yen"]), ("euro", ["euro "]), ("dollar", ["dollar", "dxy"]), ("yield", ["yield", "treasury", "bond", "rate hike", "rate cut", "fed "]),
           ("bank", ["rbi", "sebi", "repo", "monetary policy", "central bank"]), ("chip", ["ai ", "chip", "semiconductor", "gpu", "nvidia", "model"]), ("rocket", ["ipo", "funding", "raises", "startup", "series "])]
COMPANIES = {
    "jio platforms": "JIO", "reliance": "RELIANCE", "infosys": "INFY", "tcs": "TCS", "wipro": "WIPRO", "hcltech": "HCLTECH", "hcl tech": "HCLTECH", "ltimindtree": "LTIM",
    "hdfc bank": "HDFCBANK", "icici bank": "ICICIBANK", "axis bank": "AXISBANK", "kotak": "KOTAKBANK", "sbi": "SBIN", "indusind": "INDUSINDBK", "yes bank": "YESBANK",
    "union bank": "UNIONBANK", "pnb": "PNB", "punjab national": "PNB", "bajaj finance": "BAJFINANCE", "tata motors": "TATAMOTORS", "tata steel": "TATASTEEL", "jsw steel": "JSWSTEEL",
    "ultratech": "ULTRACEMCO", "adani green": "ADANIGREEN", "adani power": "ADANIPOWER", "adani energy": "ADANIENSOL", "swiggy": "SWIGGY", "eternal": "ETERNAL", "zomato": "ETERNAL",
    "hpcl": "HPCL", "bpcl": "BPCL", "havells": "HAVELLS", "dr reddy": "DRREDDY", "vodafone idea": "IDEA", "zetwerk": "ZETWERK", "paras healthcare": "PARAS", "tenstorrent": "TENSTORRENT",
    "nvidia": "NVDA", "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL", "gemini": "GOOGL", "meta": "META", "amazon": "AMZN", "apple": "AAPL", "tesla": "TSLA",
    "netflix": "NFLX", "palantir": "PLTR", "micron": "MU", "openai": "OPENAI", "anthropic": "ANTHROPIC", "deepseek": "DEEPSEEK", "youtube": "GOOGL", "ramp": "RAMP", "modal": "MODAL",
    "boldfit": "BOLDFIT", "spacex": "SPACEX", "ibm": "IBM", "nscale": "NSCALE",
}


def detect(p):
    text = " " + " ".join([p.get("title", ""), p.get("dek", "")] + (p.get("body") if isinstance(p.get("body"), list) else [str(p.get("body") or "")])).lower() + " "
    head = " " + (p.get("title", "") + " " + p.get("dek", "")).lower() + " "
    flags = list(p.get("flags") or [])
    if not flags:
        scored = []
        for code, kws in COUNTRIES:
            n = sum(text.count(k) for k in kws) + 3 * sum(head.count(k) for k in kws)
            if n:
                scored.append((n, code))
        flags = [c for _, c in sorted(scored, reverse=True)[:3]]
    sym = p.get("symbol")
    if not sym:
        for field in (p.get("title", ""), p.get("dek", "")):
            best = None
            low = " " + field.lower() + " "
            for name, kws in SYMBOLS:
                for k in kws:
                    m = re.search(r"(?<![a-z])" + re.escape(k.strip()) + r"(?![a-z])", low)
                    if m and (best is None or m.start() < best[0]):
                        best = (m.start(), name)
            if best:
                sym = best[1]; break
    comps = p.get("companies")
    if comps is None:
        found = []
        for k, t in COMPANIES.items():
            i = head.find(k)
            if i >= 0 and t not in [x[1] for x in found]:
                found.append((i, t))
        comps = [t for _, t in sorted(found)[:3]]
    else:
        comps = [c.get("ticker") or c.get("name") if isinstance(c, dict) else str(c) for c in comps][:3]
    return flags, sym, comps
