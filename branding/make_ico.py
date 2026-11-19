#!/usr/bin/env python3
"""Builds branding/generated/bastion.ico from the per-size PNGs render.js made.

Each ICO frame uses the PNG rendered at that exact size (sharper than
downscaling one big image).
"""
from pathlib import Path

from PIL import Image

GEN = Path(__file__).resolve().parent / 'generated'
ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]


def main():
    frames = [Image.open(GEN / f'logo_{s}.png').convert('RGBA') for s in ICO_SIZES]
    largest = frames[-1]
    largest.save(GEN / 'bastion.ico', format='ICO',
                 sizes=[(s, s) for s in ICO_SIZES], append_images=frames[:-1])
    print('Wrote', GEN / 'bastion.ico')


if __name__ == '__main__':
    main()
