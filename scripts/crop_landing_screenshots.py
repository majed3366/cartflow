# -*- coding: utf-8 -*-
"""Crop landing screenshots into tight product-feature assets (not page captures)."""
from __future__ import annotations

import io
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "static" / "img" / "landing"
ORIG_COMMIT = "39501a7"

# (left, top, right, bottom) on full 471×1024 Safari captures
FEATURE_CROPS: dict[str, tuple[int, int, int, int]] = {
    # Chart + reason bars + recommendations only
    "objection_reasons.png": (12, 302, 459, 842),
    # Stage flow card + price template stages (طمأنة → عرض → بديل)
    "recovery_templates.png": (12, 268, 459, 712),
    # Single cart row: value, reason, status, next-step block
    "carts_dashboard.png": (12, 398, 459, 598),
    # Widget appearance + trigger cards (both checkboxes)
    "widget_settings.png": (12, 348, 459, 718),
    # Send toggle + status panel
    "whatsapp_settings.png": (12, 198, 459, 578),
}

# Tighter crop: one cart card for the visibility section
CART_NEXT_STEP_BOX = (12, 428, 459, 598)


def load_original(name: str) -> Image.Image:
    data = subprocess.check_output(
        ["git", "show", f"{ORIG_COMMIT}:static/img/landing/{name}"],
    )
    return Image.open(io.BytesIO(data))


def is_blankish(r: int, g: int, b: int, *, threshold: int = 248) -> bool:
    if r + g + b < 24:
        return True
    return r >= threshold and g >= threshold and b >= threshold


def trim_margins(im: Image.Image, *, pad: int = 6) -> Image.Image:
    rgb = im.convert("RGB")
    w, h = rgb.size
    pixels = rgb.load()
    top = h
    bottom = 0
    left = w
    right = 0
    for y in range(h):
        for x in range(0, w, 2):
            r, g, b = pixels[x, y]
            if not is_blankish(r, g, b):
                top = min(top, y)
                bottom = max(bottom, y)
                left = min(left, x)
                right = max(right, x)
    if bottom <= top:
        return im
    return im.crop(
        (
            max(0, left - pad),
            max(0, top - pad),
            min(w, right + pad + 1),
            min(h, bottom + pad + 1),
        )
    )


def process(box: tuple[int, int, int, int], src_name: str) -> Image.Image:
    im = load_original(src_name)
    cropped = trim_margins(im.crop(box))
    return cropped


def main() -> None:
    next_im = process(CART_NEXT_STEP_BOX, "carts_dashboard.png")
    next_im.save(LANDING / "cart-next-step.png", optimize=True, quality=92)
    print(f"cart-next-step.png -> {next_im.size}")

    for name, box in FEATURE_CROPS.items():
        out = process(box, name)
        out.save(LANDING / name, optimize=True, quality=92)
        print(f"{name} -> {out.size}")


if __name__ == "__main__":
    main()
