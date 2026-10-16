"""Build the cover photo: download, crop to a portrait panel and grade to a plum -> gold tritone.

    uv run --with pillow --with requests --with numpy python powerbi/_build/make_cover.py

Source: "Apothecary bottles" by France3470, Sherbrooke Village Museum, Wikimedia Commons, public domain.
https://commons.wikimedia.org/wiki/File:Apothecarybottles.jpg
"""

from __future__ import annotations

import io
import pathlib

import numpy as np
import requests
from PIL import Image

SOURCE = "https://commons.wikimedia.org/wiki/Special:FilePath/Apothecarybottles.jpg?width=1920"
OUT = pathlib.Path(__file__).resolve().parent / "assets" / "cover.jpg"
PANEL = (520, 720)  # cover photo panel in report pixels; saved at 2x for sharpness
CROP = (1100, 75, 1920, 1211)  # left, top, right, bottom on the 1920px image: the "Ferrogen" bottle

# Tritone stops (luminance 0..1 -> colour): aubergine shadows, plum mids, warm gold-ivory highlights
STOPS = [(0.00, (16, 9, 25)), (0.50, (72, 44, 100)), (0.84, (172, 145, 92)), (1.00, (238, 228, 208))]


def tritone(img: Image.Image) -> Image.Image:
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32) / 255
    lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    lum = np.clip((lum - 0.04) / 0.92, 0, 1) ** 0.95  # gentle contrast stretch
    xs = [s[0] for s in STOPS]
    out = np.stack([np.interp(lum, xs, [s[1][c] for s in STOPS]) for c in range(3)], axis=-1)
    # soft vignette: darken the edges so text-side and corners recede
    h, w = lum.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    out *= np.clip(1.08 - 0.32 * r ** 2, 0.55, 1.0)[..., None]
    return Image.fromarray(out.astype(np.uint8))


def main() -> None:
    resp = requests.get(SOURCE, headers={"User-Agent": "rx-analytics-pipeline portfolio"}, timeout=60)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content))
    img = img.crop(CROP).resize((PANEL[0] * 2, PANEL[1] * 2), Image.LANCZOS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tritone(img).save(OUT, quality=88, optimize=True, progressive=True)
    print("cover written:", OUT, OUT.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
