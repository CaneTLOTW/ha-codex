from pathlib import Path
import subprocess

ROOT = Path.cwd()
TTYD = Path('/tmp/ttyd-dev11')
PATCH = ROOT / 'codex/ttyd-mobile-keys/ttyd-1.7.7-mobile-keys.patch'
TESTS = ROOT / 'codex/tests/test_modernization.py'
README = ROOT / 'codex/ttyd-mobile-keys/README.md'
CONFIG = ROOT / 'codex/config.yaml'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, got {count}')
    return text.replace(old, new, 1)


subprocess.run(['git', '-C', str(TTYD), 'apply', str(PATCH)], check=True)

terminal_path = TTYD / 'html/src/components/terminal/index.tsx'
terminal = terminal_path.read_text(encoding='utf-8')
old_mount = '''        await this.xterm.refreshToken();
        this.xterm.open(this.container);
        this.xterm.connect();
'''
new_mount = '''        await this.xterm.refreshToken();
        this.xterm.open(this.container);
        if (this.touchControls) {
            const selectionMode = this.xterm.toggleNativeSelection();
            this.setState({ selectionMode });
        }
        this.xterm.connect();
'''
terminal = replace_once(terminal, old_mount, new_mount, 'mobile auto-select mount')
terminal_path.write_text(terminal, encoding='utf-8')

# Tighten the regression contract around the deliberately narrow dev.11 scope.
tests = TESTS.read_text(encoding='utf-8')
anchor = '''        self.assertIn("this.touchControls && (", patch)\n        self.assertIn("if (!this.touchControls) this.container = c as HTMLElement;", patch)\n'''
replacement = '''        self.assertIn("this.touchControls && (", patch)\n        self.assertIn("if (!this.touchControls) this.container = c as HTMLElement;", patch)\n        self.assertIn("if (this.touchControls) {", patch)\n        self.assertIn("const selectionMode = this.xterm.toggleNativeSelection();", patch)\n        self.assertIn("this.setState({ selectionMode });", patch)\n        self.assertIn("private pressKeyboardDismiss(event: PointerEvent)", patch)\n        self.assertIn("this.xterm.blur();", patch)\n        self.assertIn("private pressKeyboardShow(event: PointerEvent)", patch)\n        self.assertIn("this.xterm.showKeyboard();", patch)\n'''
tests = replace_once(tests, anchor, replacement, 'dev11 regression assertions')
TESTS.write_text(tests, encoding='utf-8')

readme = README.read_text(encoding='utf-8')
old_readme = '''The intended iOS interaction is: enable `Sel`, long-press/drag terminal output
and use the native iOS Copy action. For paste, use the native iOS Paste action
at the terminal input while `Sel` is active. This path deliberately does not
use `navigator.clipboard.readText()` and is separate from terminal `Ctrl+C` or
`Ctrl+V` control sequences.
'''
new_readme = '''On supported mobile/touch devices the terminal now enters `Sel` automatically
after opening, so native selection/read mode is the default mobile state. `Sel`
remains a manual toggle and can still be switched off and back on when needed.
`Kbd↑` and `Kbd↓` keep their existing behavior: they only show or hide the
software keyboard and do not change selection mode. Copy and native paste remain
available while `Sel` is active. This path deliberately does not use
`navigator.clipboard.readText()` and is separate from terminal `Ctrl+C` or
`Ctrl+V` control sequences.
'''
readme = replace_once(readme, old_readme, new_readme, 'README default mobile selection')
README.write_text(readme, encoding='utf-8')

config = CONFIG.read_text(encoding='utf-8')
config = replace_once(config, 'version: "0.4.4-dev.10"', 'version: "0.4.4-dev.11"', 'deployment version')
CONFIG.write_text(config, encoding='utf-8')
