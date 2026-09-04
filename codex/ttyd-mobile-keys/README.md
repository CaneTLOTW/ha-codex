# ttyd mobile keys patch

This directory contains the single canonical patch applied to ttyd 1.7.7 by the
Codex add-on build. Keep the patch self-contained and regenerate it against a
clean ttyd 1.7.7 tree when behavior changes; do not stack follow-up patches.

The mobile toolbar adds touch-friendly terminal keys while preserving the
accepted desktop behavior. Mobile activation is capability-based rather than
viewport-width-based so narrow desktop windows do not get the mobile UI.

## iOS native selection and paste

`Sel` switches xterm to its DOM renderer and lets Safari own touch selection.
The helper textarea remains available so native long-press Paste can reach
xterm. Paste handling is captured and forwarded through xterm's `paste()` path,
with `beforeinput` and `input` fallbacks for `insertFromPaste`.

The keyboard buttons only show or hide the software keyboard and do not change
selection mode. Copy and native paste remain available while `Sel` is active.
This path deliberately does not use `navigator.clipboard.readText()` and is
separate from terminal `Ctrl+C` or `Ctrl+V` control sequences.

## Mobile keyboard avoidance

On touch/mobile clients, keyboard avoidance lives in the existing `Terminal`
mobile path and reuses the already accepted `touchControls` decision. There is no
second mobile detector and no separate `app.tsx` keyboard state machine.

The terminal listens only to `visualViewport.resize` (preferring an accessible
top-level viewport in Home Assistant ingress). While xterm's helper textarea is
the active element and the visual viewport shrinks by at least 120 px, the
existing terminal host is shortened by the same amount, xterm is fitted, and the
first opening transition scrolls the prompt into view. When the keyboard closes
or `Kbd↓` blurs xterm, the inline height is removed and the terminal is fitted
back to its normal size.

This does not toggle `Sel`, alter paste/input handling, or change the accepted
desktop selection path. The implementation is part of the one canonical ttyd
1.7.7 patch; no auxiliary or follow-up keyboard patch is used.

The dev.12 keyboard-avoidance path passed iPhone runtime acceptance and Desktop
regression acceptance on 2026-09-04. The four temporary Gate 5 TypeScript lint
workarounds were folded into the canonical patch before the normal multi-arch
release build; the temporary Gate 5 workflow was removed.

This behavior follows the same native DOM-selection direction discussed in
[xterm.js #3727](https://github.com/xtermjs/xterm.js/issues/3727) and implemented
by the in-progress [xterm.js PR #5961](https://github.com/xtermjs/xterm.js/pull/5961),
adapted at ttyd's integration layer so this App does not need a separate xterm
fork.

## Runtime validation

On-device testing with Home Assistant Companion on iPhone has confirmed the
fixed two-row toolbar, `Sel` mode, native text selection/copy, native paste,
page navigation, arrow navigation, `Enter`, modifier handling, mobile keyboard
avoidance, and the final mobile layout. Desktop regression testing has also
confirmed the accepted mouse/selection/input path remains intact.

The final implementation also contains the dedicated toolbar-Enter reconnect
path and the accepted desktop mouse-selection backport described below.

## Desktop selection behavior

Desktop remains intentionally separate from the touch/mobile path. Wheel input
continues to scroll terminal/tmux history. Plain left-drag is decorated as
xterm's forced-selection gesture; holding Alt leaves application mouse handling
untouched. tmux right-click bindings are removed while the browser/Windows
context menu remains available. Multi-screen-page selection scrolling is an
accepted limitation and is not replaced by a custom selection engine.

## Touch-only mobile activation

The mobile keybar, touch swipe handlers, mobile viewport wrapper, native
touch-selection mode, and keyboard-avoidance path are activated only when the
browser reports real touch capability (`navigator.maxTouchPoints > 0`) together
with an iOS/iPadOS/Android/mobile-platform signal or a coarse primary touch
pointer. A narrow desktop browser window no longer activates or renders the
mobile path. iPadOS desktop-style user agents are covered through `MacIntel`
plus multiple touch points.
