# HA-Codex Deployment 0.5.0-dev.6 — Screenshot Ctrl+V acceptance

**Experimental Developer only.** Stable `Codex` 0.5.0 remains unchanged. This candidate extends the accepted dev.5 `trzsz` file transfer with *live* image clipboard paste using the existing HA ingress terminal WebSocket. It does not introduce another listening port or separate upload HTTP endpoint.

## Preparation

1. Identify the **live** Home Assistant Supervisor App IDs and installed versions. Back up **Codex Deployment** state and current options; do not copy Stable auth, SQLite, project files or login tokens into Developer.
2. Update **Codex Deployment** from the `#deployment` repository to `0.5.0-dev.6`. Preserve `remote_control_enabled: false`, current `session_persistence`, `addons_access` and other options.
3. The new `clipboard_image_paste` option is **true** by default in Developer; explicitly enable and save it if a previous options file lacks it. Restart **Developer only**.
4. Use Windows Firefox on the normal Home Assistant ingress URL (including LAN HTTP, if applicable). Keep the existing working Codex TUI visible; **do not exit it**.

## Required user acceptance (record PASS/FAIL/BLOCKED)

| Step | Procedure | Evidence and pass criterion |
|---|---|---|
| 1. Live screenshot | Press **Win+Shift+S**, select a harmless area, focus Codex's input, press **Ctrl+V** | Screenshot accepted without a browser file picker, shell command or reload. No unexpected terminal key sequence or automatic submission |
| 2. Codex attachment | Look for an attached-image placeholder such as `[Image #1]`, add a question about a distinctive visual feature, press Enter | Codex accurately describes the **image content**. Merely inserting the pathname as text is **not a pass** |
| 3. Second screenshot | Repeat in same session with another harmless screenshot | Two different image attachments work; no duplicate attachment |
| 4. Text paste unchanged | Ctrl+V an ordinary sentence and URL | Text appears normally. No image-upload attempt |
| 5. Unsupported format | If possible, paste a copied non-PNG image (JPEG/WebP) | Normal browser behavior or clear no-action; no corrupted PNG saved. Current implementation supports only PNG |
| 6. Oversized file | Use synthetic PNG larger than 10 MiB (no private screenshots) | Graceful rejection, no browser/terminal crash, no uncontrolled process memory growth |
| 7. Privacy and files | From Developer shell, inspect `$CODEX_HOME/uploads` using `ls -l` (avoid printing image data) | Random `clipboard-*.png` names, uid 22000, files 0600, directory 0700, only PNGs; no traversal or symlink |
| 8. Browser context | Use the normal LAN HTTP Home Assistant URL and, optionally, HTTPS origin | The DOM `paste` ClipboardEvent works; no reliance on `navigator.clipboard.read` requiring secure context |
| 9. TUI lifecycle | Ctrl+C → `codex` → `codex resume --last`; switch browser tab, reconnect WebSocket | SQLite session/history intact, CLI still works, no EACCES, images only pasted on active connection |
| 10. Mobile/selection | Verify desktop mouse selection/copy and iPhone/iPad `Sel`/text copy/paste if available | No regressions; Android real-device acceptance remains separate #6 |
| 11. Disabled setting | Set `clipboard_image_paste: false`, restart Developer, attempt Ctrl+V image | New upload handler is disabled; ordinary paste remains. Restore true if tests pass |
| 12. Other App configs | Check that the dev.5 `/app_configs` RO mount remains RO | No altered Supervisor mount, AppArmor privileges or access settings |

## Protocol and security

- Browser captures `image/png` from a trusted `ClipboardEvent`, *only while the xterm input is focused*. It sends a bounded binary message to the already authenticated ttyd WebSocket; no public port, endpoint or cross-site form API.
- The server validates writable + initialized PTY, explicit server-side `CODEX_IMAGE_PASTE_ENABLED`, size <=10 MiB, PNG signature and IHDR. It opens every fixed directory through `openat(O_NOFOLLOW)`, generates 128-bit random basenames, and writes with owner UID 22000 / mode 0600.
- Only the generated absolute pathname is acknowledged over the socket. The browser verifies the fixed path pattern and sends the path as **bracketed paste**, without pressing Enter.
- Never print image bytes, original clipboard data, HA ingress session URLs, private file contents or secrets to GitHub. Failed transfers must not retry automatically or submit a prompt.
- PNG files are intentionally preserved for Codex session history; periodic retention/quota management is not yet part of this first acceptance candidate.

## Rollback

If anything fails: disable `clipboard_image_paste` in Developer and restart only Developer. If core terminal is affected, roll back **Codex Deployment** to published `0.5.0-dev.5` with its backed-up settings and data. **Stable 0.5.0 must remain running unchanged.**

References: <https://github.com/CaneTLOTW/ha-codex/issues/13> (live screenshot UX), <https://github.com/CaneTLOTW/ha-codex/issues/51> (dev.5 transfer), and upstream <https://github.com/openai/codex/blob/rust-v0.171.0/codex-rs/tui/src/bottom_pane/chat_composer/paste_input.rs>.
