#!/usr/bin/env python3
"""Apply the Codex screenshot-paste extension after the pinned ttyd 1.7.7 patch.

Fail closed if any upstream anchor changes: never silently ship an unpatched
browser and a custom WebSocket message handler.
"""
from pathlib import Path
import sys


def replace_once(path: Path, before: str, after: str) -> None:
    src = path.read_text(encoding="utf-8")
    if src.count(before) != 1:
        raise SystemExit(
            f"Codex image-paste patch incompatible: {path}, expected one "
            f"anchor (found {src.count(before)}): {before[:100]!r}"
        )
    path.write_text(src.replace(before, after), encoding="utf-8")


def apply(root: Path) -> None:
    server = root / "src/server.h"
    protocol = root / "src/protocol.c"
    xterm = root / "html/src/components/terminal/xterm/index.ts"

    replace_once(
        server,
        "  char path[128];\n  char **args;\n",
        "  char path[128];\n"
        "  /* Single pending acknowledgement to the authenticated terminal. */\n"
        "  char image_reply[320];\n"
        "  bool image_reply_pending;\n"
        "  char **args;\n",
    )

    replace_once(
        protocol,
        '#include "server.h"\n',
        '#include "server.h"\n#include "codex-image-paste.h"\n',
    )
    replace_once(
        protocol,
        "      if (pss->pty_buf != NULL) {\n"
        "        wsi_output(wsi, pss->pty_buf);\n",
        "      if (pss->image_reply_pending) {\n"
        "        unsigned char reply[LWS_PRE + sizeof(pss->image_reply)];\n"
        "        size_t count = strlen(pss->image_reply);\n"
        "        memcpy(reply + LWS_PRE, pss->image_reply, count);\n"
        "        pss->image_reply_pending = false;\n"
        "        if (lws_write(wsi, reply + LWS_PRE, count, LWS_WRITE_BINARY) < 0)\n"
        "          return -1;\n"
        "        if (pss->pty_buf != NULL) lws_callback_on_writable(wsi);\n"
        "        break;\n"
        "      }\n"
        "\n"
        "      if (pss->pty_buf != NULL) {\n"
        "        wsi_output(wsi, pss->pty_buf);\n",
    )
    replace_once(
        protocol,
        "    case LWS_CALLBACK_RECEIVE:\n"
        "      if (pss->buffer == NULL) {\n",
        "    case LWS_CALLBACK_RECEIVE:\n"
        "      /* Never buffer an unbounded screenshot or arbitrary binary data. */\n"
        "      if ((pss->buffer && pss->buffer[0] == CODEX_IMAGE_WS_REQUEST &&\n"
        "           (len > CODEX_IMAGE_MAX_SIZE + 1 ||\n"
        "            pss->len > CODEX_IMAGE_MAX_SIZE + 1 - len)) ||\n"
        "          (!pss->buffer && len > 0 &&\n"
        "           ((char *)in)[0] == CODEX_IMAGE_WS_REQUEST &&\n"
        "           len > CODEX_IMAGE_MAX_SIZE + 1)) {\n"
        "        lws_close_reason(wsi, LWS_CLOSE_STATUS_POLICY_VIOLATION, NULL, 0);\n"
        "        return -1;\n"
        "      }\n"
        "      if (pss->buffer == NULL) {\n",
    )
    replace_once(
        protocol,
        "      switch (command) {\n"
        "        case INPUT:\n",
        "      switch (command) {\n"
        "        case CODEX_IMAGE_WS_REQUEST: {\n"
        "          const char *enabled = getenv(\"CODEX_IMAGE_PASTE_ENABLED\");\n"
        "          if (!server->writable || pss->process == NULL ||\n"
        "              pss->image_reply_pending || enabled == NULL ||\n"
        "              strcmp(enabled, \"true\") != 0) {\n"
        "            snprintf(pss->image_reply, sizeof(pss->image_reply),\n"
        "                     \"%cScreenshot transfer disabled\", CODEX_IMAGE_WS_ERROR);\n"
        "          } else {\n"
        "            char path[256];\n"
        "            if (codex_image_save_png((unsigned char *)pss->buffer + 1,\n"
        "                                     pss->len - 1, path, sizeof(path)) != 0) {\n"
        "              snprintf(pss->image_reply, sizeof(pss->image_reply),\n"
        "                       \"%cScreenshot rejected\", CODEX_IMAGE_WS_ERROR);\n"
        "            } else {\n"
        "              snprintf(pss->image_reply, sizeof(pss->image_reply),\n"
        "                       \"%c%s\", CODEX_IMAGE_WS_REPLY, path);\n"
        "            }\n"
        "          }\n"
        "          pss->image_reply_pending = true;\n"
        "          lws_callback_on_writable(wsi);\n"
        "          break;\n"
        "        }\n"
        "        case INPUT:\n",
    )

    replace_once(
        xterm,
        "    SET_PREFERENCES = '2',\n\n    // client side\n",
        "    SET_PREFERENCES = '2',\n"
        "    IMAGE_PASTE_RESULT = '4',\n"
        "    IMAGE_PASTE_ERROR = '5',\n\n    // client side\n",
    )
    replace_once(
        xterm,
        "    RESUME = '3',\n}\n",
        "    RESUME = '3',\n"
        "    IMAGE_PASTE_REQUEST = '4',\n}\n",
    )
    replace_once(
        xterm,
        "    enableTrzsz: boolean;\n",
        "    enableTrzsz: boolean;\n"
        "    enableCodexImagePaste: boolean;\n",
    )
    replace_once(
        xterm,
        "    private terminal: Terminal;\n",
        "    private imagePasteEnabled = false;\n"
        "    private imagePastePending = false;\n"
        "    private terminal: Terminal;\n",
    )
    replace_once(
        xterm,
        "        register(addEventListener(window, 'beforeunload', this.onWindowUnload));\n",
        "        register(addEventListener(window, 'beforeunload', this.onWindowUnload));\n"
        "        register(\n"
        "            addCapturedEventListener(document, 'paste', event => {\n"
        "                this.onCodexImagePaste(event as ClipboardEvent);\n"
        "            })\n"
        "        );\n",
    )

    on_paste = r'''    @bind
    private async onCodexImagePaste(event: ClipboardEvent) {
        if (!this.imagePasteEnabled || !event.clipboardData) return;
        const source = event.target as HTMLElement | null;
        if (!source?.closest?.('.xterm')) return;

        // Do not intercept plain text, URLs or ordinary terminal Ctrl+V.
        // Windows Win+Shift+S and Firefox expose a PNG file through items.
        const item = Array.from(event.clipboardData.items).find(
            item => item.kind === 'file' && item.type === 'image/png'
        );
        if (!item) return;

        // The clipboard PNG is captured synchronously, during the trusted
        // paste event, before the browser invalidates clipboardData.
        const image = item.getAsFile();
        if (!image) return;
        event.preventDefault();
        event.stopImmediatePropagation();

        if (this.imagePastePending) {
            this.overlayAddon.showOverlay('Screenshot transfer already running', 1500);
            return;
        }
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            this.overlayAddon.showOverlay('Terminal disconnected - retry paste', 1800);
            return;
        }
        if (image.size < 33 || image.size > 10 * 1024 * 1024) {
            this.overlayAddon.showOverlay('Screenshot must be PNG <= 10 MiB', 2000);
            return;
        }

        this.imagePastePending = true;
        this.overlayAddon.showOverlay('Uploading screenshot...', 1000);
        const socket = this.socket;
        try {
            const bytes = new Uint8Array(await image.arrayBuffer());
            if (socket !== this.socket || socket.readyState !== WebSocket.OPEN) {
                this.imagePastePending = false;
                return;
            }
            const magic = [137, 80, 78, 71, 13, 10, 26, 10];
            if (!magic.every((byte, i) => bytes[i] === byte)) {
                this.imagePastePending = false;
                this.overlayAddon.showOverlay('Clipboard image is not PNG', 1600);
                return;
            }
            const payload = new Uint8Array(bytes.length + 1);
            payload[0] = Command.IMAGE_PASTE_REQUEST.charCodeAt(0);
            payload.set(bytes, 1);
            socket.send(payload);
        } catch (_error) {
            this.imagePastePending = false;
            this.overlayAddon.showOverlay('Could not read clipboard image', 2000);
        }
    }

'''
    replace_once(
        xterm,
        "    @bind\n    public sendData(data: string | Uint8Array) {\n",
        on_paste + "    @bind\n    public sendData(data: string | Uint8Array) {\n",
    )
    replace_once(
        xterm,
        "        console.log(`[ttyd] websocket connection closed with code: ${event.code}`);\n",
        "        console.log(`[ttyd] websocket connection closed with code: ${event.code}`);\n"
        "        this.imagePastePending = false;\n",
    )
    replace_once(
        xterm,
        "            case Command.OUTPUT:\n"
        "                this.writeFunc(data);\n"
        "                break;\n",
        "            case Command.OUTPUT:\n"
        "                this.writeFunc(data);\n"
        "                break;\n"
        "            case Command.IMAGE_PASTE_RESULT: {\n"
        "                const path = textDecoder.decode(data);\n"
        "                const prefix = '/data/codex-home/users/anonymous/.codex/uploads/clipboard-';\n"
        "                const valid = path.startsWith(prefix) && /^[0-9a-f]{32}\\.png$/.test(path.slice(prefix.length));\n"
        "                if (this.imagePastePending && valid) {\n"
        "                    this.imagePastePending = false;\n"
        "                    // Bracketed paste triggers Codex 0.171.0's existing\n"
        "                    // pasted-image-path recognition without pressing Enter.\n"
        "                    this.sendData('\\x1b[200~' + path + '\\x1b[201~');\n"
        "                    this.overlayAddon.showOverlay('Screenshot pasted', 1200);\n"
        "                }\n"
        "                break;\n"
        "            }\n"
        "            case Command.IMAGE_PASTE_ERROR:\n"
        "                if (this.imagePastePending) {\n"
        "                    this.imagePastePending = false;\n"
        "                    this.overlayAddon.showOverlay('Screenshot upload rejected', 1800);\n"
        "                }\n"
        "                break;\n",
    )
    replace_once(
        xterm,
        "    private applyPreferences(prefs: Preferences) {\n"
        "        const { terminal, fitAddon, register } = this;\n",
        "    private applyPreferences(prefs: Preferences) {\n"
        "        const { terminal, fitAddon, register } = this;\n"
        "        this.imagePasteEnabled = prefs.enableCodexImagePaste === true;\n",
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: apply-image-paste.py /path/to/pinned/ttyd-source")
    apply(Path(sys.argv[1]))
