import unittest
from pathlib import Path


CODEX_DIR = Path(__file__).resolve().parents[1]
DOCKERFILE = CODEX_DIR / "Dockerfile"
VIEWPORT_PATCH = CODEX_DIR / "ttyd-mobile-keys/ttyd-1.7.7-ios-viewport.patch"


class IOSViewportTests(unittest.TestCase):
    def test_ios_viewport_patch_is_built_into_ttyd(self):
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        patch = VIEWPORT_PATCH.read_text(encoding="utf-8")

        self.assertIn("ttyd-1.7.7-ios-viewport.patch", dockerfile)
        self.assertIn("/tmp/ttyd-ios-viewport.patch", dockerfile)
        self.assertIn('name="viewport"', patch)
        self.assertIn("width=device-width", patch)
        self.assertIn("viewport-fit=cover", patch)


if __name__ == "__main__":
    unittest.main()
