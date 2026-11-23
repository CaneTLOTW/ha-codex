# Home Assistant Codex Deployment — Developer 0.5.0-dev.9 field acceptance

Developer-only candidate. Do **not** promote to Stable until actual Windows Firefox and iPhone Home Assistant results are recorded. Build success is not browser acceptance.

## Preconditions

- Existing stable Codex 0.5.0 untouched; only **Codex Deployment** updated.
- Back up Developer app data and check retained sessions/auth/config.
- Verify `direct_file_upload: true`. The separate legacy `file_transfer_enabled` / trzsz switch may remain false.
- Existing screenshot `clipboard_image_paste` remains independent.

## Desktop — Windows Firefox

1. Launch Codex TUI through HA Ingress. Confirm the slim **Upload / Bild / Datei / Ordner** dock under the active console, without terminal overlap. Collapse and expand; verify terminal rows refit.
2. While Codex remains running, click **Datei**, choose a harmless TXT/YAML/PDF file under 10 MiB. Check progress chip and inserted absolute path. Ask Codex to read text from the file; compare to local content.
3. Click **Bild**, choose PNG/JPEG. Check Codex image attachment `[Image #...]` and ability to describe a distinctive feature. Do not assume a displayed pathname is an attachment.
4. Click **Ordner**, select a small directory with nested files. Confirm each relative path is preserved inside the new private `upload-<32hex>` batch directory. Maximum 24 files/selection.
5. Expand drop zone, drag and drop files. Confirm status and no duplicate file. Folder drop depends on browser; folder-picker is the supported deterministic method.
6. Confirm Ctrl+V PNG screenshot (already accepted in dev.8), ordinary text Ctrl+V, context-menu paste, selection/copy, normal keyboard interaction and no accidental Enter/command execution.
7. Reject a file >10 MiB, malicious traversal filename, disallowed symlink, oversized batch, reconnect mid-upload. Verify no data outside private uploads tree.
8. A file path is **not** a guarantee that nonimage content is sent to the model. Codex must explicitly open/read it.

## iPhone — Safari / HA Companion

1. Open Developer Ingress. Confirm existing keyboard-avoidance and native text selection still work.
2. Default mobile accessory keys should offer **Datei / Bild / Anhänge / Sel / Tab / Ctrl / Mehr** with arrows and basic controls. **Mehr** must expose the existing technical keys including Alt, PgUp, PgDn and Capslock; switching back must restore the upload-first bar.
3. Tap **Anhänge** to expand/close the bottom sheet. Verify safe-area padding, keyboard appearance, no overflow or cropped Codex prompt.
4. Use **Datei** to pick via iOS Files app and **Bild** through the system image/photo picker; verify stored content and terminal insertion. Browser support for native folder picker may vary.
5. Verify touch text selection, paste, terminal reconnect, Ctrl/Alt/Shift controls, Enter/Esc, iOS keyboard show/hide and scroll after uploading.

## Security / lifecycle invariants

- Single authenticated ttyd WebSocket, no new port/HTTP route.
- Per-file limit 10 MiB, selection limit 24; stored in `/data/codex-home/users/anonymous/.codex/uploads/upload-<batch>/...`.
- Files are 0600 owned by uid 22000, directory tree is 0700, no-follow paths; writes use exclusive create and never overwrite existing files.
- No automatic deletion in this candidate. Inspect storage usage and decide retention/quota policy before Stable.
- Never post private screenshots, auth secrets, full Ingress URLs or file contents into public GitHub issues.

Successful build and multiarch publication should be recorded separately from real device acceptance.
