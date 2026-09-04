from pathlib import Path
import re
import shutil
import subprocess
import tempfile


REPO = Path(__file__).resolve().parents[1]
PATCH = REPO / "codex/ttyd-mobile-keys/ttyd-1.7.7-mobile-keys.patch"
README = REPO / "codex/ttyd-mobile-keys/README.md"


def run(*args, cwd=None, stdout=None):
    subprocess.run(args, cwd=cwd, check=True, stdout=stdout)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, got {count}")
    return text.replace(old, new, 1)


with tempfile.TemporaryDirectory() as tmp:
    ttyd = Path(tmp) / "ttyd"
    run("git", "clone", "--depth", "1", "--branch", "1.7.7", "https://github.com/tsl0922/ttyd.git", str(ttyd))
    run("git", "apply", str(PATCH), cwd=ttyd)

    # Remove the overbuilt dev.12 v1 app-level implementation entirely.
    run("git", "checkout", "--", "html/src/components/app.tsx", cwd=ttyd)

    terminal_path = ttyd / "html/src/components/terminal/index.tsx"
    xterm_path = ttyd / "html/src/components/terminal/xterm/index.ts"

    terminal = terminal_path.read_text(encoding="utf-8")
    terminal = replace_once(
        terminal,
        """    private container: HTMLElement;\n    private xterm: Xterm;\n    private touchStartY?: number;\n    private readonly touchControls = shouldUseTouchControls(window);\n""",
        """    private container: HTMLElement;\n    private xterm: Xterm;\n    private host: HTMLElement;\n    private touchStartY?: number;\n    private keyboardViewport: any;\n    private keyboardBaseViewportHeight = 0;\n    private keyboardBaseHostHeight = 0;\n    private keyboardVisible = false;\n    private keyboardResizeHandler: any;\n    private readonly touchControls = shouldUseTouchControls(window);\n""",
        "terminal fields",
    )

    terminal = replace_once(
        terminal,
        """        if (this.touchControls) {\n            const selectionMode = this.xterm.toggleNativeSelection();\n            this.setState({ selectionMode });\n        }\n        this.xterm.connect();\n    }\n\n    componentWillUnmount() {\n        this.xterm.dispose();\n    }\n\n    render({ id }: Props, { modal, ctrl, alt, shift, shiftLock, selectionMode }: State) {\n""",
        """        if (this.touchControls) {\n            const selectionMode = this.xterm.toggleNativeSelection();\n            this.setState({ selectionMode });\n            this.installKeyboardAvoidance();\n        }\n        this.xterm.connect();\n    }\n\n    componentWillUnmount() {\n        this.uninstallKeyboardAvoidance();\n        this.xterm.dispose();\n    }\n\n    private resolveKeyboardViewport() {\n        try {\n            const topWindow = window.top as any;\n            if (topWindow && topWindow !== window && topWindow.visualViewport) return topWindow.visualViewport;\n        } catch (e) {\n            // Home Assistant ingress can make the top window cross-origin.\n        }\n        return (window as any).visualViewport;\n    }\n\n    private installKeyboardAvoidance() {\n        const viewport = this.resolveKeyboardViewport();\n        if (!viewport || !this.host) return;\n\n        this.keyboardViewport = viewport;\n        this.keyboardBaseViewportHeight = viewport.height;\n        this.keyboardBaseHostHeight = this.host.getBoundingClientRect().height;\n        this.keyboardResizeHandler = () => this.updateKeyboardAvoidance();\n        viewport.addEventListener('resize', this.keyboardResizeHandler);\n    }\n\n    private uninstallKeyboardAvoidance() {\n        if (this.keyboardViewport && this.keyboardResizeHandler) {\n            this.keyboardViewport.removeEventListener('resize', this.keyboardResizeHandler);\n        }\n        this.resetKeyboardAvoidance();\n        this.keyboardViewport = undefined;\n        this.keyboardResizeHandler = undefined;\n    }\n\n    private updateKeyboardAvoidance() {\n        if (!this.keyboardViewport || !this.host) return;\n\n        const active = document.activeElement as HTMLElement;\n        const inputFocused = !!active && active.classList.contains('xterm-helper-textarea');\n        const shrink = this.keyboardBaseViewportHeight - this.keyboardViewport.height;\n        if (!inputFocused || shrink < 120) {\n            this.resetKeyboardAvoidance();\n            if (!inputFocused) {\n                this.keyboardBaseViewportHeight = this.keyboardViewport.height;\n                this.keyboardBaseHostHeight = this.host.getBoundingClientRect().height;\n            }\n            return;\n        }\n\n        const opening = !this.keyboardVisible;\n        this.keyboardVisible = true;\n        const hostHeight = Math.max(160, Math.round(this.keyboardBaseHostHeight - shrink));\n        this.host.style.height = `${hostHeight}px`;\n        this.xterm.fit();\n        if (opening) this.xterm.scrollToBottom();\n    }\n\n    private resetKeyboardAvoidance() {\n        if (!this.host) return;\n        const changed = this.keyboardVisible || this.host.style.height !== '';\n        this.keyboardVisible = false;\n        this.host.style.height = '';\n        if (changed) this.xterm.fit();\n    }\n\n    render({ id }: Props, { modal, ctrl, alt, shift, shiftLock, selectionMode }: State) {\n""",
        "terminal lifecycle",
    )

    terminal = replace_once(
        terminal,
        """                ref={c => {\n                    if (!this.touchControls) this.container = c as HTMLElement;\n                }}\n""",
        """                ref={c => {\n                    this.host = c as HTMLElement;\n                    if (!this.touchControls) this.container = c as HTMLElement;\n                }}\n""",
        "terminal host ref",
    )

    terminal = replace_once(
        terminal,
        """        this.xterm.blur();\n    }\n\n    @bind\n    private clickKeyboardDismiss(event: MouseEvent) {\n        if (event.detail === 0) this.xterm.blur();\n""",
        """        this.xterm.blur();\n        this.resetKeyboardAvoidance();\n    }\n\n    @bind\n    private clickKeyboardDismiss(event: MouseEvent) {\n        if (event.detail === 0) {\n            this.xterm.blur();\n            this.resetKeyboardAvoidance();\n        }\n""",
        "keyboard dismiss",
    )
    terminal_path.write_text(terminal, encoding="utf-8")

    xterm = xterm_path.read_text(encoding="utf-8")
    xterm = replace_once(
        xterm,
        """    dispose() {\n        for (const d of this.disposables) {\n            d.dispose();\n        }\n        this.disposables.length = 0;\n    }\n\n    @bind\n    private register<T extends IDisposable>(d: T): T {\n""",
        """    dispose() {\n        for (const d of this.disposables) {\n            d.dispose();\n        }\n        this.disposables.length = 0;\n    }\n\n    public fit() {\n        this.fitAddon.fit();\n    }\n\n    public scrollToBottom() {\n        this.terminal.scrollToBottom();\n    }\n\n    @bind\n    private register<T extends IDisposable>(d: T): T {\n""",
        "xterm viewport helpers",
    )
    xterm_path.write_text(xterm, encoding="utf-8")

    run("git", "diff", "--check", cwd=ttyd)
    with PATCH.open("w", encoding="utf-8") as output:
        run("git", "diff", "--no-ext-diff", "--binary", cwd=ttyd, stdout=output)

readme = README.read_text(encoding="utf-8")
replacement = """## Mobile keyboard avoidance

On touch/mobile clients, keyboard avoidance lives in the existing `Terminal`
mobile path and reuses the already accepted `touchControls` decision. There is no
second mobile detector and no separate `app.tsx` keyboard state machine.

The terminal listens only to `visualViewport.resize` (preferring an accessible
top-level viewport in Home Assistant ingress). While xterm's helper textarea is
the active element and the visual viewport shrinks by at least 120 px, the
existing terminal host is shortened by the same amount, xterm is fitted, and the
first opening transition scrolls the prompt into view. When the keyboard closes
or `Kbd↓` blurs xterm, the inline height is removed and the terminal is fitted
back to its normal size.

This does not toggle `Sel`, alter paste/input handling, or change the accepted
desktop selection path.
"""
readme, count = re.subn(
    r"## Mobile keyboard avoidance\n.*?(?=\n## |\nThis behavior follows)",
    replacement.rstrip(),
    readme,
    count=1,
    flags=re.S,
)
if count != 1:
    raise RuntimeError(f"README keyboard section replacement count: {count}")
README.write_text(readme, encoding="utf-8")
