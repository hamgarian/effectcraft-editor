"""Put your own title and small print on generated art (image models garble text; generate without it, set it here).
The title is fitted to BOTH the band's height and the image width, so it never clips.

  python title_art.py IN.png OUT.png --title "DUSK" [--font impact.ttf] [--colour "#111111"] [--band 0.2] [--y 0.0]
                      [--stroke 6 --stroke-colour "#ffffff"] [--small "ISSUE 07 // THE NIGHT BUS SPECIAL" --small-y 0.22 --small-size 0.03]
                      [--label "NIGHT BUS" --label-x 0.04 --label-y 0.05]       # white label on a black strip
Fonts: a file name looked up in the system font folders, or a full path.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONT_DIRS = ["C:/Windows/Fonts", "/Library/Fonts", "/System/Library/Fonts", os.path.expanduser("~/Library/Fonts"),
             "/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts")]


def font(name, size):
    if os.path.exists(name):
        return ImageFont.truetype(name, size)
    for d in FONT_DIRS:
        for root, _, files in os.walk(d) if os.path.isdir(d) else []:
            for f in files:
                if f.lower() == name.lower():
                    return ImageFont.truetype(os.path.join(root, f), size)
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default(size)


def fit(draw, text, fname, width, height):
    s = 8
    while True:
        f = font(fname, s + 4); b = draw.textbbox((0, 0), text, font=f)
        if b[2] - b[0] > width or b[3] - b[1] > height or s > 2000:
            return font(fname, s)
        s += 4


a = sys.argv[1:]


def opt(k, d=None, cast=str):
    if k in a:
        i = a.index(k); v = cast(a[i + 1]); del a[i:i + 2]; return v
    return d


if len(a) < 2:
    sys.exit(__doc__)
src, dst = a[0], a[1]
title, fname, col = opt("--title"), opt("--font", "arialbd.ttf"), opt("--colour", "#111111")
band, y0, stroke, scol = opt("--band", 0.2, float), opt("--y", 0.0, float), opt("--stroke", 0, int), opt("--stroke-colour", "#ffffff")
small, sy, ss = opt("--small"), opt("--small-y", None, float), opt("--small-size", 0.03, float)
label, lx, ly = opt("--label"), opt("--label-x", 0.04, float), opt("--label-y", 0.05, float)
im = Image.open(src).convert("RGB"); W, H = im.size; d = ImageDraw.Draw(im)
if title:
    f = fit(d, title, fname, W * 0.88, H * band * 0.82)
    d.text((W / 2, H * (y0 + band / 2)), title, font=f, fill=col, anchor="mm", stroke_width=stroke, stroke_fill=scol if stroke else None)
if small:
    d.text((W * 0.06, H * (sy if sy is not None else y0 + band + 0.02)), small, font=font("arial.ttf", max(10, int(W * ss))), fill=col, anchor="lm")
if label:
    f = font("arialbd.ttf", max(12, int(W * 0.05))); b = d.textbbox((W * lx, H * ly), label, font=f, anchor="lm")
    d.rectangle((b[0] - 12, b[1] - 8, b[2] + 12, b[3] + 8), fill=(10, 10, 10)); d.text((W * lx, H * ly), label, font=f, fill=(255, 255, 255), anchor="lm")
im.save(dst)
print(dst, im.size)
