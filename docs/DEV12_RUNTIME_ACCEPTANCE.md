# dev.12 mobile keyboard avoidance – runtime acceptance record

This document records the implementation, CI recovery, temporary Gate 5 publish path, and runtime acceptance state for `0.4.4-dev.12`.

It is intentionally a **working acceptance record** until Desktop regression testing and normal multi-architecture publishing are complete.

## Status snapshot

| Item | State |
| --- | --- |
| Deployment version | `0.4.4-dev.12` |
| Behavioral source pinned for Gate 5 | `e26e6e571e51e628c754da5c353fa6fd94c5daac` |
| `deployment` HEAD while this record was prepared | `f96eea951169546a8eccb542a61a5b17eb30de5d` |
| Tracking issue | `#18` |
| iOS runtime acceptance | ✅ passed, user-confirmed 2026-09-04 |
| Desktop regression acceptance | ⏳ pending |
| Gate 5 amd64 image build | ✅ passed |
| Gate 5 amd64 publish/manifest | ✅ passed |
| Normal amd64+aarch64 release path | ⏳ not yet finalized |
| `main` | untouched |

## Objective

The dev.12 change targets iOS/mobile keyboard behavior in the embedded ttyd terminal:

- opening the software keyboard must keep the active terminal/prompt usable above the keyboard;
- closing the software keyboard must restore the terminal layout cleanly;
- mobile terminal controls must remain usable;
- accepted Desktop behavior must not regress.

The dev.12 work must not reopen or replace the accepted Desktop selection/mouse behavior.

## Implementation scope

The canonical ttyd base remains `1.7.7` and the intended end state remains a single canonical patch:

`codex/ttyd-mobile-keys/ttyd-1.7.7-mobile-keys.patch`

The dev.12 keyboard-avoidance behavior uses the browser visual viewport to react to the mobile software keyboard while preserving the already accepted ttyd/mobile controls.

An earlier app-layer attempt was rejected because it referenced a Terminal API that did not exist in that build context. That approach was reverted and must not be resurrected without a new design review.

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

These are TypeScript type corrections only. They do not intentionally alter generated runtime behavior.

## Temporary Gate 5 recovery path

A temporary workflow was added:

`.github/workflows/gate5-amd64-runtime.yml`

Purpose:

1. check out the behavioral dev.12 source at `e26e6e571e51e628c754da5c353fa6fd94c5daac`;
2. verify version `0.4.4-dev.12`;
3. apply only the four type corrections above in the CI checkout;
4. build the real `codex/Dockerfile` for `amd64`;
5. capture and post actionable build diagnostics to issue `#18` on failure;
6. push the amd64 image;
7. publish a single-architecture `0.4.4-dev.12` manifest so the Home Assistant runtime test can proceed.

Successful Gate 5 run:

- workflow run: `33908497419`
- build job: ✅
- image push: ✅
- amd64 manifest publish: ✅

This workflow is a **temporary acceptance/recovery mechanism**, not the desired permanent production pipeline.

## Runtime acceptance

### iOS / iPhone

**Status: ✅ passed**

User acceptance was reported on 2026-09-04 after installing the Gate 5 published `0.4.4-dev.12` image in Home Assistant.

The iOS result is accepted for the dev.12 keyboard-avoidance objective.

### Desktop

**Status: ⏳ pending**

The Desktop regression check must confirm that previously accepted behavior remains intact, especially:

- normal terminal input;
- terminal resize/layout behavior;
- mouse-wheel history scrolling;
- plain text selection/copy behavior;
- `Ctrl+Shift+V` paste;
- browser/OS right-click behavior;
- no regression from mobile-only controls or keyboard avoidance.

Do not mark dev.12 fully accepted until this check is recorded.

## Required finalization after Desktop passes

Once Desktop is confirmed green:

1. fold the four TypeScript corrections into `codex/ttyd-mobile-keys/ttyd-1.7.7-mobile-keys.patch` itself;
2. ensure no permanent build-time `sed`/replacement layer remains for this fix;
3. remove or neutralize the temporary Gate 5 recovery workflow once it is no longer needed;
4. run the normal validation/build pipeline from the resulting `deployment` HEAD;
5. require normal `amd64` and `aarch64` builds to pass;
6. publish the normal multi-architecture deployment manifest;
7. update this record with the final commit SHA, workflow run IDs, and Desktop result;
8. update issue `#18` and close it only when all acceptance criteria are satisfied;
9. keep `main` untouched until the user explicitly approves promotion.

## Acceptance rule

The successful amd64 Gate 5 run proves that the dev.12 runtime behavior can be built and tested after the demonstrated type-only lint fix. It does **not** replace the requirement to restore the canonical patch and normal multi-architecture pipeline before dev.12 is considered release-complete.

The final state must remain reproducible from GitHub without relying on chat history or an undocumented CI mutation.
