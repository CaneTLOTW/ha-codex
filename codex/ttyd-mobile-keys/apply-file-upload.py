#!/usr/bin/env python3
"""Layer the Developer direct-file upload UI/protocol onto pinned ttyd 1.7.7.

Run after the existing mobile-keys patch and screenshot-paste extension.
Strict anchors intentionally fail the build if upstream changes.
"""
from pathlib import Path
import sys


def replace_once(path: Path, before: str, after: str) -> None:
    src = path.read_text(encoding="utf-8")
    count = src.count(before)
    if count != 1:
        raise SystemExit(f"dev9 upload patch incompatible: {path}: {before[:70]!r}, count={count}")
    path.write_text(src.replace(before, after), encoding="utf-8")


def apply(root: Path) -> None:
    protocol = root / "src/protocol.c"
    server = root / "src/server.h"
    xterm = root / "html/src/components/terminal/xterm/index.ts"
    terminal = root / "html/src/components/terminal/index.tsx"
    style = root / "html/src/style/index.scss"

    replace_once(server, "  char image_reply[320];\n", "  char image_reply[1024];\n")
    replace_once(
        protocol,
        '#include "codex-image-paste.h"\n',
        '#include "codex-image-paste.h"\n#include "codex-file-upload.h"\n',
    )

    file_limit = r'''      /* File messages are bounded separately from terminal input and
       * handled only over the authenticated, writable ttyd socket. */
      if ((pss->buffer && pss->buffer[0] == CODEX_FILE_WS_REQUEST &&
           (len > CODEX_FILE_FRAME_MAX + 1 ||
            pss->len > CODEX_FILE_FRAME_MAX + 1 - len)) ||
          (!pss->buffer && len > 0 &&
           ((char *)in)[0] == CODEX_FILE_WS_REQUEST &&
           len > CODEX_FILE_FRAME_MAX + 1)) {
        lws_close_reason(wsi, LWS_CLOSE_STATUS_POLICY_VIOLATION, NULL, 0);
        return -1;
      }
'''
    replace_once(
        protocol,
        "      /* Never buffer an unbounded screenshot or arbitrary binary data. */\n",
        file_limit + "      /* Never buffer an unbounded screenshot or arbitrary binary data. */\n",
    )

    file_receive = r'''        case CODEX_FILE_WS_REQUEST: {
          const char *enabled = getenv("CODEX_FILE_UPLOAD_ENABLED");
          if (!server->writable || pss->process == NULL ||
              pss->image_reply_pending || enabled == NULL ||
              strcmp(enabled, "true") != 0) {
            snprintf(pss->image_reply, sizeof(pss->image_reply),
                     "%cDISABLED", CODEX_FILE_WS_ERROR);
          } else {
            char path[900];
            if (codex_file_save((const unsigned char *)pss->buffer + 1,
                                pss->len - 1, path, sizeof(path)) != 0) {
              int code = errno;
              snprintf(pss->image_reply, sizeof(pss->image_reply),
                       "%c%s", CODEX_FILE_WS_ERROR, codex_file_error_code(code));
            } else {
              snprintf(pss->image_reply, sizeof(pss->image_reply),
                       "%c%s", CODEX_FILE_WS_REPLY, path);
            }
          }
          pss->image_reply_pending = true;
          lws_callback_on_writable(wsi);
          break;
        }
'''
    replace_once(
        protocol,
        "        case CODEX_IMAGE_WS_REQUEST: {\n",
        file_receive + "        case CODEX_IMAGE_WS_REQUEST: {\n",
    )

    replace_once(
        xterm,
        "    IMAGE_PASTE_ERROR = '5',\n",
        "    IMAGE_PASTE_ERROR = '5',\n"
        "    FILE_UPLOAD_RESULT = '6',\n"
        "    FILE_UPLOAD_ERROR = '7',\n",
    )
    replace_once(
        xterm,
        "    IMAGE_PASTE_REQUEST = '4',\n",
        "    IMAGE_PASTE_REQUEST = '4',\n"
        "    FILE_UPLOAD_REQUEST = '6',\n",
    )
    replace_once(
        xterm,
        "    enableCodexImagePaste: boolean;\n",
        "    enableCodexImagePaste: boolean;\n"
        "    enableCodexFileUpload: boolean;\n",
    )
    replace_once(
        xterm,
        "    private imagePastePending = false;\n",
        "    private imagePastePending = false;\n"
        "    private fileUploadEnabled = false;\n"
        "    private fileUploadPending?: {\n"
        "        resolve: (path: string) => void;\n"
        "        reject: (error: Error) => void;\n"
        "    };\n",
    )
    replace_once(
        xterm,
        "        private transformInput: (data: string) => string = data => data\n",
        "        private transformInput: (data: string) => string = data => data,\n"
        "        private onFileUploadAvailability: (enabled: boolean) => void = () => {}\n",
    )

    upload_method = r'''    /** Serial file transfer over the existing HA Ingress terminal socket.
     * The server chooses a fixed private root, validates all path segments,
     * and returns a path only after the bytes are securely written. */
    public async uploadFiles(
        files: File[],
        progress: (index: number, status: 'uploading' | 'done' | 'error') => void
    ): Promise<void> {
        if (!this.fileUploadEnabled) throw new Error('Datei-Upload ist deaktiviert');
        if (!files.length || files.length > 24) throw new Error('Maximal 24 Dateien pro Auswahl');
        const socket = this.socket;
        if (!socket || socket.readyState !== WebSocket.OPEN) throw new Error('Terminal nicht verbunden');

        const random = new Uint8Array(16);
        crypto.getRandomValues(random);
        const batch = Array.from(random, b => b.toString(16).padStart(2, '0')).join('');
        const encoder = this.textEncoder;
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            progress(i, 'uploading');
            try {
                if (socket !== this.socket || socket.readyState !== WebSocket.OPEN) {
                    throw new Error('Terminal getrennt');
                }
                if (file.size > 10 * 1024 * 1024) {
                    throw new Error('Datei über 10 MiB');
                }
                const relative = file.webkitRelativePath || file.name;
                const parts = relative.split('/');
                if (
                    !relative ||
                    parts.length > 8 ||
                    parts.some(
                        part =>
                            !part ||
                            part === '.' ||
                            part === '..' ||
                            part.length > 120 ||
                            /[\u0000-\u001f\u007f\\]/.test(part)
                    )
                ) {
                    throw new Error('Ungültiger Dateiname');
                }
                const name = encoder.encode(relative);
                if (name.length > 480) throw new Error('Dateipfad über 480 Byte');
                const bytes = new Uint8Array(await file.arrayBuffer());
                if (socket !== this.socket || socket.readyState !== WebSocket.OPEN) {
                    throw new Error('Terminal getrennt');
                }
                const frame = new Uint8Array(35 + name.length + bytes.length);
                frame[0] = Command.FILE_UPLOAD_REQUEST.charCodeAt(0);
                frame.set(encoder.encode(batch), 1);
                frame[33] = name.length >> 8;
                frame[34] = name.length & 255;
                frame.set(name, 35);
                frame.set(bytes, 35 + name.length);

                const path = await new Promise<string>((resolve, reject) => {
                    const timeout = window.setTimeout(() => {
                        this.fileUploadPending = undefined;
                        reject(new Error('Upload-Zeitüberschreitung'));
                    }, 60000);
                    this.fileUploadPending = {
                        resolve: value => {
                            window.clearTimeout(timeout);
                            resolve(value);
                        },
                        reject: error => {
                            window.clearTimeout(timeout);
                            reject(error);
                        },
                    };
                    try {
                        socket.send(frame);
                    } catch (e) {
                        this.fileUploadPending = undefined;
                        window.clearTimeout(timeout);
                        reject(new Error('WebSocket-Upload fehlgeschlagen'));
                    }
                });

                const expected =
                    '/data/codex-home/users/anonymous/.codex/uploads/upload-' + batch + '/' + relative;
                if (path !== expected) throw new Error('Ungültige Server-Bestätigung');
                // Each image is inserted as its own bracketed paste, so Codex
                // can detect/attach it. Non-image paths remain available to read.
                if (i > 0) this.sendData(' ');
                this.sendData(String.fromCharCode(27) + '[200~' + path + String.fromCharCode(27) + '[201~');
                progress(i, 'done');
            } catch (error) {
                progress(i, 'error');
                throw error;
            }
        }
    }

'''
    replace_once(
        xterm,
        "    @bind\n    public sendData(data: string | Uint8Array) {\n",
        upload_method + "    @bind\n    public sendData(data: string | Uint8Array) {\n",
    )
    replace_once(
        xterm,
        "        this.imagePastePending = false;\n        this.manualReconnectPending = false;\n",
        "        this.imagePastePending = false;\n"
        "        this.fileUploadPending?.reject(new Error('Terminal getrennt'));\n"
        "        this.fileUploadPending = undefined;\n"
        "        this.manualReconnectPending = false;\n",
    )
    replace_once(
        xterm,
        "            case Command.IMAGE_PASTE_RESULT: {\n",
        r'''            case Command.FILE_UPLOAD_RESULT: {
                const pending = this.fileUploadPending;
                this.fileUploadPending = undefined;
                if (pending) pending.resolve(textDecoder.decode(data));
                break;
            }
            case Command.FILE_UPLOAD_ERROR: {
                const pending = this.fileUploadPending;
                this.fileUploadPending = undefined;
                if (pending) {
                    const code = textDecoder.decode(data);
                    pending.reject(new Error('Datei-Upload: ' + code.slice(0, 32)));
                }
                break;
            }
''' + "            case Command.IMAGE_PASTE_RESULT: {\n",
    )
    replace_once(
        xterm,
        "        this.imagePasteEnabled = prefs.enableCodexImagePaste === true;\n",
        "        this.imagePasteEnabled = prefs.enableCodexImagePaste === true;\n"
        "        this.fileUploadEnabled = prefs.enableCodexFileUpload === true;\n"
        "        this.onFileUploadAvailability(this.fileUploadEnabled);\n",
    )

    # The existing terminal component already owns mobile keys and native
    # selection; layer upload actions around it instead of replacing it.
    replace_once(
        terminal,
        "import { Component, h } from 'preact';\n",
        "import { Component, h, Fragment } from 'preact';\n",
    )
    replace_once(
        terminal,
        "    selectionMode: boolean;\n",
        "    selectionMode: boolean;\n"
        "    uploadEnabled: boolean;\n"
        "    uploadOpen: boolean;\n"
        "    technicalKeys: boolean;\n"
        "    uploadEntries: { name: string; status: string }[];\n",
    )
    replace_once(
        terminal,
        "    private host: HTMLElement;\n",
        "    private host: HTMLElement;\n"
        "    private filePicker?: HTMLInputElement;\n"
        "    private imagePicker?: HTMLInputElement;\n"
        "    private folderPicker?: HTMLInputElement;\n",
    )
    replace_once(
        terminal,
        "            selectionMode: false,\n",
        "            selectionMode: false,\n"
        "            uploadEnabled: false,\n"
        "            uploadOpen: false,\n"
        "            technicalKeys: false,\n"
        "            uploadEntries: [],\n",
    )
    replace_once(
        terminal,
        "this.xterm = new Xterm(props, this.showModal, this.transformInput);",
        "this.xterm = new Xterm(props, this.showModal, this.transformInput, this.setUploadEnabled);",
    )
    replace_once(
        terminal,
        "        await this.xterm.refreshToken();\n",
        "        if (this.folderPicker) this.folderPicker.setAttribute('webkitdirectory', '');\n"
        "        await this.xterm.refreshToken();\n",
    )
    replace_once(
        terminal,
        "    render({ id }: Props, { modal, ctrl, alt, shift, shiftLock, selectionMode }: State) {\n",
        "    render({ id }: Props, { modal, ctrl, alt, shift, shiftLock, selectionMode, uploadEnabled, uploadOpen, technicalKeys, uploadEntries }: State) {\n",
    )
    replace_once(
        terminal,
        "class={this.touchControls ? 'ttyd-touch-controls' : undefined}",
        "class={this.touchControls ? 'ttyd-touch-controls' : 'ttyd-upload-desktop'}",
    )
    replace_once(
        terminal,
        "                    if (!this.touchControls) this.container = c as HTMLElement;\n",
        "",
    )
    replace_once(
        terminal,
        "                {this.touchControls && (\n                    <div\n                        class=\"terminal-viewport\"\n",
        "                {(\n                    <div\n                        class=\"terminal-viewport\"\n",
    )

    mobile_nav = r'''                {this.touchControls && (
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
                )}
'''
    new_nav = r'''                {this.touchControls && (
                    <nav class="mobile-keys" aria-label="Terminal special keys">
                        {uploadEnabled && !technicalKeys ? (
                            <Fragment>
                                {this.renderUploadKey('Datei', this.chooseFiles)}
                                {this.renderUploadKey('Bild', this.chooseImages)}
                                {this.renderUploadKey('Anhänge', this.toggleUpload)}
                                {this.renderSelectionMode(selectionMode)}
                                {mobileKeys.slice(0, 2).map(this.renderMobileKey)}
                                {this.renderModifier('Ctrl', ctrl, 'ctrl')}
                                {this.renderMobileTechToggle()}
                                {mobileKeys.slice(2, 7).map(this.renderMobileKey)}
                                {this.renderKeyboardShow()}
                                {this.renderKeyboardDismiss()}
                                {this.renderModifier('Shift', shift, 'shift')}
                            </Fragment>
                        ) : (
                            <Fragment>
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
                                {uploadEnabled ? this.renderMobileTechToggle() : this.renderKeyboardDismiss()}
                            </Fragment>
                        )}
                    </nav>
                )}
'''
    replace_once(terminal, mobile_nav, new_nav)

    upload_elements = r'''                {uploadEnabled && (
                    <section class={this.touchControls ? 'codex-upload-sheet' : 'codex-upload-dock'}>
                        {!this.touchControls && (
                            <div class="codex-upload-toolbar">
                                <button type="button" onClick={this.toggleUpload} aria-expanded={uploadOpen}>
                                    {uploadOpen ? '▾' : '▸'} Upload
                                </button>
                                <button type="button" onClick={this.chooseImages}>▧ Bild</button>
                                <button type="button" onClick={this.chooseFiles}>＋ Datei</button>
                                <button type="button" onClick={this.chooseFolder}>▱ Ordner</button>
                                <span class="codex-upload-hint">Strg+V = Screenshot / Bild</span>
                            </div>
                        )}
                        {uploadOpen && (
                            <div class="codex-upload-expanded">
                                {this.touchControls && (
                                    <div class="codex-upload-title">
                                        <strong>Upload / Anhänge</strong>
                                        <button type="button" onClick={this.toggleUpload} aria-label="Schließen">×</button>
                                    </div>
                                )}
                                {this.touchControls ? (
                                    <div class="codex-upload-mobile-actions">
                                        <button type="button" onClick={this.chooseImages}>▧ Foto / Bild</button>
                                        <button type="button" onClick={this.chooseFiles}>▤ Dateien-App</button>
                                        <button type="button" onClick={this.chooseFolder}>▱ Ordner</button>
                                    </div>
                                ) : (
                                    <div
                                        class="codex-upload-dropzone"
                                        onDragOver={this.onUploadDragOver}
                                        onDrop={this.onUploadDrop}
                                    >
                                        Dateien hier ablegen oder über „Datei“ auswählen
                                        <small>Bis 10 MiB je Datei, maximal 24 Dateien pro Auswahl</small>
                                    </div>
                                )}
                                {uploadEntries.length > 0 && (
                                    <div class="codex-upload-attachments" aria-live="polite">
                                        <span>Anhänge ({uploadEntries.length})</span>
                                        {uploadEntries.map(item => (
                                            <span class="codex-upload-chip">
                                                {item.name} {item.status === 'done' ? '✓' : item.status === 'error' ? '✕' : '…'}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </section>
                )}
                <input
                    type="file"
                    multiple
                    ref={element => (this.filePicker = element as HTMLInputElement)}
                    class="codex-upload-hidden"
                    onChange={this.onFileChosen}
                />
                <input
                    type="file"
                    accept="image/*"
                    multiple
                    ref={element => (this.imagePicker = element as HTMLInputElement)}
                    class="codex-upload-hidden"
                    onChange={this.onFileChosen}
                />
                <input
                    type="file"
                    multiple
                    ref={element => (this.folderPicker = element as HTMLInputElement)}
                    class="codex-upload-hidden"
                    onChange={this.onFileChosen}
                />
'''
    replace_once(
        terminal,
        "                <Modal show={modal}>\n",
        upload_elements + "                <Modal show={modal}>\n",
    )

    terminal_actions = r'''    @bind
    private setUploadEnabled(enabled: boolean) {
        this.setState({ uploadEnabled: enabled });
    }

    @bind
    private toggleUpload() {
        this.setState(state => ({ uploadOpen: !state.uploadOpen }), () => this.xterm.fit());
    }

    @bind
    private toggleTechnicalKeys() {
        this.setState(state => ({ technicalKeys: !state.technicalKeys }), () => this.xterm.fit());
    }

    private renderUploadKey(label: string, action: () => void) {
        return (
            <button type="button" class="mobile-key" aria-label={label} onClick={action}>
                {label}
            </button>
        );
    }

    private renderMobileTechToggle() {
        return (
            <button
                type="button"
                class="mobile-key"
                aria-label="Weitere Terminaltasten"
                onClick={this.toggleTechnicalKeys}
            >
                Mehr
            </button>
        );
    }

    @bind
    private chooseFiles() {
        this.filePicker?.click();
    }

    @bind
    private chooseImages() {
        this.imagePicker?.click();
    }

    @bind
    private chooseFolder() {
        this.folderPicker?.click();
    }

    @bind
    private onFileChosen(event: Event) {
        const input = event.target as HTMLInputElement;
        const files = Array.from(input.files || []);
        input.value = '';
        if (files.length) this.beginUpload(files);
    }

    @bind
    private onUploadDragOver(event: DragEvent) {
        if (!event.dataTransfer?.types.includes('Files')) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = 'copy';
    }

    @bind
    private onUploadDrop(event: DragEvent) {
        if (!event.dataTransfer?.files.length) return;
        event.preventDefault();
        event.stopPropagation();
        this.beginUpload(Array.from(event.dataTransfer.files));
    }

    private async beginUpload(files: File[]) {
        if (!this.state.uploadEnabled) return;
        this.setState({
            uploadOpen: true,
            uploadEntries: files.map(file => ({ name: file.webkitRelativePath || file.name, status: 'queued' })),
        }, () => this.xterm.fit());
        try {
            await this.xterm.uploadFiles(files, (index, status) => {
                this.setState(state => ({
                    uploadEntries: state.uploadEntries.map((item, i) =>
                        i === index ? { ...item, status } : item
                    ),
                }));
            });
        } catch (error) {
            const message = error instanceof Error ? error.message : 'Unbekannter Upload-Fehler';
            this.setState(state => ({
                uploadEntries: state.uploadEntries.concat([{ name: message, status: 'error' }]),
            }));
        }
    }

'''
    replace_once(
        terminal,
        "    @bind\n    showModal() {\n",
        terminal_actions + "    @bind\n    showModal() {\n",
    )

    css = r'''
/* Developer direct-upload dock. The xterm viewport remains the flex child;
 * the collapsed desktop dock costs only one narrow toolbar row. */
.ttyd-upload-desktop .terminal-viewport {
  overflow: hidden;
}

.codex-upload-hidden {
  display: none;
}

.codex-upload-dock,
.codex-upload-sheet {
  box-sizing: border-box;
  flex: 0 0 auto;
  color: #cdd6f4;
  background: #242432;
  border-top: 1px solid #45475a;
  font: 12px/1.35 system-ui, -apple-system, sans-serif;
}

.codex-upload-toolbar {
  min-height: 32px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
}

.codex-upload-toolbar button,
.codex-upload-title button,
.codex-upload-mobile-actions button {
  padding: 4px 9px;
  color: #cdd6f4;
  background: #313244;
  border: 1px solid #585b70;
  border-radius: 6px;
  font: inherit;
  cursor: pointer;
  touch-action: manipulation;
}

.codex-upload-toolbar button:hover,
.codex-upload-mobile-actions button:active {
  background: #45475a;
}

.codex-upload-hint {
  margin-left: auto;
  color: #a6adc8;
}

.codex-upload-expanded {
  padding: 6px 9px 9px;
  max-height: 34vh;
  overflow: auto;
}

.codex-upload-dropzone {
  text-align: center;
  border: 1px dashed #74788f;
  border-radius: 7px;
  padding: 13px 8px;
  color: #cdd6f4;
  background: #303042;
}

.codex-upload-dropzone small {
  display: block;
  color: #a6adc8;
  padding-top: 4px;
}

.codex-upload-attachments {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 5px;
  padding-top: 6px;
}

.codex-upload-chip {
  display: inline-block;
  max-width: min(220px, 90vw);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: #414155;
  border-radius: 5px;
  padding: 4px 7px;
}

.codex-upload-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 8px;
}

.codex-upload-mobile-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
}

.codex-upload-mobile-actions button {
  min-height: 44px;
}

@media (hover: none), (pointer: coarse), (max-width: 768px) {
  .codex-upload-sheet {
    border-radius: 14px 14px 0 0;
  }

  .codex-upload-sheet .codex-upload-expanded {
    padding: 10px max(8px, env(safe-area-inset-right))
      10px max(8px, env(safe-area-inset-left));
  }

  .codex-upload-hint {
    display: none;
  }
}
'''
    style.write_text(style.read_text(encoding="utf-8") + css, encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: apply-file-upload.py /path/to/pinned/ttyd-source")
    apply(Path(sys.argv[1]))
