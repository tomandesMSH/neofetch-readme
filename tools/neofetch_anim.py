#!/usr/bin/env python3
"""
Generates generated/icon-frames.json: a manifest of 14-frame ASCII "smoke
dissolve" PNG sequences for a curated set of Simple Icons logos.

The manifest is consumed at request time by api/svg.js (no runtime image
rendering happens on Vercel - this script is the only place that touches
fonts, Simple Icons artwork, or a browser).

Pipeline per icon:
  1. Fetch the icon's monochrome SVG from a pinned Simple Icons CDN release.
  2. Rasterize it (via a headless Chromium tab) and downsample to a
     56x28 coverage grid.
  3. Map coverage -> ASCII density ramp characters.
  4. Render frame 0 (fully formed logo) with Pillow + JetBrains Mono.
  5. Derive frames 1..13: characters thin (lighter ramp glyph), fade
     (alpha) and rise (upward offset), each on a per-character randomized
     (but deterministic) start time, so the dissolve looks like smoke
     rather than a uniform wipe. Frame 13 is mostly - but not fully -
     empty, leaving faint scattered specks.
  6. Encode all frames as base64 PNG data URIs.

Frame sequences are reused in both directions by the SVG builder: played
forward they dissolve a logo away, played backward (13 -> 0) they
assemble the *next* logo out of the scattered characters, which is why
every icon only needs its own single 14-frame set.

Usage:
    python tools/neofetch_anim.py
    python tools/neofetch_anim.py --icons javascript,typescript,react
    python tools/neofetch_anim.py --out generated/icon-frames.json --cell 8
"""

from __future__ import annotations

import argparse
import base64
import colorsys
import hashlib
import io
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "generated" / "icon-frames.json"
DEFAULT_FONT = REPO_ROOT / "fonts" / "JetBrainsMono-Regular.ttf"
CACHE_DIR = REPO_ROOT / ".cache" / "simple-icons"

SIMPLE_ICONS_VERSION = "13.21.0"
SIMPLE_ICONS_BASE = f"https://cdn.jsdelivr.net/npm/simple-icons@{SIMPLE_ICONS_VERSION}/icons"

COLS = 56
ROWS = 28
FRAME_COUNT = 14
RAMP = " .:-=+*#%@"
FADE_WIDTH = 0.38
MAX_START = 0.8
MAX_RISE_PX_FRAC = 0.9  # fraction of one cell height
MIN_LUMINANCE = 95.0  # keep logos visible against the #0d0d11 card background

# slug -> (display title, brand hex) resolved once from Simple Icons'
# _data/simple-icons.json for the pinned version above. Hardcoded (rather
# than re-deriving the slug<->title mapping at run time) so the generator
# has no dependency on the large upstream metadata file.
ICON_CATALOG: dict[str, tuple[str, str]] = {
    "javascript": ("JavaScript", "F7DF1E"),
    "typescript": ("TypeScript", "3178C6"),
    "react": ("React", "61DAFB"),
    "vuedotjs": ("Vue.js", "4FC08D"),
    "angular": ("Angular", "0F0F11"),
    "svelte": ("Svelte", "FF3E00"),
    "nodedotjs": ("Node.js", "5FA04E"),
    "php": ("PHP", "777BB4"),
    "python": ("Python", "3776AB"),
    "openjdk": ("Java", "000000"),
    "kotlin": ("Kotlin", "7F52FF"),
    "swift": ("Swift", "F05138"),
    "go": ("Go", "00ADD8"),
    "rust": ("Rust", "000000"),
    "cplusplus": ("C++", "00599C"),
    "html5": ("HTML5", "E34F26"),
    "css3": ("CSS3", "1572B6"),
    "tailwindcss": ("Tailwind CSS", "06B6D4"),
    "docker": ("Docker", "2496ED"),
    "kubernetes": ("Kubernetes", "326CE5"),
    "git": ("Git", "F05032"),
    "github": ("GitHub", "181717"),
    "linux": ("Linux", "FCC624"),
    "apple": ("Apple", "000000"),
    "postgresql": ("PostgreSQL", "4169E1"),
    "mysql": ("MySQL", "4479A1"),
    "mongodb": ("MongoDB", "47A248"),
    "redis": ("Redis", "FF4438"),
    "graphql": ("GraphQL", "E10098"),
    "amazonwebservices": ("AWS", "232F3E"),
    "googlecloud": ("Google Cloud", "4285F4"),
    "vercel": ("Vercel", "000000"),
    "dotnet": (".NET", "512BD4"),
    "lua": ("Lua", "2C2D72"),
    "bootstrap": ("Bootstrap", "7952B3"),
    "blender": ("Blender", "E87D0D"),
}

DEFAULT_ICONS = [
    "javascript", "typescript", "react", "nodedotjs",
    "php", "python", "git", "linux",
]


def fetch_icon_svg(slug: str) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{slug}.svg"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")
    url = f"{SIMPLE_ICONS_BASE}/{slug}.svg"
    with urllib.request.urlopen(url, timeout=20) as resp:
        svg = resp.read().decode("utf-8")
    cache_file.write_text(svg, encoding="utf-8")
    return svg


def prepare_svg_for_render(svg: str, size_px: int) -> str:
    """Force an explicit size + solid black fill so the rasterized mask is
    unambiguous (brand color is applied later, during ASCII rendering)."""
    svg = re.sub(r"\swidth=\"[^\"]*\"", "", svg, count=1)
    svg = re.sub(r"\sheight=\"[^\"]*\"", "", svg, count=1)
    svg = svg.replace(
        "<svg ", f'<svg width="{size_px}" height="{size_px}" fill="#000000" ', 1
    )
    return svg


def rasterize_coverage_grid(page, svg: str, render_px: int) -> list[list[float]]:
    """Render the icon with a headless browser tab and return a ROWS x COLS
    grid of 0..1 coverage values (box-downsampled alpha)."""
    html = (
        "<html><head><style>"
        "html,body{margin:0;padding:0;background:transparent;}"
        "</style></head><body>"
        f"{prepare_svg_for_render(svg, render_px)}"
        "</body></html>"
    )
    page.set_viewport_size({"width": render_px, "height": render_px})
    page.set_content(html)
    png_bytes = page.screenshot(omit_background=True)
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    # Squash the square render directly onto the (wide) character grid: a
    # BOX downsample from a render_px^2 square to COLS x ROWS both
    # resamples for anti-aliased coverage *and* pre-compensates for the
    # ~2:1 tall aspect of monospace glyph cells.
    small = img.resize((COLS, ROWS), resample=Image.Resampling.BOX)
    alpha = small.getchannel("A")
    grid = [
        [alpha.getpixel((c, r)) / 255.0 for c in range(COLS)]
        for r in range(ROWS)
    ]
    return grid


def ensure_visible(hex_color: str) -> tuple[int, int, int]:
    """Lift near-black brand colors so they read against the #0d0d11 card."""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    if lum >= MIN_LUMINANCE:
        return r, g, b
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)[0], None, None
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    target_l = max(l, MIN_LUMINANCE / 255 + 0.12)
    nr, ng, nb = colorsys.hls_to_rgb(h, target_l, max(s, 0.35))
    return int(nr * 255), int(ng * 255), int(nb * 255)


def char_seed(slug: str, r: int, c: int) -> float:
    digest = hashlib.sha1(f"{slug}:{r}:{c}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def build_cells(grid: list[list[float]]):
    """Map the coverage grid to (row, col, ramp_index, coverage) cells,
    skipping blanks."""
    cells = []
    for r in range(ROWS):
        for c in range(COLS):
            coverage = grid[r][c]
            idx = round(coverage * (len(RAMP) - 1))
            if idx <= 0:
                continue
            cells.append((r, c, idx, coverage))
    return cells


def render_frames(slug: str, cells, color: tuple[int, int, int], font_path: Path, cell_px: int):
    font = ImageFont.truetype(str(font_path), int(cell_px * 1.35))
    cell_w = max(1, round(font.getlength("M")))
    cell_h = int(cell_px * 1.35 * 1.05)

    canvas_w = COLS * cell_w
    canvas_h = ROWS * cell_h
    r_, g_, b_ = color

    frames = []
    for f in range(FRAME_COUNT):
        p = f / (FRAME_COUNT - 1)
        img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for (row, col, idx, coverage) in cells:
            start = char_seed(slug, row, col) * MAX_START
            local = max(0.0, min(1.0, (p - start) / FADE_WIDTH))
            fade_alpha = 1.0 - local
            if fade_alpha <= 0.015:
                continue

            thin_steps = round(local * 3)
            glyph_idx = max(1, idx - thin_steps)
            glyph = RAMP[glyph_idx]

            base_alpha = 0.35 + 0.65 * coverage
            alpha = max(0.0, min(1.0, base_alpha * fade_alpha))
            # Quantize alpha and round the rise to whole pixels: PNG
            # compresses this *dramatically* better than the continuous
            # per-character gradients a float alpha/offset would produce,
            # with no visible loss at card display size.
            alpha_q = (int(alpha * 255) // 10) * 10
            if alpha_q <= 0:
                continue
            rise = round(local * MAX_RISE_PX_FRAC * cell_h)

            x = col * cell_w
            y = row * cell_h - rise
            draw.text((x, y), glyph, font=font, fill=(r_, g_, b_, alpha_q))
        img = img.quantize(colors=48, method=Image.Quantize.FASTOCTREE)
        frames.append(img)
    return frames


def frame_to_data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True, compress_level=9)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def generate_icon(page, slug: str, font_path: Path, cell_px: int, render_px: int):
    if slug not in ICON_CATALOG:
        raise ValueError(f"Unknown icon slug: {slug!r}. Add it to ICON_CATALOG first.")
    title, hex_color = ICON_CATALOG[slug]
    svg = fetch_icon_svg(slug)
    grid = rasterize_coverage_grid(page, svg, render_px)
    cells = build_cells(grid)
    color = ensure_visible(hex_color)
    frames = render_frames(slug, cells, color, font_path, cell_px)
    data_uris = [frame_to_data_uri(f) for f in frames]
    size = frames[0].size
    return {
        "title": title,
        "hex": f"#{hex_color}",
        "width": size[0],
        "height": size[1],
        "frames": data_uris,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--icons",
        default="all",
        help="Comma-separated slugs to (re)generate, or 'all' for the full catalog "
             "(default: all - needed so the live API can serve any of them).",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--font", default=str(DEFAULT_FONT))
    parser.add_argument("--cell", type=int, default=7, help="Base font-size unit in px (controls output size).")
    parser.add_argument("--render-px", type=int, default=560, help="Square render resolution used for AA sampling.")
    args = parser.parse_args()

    if args.icons == "all":
        slugs = list(ICON_CATALOG.keys())
    else:
        slugs = [s.strip() for s in args.icons.split(",") if s.strip()]

    font_path = Path(args.font)
    if not font_path.exists():
        print(f"Font not found: {font_path}", file=sys.stderr)
        sys.exit(1)

    from playwright.sync_api import sync_playwright

    manifest: dict[str, dict] = {}
    out_path = Path(args.out)
    if out_path.exists():
        try:
            manifest = json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        for i, slug in enumerate(slugs, 1):
            print(f"[{i}/{len(slugs)}] {slug} ...", end=" ", flush=True)
            entry = generate_icon(page, slug, font_path, args.cell, args.render_px)
            manifest[slug] = entry
            approx_kb = sum(len(u) for u in entry["frames"]) // 1024
            print(f"ok ({approx_kb} KB, {entry['width']}x{entry['height']})")
        browser.close()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=0, separators=(",", ":")), encoding="utf-8")
    total_kb = out_path.stat().st_size // 1024
    print(f"\nWrote {out_path} ({total_kb} KB, {len(manifest)} icons)")
    print("Preview locally with: node tools/preview.js  (renders via the same lib/buildSvg.js used in production)")


if __name__ == "__main__":
    main()
