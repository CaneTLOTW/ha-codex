from pathlib import Path
import subprocess

ROOT = Path.cwd()
TTYD = Path('/tmp/ttyd-dev10')
PATCH = ROOT / 'codex/ttyd-mobile-keys/ttyd-1.7.7-mobile-keys.patch'
TESTS = ROOT / 'codex/tests/test_modernization.py'
README = ROOT / 'codex/ttyd-mobile-keys/README.md'
CONFIG = ROOT / 'codex/config.yaml'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, got {count}')
    return text.replace(old, new, 1)


# Apply the one canonical repository patch to a clean ttyd 1.7.7 tree. All
# changes below are made to the materialized source and the canonical patch is
# regenerated afterwards; there is no supplemental patch chain.
subprocess.run(['git', '-C', str(TTYD), 'apply', str(PATCH)], check=True)

xterm_path = TTYD / 'html/src/components/terminal/xterm/index.ts'
xterm = xterm_path.read_text(encoding='utf-8')

old_guard = '''        const guardTouchGesture = (event: Event) => {
            if (!this.nativeSelectionMode) return;
            const target = event.target as Element | null;
            if (!target?.closest('.xterm-rows, .xterm-helper-textarea')) return;
            event.stopPropagation();
        };
'''
new_guard = '''        const guardTouchGesture = (event: Event) => {
            if (!this.nativeSelectionMode) return;
            // In native iOS selection mode Safari must own the entire touch
            // gesture consistently. Letting xterm's gesture layer receive
            // touches that start between rows causes the jumpy split behavior.
            event.stopPropagation();
        };
'''
xterm = replace_once(xterm, old_guard, new_guard, 'native touch gesture guard')

old_paste = '''        const pasteHandler = (event: Event) => {
            if (!this.nativeSelectionMode) return;
            const pasteEvent = event as ClipboardEvent;
            if (pasteEvent.clipboardData) {
                // xterm's normal paste handler will consume clipboardData. Prevent the
                // browser from inserting the same text into the helper textarea again.
                pasteEvent.preventDefault();
            }
        };
        this.register(addCapturedEventListener(textarea, 'paste', pasteHandler));

        const inputFallback = (event: Event) => {
            if (!this.nativeSelectionMode) return;
            const inputEvent = event as InputEvent;
            if (inputEvent.inputType !== 'insertFromPaste' || !textarea.value) return;

            const text = textarea.value;
            textarea.value = '';
            this.terminal.paste(text);
            inputEvent.preventDefault();
            inputEvent.stopPropagation();
        };
        this.register(addCapturedEventListener(textarea, 'input', inputFallback));
'''
new_paste = '''        const pasteHandler = (event: Event) => {
            if (!this.nativeSelectionMode) return;
            const pasteEvent = event as ClipboardEvent;
            const text = pasteEvent.clipboardData?.getData('text/plain');
            if (!text) return;

            // Handle iOS paste directly instead of relying on xterm's hidden
            // textarea listener ordering. Capture + stopImmediatePropagation
            // guarantees one bracketed-paste path and avoids duplicate text.
            pasteEvent.preventDefault();
            pasteEvent.stopImmediatePropagation();
            textarea.value = '';
            this.terminal.paste(text);
        };
        this.register(addCapturedEventListener(textarea, 'paste', pasteHandler));

        const beforeInputFallback = (event: Event) => {
            if (!this.nativeSelectionMode) return;
            const inputEvent = event as InputEvent;
            if (inputEvent.inputType !== 'insertFromPaste' || !inputEvent.data) return;

            inputEvent.preventDefault();
            inputEvent.stopImmediatePropagation();
            textarea.value = '';
            this.terminal.paste(inputEvent.data);
        };
        this.register(addCapturedEventListener(textarea, 'beforeinput', beforeInputFallback));

        const inputFallback = (event: Event) => {
            if (!this.nativeSelectionMode) return;
            const inputEvent = event as InputEvent;
            if (inputEvent.inputType !== 'insertFromPaste' || !textarea.value) return;

            const text = textarea.value;
            textarea.value = '';
            this.terminal.paste(text);
            inputEvent.preventDefault();
            inputEvent.stopImmediatePropagation();
        };
        this.register(addCapturedEventListener(textarea, 'input', inputFallback));
'''
xterm = replace_once(xterm, old_paste, new_paste, 'native iOS paste path')

old_state = '''        this.parent?.classList.toggle('ttyd-native-touch-selection-host', this.nativeSelectionMode);
        this.setRendererType(this.nativeSelectionMode ? 'dom' : this.requestedRenderer);
        if (this.nativeSelectionMode) this.terminal.blur();
        this.fitAddon.fit();
'''
new_state = '''        this.parent?.classList.toggle('ttyd-native-touch-selection-host', this.nativeSelectionMode);
        this.setRendererType(this.nativeSelectionMode ? 'dom' : this.requestedRenderer);
        // Do not force-blur the helper textarea on entry. Upstream xterm's iOS
        // implementation keeps the native textarea available at the cursor so
        // Safari can expose its long-press Paste action. Exiting selection mode
        // restores the normal terminal focus path.
        if (!this.nativeSelectionMode) this.terminal.focus();
        this.fitAddon.fit();
'''
xterm = replace_once(xterm, old_state, new_state, 'selection focus state')
xterm_path.write_text(xterm, encoding='utf-8')

style_path = TTYD / 'html/src/style/index.scss'
style = style_path.read_text(encoding='utf-8')
style_anchor = '''  .terminal-viewport .xterm.ttyd-native-touch-selection .xterm-rows span {
    display: inline !important;
  }

'''
style_replacement = style_anchor + '''  // Keep xterm's DOM measurement helpers out of Safari's native selection
  // layout. This mirrors the upstream iOS native-selection fix and avoids
  // measurement nodes affecting wrapped/box-drawing output.
  .terminal-viewport .xterm.ttyd-native-touch-selection .xterm-char-measure-element,
  .terminal-viewport .xterm.ttyd-native-touch-selection .xterm-width-cache-measure-container {
    position: absolute !important;
    visibility: hidden !important;
    left: -9999em !important;
    top: 0 !important;
  }

'''
style = replace_once(style, style_anchor, style_replacement, 'DOM measurement CSS')
style_path.write_text(style, encoding='utf-8')

# Tight regression contract: preserve the accepted desktop arbitration while
# requiring the mobile-only iOS fixes above.
tests = TESTS.read_text(encoding='utf-8')
anchor = '''        self.assertIn("window.matchMedia?.('(hover: none) and (pointer: coarse)')", patch)
        self.assertNotIn("installDesktopShiftSelectionScroll", patch)
'''
replacement = '''        self.assertIn("window.matchMedia?.('(hover: none) and (pointer: coarse)')", patch)
        self.assertIn("installDesktopSelectionPreference", patch)
        self.assertIn("Object.defineProperty(event, 'shiftKey'", patch)
        self.assertIn("stopImmediatePropagation", patch)
        self.assertIn("beforeInputFallback", patch)
        self.assertIn("inputEvent.inputType !== 'insertFromPaste'", patch)
        self.assertIn("xterm-char-measure-element", patch)
        self.assertIn("xterm-width-cache-measure-container", patch)
        self.assertIn("if (!this.nativeSelectionMode) this.terminal.focus();", patch)
        self.assertNotIn("if (this.nativeSelectionMode) this.terminal.blur();", patch)
        self.assertNotIn("installDesktopShiftSelectionScroll", patch)
'''
tests = replace_once(tests, anchor, replacement, 'mobile regression assertions')
TESTS.write_text(tests, encoding='utf-8')

readme = README.read_text(encoding='utf-8')
needle = '''This does not add a second selection implementation or a second ttyd patch.
'''
addition = needle + '''
On iOS, `Sel` uses Safari's native DOM selection. The helper textarea remains
available at the cursor for the native Paste action; paste events are captured
once and forwarded through xterm's `paste()` API. While `Sel` is active Safari
owns touch gestures consistently, and DOM measurement helpers are hidden from
the selection layout. Desktop mouse arbitration is unchanged by this path.
'''
readme = replace_once(readme, needle, addition, 'README mobile selection note')
README.write_text(readme, encoding='utf-8')

config = CONFIG.read_text(encoding='utf-8')
config = replace_once(config, 'version: "0.4.4-dev.9"', 'version: "0.4.4-dev.10"', 'deployment version')
CONFIG.write_text(config, encoding='utf-8')
