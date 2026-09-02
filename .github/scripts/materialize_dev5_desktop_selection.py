from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


root = Path("/tmp/ttyd-1.7.7")
xterm = root / "html/src/components/terminal/xterm/index.ts"
text = xterm.read_text(encoding="utf-8")

text = replace_once(
    text,
    "    private nativeSelectionCapable = false;\n    private nativeSelectionMode = false;\n",
    "    private nativeSelectionCapable = false;\n"
    "    private nativeSelectionMode = false;\n"
    "    private desktopSelectionActive = false;\n"
    "    private desktopSelectionPointer?: { x: number; y: number };\n"
    "    private desktopSelectionScrollDirection = 0;\n"
    "    private desktopSelectionScrollTimer?: number;\n",
    "desktop selection fields",
)

text = replace_once(
    text,
    "        terminal.open(parent);\n        this.installNativeTouchSelection();\n        fitAddon.fit();\n",
    "        terminal.open(parent);\n"
    "        this.installNativeTouchSelection();\n"
    "        this.installDesktopShiftSelectionScroll();\n"
    "        fitAddon.fit();\n",
    "desktop selection install call",
)

marker = "    private applyNativeSelectionState() {\n"
methods = r'''    private installDesktopShiftSelectionScroll() {
        if (this.nativeSelectionCapable || !this.terminal.element) return;

        const terminalElement = this.terminal.element;
        const screenElement = terminalElement.querySelector('.xterm-screen') as HTMLElement | null;
        if (!screenElement) return;

        const updatePointer = (event: MouseEvent) => {
            if (!this.desktopSelectionActive) return;
            this.desktopSelectionPointer = { x: event.clientX, y: event.clientY };

            const bounds = screenElement.getBoundingClientRect();
            const threshold = Math.min(36, Math.max(18, bounds.height * 0.06));
            let direction = 0;
            if (event.clientY <= bounds.top + threshold) direction = -1;
            else if (event.clientY >= bounds.bottom - threshold) direction = 1;
            this.setDesktopSelectionScrollDirection(direction);
        };

        const startSelection = (event: Event) => {
            const mouseEvent = event as MouseEvent;
            const target = mouseEvent.target as Element | null;
            if (mouseEvent.button !== 0 || !mouseEvent.shiftKey || !target?.closest('.xterm-screen')) return;
            this.desktopSelectionActive = true;
            updatePointer(mouseEvent);
        };
        const moveSelection = (event: Event) => updatePointer(event as MouseEvent);
        const stopSelection = () => this.stopDesktopSelectionScroll();

        this.register(addCapturedEventListener(terminalElement, 'mousedown', startSelection));
        this.register(addCapturedEventListener(terminalElement.ownerDocument, 'mousemove', moveSelection));
        this.register(addCapturedEventListener(terminalElement.ownerDocument, 'mouseup', stopSelection));
        this.register(addCapturedEventListener(window, 'blur', stopSelection));
        this.register(toDisposable(stopSelection));

        this.terminal.attachCustomWheelEventHandler(event => {
            if (!event.shiftKey) return true;
            event.preventDefault();
            event.stopPropagation();
            this.scrollDesktopSelectionWheel(event);
            if (this.desktopSelectionActive) this.replayDesktopSelectionMove();
            return false;
        });
    }

    private scrollDesktopSelectionWheel(event: WheelEvent) {
        if (!event.deltaY) return;
        let lines = event.deltaY;
        if (event.deltaMode === 0) lines /= 40;
        else if (event.deltaMode === 2) lines *= this.terminal.rows;

        let amount = Math.trunc(lines);
        if (!amount) amount = Math.sign(event.deltaY);
        amount = Math.max(-this.terminal.rows, Math.min(this.terminal.rows, amount));
        this.terminal.scrollLines(amount);
    }

    private setDesktopSelectionScrollDirection(direction: number) {
        this.desktopSelectionScrollDirection = direction;
        if (!direction) {
            if (this.desktopSelectionScrollTimer !== undefined) {
                window.clearInterval(this.desktopSelectionScrollTimer);
                this.desktopSelectionScrollTimer = undefined;
            }
            return;
        }
        if (this.desktopSelectionScrollTimer !== undefined) return;

        this.desktopSelectionScrollTimer = window.setInterval(() => {
            if (!this.desktopSelectionActive || !this.desktopSelectionScrollDirection) return;
            this.terminal.scrollLines(this.desktopSelectionScrollDirection);
            this.replayDesktopSelectionMove();
        }, 50);
    }

    private replayDesktopSelectionMove() {
        if (!this.desktopSelectionActive || !this.desktopSelectionPointer || !this.terminal.element) return;
        const ownerDocument = this.terminal.element.ownerDocument;
        ownerDocument.dispatchEvent(
            new MouseEvent('mousemove', {
                bubbles: true,
                cancelable: true,
                view: window,
                clientX: this.desktopSelectionPointer.x,
                clientY: this.desktopSelectionPointer.y,
                buttons: 1,
                shiftKey: true,
            })
        );
    }

    private stopDesktopSelectionScroll() {
        this.desktopSelectionActive = false;
        this.desktopSelectionPointer = undefined;
        this.desktopSelectionScrollDirection = 0;
        if (this.desktopSelectionScrollTimer !== undefined) {
            window.clearInterval(this.desktopSelectionScrollTimer);
            this.desktopSelectionScrollTimer = undefined;
        }
    }

'''
text = replace_once(text, marker, methods + marker, "native selection state marker")
xterm.write_text(text, encoding="utf-8")


test = Path("codex/tests/test_modernization.py")
test_text = test.read_text(encoding="utf-8")
old = (
    '        self.assertIn("if (!this.touchControls) this.container = c as HTMLElement;", patch)\n'
    '        self.assertNotIn("if (!window.matchMedia(\'(hover: none), (pointer: coarse), (max-width: 768px)\').matches)", patch)\n'
)
new = old + (
    '        # Desktop forced selection keeps wheel/edge scrolling local to xterm even when the TUI reports mouse events.\n'
    '        self.assertIn("installDesktopShiftSelectionScroll", patch)\n'
    '        self.assertIn("attachCustomWheelEventHandler", patch)\n'
    '        self.assertIn("if (!event.shiftKey) return true", patch)\n'
    '        self.assertIn("scrollDesktopSelectionWheel", patch)\n'
    '        self.assertIn("setDesktopSelectionScrollDirection", patch)\n'
    '        self.assertIn("replayDesktopSelectionMove", patch)\n'
)
test_text = replace_once(test_text, old, new, "desktop regression test marker")
test.write_text(test_text, encoding="utf-8")

readme = Path("codex/ttyd-mobile-keys/README.md")
doc = readme.read_text(encoding="utf-8")
note = """
### Desktop selection scroll in Home Assistant ingress

On desktop, Shift-forced xterm selection keeps wheel events local to the xterm scrollback instead of forwarding them to the mouse-aware TUI. A small in-frame edge zone also drives selection scrolling before the pointer leaves the Home Assistant ingress iframe, preserving multi-screen selection without changing the touch/mobile path.
"""
if "### Desktop selection scroll in Home Assistant ingress" not in doc:
    readme.write_text(doc.rstrip() + "\n" + note, encoding="utf-8")
