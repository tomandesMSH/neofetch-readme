#!/usr/bin/env python3
"""
Generates public/favicon.svg and public/favicon.ico: a terminal-style
lowercase "n" (JetBrains Mono, card accent color on the card background),
matching the rest of the project's look.

Usage: python tools/make_favicon.py
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = REPO_ROOT / "fonts" / "JetBrainsMono-Regular.ttf"
OUT_DIR = REPO_ROOT / "public"

BG = "#0d0d11"
FG = "#7dd3fc"
SIZES = [16, 32, 48, 64]


def render_png(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), BG)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(FONT_PATH), int(size * 0.82))
    glyph = "n"
    bbox = draw.textbbox((0, 0), glyph, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - w) / 2 - bbox[0]
    y = (size - h) / 2 - bbox[1]
    draw.text((x, y), glyph, font=font, fill=FG)
    return img


def write_svg():
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
<rect width="32" height="32" fill="{BG}"/>
<text x="16" y="23" font-family="'JetBrains Mono', ui-monospace, Consolas, monospace"
      font-size="22" font-weight="700" fill="{FG}" text-anchor="middle">n</text>
</svg>
'''
    (OUT_DIR / "favicon.svg").write_text(svg, encoding="utf-8")


def write_ico():
    base = render_png(64).convert("RGB")
    base.save(
        OUT_DIR / "favicon.ico",
        sizes=[(s, s) for s in SIZES],
    )


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_svg()
    write_ico()
    print(f"Wrote {OUT_DIR / 'favicon.svg'} and {OUT_DIR / 'favicon.ico'}")


if __name__ == "__main__":
    main()
