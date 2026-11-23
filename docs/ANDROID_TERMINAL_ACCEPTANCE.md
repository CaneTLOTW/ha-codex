# Android terminal acceptance checklist (Issue #6)

The terminal is currently accepted on iOS and desktop. Generic touch controls are expected to work on Android, but there is **no real Android acceptance report** as of 2026-11-22. Apple-only `Sel` cannot be described as Android-supported.

## Reproduction template

Record Android version, HA Companion version or browser/version, device orientation, visible terminal width, user input type (soft keyboard vs physical keyboard), app version and Codex/ttyd version. Do not include ingress session URLs, access tokens, or private terminal output.

For each device configuration, test:
1. `Enter`, arrows, `Esc`, `Tab`, Ctrl/Alt/Shift/Shift Lock.
2. `PgUp`, `PgDn`, swipe/history navigation with `session_persistence: true` and `false`.
3. Keyboard show/hide, foreground/background transition and resuming without lost input.
4. Long output, long command, screen rotation, copy and paste.
5. `Sel` behavior: verify it is unavailable or explicitly disabled on Android; do not promise iOS native-selection parity.
6. WebSocket disconnect/reconnect behavior and preservation of tmux session (see #34).

## Acceptance criteria

- No hidden modifier states, stuck keyboard or unexpected focus loss.
- No regression in desktop and iOS control paths.
- Document first tested Android device and exact versions as known-good.
- Any native Android copy/paste work gets its own bounded issue and separate build.

**Status:** hardware test pending. CI or simulated browser tests alone cannot close this issue.
