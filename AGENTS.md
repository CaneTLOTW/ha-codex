# Repository development guardrails

These rules are mandatory for work in this repository. The detailed workflow is documented in [`docs/DEVELOPMENT_WORKFLOW.md`](docs/DEVELOPMENT_WORKFLOW.md) and must be read before changing runtime/build code.

## Branch discipline

- `deployment` is the development and runtime-acceptance branch.
- Do **not** modify, merge, rebase, or promote to `main` without explicit user approval.
- Treat chat handoffs, summaries, and remembered SHAs only as orientation. The live GitHub branch and current CI state are the source of truth.

## Re-ground after every session or chat restart

Before making a change:

1. Read the current `deployment` HEAD and version.
2. Inspect the exact current diff/state relevant to the task.
3. Inspect the current workflow, failed job, failed step, and original error output.
4. Do not diagnose or patch a CI failure from the overall workflow conclusion alone.

## Evidence-first CI

Track these gates independently; never collapse them into one status:

1. canonical patch applies cleanly;
2. static/regression validation passes;
3. target architectures compile/build;
4. images and multi-architecture manifest publish successfully;
5. runtime acceptance passes on the required clients.

A workflow can be red while a validation job is green. Always report the failing job/step precisely.

## ttyd rules

- Base remains ttyd `1.7.7` unless explicitly approved otherwise.
- Maintain exactly one canonical patch: `codex/ttyd-mobile-keys/ttyd-1.7.7-mobile-keys.patch`.
- No patch-on-patch chains and no permanent runtime `sed`/materializer layer.
- Temporary materializer workflows/scripts, if absolutely necessary, must be removed immediately after the canonical patch has been materialized.
- Make the smallest evidence-backed fix. No speculative refactors while fixing a concrete CI/runtime failure.
- Preserve accepted Desktop behavior; do not add a new Desktop selection engine or unrelated Desktop changes while working on Mobile behavior.

## Acceptance and promotion

- Do not ask for runtime testing until build **and** publish/manifest gates are green.
- Runtime findings must be documented and regression coverage updated where practical.
- Promotion to `main` happens only after runtime acceptance and explicit user approval.
