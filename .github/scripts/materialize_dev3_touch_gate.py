from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


root = Path("/tmp/ttyd-1.7.7")
terminal = root / "html/src/components/terminal/index.tsx"

marker = "];\n\nexport class Terminal extends Component<Props, State> {"
detector = r'''];

function shouldUseTouchControls(targetWindow: Window): boolean {
    const navigator = targetWindow.navigator as Navigator & {
        maxTouchPoints?: number;
        userAgentData?: { mobile?: boolean };
    };
    const touchPoints = navigator.maxTouchPoints ?? 0;
    if (touchPoints <= 0) return false;

    const mobilePlatform =
        /Android|iPhone|iPad|iPod/i.test(navigator.userAgent || '') ||
        (navigator.platform === 'MacIntel' && touchPoints > 1) ||
        navigator.userAgentData?.mobile === true;
    const coarsePrimaryPointer = targetWindow.matchMedia?.('(hover: none) and (pointer: coarse)').matches === true;

    return mobilePlatform || coarsePrimaryPointer;
}

export class Terminal extends Component<Props, State> {'''
replace_once(terminal, marker, detector, "insert touch detector")
replace_once(
    terminal,
    "    private xterm: Xterm;\n    private touchStartY?: number;\n",
    "    private xterm: Xterm;\n    private touchStartY?: number;\n    private readonly touchControls = shouldUseTouchControls(window);\n",
    "add touchControls flag",
)

old_render = r'''            <div id={id}>
                <div
                    class="terminal-viewport"
                    ref={c => (this.container = c as HTMLElement)}
                    onTouchStart={this.startTouchScroll}
                    onTouchMove={this.continueTouchScroll}
                    onTouchEnd={this.finishTouchScroll}
                    onTouchCancel={this.cancelTouchScroll}
                />
                <nav class="mobile-keys" aria-label="Terminal special keys">
                    {mobileKeys.slice(2, 7).map(this.renderMobileKey)}
                    {this.renderSelectionMode(selectionMode)}
                    {mobileKeys.slice(7, 8).map(this.renderMobileKey)}
                    {this.renderKeyboardShow()}
                    {mobileKeys.slice(0, 2).map(this.renderMobileKey)}
                    {this.renderModifier('Ctrl', ctrl, 'ctrl')}
                    {this.renderModifier('Alt', alt, 'alt')}
                    {this.renderModifier('Shift', shift, 'shift')}
                    {this.renderShiftLock(shiftLock)}
                    {mobileKeys.slice(8, 9).map(this.renderMobileKey)}
                    {this.renderKeyboardDismiss()}
                </nav>'''
new_render = r'''            <div
                id={id}
                class={this.touchControls ? 'ttyd-touch-controls' : undefined}
                ref={c => {
                    if (!this.touchControls) this.container = c as HTMLElement;
                }}
            >
                {this.touchControls && (
                    <div
                        class="terminal-viewport"
                        ref={c => (this.container = c as HTMLElement)}
                        onTouchStart={this.startTouchScroll}
                        onTouchMove={this.continueTouchScroll}
                        onTouchEnd={this.finishTouchScroll}
                        onTouchCancel={this.cancelTouchScroll}
                    />
                )}
                {this.touchControls && (
                    <nav class="mobile-keys" aria-label="Terminal special keys">
                        {mobileKeys.slice(2, 7).map(this.renderMobileKey)}
                        {this.renderSelectionMode(selectionMode)}
                        {mobileKeys.slice(7, 8).map(this.renderMobileKey)}
                        {this.renderKeyboardShow()}
                        {mobileKeys.slice(0, 2).map(this.renderMobileKey)}
                        {this.renderModifier('Ctrl', ctrl, 'ctrl')}
                        {this.renderModifier('Alt', alt, 'alt')}
                        {this.renderModifier('Shift', shift, 'shift')}
                        {this.renderShiftLock(shiftLock)}
                        {mobileKeys.slice(8, 9).map(this.renderMobileKey)}
                        {this.renderKeyboardDismiss()}
                    </nav>
                )}'''
replace_once(terminal, old_render, new_render, "gate mobile render tree")

xterm = root / "html/src/components/terminal/xterm/index.ts"
old_detector = r'''function shouldUseNativeTouchSelection(targetWindow: Window): boolean {
    const navigator = targetWindow.navigator as Navigator & { maxTouchPoints?: number };
    const appleTouchDevice =
        /iPad|iPhone|iPod/.test(navigator.userAgent) ||
        (navigator.platform === 'MacIntel' && (navigator.maxTouchPoints ?? 0) > 1);
    const coarsePointer = targetWindow.matchMedia?.('(hover: none) and (pointer: coarse)').matches ?? true;
    return appleTouchDevice && coarsePointer;
}'''
new_detector = r'''function shouldUseNativeTouchSelection(targetWindow: Window): boolean {
    const navigator = targetWindow.navigator as Navigator & {
        maxTouchPoints?: number;
        userAgentData?: { mobile?: boolean };
    };
    const touchPoints = navigator.maxTouchPoints ?? 0;
    if (touchPoints <= 0) return false;

    const mobilePlatform =
        /Android|iPhone|iPad|iPod/i.test(navigator.userAgent || '') ||
        (navigator.platform === 'MacIntel' && touchPoints > 1) ||
        navigator.userAgentData?.mobile === true;
    const coarsePrimaryPointer = targetWindow.matchMedia?.('(hover: none) and (pointer: coarse)').matches === true;

    return mobilePlatform || coarsePrimaryPointer;
}'''
replace_once(xterm, old_detector, new_detector, "generalize native touch detector")
replace_once(
    xterm,
    "        if (!window.matchMedia('(hover: none), (pointer: coarse), (max-width: 768px)').matches) {\n            this.terminal?.focus();\n        }",
    "        if (!shouldUseNativeTouchSelection(window)) {\n            this.terminal?.focus();\n        }",
    "remove viewport-width focus heuristic",
)

# Regression tests: enforce touch capability/platform detection and native desktop DOM path.
test = Path("codex/tests/test_modernization.py")
text = test.read_text(encoding="utf-8")
text = text.replace(
    '        self.assertIn("shouldUseNativeTouchSelection", patch)\n',
    '        self.assertIn("shouldUseNativeTouchSelection", patch)\n'
    '        self.assertIn("shouldUseTouchControls", patch)\n'
    '        self.assertIn("maxTouchPoints", patch)\n'
    '        self.assertIn("Android|iPhone|iPad|iPod", patch)\n'
    '        self.assertIn("userAgentData?.mobile", patch)\n'
    '        self.assertIn("coarsePrimaryPointer", patch)\n'
    '        self.assertIn("this.touchControls && (", patch)\n'
    '        self.assertIn("if (!this.touchControls) this.container = c as HTMLElement;", patch)\n'
)
old_assertions = (
    '        # Desktop xterm drag-selection must not be clipped by the mobile layout wrapper.\n'
    '        self.assertNotIn("+    min-height: 0;\\n+    overflow: hidden;\\n+  }\\n+  .terminal {", patch)\n'
    '        self.assertIn("+@media (hover: none), (pointer: coarse), (max-width: 768px) {\\n+  .terminal-viewport {\\n+    overflow: hidden;", patch)\n'
)
new_assertions = (
    '        # Desktop keeps the upstream ttyd/xterm parent DOM; the mobile wrapper is rendered only on detected touch devices.\n'
    '        self.assertIn("class={this.touchControls ? \'ttyd-touch-controls\' : undefined}", patch)\n'
    '        self.assertIn("if (!this.touchControls) this.container = c as HTMLElement;", patch)\n'
    '        self.assertNotIn("if (!window.matchMedia(\'(hover: none), (pointer: coarse), (max-width: 768px)\').matches)", patch)\n'
)
if old_assertions not in text:
    raise SystemExit("desktop/mobile regression assertion block not found")
test.write_text(text.replace(old_assertions, new_assertions, 1), encoding="utf-8")

readme = Path("codex/ttyd-mobile-keys/README.md")
doc = readme.read_text(encoding="utf-8")
note = '''
### Touch-only mobile activation

The mobile keybar, touch swipe handlers, mobile viewport wrapper, and native touch-selection mode are activated only when the browser reports real touch capability (`navigator.maxTouchPoints > 0`) together with an iOS/iPadOS/Android/mobile-platform signal or a coarse primary touch pointer. A narrow desktop browser window no longer activates or renders the mobile path. iPadOS desktop-style user agents are covered through `MacIntel` plus multiple touch points.
'''
if "### Touch-only mobile activation" not in doc:
    readme.write_text(doc.rstrip() + "\n" + note, encoding="utf-8")
