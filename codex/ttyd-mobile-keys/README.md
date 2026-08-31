# ttyd mobile controls

The Codex App builds ttyd 1.7.7 from source and applies one canonical
`ttyd-1.7.7-mobile-keys.patch` directly to that clean source tree before
building the customized frontend. No patch-on-patch chain is used.

The mobile toolbar adds `Esc`, `Tab`, `Enter`, one-shot `Ctrl`, `Alt`, and
`Shift`, persistent Shift Lock, arrow keys, `PgUp`/`PgDn`, explicit keyboard
show/hide buttons, and a `Sel` mode. On narrow/touch layouts the controls are
shown as a fixed two-row grid so the toolbar itself does not need horizontal
scrolling. The App's tmux configuration maps `PgUp` and `PgDn` to copy-mode
navigation when session persistence is enabled.

The current mobile row order is intentionally optimized for iOS reachability:

- row 1: `Enter`, `←`, `↓`, `↑`, `→`, `Sel`, `PgUp`, `Kbd↑`
- row 2: `Esc`, `Tab`, `Ctrl`, `Alt`, `Shift`, `⇪`, `PgDn`, `Kbd↓`

When ttyd is disconnected, the toolbar `Enter` uses the same manual reconnect path as a physical Enter key instead of trying to write to the closed WebSocket. In embedded Home Assistant ingress, the toolbar avoids adding a second iOS bottom safe-area inset because the parent panel already reserves that space.

One-shot modifiers are consumed only by modifier-eligible keyboard input. Mouse/touch
reporting sequences and multi-character paste do not clear them, so `Ctrl`/`Alt`/
`Shift` can be armed before `Kbd↑` or a prompt tap and still apply to the next key.

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
a separate xterm fork. On-device testing with Home Assistant Companion on an
iPhone 13 Pro has confirmed the two-row toolbar, `Sel` mode, native text
selection/copy, native paste, page navigation, Enter, and modifier handling.
The final mobile retest now covers `Kbd↑` reachability in the reordered toolbar,
toolbar-Enter reconnect while the WebSocket is closed, and the reduced embedded
safe-area padding in Home Assistant ingress.

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
