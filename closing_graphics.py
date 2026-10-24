"""Daily market-close graphics: four 1536x1024 PNGs drawn on the owner's approved artwork.

    market-close.png  sector-performance.png  top-movers.png  fii-dii-flows.png

Input is a *verified* closing dataset (see pipeline/closing.py): every number comes from an
archived exchange file or a sourced figure. A panel whose data is missing says
AWAITING VERIFIED DATA instead of showing anything estimated. The artwork is decoration only;
all data bars are drawn here, proportional to the real values.
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, "fonts")
F = lambda name, size: ImageFont.truetype(os.path.join(FD, name), int(size))
BLACK, XB, SEMI, MED = "InterDisplay-Black.otf", "InterDisplay-ExtraBold.otf", "Inter-SemiBold.otf", "Inter-Medium.otf"
W, H = 1536, 1024
PANEL = (8, 17, 40)
WHITE, GREY, GOLD = (255, 255, 255), (148, 163, 184), (212, 168, 67)
GREEN, RED, AMBER = (16, 196, 122), (242, 92, 102), (251, 191, 36)
X0, TEXT_W = 72, 640           # left 45% (to ~690 px) holds all text and data

ART = {"close": "close-summary", "sectors": "close-sectors", "movers": "close-movers", "flows": "close-flows"}


def num(v):
    try:
        return float(str(v).replace(",", "").replace("₹", "").replace("%", "").replace("+", "").replace("−", "-"))
    except (TypeError, ValueError):
        return None


def inr(v, dec=2):
    n = float(v)
    whole, frac = f"{abs(n):.{dec}f}".split(".") if dec else (f"{abs(n):.0f}", "")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        whole = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1]) + "," + tail
    return ("-" if n < 0 else "") + whole + ("." + frac if frac else "")


def signed(v, dec=2, suffix=""):
    n = float(v)
    return ("+" if n > 0 else "−" if n < 0 else "") + inr(abs(n), dec) + suffix


def rupees(n):
    return ("+" if n > 0 else "−" if n < 0 else "") + "₹" + inr(abs(n)) + " cr"


def col(v):
    n = num(v)
    return GREY if n is None or n == 0 else (GREEN if n > 0 else RED)


def fit(dr, text, font, size, max_w, min_size=18):
    f = F(font, size)
    while dr.textlength(text, font=f) > max_w and size > min_size:
        size -= 2
        f = F(font, size)
    return f


def canvas(kind):
    """Artwork scaled to 1536x1024, sharpened, with a dark panel fading in over the left 45%."""
    import market_art
    reg = {i["id"]: i for i in market_art._registry()}
    it = reg.get(ART[kind])
    im = Image.new("RGBA", (W, H), PANEL + (255,))
    if it:
        src = Image.open(os.path.join(HERE, it["file"])).convert("RGBA")
        im.alpha_composite(src.resize((W, H), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 70, 2)))
    fade = np.zeros((H, W, 4), np.uint8)
    fade[..., :3] = PANEL
    fade[..., 3] = (np.clip((760 - np.arange(W)) / 260, 0, 1) * 235).astype(np.uint8)[None, :]
    im.alpha_composite(Image.fromarray(fade, "RGBA"))
    return im


def rrect(im, box, r, fill=None, outline=None, width=2):
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)
    im.alpha_composite(lay)


def header(im, kicker, title, date_label):
    dr = ImageDraw.Draw(im)
    dr.rectangle([X0, 70, X0 + 9, 102], fill=GOLD)
    dr.text((X0 + 26, 86), kicker.upper(), font=F(SEMI, 26), fill=(226, 232, 240), anchor="lm")
    tf = fit(dr, title, BLACK, 84, TEXT_W)
    dr.text((X0, 126), title, font=tf, fill=WHITE)
    dr.text((X0 + 2, 126 + tf.size + 14), date_label, font=F(MED, 30), fill=GREY)
    return 126 + tf.size + 14 + 30 + 40


def footer(im, sources, status=""):
    dr = ImageDraw.Draw(im)
    line = "Source: " + ", ".join(sources) + (f" · {status}" if status else "")
    dr.text((X0, H - 62), line, font=fit(dr, line, MED, 22, 900, 16), fill=GREY)
    pill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(pill).rounded_rectangle([W - 330, H - 100, W - 36, H - 30], radius=36, fill=(6, 10, 22, 235))
    im.alpha_composite(pill)
    dr = ImageDraw.Draw(im)
    bf = F(XB, 32)
    w = dr.textlength("TotalMarket", font=bf)
    x, y = W - 64 - w, H - 84
    dr.rectangle([x - 22, y + 6, x - 12, y + 32], fill=GOLD)
    dr.text((x, y), "Total", font=bf, fill=WHITE)
    dr.text((x + dr.textlength("Total", font=bf), y), "Market", font=bf, fill=GOLD)


def awaiting(im, y, reason):
    rrect(im, [X0, y, X0 + TEXT_W, y + 210], 26, fill=(255, 255, 255, 14), outline=(251, 191, 36, 150), width=3)
    dr = ImageDraw.Draw(im)
    dr.text((X0 + 32, y + 40), "AWAITING VERIFIED DATA", font=F(XB, 40), fill=AMBER)
    words, lines, cur = reason.split(), [], ""
    f = F(MED, 26)
    for w_ in words:
        t = (cur + " " + w_).strip()
        if dr.textlength(t, font=f) > TEXT_W - 64:
            lines.append(cur); cur = w_
        else:
            cur = t
    lines.append(cur)
    for k, ln in enumerate(lines[:3]):
        dr.text((X0 + 32, y + 104 + k * 34), ln, font=f, fill=(203, 213, 225))


# ------------------------------------------------------------------ 1 market close
def market_close(d, out):
    im = canvas("close")
    y = header(im, "Indian markets · close", "MARKET CLOSE", d["dateLabel"])
    dr = ImageDraw.Draw(im)
    rows = [("NIFTY 50", True), ("SENSEX", True), ("NIFTY BANK", False), ("INDIA VIX", False)]
    for name, pts in rows:
        x = (d.get("indices") or {}).get(name)
        dr.text((X0, y), {"NIFTY BANK": "BANK NIFTY"}.get(name, name), font=F(SEMI, 24), fill=GREY)
        if not x:
            dr.text((X0, y + 32), "Awaiting verified data", font=F(MED, 34), fill=AMBER)
        else:
            close = inr(x["close"])
            dr.text((X0, y + 28), close, font=F(XB, 52), fill=WHITE)
            cx = X0 + dr.textlength(close, font=F(XB, 52)) + 26
            bits = ([signed(x["change"])] if pts and x.get("change") not in (None, "") else []) + [signed(x["pct"], 2, "%")]
            dr.text((cx, y + 46), "   ".join(bits), font=F(SEMI, 34), fill=col(x["pct"]))
        y += 100
    b = d.get("breadth")
    dr.text((X0, y + 4), f"MARKET BREADTH · {b['universe'].upper()}" if b else "MARKET BREADTH", font=F(SEMI, 24), fill=GREY)
    if b:
        a, dcl = int(b["advances"]), int(b["declines"])
        dr.text((X0, y + 34), f"▲ {a:,} advanced", font=F(XB, 36), fill=GREEN)
        dr.text((X0 + 320, y + 34), f"▼ {dcl:,} declined", font=F(XB, 36), fill=RED)
        tot = a + dcl + int(b.get("unchanged") or 0)
        bw = TEXT_W
        ImageDraw.Draw(im).rounded_rectangle([X0, y + 88, X0 + bw, y + 100], radius=6, fill=RED)
        ImageDraw.Draw(im).rounded_rectangle([X0, y + 88, X0 + max(12, int(bw * a / tot)), y + 100], radius=6, fill=GREEN)
    else:
        dr.text((X0, y + 34), "Awaiting verified data", font=F(MED, 32), fill=AMBER)
    y += 124
    if d.get("bottomLine"):
        dr = ImageDraw.Draw(im)
        dr.text((X0, y), "BOTTOM LINE", font=F(SEMI, 24), fill=GOLD)
        f = F(MED, 28)
        words, cur, k = d["bottomLine"].split(), "", 0
        for w_ in words + [None]:
            t = (cur + " " + w_).strip() if w_ else None
            if w_ is None or dr.textlength(t, font=f) > TEXT_W:
                dr.text((X0, y + 32 + k * 36), cur, font=f, fill=WHITE); k += 1; cur = w_ or ""
            else:
                cur = t
    footer(im, d.get("sourceNames") or ["NSE"], d.get("status", ""))
    im.convert("RGB").save(out, "PNG", optimize=True)


# ------------------------------------------------------------------ 2 sectors
def _bars(im, y, rows, max_abs, label_w=300, bar_w=230):
    dr = ImageDraw.Draw(im)
    for name, pct in rows:
        dr.text((X0, y + 26), name, font=fit(dr, name, SEMI, 32, label_w - 16, 20), fill=WHITE, anchor="lm")
        L = max(10, abs(pct) / (max_abs or 1) * bar_w)
        c = GREEN if pct > 0 else RED if pct < 0 else GREY
        rrect(im, [X0 + label_w, y + 8, X0 + label_w + L, y + 44], 8, fill=c + (235,))
        ImageDraw.Draw(im).text((X0 + label_w + L + 14, y + 26), signed(pct, 2, "%"), font=F(XB, 30), fill=c, anchor="lm")
        y += 62
    return y


def sector_performance(d, out):
    im = canvas("sectors")
    y = header(im, "NSE sector indices · day change", "SECTOR PERFORMANCE", d["dateLabel"])
    secs = [s for s in d.get("sectors") or [] if num(s.get("pct")) is not None]
    if len(secs) < 6:
        awaiting(im, y, "Fewer than six NSE sector indices with a verified close for this date.")
    else:
        secs.sort(key=lambda s: num(s["pct"]), reverse=True)
        top, bot = secs[:3], secs[-3:]
        mx = max(abs(num(s["pct"])) for s in top + bot)
        dr = ImageDraw.Draw(im)
        dr.text((X0, y), "STRONGEST", font=F(SEMI, 24), fill=GREEN if num(top[0]["pct"]) > 0 else GREY)
        y = _bars(im, y + 36, [(s["name"], num(s["pct"])) for s in top], mx)
        dr = ImageDraw.Draw(im)
        dr.text((X0, y + 18), "WEAKEST", font=F(SEMI, 24), fill=RED)
        _bars(im, y + 54, [(s["name"], num(s["pct"])) for s in bot], mx)
    footer(im, d.get("sourceNames") or ["NSE"], d.get("status", ""))
    im.convert("RGB").save(out, "PNG", optimize=True)


# ------------------------------------------------------------------ 3 top movers
def top_movers(d, out):
    im = canvas("movers")
    m = d.get("movers") or {}
    y = header(im, f"{m.get('universe', 'Nifty 50')} · closing prices", "TODAY'S TOP MOVERS", d["dateLabel"])
    if not (m.get("gainers") and m.get("losers")):
        awaiting(im, y, "Stock closing prices from NSE's end-of-day file are not available for this date yet.")
    else:
        dr = ImageDraw.Draw(im)
        for title, rows, c in (("TOP GAINERS", m["gainers"][:3], GREEN), ("TOP LOSERS", m["losers"][:3], RED)):
            dr.text((X0, y), title, font=F(SEMI, 24), fill=c)
            y += 38
            for r in rows:
                rrect(im, [X0, y, X0 + TEXT_W, y + 64], 14, fill=(255, 255, 255, 14))
                dr = ImageDraw.Draw(im)
                dr.text((X0 + 22, y + 32), r["name"], font=fit(dr, r["name"], XB, 32, 270, 20), fill=WHITE, anchor="lm")
                dr.text((X0 + 400, y + 32), "₹" + inr(r["close"]), font=F(SEMI, 30), fill=(226, 232, 240), anchor="rm")
                dr.text((X0 + TEXT_W - 22, y + 32), signed(r["pct"], 2, "%"), font=F(XB, 32), fill=c, anchor="rm")
                y += 74
            y += 22
    footer(im, d.get("moverSources") or d.get("sourceNames") or ["NSE"], d.get("status", ""))
    im.convert("RGB").save(out, "PNG", optimize=True)


# ------------------------------------------------------------------ 4 FII / DII
def fii_dii_flows(d, out):
    im = canvas("flows")
    f = d.get("flows")
    y = header(im, "Cash market · ₹ crore", "INSTITUTIONAL MONEY FLOW", d["dateLabel"])
    if not f:
        awaiting(im, y, "NSE has not yet published FII/FPI and DII cash-market figures for this date.")
    else:
        dr = ImageDraw.Draw(im)
        for label, v in (("FII / FPI NET FLOW", f["fii"]), ("DII NET FLOW", f["dii"])):
            n = num(v)
            dr.text((X0, y), label, font=F(SEMI, 24), fill=GREY)
            dr.text((X0, y + 30), rupees(n), font=F(XB, 64), fill=col(n))
            dr.text((X0, y + 108), "Net buying" if n > 0 else "Net selling" if n < 0 else "Flat", font=F(SEMI, 28), fill=col(n))
            y += 170
        tot = num(f["fii"]) + num(f["dii"])
        rrect(im, [X0, y, X0 + TEXT_W, y + 120], 22, fill=(255, 255, 255, 16), outline=(212, 168, 67, 140), width=2)
        dr = ImageDraw.Draw(im)
        dr.text((X0 + 26, y + 20), "NET COMBINED FLOW", font=F(SEMI, 24), fill=GOLD)
        dr.text((X0 + 26, y + 54), rupees(tot), font=F(XB, 46), fill=col(tot))
    status = f"{(f or {}).get('status', 'provisional')} figures" if f else ""
    footer(im, d.get("flowSources") or ["NSE"], status)
    im.convert("RGB").save(out, "PNG", optimize=True)


FILES = {"market-close.png": market_close, "sector-performance.png": sector_performance,
         "top-movers.png": top_movers, "fii-dii-flows.png": fii_dii_flows}


def render_all(d, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for name, fn in FILES.items():
        fn(d, os.path.join(out_dir, name))
    return [os.path.join(out_dir, n) for n in FILES]
