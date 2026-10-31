#!/usr/bin/env python3
"""
Records the live card in headless Chromium so the dissolve animation can
be eyeballed for smoothness/jank before pushing - GitHub renders SMIL
through a real browser (via its image proxy), so this is the closest
local approximation.

Usage:
    vercel dev &                      # in another terminal
    python tools/verify_animation.py  # defaults to http://localhost:3000

    python tools/verify_animation.py --url https://<deployment>.vercel.app --duration 46
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUERY = (
    "user=tomas&host=github&os=Arch+Linux&school=FIT+CTU&city=Prague"
    "&frontend=React%2C+TypeScript&backend=Node.js%2C+PHP&mail=tomas%40example.com"
    "&projects=neofetch-readme"
)


def detect_duration(svg_url: str) -> float | None:
    try:
        with urllib.request.urlopen(svg_url, timeout=15) as resp:
            svg = resp.read().decode("utf-8")
    except Exception as e:
        print(f"Could not fetch SVG to auto-detect duration: {e}", file=sys.stderr)
        return None
    m = re.search(r'dur="([\d.]+)s"', svg)
    return float(m.group(1)) if m else None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://localhost:3000", help="Base URL serving api/svg.js (vercel dev, or a real deployment).")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--duration", type=float, default=None, help="Seconds to record; default: auto-detect one full loop from the SVG + 2s buffer.")
    parser.add_argument("--out-dir", default=str(REPO_ROOT / ".verify"))
    args = parser.parse_args()

    svg_url = f"{args.url.rstrip('/')}/api/svg?{args.query}"
    print(f"Target: {svg_url}")

    duration = args.duration or detect_duration(svg_url)
    if duration is None:
        print("Falling back to 46s (default 8-icon cycle).")
        duration = 46.0
    record_seconds = duration + 2.0
    print(f"Recording {record_seconds:.1f}s (one full loop + buffer)...")

    from playwright.sync_api import sync_playwright

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    html_path = out_dir / "harness.html"
    html_path.write_text(
        f'<!doctype html><html><body style="margin:0;background:#1e1e24">'
        f'<img src="{svg_url}" width="1200" height="540"/>'
        f"</body></html>",
        encoding="utf-8",
    )

    console_errors: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1200, "height": 540},
            record_video_dir=str(out_dir),
            record_video_size={"width": 1200, "height": 540},
        )
        page = context.new_page()
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        page.goto(html_path.as_uri())
        page.wait_for_timeout(int(record_seconds * 1000))

        video_path = page.video.path() if page.video else None
        context.close()
        browser.close()

    if console_errors:
        print("\nConsole/page errors detected:")
        for e in console_errors:
            print(" -", e)
    else:
        print("\nNo console/page errors.")

    if video_path:
        final_path = out_dir / "animation_check.webm"
        Path(video_path).replace(final_path)
        print(f"\nSaved recording: {final_path}")
        print("Watch it before pushing - look for: no hard cuts between logos,")
        print("no rotation/sliding, smooth crossfade, name label changes in sync.")
    else:
        print("No video was produced.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
