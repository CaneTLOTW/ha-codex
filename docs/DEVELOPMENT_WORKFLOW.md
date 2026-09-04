# Development workflow

This document defines the authoritative working method for changes in `CaneTLOTW/ha-codex`. Its purpose is to prevent process drift after chat/session handovers and to keep GitHub, CI, publishing, and runtime acceptance clearly separated.

## 1. Source of truth and session re-grounding

A chat transcript, handoff, remembered SHA, or previous status report is **not** the authoritative current state. After every new session, reactivated chat, or substantial interruption, re-ground against GitHub before changing code.

Required pre-change checks:

1. Fetch the live `deployment` branch and record its current HEAD.
2. Read the current add-on version from the repository.
3. Inspect the exact files/diff relevant to the task.
4. Fetch the latest relevant GitHub Actions workflow run.
5. For a failure, identify the exact failed job and failed step and read the original error output.

Do not infer the current failure from an older handoff if live CI is available.

## 2. Branch discipline

| Branch | Purpose | Rule |
| --- | --- | --- |
| `deployment` | Development, experimental builds, runtime acceptance | Normal working branch |
| `main` | Accepted/stable state | No modification, merge, rebase, or promotion without explicit user approval |

Never use an unrelated repository as an upstream/write target merely because similar source code exists there.

## 3. Five independent quality gates

Always track and report these separately:

| Gate | Meaning | Typical evidence |
| --- | --- | --- |
| 1. Patch | Canonical ttyd patch applies cleanly | patch/apply check |
| 2. Validate | Static checks and regression tests pass | validation job/tests |
| 3. Build | Required target architectures compile/build | `amd64` / `aarch64` build jobs |
| 4. Publish | Images and final multi-arch manifest exist | publish jobs + manifest |
| 5. Runtime | Required real clients behave correctly | PC/iPhone/Home Assistant acceptance |

A green job does not make a red workflow green, and a red workflow does not mean every job is red. Never use phrases such as “Validate is green/red” without distinguishing the workflow from the relevant job when that distinction matters.

Runtime testing starts only after Gates 1–4 are green.

## 4. Evidence-first failure analysis

For every CI/build failure, use this order:

`workflow → failed job → failed step → original error → affected source → minimal fix`

Rules:

- Do not patch based only on the overall workflow conclusion.
- Do not patch based only on a visual diff or a plausible hypothesis when the current error output can be obtained.
- Preserve the original error message in the working notes/status until the fix is verified.
- Change only what is necessary to address the demonstrated failure.
- After the change, run the normal gates again instead of assuming the fix worked.

If CI output cannot be obtained, state that limitation and do not disguise a hypothesis as a diagnosis.

## 5. ttyd patch discipline

The ttyd base remains `1.7.7` unless explicitly approved otherwise.

There is exactly one canonical patch:

`codex/ttyd-mobile-keys/ttyd-1.7.7-mobile-keys.patch`

Mandatory rules:

- No patch-on-patch chains.
- No second ttyd behavior patch for the same feature.
- No permanent build/runtime `sed` layer that mutates the already-patched source.
- A temporary materializer may be used only when repository tooling makes a direct canonical-patch edit impractical; its result must be folded into the canonical patch and the temporary workflow/script removed immediately.
- Keep regression tests aligned with intentional patch behavior.

## 6. Preserve accepted Desktop behavior

Desktop ttyd behavior is an accepted baseline and must not be casually reopened while working on Mobile issues.

Accepted behavior includes:

- mouse wheel scrolls terminal history/output;
- plain text selection works without Shift;
- selection can be copied;
- `Ctrl+Shift+V` paste works;
- tmux right-click menu is removed while normal browser/OS right-click remains;
- tmux mouse remains enabled;
- `MouseDown3Pane` and `M-MouseDown3Pane` are unbound;
- plain left-drag follows the accepted forced-selection behavior, wheel handling stays untouched, and Alt preserves application mouse behavior;
- unreliable selection scrolling over multiple screen pages is an accepted limitation.

Do not introduce a new Desktop selection engine or unrelated Desktop workaround during Mobile development.

## 7. Minimal commits and CI triggering

Prefer small, attributable commits that answer one question at a time: documentation, regression lock, compiler fix, runtime fix, etc.

Be aware that commits created by a GitHub Actions `GITHUB_TOKEN` may not trigger another workflow run. Do not interpret the absence of a new run as a successful validation. When a normal CI rerun is required, use a repository write/ref update that actually triggers the configured workflow and verify that a new run belongs to the intended HEAD.

## 8. Publish and runtime acceptance

Do not tell the user to install/test a development version until:

- the canonical patch applies;
- static/regression validation is green;
- all required architecture builds are green;
- the publish stage and multi-architecture manifest are green/available.

During runtime acceptance, verify only the intended behavior first and explicitly check that previously accepted behavior has not regressed. Record runtime findings in the relevant documentation/tests before considering promotion.

## 9. Promotion

Promotion is a separate decision, not an automatic consequence of a successful build.

Required order:

1. all CI/publish gates green;
2. required runtime smoke/acceptance tests green;
3. documentation/regressions current;
4. promotion plan reviewed;
5. explicit user approval;
6. only then modify/merge `main`.

## 10. Status-report template

For development status, report concrete evidence in this form where applicable:

- `deployment` HEAD: `<sha>`
- version: `<version>`
- Patch gate: ✅/❌
- Static/regression job: ✅/❌
- `amd64` build: ✅/❌
- `aarch64` build: ✅/❌
- Multi-arch publish/manifest: ✅/❌
- Runtime PC: ✅/❌/not started
- Runtime iPhone/mobile: ✅/❌/not started
- `main`: untouched / explicitly approved change

The objective is reproducibility: a new chat or a different agent should be able to resume work from GitHub and CI without relying on unstated conversational context.
