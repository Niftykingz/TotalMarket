"""Cartoon characters for covers, drawn from simple shapes (no real people).

character(name, size) -> RGBA image (size x size) or None.
Available: ravan, bull, bear.
"""
import math
from PIL import Image, ImageDraw, ImageFilter

SS = 3  # supersample factor for smooth edges


def _face(d, cx, cy, r, skin, main=False):
    # crown
    gold, gold2 = (255, 196, 37), (214, 140, 0)
    ch = r * (1.25 if main else .85)
    d.polygon([(cx - r * .78, cy - r * .62), (cx - r * .5, cy - r * .62 - ch * .55), (cx - r * .25, cy - r * .62 - ch * .25),
               (cx, cy - r * .62 - ch), (cx + r * .25, cy - r * .62 - ch * .25), (cx + r * .5, cy - r * .62 - ch * .55),
               (cx + r * .78, cy - r * .62)], fill=gold, outline=gold2, width=max(2, int(r * .06)))
    d.ellipse([cx - r * .14, cy - r * .62 - ch * .62, cx + r * .14, cy - r * .62 - ch * .34], fill=(220, 40, 60))
    # face
    d.ellipse([cx - r, cy - r, cx + r, cy + r * 1.05], fill=skin, outline=(60, 20, 10), width=max(2, int(r * .06)))
    # brows (fierce)
    bw = max(3, int(r * .12))
    d.line([(cx - r * .62, cy - r * .32), (cx - r * .14, cy - r * .12)], fill=(30, 10, 5), width=bw)
    d.line([(cx + r * .62, cy - r * .32), (cx + r * .14, cy - r * .12)], fill=(30, 10, 5), width=bw)
    # eyes
    for sx in (-1, 1):
        ex = cx + sx * r * .36
        d.ellipse([ex - r * .2, cy - r * .1, ex + r * .2, cy + r * .18], fill=(255, 255, 255), outline=(30, 10, 5), width=max(1, int(r * .04)))
        d.ellipse([ex - r * .08, cy - r * .02, ex + r * .08, cy + r * .14], fill=(20, 10, 5))
    # tilak
    d.rectangle([cx - r * .04, cy - r * .55, cx + r * .04, cy - r * .2], fill=(220, 40, 40))
    # moustache (big curled)
    mw = max(3, int(r * .14))
    d.arc([cx - r * .75, cy + r * .1, cx - r * .02, cy + r * .62], 200, 340, fill=(20, 10, 5), width=mw)
    d.arc([cx + r * .02, cy + r * .1, cx + r * .75, cy + r * .62], 200, 340, fill=(20, 10, 5), width=mw)
    # mouth
    d.arc([cx - r * .3, cy + r * .45, cx + r * .3, cy + r * .82], 200, 340, fill=(140, 20, 20), width=max(2, int(r * .07)))
    # ear rings
    for sx in (-1, 1):
        d.ellipse([cx + sx * r * .98 - r * .09, cy + r * .2, cx + sx * r * .98 + r * .09, cy + r * .38], fill=gold)


def ravan(s):
    W = s * SS
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = W / 2
    # body: shoulders + robe
    d.polygon([(c - W * .34, W * .98), (c - W * .3, W * .7), (c - W * .14, W * .58), (c + W * .14, W * .58), (c + W * .3, W * .7), (c + W * .34, W * .98)],
              fill=(150, 20, 45), outline=(80, 10, 20), width=SS * 3)
    d.polygon([(c - W * .14, W * .58), (c, W * .78), (c + W * .14, W * .58)], fill=(255, 196, 37))
    # necklace
    for k in range(9):
        a = math.radians(200 + k * 17.5)
        d.ellipse([c + math.cos(a) * W * .17 - W * .016, W * .6 + (math.sin(a) + 1) * W * .05 - W * .016,
                   c + math.cos(a) * W * .17 + W * .016, W * .6 + (math.sin(a) + 1) * W * .05 + W * .016], fill=(255, 220, 90))
    # arms: sword in the left hand, fist on the right
    d.line([(c - W * .3, W * .74), (c - W * .44, W * .62)], fill=(150, 20, 45), width=int(W * .06))
    d.line([(c - W * .46, W * .66), (c - W * .46, W * .36)], fill=(220, 225, 235), width=int(W * .02))
    d.rectangle([c - W * .5, W * .64, c - W * .42, W * .67], fill=(255, 196, 37))
    d.line([(c + W * .3, W * .74), (c + W * .44, W * .66)], fill=(150, 20, 45), width=int(W * .06))
    d.ellipse([c + W * .41, W * .62, c + W * .48, W * .69], fill=(232, 168, 110))
    # ten heads: 4 on the left, the main head, 5 on the right
    skins = [(232, 168, 110), (110, 170, 120), (120, 150, 220), (230, 140, 90), (240, 190, 120)]
    side = [-.43, -.345, -.26, -.175, .095, .18, .265, .35, .435]
    for k, x in enumerate(sorted(side, key=lambda v: -abs(v))):
        _face(d, c + x * W, W * .52, W * .052, skins[k % len(skins)])
    d.rectangle([c - W * .075, W * .5, c - W * .005, W * .6], fill=(225, 165, 105))
    _face(d, c - W * .04, W * .47, W * .09, (240, 190, 120), True)
    im = im.resize((s, s), Image.LANCZOS)
    return im


def bull(s):
    W = s * SS
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = W / 2
    body, dark = (34, 197, 94), (10, 110, 50)
    # horns
    horn = (250, 240, 220)
    for sx in (-1, 1):
        pts = [(c + sx * W * .18, W * .34), (c + sx * W * .3, W * .3), (c + sx * W * .4, W * .22), (c + sx * W * .45, W * .1),
               (c + sx * W * .47, W * .2), (c + sx * W * .42, W * .3), (c + sx * W * .3, W * .38), (c + sx * W * .2, W * .4)]
        d.polygon(pts, fill=horn, outline=(200, 180, 150))
    # ears
    d.ellipse([c - W * .42, W * .33, c - W * .22, W * .45], fill=dark)
    d.ellipse([c + W * .22, W * .33, c + W * .42, W * .45], fill=dark)
    # head
    d.rounded_rectangle([c - W * .25, W * .26, c + W * .25, W * .74], radius=W * .14, fill=body, outline=dark, width=SS * 4)
    # snout
    d.rounded_rectangle([c - W * .2, W * .56, c + W * .2, W * .8], radius=W * .1, fill=(134, 239, 172), outline=dark, width=SS * 3)
    for sx in (-1, 1):
        d.ellipse([c + sx * W * .09 - W * .035, W * .64, c + sx * W * .09 + W * .035, W * .7], fill=dark)
    # nose ring
    d.arc([c - W * .07, W * .7, c + W * .07, W * .84], 0, 180, fill=(255, 196, 37), width=SS * 5)
    # eyes (determined)
    for sx in (-1, 1):
        ex = c + sx * W * .11
        d.ellipse([ex - W * .045, W * .4, ex + W * .045, W * .48], fill=(255, 255, 255))
        d.ellipse([ex - W * .02, W * .42, ex + W * .02, W * .47], fill=(15, 15, 20))
        d.line([(ex - sx * W * .06, W * .37), (ex + sx * W * .04, W * .39)], fill=dark, width=SS * 4)
    return im.resize((s, s), Image.LANCZOS)


def bear(s):
    W = s * SS
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = W / 2
    fur, dark, muzzle = (150, 82, 48), (80, 40, 20), (222, 184, 135)
    # ears
    for sx in (-1, 1):
        d.ellipse([c + sx * W * .25 - W * .1, W * .14, c + sx * W * .25 + W * .1, W * .34], fill=fur, outline=dark, width=SS * 3)
        d.ellipse([c + sx * W * .25 - W * .05, W * .19, c + sx * W * .25 + W * .05, W * .29], fill=(239, 68, 68))
    # head
    d.ellipse([c - W * .3, W * .2, c + W * .3, W * .78], fill=fur, outline=dark, width=SS * 4)
    # muzzle + nose
    d.ellipse([c - W * .15, W * .5, c + W * .15, W * .74], fill=muzzle, outline=dark, width=SS * 3)
    d.ellipse([c - W * .06, W * .52, c + W * .06, W * .6], fill=(30, 15, 10))
    d.arc([c - W * .08, W * .64, c + W * .08, W * .74], 200, 340, fill=(30, 15, 10), width=SS * 4)
    # grumpy eyes
    for sx in (-1, 1):
        ex = c + sx * W * .12
        d.ellipse([ex - W * .035, W * .4, ex + W * .035, W * .47], fill=(20, 10, 5))
        d.line([(ex - sx * W * .07, W * .36), (ex + sx * W * .04, W * .39)], fill=dark, width=SS * 5)
    return im.resize((s, s), Image.LANCZOS)


CHARS = {"ravan": ravan, "bull": bull, "bear": bear}


def character(name, size):
    f = CHARS.get(name)
    return f(size) if f else None
