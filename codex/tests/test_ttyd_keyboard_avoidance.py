import unittest
from pathlib import Path


CODEX_DIR = Path(__file__).resolve().parents[1]
PATCH = CODEX_DIR / "ttyd-mobile-keys/ttyd-1.7.7-mobile-keys.patch"


class MobileKeyboardAvoidanceTests(unittest.TestCase):
    def test_touch_keyboard_avoidance_stays_in_canonical_ttyd_patch(self):
        patch = PATCH.read_text(encoding="utf-8")

        self.assertIn("diff --git a/html/src/components/app.tsx", patch)
        self.assertIn("MOBILE_KEYBOARD_THRESHOLD = 120", patch)
        self.assertIn("shouldUseMobileKeyboardAvoidance", patch)
        self.assertIn("window.top && window.top !== window && window.top.visualViewport", patch)
        self.assertIn("viewport.addEventListener('resize', schedule)", patch)
        self.assertIn("xterm-helper-textarea", patch)
        self.assertIn("host.style.height = `${Math.round(hostHeight)}px`", patch)
        self.assertIn("window.term?.fit()", patch)
        self.assertIn("window.term?.scrollToBottom()", patch)
        self.assertIn("this.resetKeyboardAvoidance(host)", patch)
        self.assertIn("maxTouchPoints", patch)
        self.assertIn("pointer: coarse", patch)
        self.assertIn("private keyboardCleanup: any;", patch)

        # dev.12 must not replace the accepted selection or keyboard button paths.
        self.assertIn("const selectionMode = this.xterm.toggleNativeSelection();", patch)
        self.assertIn("this.xterm.showKeyboard();", patch)
        self.assertIn("this.xterm.blur();", patch)


if __name__ == "__main__":
    unittest.main()
