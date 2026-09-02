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

This behavior follows the same native DOM-selection direction discussed in
[xterm.js #3727](https://github.com/xtermjs/xterm.js/issues/3727) and implemented
by the in-progress [xterm.js PR #5961](https://github.com/xtermjs/xterm.js/pull/5961),
adapted at ttyd's integration layer so this App does not need a separate xterm
fork.

## Runtime validation

On-device testing with Home Assistant Companion on iPhone has confirmed the
fixed two-row toolbar, `Sel` mode, native text selection/copy, native paste,
page navigation, arrow navigation, `Enter`, modifier handling, and the final
mobile layout. The validated `0.4.0` runtime uses Codex CLI `0.151.0`,
`gpt-5.6-sol`, and `/homeassistant` as the working directory.

The final implementation also contains the dedicated toolbar-Enter reconnect
path and avoids a duplicate bottom safe-area inset inside Home Assistant
ingress. These are covered by the maintained patch/regression contract; future
ttyd/xterm changes should keep them in the same canonical patch rather than
adding another patch layer.

Desktop selection remains separate from the mobile controls. On desktop, persistent
tmux sessions keep mouse reporting enabled so wheel scrolling/history continues to
work. Because ttyd 1.7.7 is pinned to xterm 5.x, the frontend backports the behavior
of xterm's newer `mouseEventsRequireAlt` arbitration at the integration layer: plain
left-drag is decorated as xterm's existing forced-selection gesture, wheel events are
left untouched for tmux, and holding Alt leaves application mouse interaction alone.
This does not add a second selection implementation or a second ttyd patch.

On iOS, `Sel` uses Safari's native DOM selection. The helper textarea remains
available at the cursor for the native Paste action; paste events are captured
once and forwarded through xterm's `paste()` API. While `Sel` is active Safari
owns touch gestures consistently, and DOM measurement helpers are hidden from
the selection layout. Desktop mouse arbitration is unchanged by this path.

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

### Touch-only mobile activation

The mobile keybar, touch swipe handlers, mobile viewport wrapper, and native touch-selection mode are activated only when the browser reports real touch capability (`navigator.maxTouchPoints > 0`) together with an iOS/iPadOS/Android/mobile-platform signal or a coarse primary touch pointer. A narrow desktop browser window no longer activates or renders the mobile path. iPadOS desktop-style user agents are covered through `MacIntel` plus multiple touch points.
