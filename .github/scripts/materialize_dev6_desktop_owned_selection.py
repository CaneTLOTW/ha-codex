from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


root = Path("/tmp/ttyd-1.7.7")
xterm = root / "html/src/components/terminal/xterm/index.ts"
text = xterm.read_text(encoding="utf-8")

old_fields = '''    private nativeSelectionCapable = false;
    private nativeSelectionMode = false;
    private desktopSelectionActive = false;
    private desktopSelectionPointer?: { x: number; y: number };
    private desktopSelectionScrollDirection = 0;
    private desktopSelectionScrollTimer?: number;
'''
new_fields = '''    private nativeSelectionCapable = false;
    private nativeSelectionMode = false;
    private desktopSelectionActive = false;
    private desktopSelectionAnchor?: { col: number; row: number };
    private desktopSelectionPointer?: { x: number; y: number };
    private desktopSelectionScrollDirection = 0;
    private desktopSelectionScrollTimer?: number;
'''
text = replace_once(text, old_fields, new_fields, "desktop selection fields")

start = text.index("    private installDesktopShiftSelectionScroll() {\n")
end = text.index("    private applyNativeSelectionState() {\n", start)

methods = r'''    private installDesktopShiftSelectionScroll() {
        if (this.nativeSelectionCapable || !this.terminal.element) return;

        const terminalElement = this.terminal.element;
        const screenElement = terminalElement.querySelector('.xterm-screen') as HTMLElement | null;
        if (!screenElement) return;

        const startSelection = (event: Event) => {
            const mouseEvent = event as MouseEvent;
            const target = mouseEvent.target as Element | null;
            if (mouseEvent.button !== 0 || !mouseEvent.shiftKey || !target?.closest('.xterm-screen')) return;

            const point = this.desktopBufferPoint(screenElement, mouseEvent.clientX, mouseEvent.clientY);
            if (!point) return;

            mouseEvent.preventDefault();
            mouseEvent.stopImmediatePropagation();
            this.desktopSelectionActive = true;
            this.desktopSelectionAnchor = point;
            this.desktopSelectionPointer = { x: mouseEvent.clientX, y: mouseEvent.clientY };
            this.terminal.select(point.col, point.row, 1);
            this.updateDesktopSelectionEdge(screenElement, mouseEvent.clientY);
        };

        const moveSelection = (event: Event) => {
            if (!this.desktopSelectionActive) return;
            const mouseEvent = event as MouseEvent;
            mouseEvent.preventDefault();
            mouseEvent.stopImmediatePropagation();
            this.desktopSelectionPointer = { x: mouseEvent.clientX, y: mouseEvent.clientY };
            this.updateDesktopOwnedSelection(screenElement);
            this.updateDesktopSelectionEdge(screenElement, mouseEvent.clientY);
        };

        const stopSelection = (event?: Event) => {
            if (this.desktopSelectionActive && event) {
                event.preventDefault();
                event.stopImmediatePropagation();
            }
            this.stopDesktopSelectionScroll();
        };

        const leaveDocument = (event: Event) => {
            const mouseEvent = event as MouseEvent;
            if (mouseEvent.relatedTarget === null) stopSelection();
        };

        const wheelSelection = (event: Event) => {
            const wheelEvent = event as WheelEvent;
            if (!wheelEvent.shiftKey && !this.desktopSelectionActive) return;
            wheelEvent.preventDefault();
            wheelEvent.stopImmediatePropagation();
            this.scrollDesktopSelectionWheel(wheelEvent);
            if (this.desktopSelectionActive) this.updateDesktopOwnedSelection(screenElement);
        };

        this.register(addCapturedEventListener(terminalElement, 'mousedown', startSelection));
        this.register(addCapturedEventListener(terminalElement.ownerDocument, 'mousemove', moveSelection));
        this.register(addCapturedEventListener(terminalElement.ownerDocument, 'mouseup', stopSelection));
        this.register(addCapturedEventListener(terminalElement.ownerDocument, 'mouseout', leaveDocument));
        this.register(addCapturedEventListener(terminalElement, 'wheel', wheelSelection));
        this.register(addCapturedEventListener(window, 'blur', stopSelection));
        this.register(toDisposable(() => this.stopDesktopSelectionScroll()));
    }

    private desktopBufferPoint(screenElement: HTMLElement, clientX: number, clientY: number) {
        const bounds = screenElement.getBoundingClientRect();
        if (bounds.width <= 0 || bounds.height <= 0 || this.terminal.cols <= 0 || this.terminal.rows <= 0) {
            return undefined;
        }

        const relativeX = Math.min(Math.max(clientX - bounds.left, 0), Math.max(bounds.width - 1, 0));
        const relativeY = Math.min(Math.max(clientY - bounds.top, 0), Math.max(bounds.height - 1, 0));
        const col = Math.min(
            this.terminal.cols - 1,
            Math.max(0, Math.floor((relativeX / bounds.width) * this.terminal.cols))
        );
        const viewportRow = Math.min(
            this.terminal.rows - 1,
            Math.max(0, Math.floor((relativeY / bounds.height) * this.terminal.rows))
        );
        return { col, row: this.terminal.buffer.active.viewportY + viewportRow };
    }

    private updateDesktopOwnedSelection(screenElement: HTMLElement) {
        if (!this.desktopSelectionActive || !this.desktopSelectionAnchor || !this.desktopSelectionPointer) return;
        const point = this.desktopBufferPoint(
            screenElement,
            this.desktopSelectionPointer.x,
            this.desktopSelectionPointer.y
        );
        if (!point) return;

        const cols = this.terminal.cols;
        const anchorOffset = this.desktopSelectionAnchor.row * cols + this.desktopSelectionAnchor.col;
        const pointOffset = point.row * cols + point.col;
        const startOffset = Math.min(anchorOffset, pointOffset);
        const endOffset = Math.max(anchorOffset, pointOffset);
        const startRow = Math.floor(startOffset / cols);
        const startCol = startOffset % cols;
        const length = Math.max(1, endOffset - startOffset + 1);
        this.terminal.select(startCol, startRow, length);
    }

    private updateDesktopSelectionEdge(screenElement: HTMLElement, clientY: number) {
        if (!this.desktopSelectionActive) return;
        const bounds = screenElement.getBoundingClientRect();
        const threshold = Math.min(42, Math.max(24, bounds.height * 0.08));
        let direction = 0;
        if (clientY <= bounds.top + threshold) direction = -1;
        else if (clientY >= bounds.bottom - threshold) direction = 1;
        this.setDesktopSelectionScrollDirection(direction, screenElement);
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

    private setDesktopSelectionScrollDirection(direction: number, screenElement: HTMLElement) {
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
            this.updateDesktopOwnedSelection(screenElement);
        }, 50);
    }

    private stopDesktopSelectionScroll() {
        this.desktopSelectionActive = false;
        this.desktopSelectionAnchor = undefined;
        this.desktopSelectionPointer = undefined;
        this.desktopSelectionScrollDirection = 0;
        if (this.desktopSelectionScrollTimer !== undefined) {
            window.clearInterval(this.desktopSelectionScrollTimer);
            this.desktopSelectionScrollTimer = undefined;
        }
    }

'''
text = text[:start] + methods + text[end:]
xterm.write_text(text, encoding="utf-8")


test = Path("codex/tests/test_modernization.py")
t = test.read_text(encoding="utf-8")
old = '''        self.assertIn("installDesktopShiftSelectionScroll", patch)
        self.assertIn("attachCustomWheelEventHandler", patch)
        self.assertIn("if (!event.shiftKey) return true", patch)
        self.assertIn("scrollDesktopSelectionWheel", patch)
        self.assertIn("setDesktopSelectionScrollDirection", patch)
        self.assertIn("replayDesktopSelectionMove", patch)
'''
new = '''        self.assertIn("installDesktopShiftSelectionScroll", patch)
        self.assertIn("desktopSelectionAnchor", patch)
        self.assertIn("desktopBufferPoint", patch)
        self.assertIn("updateDesktopOwnedSelection", patch)
        self.assertIn("mouseEvent.stopImmediatePropagation()", patch)
        self.assertIn("this.terminal.select(startCol, startRow, length)", patch)
        self.assertIn("this.terminal.buffer.active.viewportY", patch)
        self.assertIn("scrollDesktopSelectionWheel", patch)
        self.assertIn("setDesktopSelectionScrollDirection", patch)
        self.assertNotIn("attachCustomWheelEventHandler", patch)
        self.assertNotIn("replayDesktopSelectionMove", patch)
'''
t = replace_once(t, old, new, "desktop regression assertions")
test.write_text(t, encoding="utf-8")

readme = Path("codex/ttyd-mobile-keys/README.md")
d = readme.read_text(encoding="utf-8")
old_doc = '''### Desktop selection scroll in Home Assistant ingress

On desktop, Shift-forced xterm selection keeps wheel events local to the xterm scrollback instead of forwarding them to the mouse-aware TUI. A small in-frame edge zone also drives selection scrolling before the pointer leaves the Home Assistant ingress iframe, preserving multi-screen selection without changing the touch/mobile path.
'''
new_doc = '''### Desktop selection scroll in Home Assistant ingress

Desktop Shift-selection is intentionally independent from the mobile `Sel` path and from xterm's forced-selection mouse handler. A capture-phase desktop adapter owns Shift+drag, maps pointer coordinates directly into the public xterm buffer, updates the selection through `Terminal.select()`, and keeps Shift+wheel plus an in-frame edge zone local to xterm scrollback. This avoids depending on mousemove events after the pointer crosses the Home Assistant ingress iframe boundary.
'''
d = replace_once(d, old_doc, new_doc, "desktop selection documentation")
readme.write_text(d, encoding="utf-8")
