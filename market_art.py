"""Bull / bear artwork for market-move covers (owner-approved files only).

Used for Indian market stories published from ART_FROM onwards: a falling verified move gets a
bear, a rising one a bull. Covers published before ART_FROM are never changed. A file is used only
if it is listed in data/cover-art.json as approved and its bytes match the recorded sha256.
"""
import hashlib
import json
import os
from datetime import datetime

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ART_FROM = datetime.fromisoformat("2026-10-24T08:45:00+05:30")
# Earlier stories the owner asked to switch to the new artwork (24 Oct 2026).
ALSO = {"2026-10-23-sensex-nifty-close-fourth-straight-fall-recovers-from-lows", "2026-10-23-weekly-market-review",
        "2026-10-23-jio-platforms-ipo-closes-22-times-subscribed", "2026-10-24-paras-healthcare-ipo-closes-2-34-times-subscribed"}
_CACHE = {}


def _registry():
    if "reg" not in _CACHE:
        p = os.path.join(HERE, "data", "cover-art.json")
        items = []
        if os.path.isfile(p):
            for it in json.load(open(p, encoding="utf-8")).get("items", []):
                f = os.path.join(HERE, it.get("file", ""))
                if it.get("approved") is True and it.get("rights") and os.path.isfile(f) \
                        and hashlib.sha256(open(f, "rb").read()).hexdigest() == it.get("sha256"):
                    items.append(it)
        _CACHE["reg"] = items
    return _CACHE["reg"]


def choice(p, direction):
    """The artwork id for this story, or None (old story, not a market move, flat, or no art)."""
    if p.get("category") != "markets" or direction not in ("up", "down"):
        return None
    try:
        if p.get("id") not in ALSO and datetime.fromisoformat(str(p.get("publishedAt"))) < ART_FROM:
            return None
    except ValueError:
        return None
    pool = sorted((it for it in _registry() if it["kind"] in ("bull", "bear") and it["direction"] == direction), key=lambda it: it["id"])
    if not pool:
        return None
    k = int(hashlib.md5(str(p.get("id")).encode()).hexdigest(), 16) % len(pool)  # stable rotation
    return pool[k]["id"]


def _new_enough(p):
    try:
        return p.get("id") in ALSO or datetime.fromisoformat(str(p.get("publishedAt"))) >= ART_FROM
    except ValueError:
        return False


def ipo_choice(p):
    """Artwork id for an IPO story's cover, or None."""
    if not _new_enough(p):
        return None
    pool = sorted((it for it in _registry() if it["kind"] == "ipo"), key=lambda it: it["id"])
    if not pool:
        return None
    return pool[int(hashlib.md5(str(p.get("id")).encode()).hexdigest(), 16) % len(pool)]["id"]


def stage_art(p, stage):
    """Artwork id for an IPO-stage cover ('opens', 'anchor', 'listing', ...), or None."""
    if not _new_enough(p):
        return None
    it = next((i for i in _registry() if i["kind"] == "ipo-stage" and i.get("stage") == stage), None)
    return it["id"] if it else None


def stage_layer(art_id, W, H, panel=(9, 20, 48), edge=980, shift=160):
    """Dark IPO-stage artwork, upscaled and sharpened, right-aligned; navy panel fading in from the left."""
    it = next(i for i in _registry() if i["id"] == art_id)
    src = Image.open(os.path.join(HERE, it["file"])).convert("RGBA")
    a2 = src.resize((int(src.width * H / src.height), H), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
    im = Image.new("RGBA", (W, H), panel + (255,))
    im.alpha_composite(a2, (W - a2.width + shift, 0))
    fade = np.zeros((H, W, 4), np.uint8)
    fade[..., :3] = panel
    fade[..., 3] = (np.clip((edge - np.arange(W)) / 380, 0, 1) * 255).astype(np.uint8)[None, :]
    im.alpha_composite(Image.fromarray(fade, "RGBA"))
    return im


def ipo_layer(art_id, W, H, panel=(10, 22, 48), edge=1000):
    """Light artwork on the right; a solid navy panel on the left that fades into it."""
    it = next(i for i in _registry() if i["id"] == art_id)
    src = Image.open(os.path.join(HERE, it["file"])).convert("RGBA")
    im = Image.new("RGBA", (W, H), panel + (255,))
    a2 = src.resize((int(src.width * H / src.height), H), Image.LANCZOS)
    im.alpha_composite(a2, (W - a2.width + 260, 0))
    fade = np.zeros((H, W, 4), np.uint8)
    fade[..., :3] = panel
    fade[..., 3] = (np.clip((edge - np.arange(W)) / 360, 0, 1) * 255).astype(np.uint8)[None, :]
    im.alpha_composite(Image.fromarray(fade, "RGBA"))
    return im


def layer(art_id, W, H, strength=1.0, text_width=900):
    """W x H RGBA layer: the artwork right-aligned, its left edge fading out under the headline,
    with extra darkening behind the text. strength < 1 dims the art (for covers with data tiles)."""
    it = next(i for i in _registry() if i["id"] == art_id)
    src = Image.open(os.path.join(HERE, it["file"])).convert("RGBA")
    im = src.resize((int(src.width * H / src.height), H), Image.LANCZOS)
    a = np.asarray(im).copy()
    fade = np.clip((np.arange(im.width) - 120) / 520, 0, 1) ** 1.3
    a[..., 3] = (a[..., 3] * fade[None, :] * strength).astype(np.uint8)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.alpha_composite(Image.fromarray(a, "RGBA"), (W - im.width + 120, 0))
    shade = np.zeros((H, W, 4), np.uint8)
    shade[..., 3] = (np.clip(1 - np.arange(W) / text_width, 0, 1) ** 1.2 * 200).astype(np.uint8)[None, :]
    out.alpha_composite(Image.fromarray(shade, "RGBA"))
    return out


def brand_backing(im, W, H):
    """Dark soft pill behind the bottom-right TotalMarket wordmark so artwork never runs through it."""
    pill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(pill).rounded_rectangle([W - 400, H - 118, W - 34, H - 22], radius=44, fill=(8, 6, 10, 240))
    im.alpha_composite(pill.filter(ImageFilter.GaussianBlur(2)))
