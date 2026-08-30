# ttyd mobile controls

The Codex App builds ttyd 1.7.7 from source and applies one canonical
`ttyd-1.7.7-mobile-keys.patch` directly to that clean source tree before
building the customized frontend. No patch-on-patch chain is used.

The mobile toolbar adds `Esc`, `Tab`, `Enter`, one-shot `Ctrl`, `Alt`, and
`Shift`, persistent Shift Lock, arrow keys, `PgUp`/`PgDn`, a keyboard-dismiss
button, and an explicit `Sel` mode. On narrow/touch layouts the controls are
shown as a fixed two-row grid so the toolbar itself does not need horizontal
scrolling. The App's tmux configuration maps `PgUp` and `PgDn` to copy-mode
navigation when session persistence is enabled.

## iOS selection mode

Normal mobile mode keeps the terminal optimized for input and vertical swipe
page navigation. `Sel` temporarily changes that behavior on supported Apple
touch devices:

- ttyd switches xterm from the configured renderer (normally canvas) to the DOM
  renderer so terminal rows exist as selectable DOM text;
- native WebKit text selection and touch callouts are enabled for terminal rows;
- ttyd/xterm touch gesture handling is kept out of the way while native
  selection is active;
- the xterm helper textarea remains available for the native iOS paste path,
  with an `insertFromPaste` fallback routed through xterm's public `paste()`
  method;
- leaving `Sel` restores the requested renderer and normal swipe behavior.

The intended iOS interaction is: enable `Sel`, long-press/drag terminal output
and use the native iOS Copy action. For paste, use the native iOS Paste action
at the terminal input while `Sel` is active. This path deliberately does not
use `navigator.clipboard.readText()` and is separate from terminal `Ctrl+C` or
`Ctrl+V` control sequences.

This behavior is based on the native-selection approach being developed in
xterm.js for iOS, adapted at ttyd's integration layer so this App does not need
a separate xterm fork. Runtime behavior in Home Assistant Companion remains an
acceptance item until verified on-device.

Desktop selection and normal browser/terminal clipboard behavior remain native
ttyd/xterm behavior and are deliberately kept separate from the mobile controls.

To validate the patch against a clean ttyd source tree:

```bash
git clone --depth 1 --branch 1.7.7 https://github.com/tsl0922/ttyd.git /tmp/ttyd-1.7.7
git -C /tmp/ttyd-1.7.7 apply /path/to/ttyd-1.7.7-mobile-keys.patch
cd /tmp/ttyd-1.7.7/html
corepack enable
yarn install --immutable
yarn check
```

The customized ttyd frontend remains covered by ttyd's MIT license, included
beside this file.
