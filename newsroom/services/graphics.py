"""Newsroom graphic renderer (Pillow), built on the site's existing cover_templates helpers.

The renderer draws ONLY the items in a graphic spec, so what the Fact Checker verifies is
exactly what appears in the image. Templates:

  policy_rate   central-bank rate decision: old rate → new rate as an original step graphic,
                change in bps and % change, institution name as plain text (no logo).
  number_free   neutral original illustration with headline words only (used when no
                verified figures exist).

Output: 1600×900 WebP + 1200×675 PNG (default news-cover size), plus a JSON sidecar with
source facts, template, generation method and review status.
"""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

import cover_templates as ct

W, H = ct.W, ct.H


def _items(spec):
    return {it.get("role"): it for it in spec["items"] if it.get("role")}


def _demo_ribbon(im, text):
    dr = ImageDraw.Draw(im)
    f = ct.F(ct.SEMI, 24)
    w = dr.textlength(text, font=f) + 40
    ct._rrect(im, [W - 72 - w, 60, W - 72, 106], 23, fill=(239, 68, 68, 235))
    ImageDraw.Draw(im).text((W - 72 - w / 2, 83), text, font=f, fill=(255, 255, 255), anchor="mm")


def policy_rate(spec, out_base: Path):
    it = _items(spec)
    im = ct._grad((236, 243, 255), (255, 255, 255), .35)
    dr = ImageDraw.Draw(im)
    # soft original background motif: concentric arcs (abstract "policy dial"), no symbols
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    for i, r in enumerate(range(260, 900, 90)):
        ld.arc([1180 - r, 520 - r, 1180 + r, 520 + r], 180, 360, fill=(37, 99, 235, 26 - i * 2), width=3)
    im.alpha_composite(lay)
    dr = ImageDraw.Draw(im)
    ct._kicker(dr, it["kicker"]["text"], dark=False, accent=ct.BLUE)
    if "badge" in it:
        _demo_ribbon(im, it["badge"]["text"])
        dr = ImageDraw.Draw(im)
    tf = ct._fit(dr, it["title"]["text"], ct.BLACK, 84, 760)
    dr.text((84, 170), it["title"]["text"], font=tf, fill=ct.INK)
    if "org" in it:
        dr.text((86, 280), it["org"]["text"], font=ct.F(ct.SEMI, 32), fill=ct.NAVY)
    # step graphic: two original columns (old → new)
    old, new = it["old"], it["new"]
    ov, nv = ct_float(old["text"]), ct_float(new["text"])
    # bars start at zero so their heights are honest; the change card carries the magnitude
    base_y, max_h = 790, 300
    hi = max(ov, nv)
    hgt = lambda v: v / hi * max_h
    cols = [(110, old, ov, (148, 163, 184)), (430, new, nv, ct.BLUE)]
    for x, item, v, col in cols:
        h = hgt(v)
        ct._rrect(im, [x, base_y - h, x + 230, base_y], 22, fill=col + (255,))
    dr = ImageDraw.Draw(im)
    for x, item, v, col in cols:
        h = hgt(v)
        dr.text((x + 115, base_y - h - 18), item["text"], font=ct.F(ct.XB, 54), fill=ct.INK, anchor="mb")
        dr.text((x + 115, base_y + 18), item.get("label", ""), font=ct.F(ct.MED, 26), fill=ct.MUTED, anchor="ma")
    # arrow between columns
    ay = base_y - hgt(ov) / 2 - 40
    dr.line([(358, ay), (412, ay)], fill=ct.NAVY, width=8)
    dr.polygon([(412, ay - 16), (436, ay), (412, ay + 16)], fill=ct.NAVY)
    # change card
    ch = it.get("change")
    if ch:
        down = ch["text"].strip()[:1] in "-−"
        col = ct.DOWN_D if down else ct.UP_D
        ct._rrect(im, [860, 380, 1500, 560], 28, fill=(255, 255, 255, 255), outline=ct.LINE + (255,), width=3)
        dr = ImageDraw.Draw(im)
        dr.text((900, 410), ch.get("label", "").upper(), font=ct.F(ct.SEMI, 24), fill=ct.MUTED)
        dr.text((900, 450), ch["text"], font=ct.F(ct.BLACK, 76), fill=col)
    rc = it.get("rel_change")
    if rc:
        ct._rrect(im, [860, 590, 1500, 720], 28, fill=ct._tint(ct.BLUE, .10) + (255,))
        dr = ImageDraw.Draw(im)
        dr.text((900, 612), rc.get("label", "").upper(), font=ct.F(ct.SEMI, 22), fill=ct.NAVY)
        dr.text((900, 645), rc["text"], font=ct.F(ct.XB, 50), fill=ct.NAVY)
    if "date" in it:
        dr.text((86, 334), it["date"]["text"].upper(), font=ct.F(ct.MED, 28), fill=ct.MUTED)
    ct._brand(dr, dark=False, accent=ct.BLUE)
    return _save(im, out_base)


def number_free(spec, out_base: Path):
    it = _items(spec)
    im = ct._grad(ct.NAVY, ct.MIDNIGHT, .5)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    for i in range(9):
        ld.ellipse([1000 + i * 30, 150 + i * 40, 1500 - i * 20, 650 + i * 15], outline=(255, 255, 255, 22), width=3)
    im.alpha_composite(lay)
    dr = ImageDraw.Draw(im)
    ct._kicker(dr, it["kicker"]["text"])
    if "badge" in it:
        _demo_ribbon(im, it["badge"]["text"])
        dr = ImageDraw.Draw(im)
    tf = ct._fit(dr, it["title"]["text"], ct.BLACK, 80, 900)
    dr.text((84, 360), it["title"]["text"], font=tf, fill=(255, 255, 255))
    if "org" in it:
        dr.text((86, 470), it["org"]["text"], font=ct.F(ct.SEMI, 32), fill=ct.GOLD)
    ct._brand(dr)
    return _save(im, out_base)


def ct_float(s):
    return float(str(s).replace("%", "").replace("−", "-").replace(",", "").strip())


def _save(im, out_base: Path):
    out_base.parent.mkdir(parents=True, exist_ok=True)
    rgb = im.convert("RGB")
    webp, png = out_base.with_suffix(".webp"), out_base.with_suffix(".png")
    rgb.save(webp, "WEBP", quality=82, method=6)
    rgb.resize((1200, 675), Image.LANCZOS).save(png, "PNG", optimize=True)
    return png, hashlib.sha256(png.read_bytes()).hexdigest()


TEMPLATES = {"policy_rate": policy_rate, "number_free": number_free}


def render(spec, out_base: Path):
    """Render the spec and write the metadata sidecar. Returns (png_path, sha256)."""
    png, sha = TEMPLATES[spec["template"]](spec, Path(out_base))
    meta = dict(spec, file=str(png.name), sha256=sha)
    Path(out_base).with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return png, sha
