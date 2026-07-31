"""Recolor landing dashboard.png chrome from forest green to navy + teal."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw
import colorsys

SRC = Path(__file__).resolve().parents[1] / "static" / "img" / "landing_v1" / "dashboard.png"
MARK = Path(__file__).resolve().parents[1] / "static" / "img" / "brand" / "concept_13_mark.png"

NAVY = (8, 32, 72)
NAVY_MID = (12, 48, 96)
TEAL = (24, 176, 168)
TEAL_SOFT = (14, 120, 118)


def is_chrome_green(r: int, g: int, b: int) -> bool:
    if g < 40:
        return False
    # Forest / mint chrome family in the current screenshot
    return g > r + 8 and g >= b - 8 and r < 100 and g < 170 and b < 150


def map_chrome(r: int, g: int, b: int) -> tuple[int, int, int]:
    # Luminance of source green drives navy→teal mix for active chips
    lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    # Brighter / more saturated greens (active pills) → teal-tinted navy
    if lum > 0.38 or (s > 0.35 and g > 95):
        t = min(1.0, (lum - 0.28) / 0.35)
        nr = int(NAVY[0] + (TEAL_SOFT[0] - NAVY[0]) * t * 0.85)
        ng = int(NAVY[1] + (TEAL_SOFT[1] - NAVY[1]) * t * 0.85)
        nb = int(NAVY[2] + (TEAL_SOFT[2] - NAVY[2]) * t * 0.55)
        # preserve a touch of highlight
        boost = max(0.0, (v - 0.25) * 0.35)
        nr = min(255, int(nr + (TEAL[0] - nr) * boost))
        ng = min(255, int(ng + (TEAL[1] - ng) * boost))
        nb = min(255, int(nb + (TEAL[2] - nb) * boost))
        return nr, ng, nb
    # Dark chrome → navy, keep slight value variation
    shade = max(0.55, min(1.15, v / 0.28))
    return (
        min(255, int(NAVY[0] * shade + (NAVY_MID[0] - NAVY[0]) * max(0, shade - 1) * 2)),
        min(255, int(NAVY[1] * shade + (NAVY_MID[1] - NAVY[1]) * max(0, shade - 1) * 2)),
        min(255, int(NAVY[2] * shade + (NAVY_MID[2] - NAVY[2]) * max(0, shade - 1) * 2)),
    )


def recolor(im: Image.Image) -> Image.Image:
    out = im.copy()
    px = out.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 8:
                continue
            if is_chrome_green(r, g, b):
                nr, ng, nb = map_chrome(r, g, b)
                px[x, y] = (nr, ng, nb, a)
    return out


def stamp_mark(im: Image.Image) -> Image.Image:
    """Place Concept 13 mark beside the CartFlow wordmark in the top chrome."""
    if not MARK.exists():
        return im
    mark = Image.open(MARK).convert("RGBA")
    # Header wordmark sits near top-right in RTL chrome; stamp just before it
    size = 34
    mark = mark.resize((size, size), Image.Resampling.LANCZOS)
    # Make mark white for dark navy chrome
    px = mark.load()
    for y in range(mark.height):
        for x in range(mark.width):
            r, g, b, a = px[x, y]
            if a > 20:
                px[x, y] = (255, 255, 255, a)
    # Approximate CartFlow text position from prior captures (~x 1280-1360, y ~18)
    x, y = 1248, 14
    im.alpha_composite(mark, (x, y))
    return im


def main() -> None:
    im = Image.open(SRC).convert("RGBA")
    out = recolor(im)
    out = stamp_mark(out)
    out.save(SRC, optimize=True)
    print("recolored", SRC, out.size)


if __name__ == "__main__":
    main()
