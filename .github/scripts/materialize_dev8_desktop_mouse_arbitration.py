from pathlib import Path
import subprocess


ROOT = Path.cwd()
TTYD = Path("/tmp/ttyd-dev8")
PATCH = ROOT / "codex/ttyd-mobile-keys/ttyd-1.7.7-mobile-keys.patch"
SESSION = ROOT / "codex/rootfs/usr/local/bin/codex-session"
TESTS = ROOT / "codex/tests/test_modernization.py"
README = ROOT / "codex/ttyd-mobile-keys/README.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, got {count}")
    return text.replace(old, new, 1)


# Apply the current single canonical patch to a clean ttyd 1.7.7 tree, then
# modify the resulting source. The canonical patch is regenerated from that
# clean tree at the end; no patch-on-patch chain is created.
subprocess.run(["git", "-C", str(TTYD), "apply", str(PATCH)], check=True)

xterm = TTYD / "html/src/components/terminal/xterm/index.ts"
text = xterm.read_text(encoding="utf-8")
text = replace_once(
    text,
    "    private terminal: Terminal;\n",
    "    private terminal: Terminal;\n    private desktopSelectionActive = false;\n",
    "desktop selection field",
)
text = replace_once(
    text,
    "        terminal.open(parent);\n        this.installNativeTouchSelection();\n        fitAddon.fit();\n",
    "        terminal.open(parent);\n        this.installNativeTouchSelection();\n        this.installDesktopSelectionPreference();\n        fitAddon.fit();\n",
    "desktop selection installer call",
)
method_marker = "    private installNativeTouchSelection() {\n"
method = r'''    /**
     * Backport the mouse arbitration added upstream as xterm's
     * `mouseEventsRequireAlt` option. ttyd 1.7.7 is pinned to xterm 5.x, so we
     * keep that stable stack and only make plain desktop left-drag look like
     * xterm's existing forced-selection gesture. Wheel events are untouched and
     * continue to the application/tmux. Holding Alt leaves application mouse
     * interaction untouched as well.
     */
    private installDesktopSelectionPreference() {
        const element = this.terminal.element;
        if (!element) return;

        const navigator = window.navigator as Navigator & {
            maxTouchPoints?: number;
            userAgentData?: { mobile?: boolean };
        };
        const touchPoints = navigator.maxTouchPoints ?? 0;
        const mobilePlatform =
            /Android|iPhone|iPad|iPod/i.test(navigator.userAgent || '') ||
            (navigator.platform === 'MacIntel' && touchPoints > 1) ||
            navigator.userAgentData?.mobile === true;
        const coarsePrimaryPointer = window.matchMedia?.('(hover: none) and (pointer: coarse)').matches === true;
        if (touchPoints > 0 && (mobilePlatform || coarsePrimaryPointer)) return;

        const forceSelectionModifier = (event: MouseEvent) => {
            if (event.altKey || event.shiftKey) return;
            try {
                Object.defineProperty(event, 'shiftKey', {
                    configurable: true,
                    value: true,
                });
            } catch {
                // Keep upstream behavior if the browser refuses event decoration.
            }
        };

        const onMouseDown = (event: Event) => {
            const mouseEvent = event as MouseEvent;
            if (mouseEvent.button !== 0 || mouseEvent.altKey) return;
            this.desktopSelectionActive = true;
            forceSelectionModifier(mouseEvent);
        };
        const onMouseMove = (event: Event) => {
            if (!this.desktopSelectionActive) return;
            forceSelectionModifier(event as MouseEvent);
        };
        const onMouseUp = (event: Event) => {
            if (!this.desktopSelectionActive) return;
            forceSelectionModifier(event as MouseEvent);
            this.desktopSelectionActive = false;
        };
        const onBlur = () => {
            this.desktopSelectionActive = false;
        };

        element.addEventListener('mousedown', onMouseDown, true);
        document.addEventListener('mousemove', onMouseMove, true);
        document.addEventListener('mouseup', onMouseUp, true);
        window.addEventListener('blur', onBlur, true);
        this.register(
            toDisposable(() => {
                element.removeEventListener('mousedown', onMouseDown, true);
                document.removeEventListener('mousemove', onMouseMove, true);
                document.removeEventListener('mouseup', onMouseUp, true);
                window.removeEventListener('blur', onBlur, true);
            })
        );
    }

'''
text = replace_once(text, method_marker, method + method_marker, "native touch selection marker")
xterm.write_text(text, encoding="utf-8")

# Re-enable tmux mouse reporting for persistent sessions so the wheel once again
# drives tmux history/copy-mode. The desktop ttyd adapter above keeps plain drag
# in xterm selection, matching the intent of upstream mouseEventsRequireAlt.
session = SESSION.read_text(encoding="utf-8")
old = '''  # Browser terminals need xterm/ttyd to own mouse selection and scrollback.
  # Match the Home Assistant Advanced SSH & Web Terminal behavior: tmux
  # persistence remains enabled, but tmux mouse reporting is disabled under ttyd.
  if ! "${tmux_env[@]}" tmux -S "$tmux_socket" set-option -g mouse off; then
    echo "[WARN] Unable to disable tmux mouse mode for the ttyd session." >&2
  fi
'''
new = '''  # Keep tmux wheel/history support. The ttyd frontend separately prefers
  # xterm's forced-selection path for plain desktop left-drag, while Alt can
  # still be used for application mouse interaction.
  if ! "${tmux_env[@]}" tmux -S "$tmux_socket" set-option -g mouse on; then
    echo "[WARN] Unable to enable tmux mouse mode for the ttyd session." >&2
  fi
'''
session = replace_once(session, old, new, "persistent tmux mouse block")
SESSION.write_text(session, encoding="utf-8")

# Update the maintained regression contract.
tests = TESTS.read_text(encoding="utf-8")
old_test = '''    def test_persistent_ttyd_session_disables_tmux_mouse(self):
        session_text = SESSION.read_text(encoding="utf-8")
        patch = MOBILE_PATCH.read_text(encoding="utf-8")
        self.assertIn('tmux -S "$tmux_socket" set-option -g mouse off', session_text)
        self.assertIn('tmux -S "$tmux_socket" attach-session -t codex', session_text)
        self.assertNotIn("installDesktopShiftSelectionScroll", patch)
        self.assertNotIn("desktopSelectionAnchor", patch)

'''
new_test = '''    def test_persistent_ttyd_session_keeps_wheel_and_prefers_desktop_selection(self):
        session_text = SESSION.read_text(encoding="utf-8")
        patch = MOBILE_PATCH.read_text(encoding="utf-8")
        self.assertIn('tmux -S "$tmux_socket" set-option -g mouse on', session_text)
        self.assertIn('tmux -S "$tmux_socket" attach-session -t codex', session_text)
        self.assertIn("installDesktopSelectionPreference", patch)
        self.assertIn("desktopSelectionActive", patch)
        self.assertIn("Object.defineProperty(event, 'shiftKey'", patch)
        self.assertIn("mouseEvent.button !== 0 || mouseEvent.altKey", patch)
        self.assertIn("window.matchMedia?.('(hover: none) and (pointer: coarse)')", patch)
        self.assertNotIn("installDesktopShiftSelectionScroll", patch)
        self.assertNotIn("desktopSelectionAnchor", patch)

'''
tests = replace_once(tests, old_test, new_test, "dev.7 regression test")
TESTS.write_text(tests, encoding="utf-8")

# Document the experiment accurately: terminal-overrides was already present;
# dev.8 changes mouse arbitration only.
readme = README.read_text(encoding="utf-8")
anchor = "Desktop selection and normal browser/terminal clipboard behavior remain native\nttyd/xterm behavior and are deliberately kept separate from the mobile controls.\n"
replacement = '''Desktop selection remains separate from the mobile controls. On desktop, persistent
tmux sessions keep mouse reporting enabled so wheel scrolling/history continues to
work. Because ttyd 1.7.7 is pinned to xterm 5.x, the frontend backports the behavior
of xterm's newer `mouseEventsRequireAlt` arbitration at the integration layer: plain
left-drag is decorated as xterm's existing forced-selection gesture, wheel events are
left untouched for tmux, and holding Alt leaves application mouse interaction alone.
This does not add a second selection implementation or a second ttyd patch.
'''
readme = replace_once(readme, anchor, replacement, "desktop README paragraph")
README.write_text(readme, encoding="utf-8")
