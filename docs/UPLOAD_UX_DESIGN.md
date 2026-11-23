# Image and file upload design (Issue #13)

## Goal

Bring an explicit upload path to the Home Assistant Codex terminal without disturbing established text selection, copy/paste, iOS `Sel` mode, or other terminal input.

## Proposed first increment

- File-picker button (desktop and mobile) for **image files only**.
- Desktop drag/drop and clipboard paste as later opt-in enhancements, only when browsers permit them.
- Accept `image/png`, `image/jpeg`, `image/webp` with server-side MIME/content inspection and a strict size cap (proposal: 10 MiB/file, 5 files per transaction).
- Write with generated unpredictable filenames to a per-session staging folder under **private persistent App data**, e.g. `/data/codex-uploads/<session-id>/`; never write arbitrary user-supplied paths.
- Use atomic writes, reject symlink/path traversal and normalize filenames; default `0600` file permissions under the Codex UID. No executable upload.
- Provide a visible in-terminal path that the active Codex session can read, without leaking the upload into shared public folders.
- Define cleanup: user-triggered removal and automatic expiry; document that persistent `/data` survives app restarts.
- Require same-origin ingress session authorization and CSRF/security review; do not expose a new unauthenticated host port.

## Architecture constraints

A browser picker alone is not a complete transfer service. The current ttyd modal/file input is associated with the optional Zmodem/Trzsz path and does not prove arbitrary image paste/upload support in the running Codex image. Do not claim it works without runtime verification.

Option A: a narrow authenticated upload handler in the existing ingress web service, forwarding the staging path to Codex.
Option B: test an existing ttyd-compatible transfer protocol end-to-end and use it only if correctly authenticated and available across HAOS/Firefox/iOS.

Do not expand host privileges, copy credentials, enable direct internet exposure, or bypass normal HA ingress auth.

## Required acceptance matrix

| Test | Desktop Firefox | Desktop Chrome | iOS HA Companion | Android HA Companion |
|---|---|---|---|---|
| File picker -> stage file -> Codex read | Pending | Pending | Pending | Pending |
| Drag/drop | Pending | Pending | N/A | N/A |
| Clipboard image paste | Pending | Pending | Pending | Pending |
| Text paste / selection unchanged | Pending | Pending | Pending | Pending |
| Oversize, MIME and filename rejection | Pending | Pending | Pending | Pending |
| Cleanup, stop/restart and auth isolation | Pending | Pending | Pending | Pending |

**Status:** design only; implementation requires a separate reviewed PR and security tests.
