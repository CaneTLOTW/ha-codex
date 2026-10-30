# Issue 26 build/deployment readiness recheck

Date: 2026-10-30
Source branch: `issue26-local-test`
Source HEAD: `5834742e21c21a23bb7ec8a9630f7f1e912cebf1`
Compared PR source: local `origin/pr27` at `d01d178ea5e1bbd2e6c7606a2efe03c8dca12c34`

## Decision

**READY FOR TEST INSTALLATION** is the provisional decision, contingent on Luna A completing the genuine-failing-`setfacl` probe and the coordinator gate passing. Until both are recorded as passing, do not install. This is readiness for a dedicated Supervisor local-build test; it does not certify that either architecture has built successfully.

## Findings

- `codex/config.yaml` identifies the test as `Codex SSH Hotfix Test`, slug `codex_issue26`, version `0.4.28-test.26.1`, `boot: manual`, and `stage: experimental`. It declares `amd64` and `aarch64` and has no `image:` field; Supervisor should therefore build from the included Dockerfile. Production manifest identity is `Codex` / `codex` / `0.4.28` with a GHCR image. The manifest slug is distinct, and the package source is configured for a local build.
- Bounded Dockerfile checks are recorded in `dockerfile_static_results.txt`; the checker and exact command are `check_dockerfile_static.py`. It scans continued logical instructions, skips COPY heredoc bodies, ran `bash -n` on all nine actual shell-form RUN payloads without executing them, parsed JSON ENTRYPOINT/CMD, and verified both non-heredoc COPY sources exist under the `codex/` build context. This is not full Dockerfile frontend validation. The Dockerfile downloads the HA CLI separately for `amd64` and `aarch64`, and uses Alpine packages plus Node/npm and native ttyd compilation. Those choices are statically consistent with the manifest architectures; actual base-image availability, dependency resolution, compilation, image creation, and runtime compatibility remain **NOT TESTED**.
- Compared against the available current `origin/pr27` ref, `codex/rootfs/usr/local/bin/codex-grant-access`, `codex/rootfs/usr/local/bin/codex-start`, and `codex/tests/test_ssh_acl_protection.py` are byte-for-byte unchanged. The intentional local-test manifest differences are identity/version, boot/stage, and omission of the production GHCR image. The UI may not expose a commit SHA. Confirm the repository branch/version is `issue26-local-test` and the displayed manifest identifies the test version; the coordinator’s Git pin is the commit-level source evidence. The final coordinator HEAD may be a docs-only descendant of `5834742e...`, which is acceptable; do not require the UI to display the original SHA.
- No read-only Supervisor add-on inventory/management interface is available in this session. Do not infer the full Supervisor add-on slug from `codex_issue26`: repository registration may qualify it. The UI must show the expected test item/full slug and no existing test installation/repository collision before proceeding. If the item is ambiguous or an existing installation would be replaced, stop.
- The test manifest retains `hassio_role: manager`, but this does not grant this agent Supervisor management access. No management token was read or extracted. Installation is a user UI action under the acceptance runbook.

## Safe UI steps

1. Wait until Luna A’s genuine-failing-`setfacl` probe and the coordinator gate are recorded as passing. In Home Assistant, open **Settings → Apps → App Store → Repositories** (label may appear as Add-on Store on older UI versions). Add `https://github.com/CaneTLOTW/ha-codex#issue26-local-test`, then refresh the store.
2. Confirm the repository branch is `issue26-local-test`. The UI may not expose a commit SHA: use the coordinator’s Git pin for commit evidence; a final docs-only descendant of `5834742e...` is acceptable. Locate the exact item **Codex SSH Hotfix Test**. Confirm its displayed identity/version match `codex_issue26` / `0.4.28-test.26.1`, and inspect the full Supervisor slug.
3. Before clicking Install, confirm the full slug is not already installed and that the UI is not offering the production `Codex` item (`codex`, `0.4.28`). If any collision or ambiguity appears, stop without installing.
4. Install only **Codex SSH Hotfix Test**. Supervisor should build locally because this manifest has no image reference. Leave **Start on boot** disabled. Do not install/start/update the production item.
5. If Supervisor reports missing permissions, a build failure, or an unexpected source/image, stop and record the exact UI error. Do not bypass the Supervisor permission boundary.

## Gate status

- Manifest identity/local Dockerfile source: **PASS (static)**
- Helper packaging and bash invocation: **PASS (static)**
- PR27 shared helper/startup/test equality: **PASS (ref comparison)**
- Dockerfile bounded syntax/consistency check: **PASS (not full frontend validation)**
- `amd64` build: **NOT TESTED**
- `aarch64` build: **NOT TESTED**
- Genuine-failing-`setfacl` probe / coordinator gate: **PENDING; installation blocked until pass**
- Full Supervisor slug / repository collision: **UI confirmation required before install**
- Supervisor install authorization from this agent: **UNAVAILABLE**
- Runtime acceptance: **NOT STARTED**
