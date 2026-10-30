# Issue #26 — local Supervisor hotfix acceptance (Codex runbook)

This branch is **not a release**. It derives from PR #27 but changes the HA App manifest to:

- name: Codex SSH Hotfix Test
- slug: codex_issue26
- version: 0.4.28-test.26.1
- boot: manual, stage: experimental
- no image: key, so Supervisor must build the included Dockerfile locally

## Hard safety rules

1. Do NOT alter the installed production App (historically e6fb3748_codex), its image, configuration, state, container, repository or restart it.
2. Do NOT force-reset or overwrite the existing deployment branch. It has its own divergent work.
3. Do NOT expose, copy, rotate or print private SSH keys or Supervisor tokens.
4. Do NOT modify the permissions or ownership of Home Assistant data as a repair. Existing ACL repair is out of scope.
5. Do NOT use direct Docker image replacement, direct host access escalation, or obtain privileged credentials to bypass the established HA Add-on permissions model.
6. Do NOT merge PR #27 or publish an official release as a result of this test.
7. If installation or test requires an unprovided Supervisor permission, stop there and provide the exact next UI step for the user. Do not silently claim deployment.

## Phase 1 — Read-only preflight

- Identify the active production installation and any Codex Deployment / legacy Codex Test installations. Use read-only metadata, not assumptions about current runtime.
- Confirm source HEAD is the issue26-local-test branch and the new manifest above; ensure package uses local Dockerfile, not production GHCR image.
- Determine the test App's full Supervisor slug after repository registration, not by guessing it.
- Record the owner, mode and existing *ACL metadata only* (no file contents) for /config/.ssh and any SSH key names, plus a normal workspace file. From within the Add-on equivalent paths are /homeassistant/.ssh etc.
- If the test would overwrite any existing App or repository, stop instead of installing.

## Phase 2 — Source checks (before deployment)

- Run bash -n for codex-start and codex-grant-access.
- Run python3 -m unittest discover -s codex/tests -v.
- If available, run ACL integration tests in an isolated temporary filesystem with real setfacl/getfacl, checking 0700 .ssh and 0600 private key, no access/default ACL changes, repeat execution twice, and a writable ordinary test file.
- Explicitly check owner-private files, keys outside .ssh, direct workdir nested in .ssh, symlinks to .ssh, and chmod fallback.
- Check that Dockerfile COPY rootfs/ supplies codex-grant-access and codex-start invokes it through bash.
- Fail closed on a test failure; don't deploy.

## Phase 3 — Install isolated test instance

Use **only** the dedicated test source:
https://github.com/CaneTLOTW/ha-codex#issue26-local-test

Preferred path: HA Settings > Add-ons > Add-on Store > Repositories, add this branch URL; refresh store; locate 'Codex SSH Hotfix Test'; click Install. Supervisor builds from Dockerfile because image is absent. Do not click a different 'Codex' item.

Codex may perform this only if it has an already-authorized Supervisor add-on management interface. The normal ha-codex CLI intentionally has no general Supervisor management token. If unavailable, ask the human to perform the UI installation and resume after it has been installed.

Leave 'Start on boot' disabled. Test App must use its own /data state and must not share production add-on data.

## Phase 4 — Runtime checks (only after explicit test installation)

- Inspect the test add-on logs for successful startup, no ACL/chmod errors, and no crash.
- Compare /config/.ssh and key owner/modes/ACL metadata with preflight. A previously damaged ACL must be reported, not automatically fixed.
- Start the test twice, comparing metadata each time.
- Verify a regular scratch YAML file under an authorized workspace can be accessed by the test Codex user; do not edit actual automations.
- If the owner had a representative SSH HA automation, ask permission before triggering it; otherwise check existing HA logs read-only for OpenSSH 'bad permissions'.
- Check the test CodeX session, MCP connectivity, and that the production App remains active and unchanged.
- Record all observations, logs with secrets redacted, test source SHA, and a PASS/FAIL/NOT TESTED matrix.

## Phase 5 — Cleanup and report

Stop the isolated test App when testing finishes; remove it only with user approval. Do not modify production.
Report precise remaining failures and recommended changes to PR #27; do not mark Issue #26 fixed or merge PR #27 until verified.
