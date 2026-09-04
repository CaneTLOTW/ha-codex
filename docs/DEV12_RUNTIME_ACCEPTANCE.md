# dev.12 mobile keyboard avoidance – runtime acceptance record

This document records the implementation, CI recovery, temporary Gate 5 publish path, and completed runtime/release acceptance for `0.4.4-dev.12`.

## Status snapshot

| Item | State |
| --- | --- |
| Deployment version | `0.4.4-dev.12` |
| Behavioral source pinned for Gate 5 | `e26e6e571e51e628c754da5c353fa6fd94c5daac` |
| Canonical release source | `8d429a007db7eaed0df8ec5ae9c7750d9c8cfaf4` |
| Tracking issue | `#18` |
| iOS runtime acceptance | ✅ passed, user-confirmed 2026-09-04 |
| Desktop regression acceptance | ✅ passed, user-confirmed 2026-09-04 |
| Gate 5 amd64 image build | ✅ passed |
| Gate 5 amd64 publish/manifest | ✅ passed |
| Normal validation/build | ✅ passed — run `33921576192` |
| Normal amd64+aarch64 publish | ✅ passed — run `33921576250` |
| Normal multi-arch manifest | ✅ passed — run `33921576250` |
| Stable promotion | ✅ user-approved 2026-09-04; target `0.4.8` |

## Objective

The dev.12 change targets iOS/mobile keyboard behavior in the embedded ttyd terminal:

- opening the software keyboard must keep the active terminal/prompt usable above the keyboard;
- closing the software keyboard must restore the terminal layout cleanly;
- mobile terminal controls must remain usable;
- accepted Desktop behavior must not regress.

The dev.12 work must not reopen or replace the accepted Desktop selection/mouse behavior.

## Implementation scope

The canonical ttyd base remains `1.7.7` and the final implementation remains a single canonical patch:

`codex/ttyd-mobile-keys/ttyd-1.7.7-mobile-keys.patch`

The dev.12 keyboard-avoidance behavior uses the browser visual viewport to react to the mobile software keyboard while preserving the already accepted ttyd/mobile controls.

An earlier app-layer attempt was rejected because it referenced a Terminal API that did not exist in that build context. That approach was reverted and is not part of the accepted implementation.

## CI failure that blocked runtime testing

The final blocker was not GHCR, Docker, or the Home Assistant multi-architecture manifest.

The actual ttyd frontend build reached ESLint and failed on four instances of:

`@typescript-eslint/no-explicit-any`

in `html/src/components/terminal/index.tsx`.

The four type-only corrections are:

| Temporary dev.12 form | Correct typed form |
| --- | --- |
| `private keyboardViewport: any;` | `private keyboardViewport?: VisualViewport;` |
| `private keyboardResizeHandler: any;` | `private keyboardResizeHandler?: () => void;` |
| `const topWindow = window.top as any;` | `const topWindow = window.top;` |
| `return (window as any).visualViewport;` | `return window.visualViewport;` |

These are TypeScript type corrections only. They do not intentionally alter generated runtime behavior. They are now part of the canonical patch itself; no build-time replacement remains.

## Temporary Gate 5 recovery path

A temporary workflow was used to unblock runtime acceptance while the four lint-only corrections were still outside the canonical patch.

Successful Gate 5 run:

- workflow run: `33908497419`
- build job: ✅
- image push: ✅
- amd64 manifest publish: ✅

The temporary Gate 5 workflow was removed during finalization and is not part of the release pipeline.

## Runtime acceptance

### iOS / iPhone

**Status: ✅ passed**

User acceptance was reported on 2026-09-04 after installing the Gate 5 published `0.4.4-dev.12` image in Home Assistant.

The iOS result is accepted for the dev.12 keyboard-avoidance objective.

### Desktop

**Status: ✅ passed**

Desktop regression acceptance was user-confirmed on 2026-09-04. The accepted Desktop behavior remains intact, including:

- normal terminal input;
- terminal resize/layout behavior;
- mouse-wheel history scrolling;
- plain text selection/copy behavior;
- `Ctrl+Shift+V` paste;
- browser/OS right-click behavior;
- no regression from mobile-only controls or keyboard avoidance.

## Canonical release finalization

The final `deployment` release source is `8d429a007db7eaed0df8ec5ae9c7750d9c8cfaf4`.

Completed items:

1. the four TypeScript corrections are folded into `codex/ttyd-mobile-keys/ttyd-1.7.7-mobile-keys.patch`;
2. no permanent build-time `sed`/replacement layer remains;
3. the temporary Gate 5 workflow has been removed;
4. regression tests assert the typed canonical forms and reject the four old `any` forms;
5. normal validation and the independent amd64 validation build passed in run `33921576192`;
6. normal `amd64` and `aarch64` deployment image builds passed in run `33921576250`;
7. the normal deployment multi-architecture manifest passed in run `33921576250`;
8. iPhone and Desktop runtime acceptance both passed;
9. the user explicitly approved promotion to `main` on 2026-09-04.

## Stable promotion

At approval time, stable `main` is already at `0.4.7` and contains newer Codex CLI update commits. The accepted dev.12 product state is therefore promoted as **`0.4.8`**, while preserving the newer stable Codex CLI/tooling state rather than overwriting `main` with the older deployment metadata.

## Acceptance rule

Dev.12 is release-complete. Its final state is reproducible from GitHub through the normal validation and multi-architecture publication pipeline and no longer depends on the temporary Gate 5 mutation or chat history.
