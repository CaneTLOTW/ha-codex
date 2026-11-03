# Deployment-only HAOS acceptance: 0.4.30-dev.2 / Issues #24, #29, #26, #25, #14

This is a **runbook, not permission to install**. The code must first pass a PR review, be merged to the Deployment branch after explicit operator approval, and pass the multi-architecture publish workflow. Stable remains untouched.

## Preflight (read-only; STOP if unavailable)

1. Identify the actual full Supervisor identifiers. Previous evidence: Stable e6fb3748_codex at 0.4.30; Deployment 1e25a555_codex at 0.4.10-dev.2. Re-read the **current** values rather than assuming these are still correct.
2. Confirm distinct repository identities, the deployment image version, running states, options and update availability. Both app instances must have **auto_update: false**. Keep Deployment **boot: manual**.
3. Confirm that the reviewed 0.4.30-dev.2 image is available in the Deployment repository, not in Stable. Record installed Deployment version, image identity, saved settings and a proven rollback path.
4. Verify no existing real SSH keys or live project files would be touched by the synthetic tests. No secrets or pairing codes in reports.
5. STOP and report any ambiguous app identity, unavailable target image, failed backup/rollback verification or inconsistent permissions. Do not improvise.

## Installation (only after separate operator approval)

1. Update **only** Codex Deployment to the reviewed 0.4.30-dev.2 version. Initially set **remote_control_enabled: false** and **addons_access: read_only**.
2. Start only Deployment manually. Confirm startup, health, ingress, existing Codex login/session, Home Assistant MCP and a disposable workspace. Record Stable's version/status before and after.
3. **#29:** Inspect /addons access options. The Supervisor mount is RW; read_only is a Codex-runtime policy, **not** a host-level read-only mount. Use only synthetic fixtures; do not claim complete OS sandbox isolation from the helper filter test. Check that read_write is an intentional opt-in; do not modify actual App sources.
4. **#26:** Use a synthetic .ssh directory and fake key in a disposable folder to compare ownership, modes and ACLs before/after two startup cycles. Never alter a real SSH directory/key or run recursive ACL repair.
5. **#14:** Inspect generated AGENTS.md, mapped paths and basic tool availability (python3, git, gh, yq, yamllint, sqlite3, mosquitto_pub, ha-readonly). Document discrepancies; no extra development during this test.
6. **#25:** Manually test desktop text selection/copy/paste and drag selection beyond the viewport. Also preserve the known iOS selection mode; do not patch ttyd in this run. Record any still-missing auto-scroll as a known enhancement.
7. **#24 OFF:** With the switch disabled, confirm no managed Remote Control process was started and ttyd/MCP still work.
8. **#24 ON:** Enable the UI setting, save and restart **only** Deployment. Confirm one official unprivileged app-server process, no new inbound TCP port, meaningful status/error logs. From the same persistent Codex home, pair manually using the official Codex CLI and the ChatGPT iOS app. Access **only a disposable Git project** in /share/codex/projects. A manual pairing step is not automatable and must not be reported as PASS without a real device test.
9. Restart Deployment once with Remote Control enabled; confirm no duplicate process, expected session persistence where supported. Disable Remote Control, save/restart, verify the managed process is stopped while ttyd remains available. No hot-toggle without restart is claimed.
10. Confirm **auto_update: false** for Stable and Deployment, Deployment boot still manual, and Stable identity/version/options/running state remain unchanged. The historical codex_apps HTTP 401 is a separate issue, not a new success criterion.

## On failure / rollback

Stop only Codex Deployment. Restore its previously recorded image version and settings using the verified rollback procedure. Do not reset Git history, change Stable, modify HA automation credentials, or start new Docker/VM/security infrastructure. If user approval or required privileges are missing, STOP and report.

## Evidence and closure

For #29, #24, #26, #25 and #14 record **PASS**, **FAIL**, **NOT RUN** or **MANUAL PENDING** per check, with version, exact Supervisor IDs, option state, commands/results and relevant log excerpts **without secrets**. Leave independent feature issues open unless their actual acceptance is satisfied. The Codex operator must perform only installation and bounded runtime checks; no coding, branch changes, image publishing or new features during this run.
