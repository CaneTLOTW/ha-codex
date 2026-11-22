# Desktop drag-selection auto-scroll (Issue #25)

## Scope

Plain left-drag selection and copying work for currently visible text. The remaining reported defect is **selecting across multiple terminal screens by holding the left mouse button and dragging beyond the viewport edge**. Do not mix in unrelated changes to iOS selection or terminal reconnect.

## Minimal test matrix

Test in a normal desktop browser, with 100+ lines of harmless generated output and no secrets:

| Mode | Left-drag visible text | Bottom edge scroll | Top edge scroll | Copy |
|---|---|---|---|---|
| Bare shell, mouse reporting off | Baseline | Baseline | Baseline | Baseline |
| Codex TUI, mouse reporting on | Baseline | Baseline | Baseline | Baseline |
| tmux session, mouse reporting on | Baseline | Baseline | Baseline | Baseline |
| Desktop touch-capable laptop, physical mouse | Baseline | Baseline | Baseline | Baseline |
| iPhone/iPad `Sel` | Existing accepted path | N/A | N/A | Existing accepted path |

## Candidate implementation criteria

If not already supported, implement edge-scroll **only while an actual desktop text-selection gesture is active**, not during normal mouse movement. Stop scrolling promptly on `pointerup`, cancellation or when crossing the terminal bounds. Do not hijack wheel events, application mouse reporting, Alt+drag or iOS/Android touch gestures. Ensure timer/animation-frame cleanup when the panel unmounts and on WebSocket reconnect.

A browser-specific edge-scroll adjustment must be tested on a disposable app image before being included in stable. The same canonical ttyd patch is also modified by #34; **do not independently merge overlapping patch hunks without rebasing and rerunning all terminal tests**.

**Status:** reproducible externally, not yet demonstrated on our runtime or implemented. Keep open until real desktop/iOS regression acceptance.
