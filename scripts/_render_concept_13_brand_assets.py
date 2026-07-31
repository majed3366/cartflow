"""Render Concept 13 Frame Open mark + favicons for production landing."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "static" / "img" / "brand"
NAVY = (8, 32, 72, 255)


def draw_frame_open(size: int, ink: tuple[int, int, int, int] = NAVY, bg=None) -> Image.Image:
    img = Image.new("RGBA", (size, size), bg if bg is not None else (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Scale from 96 viewBox: stroke 12, frame 16..80, opening 68..88 x 40..56
    s = size / 96.0
    stroke = max(2, round(12 * s))
    x0, y0 = round(16 * s), round(16 * s)
    x1, y1 = round(80 * s), round(80 * s)
    # Outer frame
    draw.rectangle([x0, y0, x1, y1], outline=ink, width=stroke)
    # Opening cut on the right (erase / cover with transparent or bg)
    ox0 = round(66 * s)
    oy0 = round(39 * s)
    ox1 = size
    oy1 = round(57 * s)
    if bg is None:
        clear = Image.new("RGBA", (max(1, ox1 - ox0), max(1, oy1 - oy0)), (0, 0, 0, 0))
        img.paste(clear, (ox0, oy0))
    else:
        draw.rectangle([ox0, oy0, ox1, oy1], fill=bg)
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    draw_frame_open(128).save(OUT / "concept_13_mark.png")
    draw_frame_open(32).save(OUT / "favicon-32.png")
    draw_frame_open(64).save(OUT / "favicon-64.png")
    # Apple touch: solid soft page field behind mark
    page = (245, 247, 251, 255)
    touch = Image.new("RGBA", (180, 180), page)
    mark = draw_frame_open(140, bg=page)
    touch.paste(mark, ((180 - 140) // 2, (180 - 140) // 2), mark)
    touch.save(OUT / "concept_13_app_mark.png")
    print("wrote", OUT / "concept_13_mark.png")
    print("wrote", OUT / "favicon-32.png")
    print("wrote", OUT / "favicon-64.png")
    print("wrote", OUT / "concept_13_app_mark.png")


if __name__ == "__main__":
    main()
