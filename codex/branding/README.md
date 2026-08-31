# ha-codex branding

This directory contains the editable source artwork for the Home Assistant App presentation assets.

## Files

- `icon.svg` — square master for `../icon.png` (rendered at 128×128).
- `logo.svg` — horizontal master for `../logo.png` (rendered at 250×100).
- `render.sh` — reproducible rasterization using `rsvg-convert`.

## Visual direction

The mark combines a generic terminal prompt with a small connected-node automation motif. It is original artwork for this repository and deliberately does **not** reproduce the OpenAI knot mark, the Home Assistant house/circuit logo, or other protected third-party artwork.

The dark slate surface, white prompt and teal automation nodes are intended to remain readable in both light and dark Home Assistant themes and at small App Store/card sizes.

## License / attribution

The artwork in this directory was created specifically for `CaneTLOTW/ha-codex` and is distributed under the same repository license. No third-party visual asset is embedded and no attribution is required.

## Rendering

On a system with `librsvg2-bin` installed:

```bash
./codex/branding/render.sh
```

The script writes deterministic-size PNGs to `codex/icon.png` and `codex/logo.png` and strips ancillary metadata through the renderer output.
