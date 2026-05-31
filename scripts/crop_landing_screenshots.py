# -*- coding: utf-8 -*-
"""Crop landing page screenshots — remove browser chrome, tighten to product UI."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "static" / "img" / "landing"

# (left, top, right, bottom) — tuned for 471×1024 Safari captures
CROPS: dict[str, tuple[int, int, int, int]] = {
    "objection_reasons.png": (0, 154, 471, 850),
    "recovery_templates.png": (0, 154, 471, 708),
    "carts_dashboard.png": (0, 154, 471, 812),
    "widget_settings.png": (0, 154, 471, 788),
    "whatsapp_settings.png": (0, 154, 471, 652),
}

CART_NEXT_STEP_BOX = (0, 246, 471, 812)


def is_blankish(r: int, g: int, b: int, *, threshold: int = 248) -> bool:
    if r + g + b < 24:
        return True
    return r >= threshold and g >= threshold and b >= threshold


def trim_bottom_whitespace(im: Image.Image, *, pad: int = 10) -> Image.Image:
    rgb = im.convert("RGB")
    w, h = rgb.size
    pixels = rgb.load()
    last_content = 0
    for y in range(h):
        for x in range(0, w, 2):
            r, g, b = pixels[x, y]
            if not is_blankish(r, g, b):
                last_content = y
                break
    if last_content <= 0:
        return im
    return im.crop((0, 0, w, min(h, last_content + pad)))


def crop_and_save(path: Path, box: tuple[int, int, int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
    im = Image.open(path)
    out = trim_bottom_whitespace(im.crop(box))
    out.save(path, optimize=True, quality=92)
    return im.size, out.size


def main() -> None:
    carts_src = LANDING / "carts_dashboard.png"
    with Image.open(carts_src) as raw:
        next_im = trim_bottom_whitespace(raw.crop(CART_NEXT_STEP_BOX))
        next_im.save(LANDING / "cart-next-step.png", optimize=True, quality=92)
        print(f"cart-next-step.png: rebuilt -> {next_im.size}")

    for name, box in CROPS.items():
        before, after = crop_and_save(LANDING / name, box)
        print(f"{name}: {before} -> {after}")


if __name__ == "__main__":
    main()
