import unittest
from pathlib import Path


CODEX_DIR = Path(__file__).resolve().parents[1]
DOCKERFILE = CODEX_DIR / "Dockerfile"
MOBILE_PATCH = CODEX_DIR / "ttyd-mobile-keys/ttyd-1.7.7-mobile-keys.patch"


class IOSViewportTests(unittest.TestCase):
    def test_ios_viewport_is_part_of_canonical_ttyd_patch(self):
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        patch = MOBILE_PATCH.read_text(encoding="utf-8")

        self.assertIn("ttyd-1.7.7-mobile-keys.patch", dockerfile)
        self.assertNotIn("ios-viewport.patch", dockerfile)
        self.assertIn('name="viewport"', patch)
        self.assertIn("width=device-width", patch)
        self.assertIn("viewport-fit=cover", patch)


if __name__ == "__main__":
    unittest.main()
