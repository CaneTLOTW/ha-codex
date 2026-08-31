#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
branding_dir="$repo_root/codex/branding"

command -v rsvg-convert >/dev/null 2>&1 || {
  echo "rsvg-convert is required (package: librsvg2-bin)" >&2
  exit 1
}

rsvg-convert --width 128 --height 128 --format png \
  --output "$repo_root/codex/icon.png" \
  "$branding_dir/icon.svg"

rsvg-convert --width 250 --height 100 --format png \
  --output "$repo_root/codex/logo.png" \
  "$branding_dir/logo.svg"

python3 - "$repo_root/codex/icon.png" "$repo_root/codex/logo.png" <<'PY'
import struct
import sys

expected = {
    sys.argv[1]: (128, 128),
    sys.argv[2]: (250, 100),
}
for path, dimensions in expected.items():
    with open(path, "rb") as f:
        signature = f.read(8)
        if signature != b"\x89PNG\r\n\x1a\n":
            raise SystemExit(f"{path}: not a PNG")
        length = struct.unpack(">I", f.read(4))[0]
        chunk = f.read(4)
        if chunk != b"IHDR" or length != 13:
            raise SystemExit(f"{path}: invalid PNG IHDR")
        width, height = struct.unpack(">II", f.read(8))
    if (width, height) != dimensions:
        raise SystemExit(f"{path}: expected {dimensions}, got {(width, height)}")
    print(f"{path}: {width}x{height}")
PY
