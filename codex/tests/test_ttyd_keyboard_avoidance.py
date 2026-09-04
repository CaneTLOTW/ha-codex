import unittest
from pathlib import Path


CODEX_DIR = Path(__file__).resolve().parents[1]
PATCH = CODEX_DIR / "ttyd-mobile-keys/ttyd-1.7.7-mobile-keys.patch"


class MobileKeyboardAvoidanceTests(unittest.TestCase):
    def test_touch_keyboard_avoidance_stays_in_canonical_ttyd_patch(self):
        patch = PATCH.read_text(encoding="utf-8")

        # dev.12 keyboard avoidance must stay in the existing mobile Terminal path.
        self.assertNotIn("diff --git a/html/src/components/app.tsx", patch)
        self.assertNotIn("shouldUseMobileKeyboardAvoidance", patch)
        self.assertIn("private host: HTMLElement;", patch)
        self.assertIn("private installKeyboardAvoidance()", patch)
        self.assertIn("private updateKeyboardAvoidance()", patch)
        self.assertIn("private resetKeyboardAvoidance()", patch)
        self.assertIn("const topWindow = window.top as any;", patch)
        self.assertIn("topWindow.visualViewport", patch)
        self.assertIn("viewport.addEventListener('resize', this.keyboardResizeHandler)", patch)
        self.assertIn("this.keyboardViewport.removeEventListener('resize', this.keyboardResizeHandler)", patch)
        self.assertIn("active.classList.contains('xterm-helper-textarea')", patch)
        self.assertIn("shrink < 120", patch)
        self.assertIn("Math.max(160, Math.round(this.keyboardBaseHostHeight - shrink))", patch)
        self.assertIn("this.host.style.height = `${hostHeight}px`", patch)
        self.assertIn("this.host.style.height = '';", patch)
        self.assertIn("this.xterm.fit();", patch)
        self.assertIn("this.xterm.scrollToBottom();", patch)
        self.assertIn("public fit()", patch)
        self.assertIn("public scrollToBottom()", patch)

        # Accepted dev.11 mobile and desktop behavior must remain present.
        self.assertIn("const selectionMode = this.xterm.toggleNativeSelection();", patch)
        self.assertIn("this.xterm.showKeyboard();", patch)
        self.assertIn("this.xterm.blur();", patch)
        self.assertIn("shouldUseTouchControls", patch)
        self.assertIn("maxTouchPoints", patch)
        self.assertIn("pointer: coarse", patch)


if __name__ == "__main__":
    unittest.main()
