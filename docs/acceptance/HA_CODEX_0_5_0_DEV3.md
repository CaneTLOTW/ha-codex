# HA-Codex 0.5.0-dev.3 — deployment acceptance (2026-11-22)

## Identity and safety
- Candidate branch: `release/dev-0.5.0-rc1`. Publication target after reviewed merge: `deployment`, **not** `main`.
- Developer repository: `https://github.com/CaneTLOTW/ha-codex#deployment`; app: **Codex Deployment**, stage `experimental`, boot `manual`, version `0.5.0-dev.3`.
- Stable repository: `#main`; app: **Codex**; keep it untouched. **Do not infer** the current app IDs from old logs. Query the live Supervisor and capture names/IDs/versions/images before any writes.
- The 2026.11 **Marketplace** (integrated HACS) is separate from the **Supervisor App Store** used by HA-Codex. The App image is a GHCR container; there is no HACS integration migration.
- Preserve both apps' current `auto_update=false`; confirm the actual setting, do not silently switch it.
- Collect versioned backup/snapshot of deployment options and persistent state and verify rollback before installing. Do not overwrite a working Stable image or copy its `/data` into the Deployment app.

## Publish prerequisites (outside HA)
1. Canonical ttyd patch applies to pristine ttyd 1.7.7.
2. Python/shell/YAML/translation tests pass in new combined candidate, not merely on its source PRs.
3. AMD64 and AARCH64 images build successfully.
4. Publish both versioned `0.5.0-dev.3` images and the **multiarch manifest** on the deployment channel only. Check job SHAs, digests and effective CLI version `0.171.0`.
5. No `latest`/Stable tag is moved, and no `main` commit is changed.

Do not begin HA installation if any prerequisite fails.

## Home Assistant installation — Developer only
1. In **Settings → Apps → App Store**, check the existing `#deployment` repository and refresh the App Store/repositories. Do not use **Settings → Marketplace**.
2. Read back version, running state, current options and available update for **Codex Deployment**, with exact live Supervisor ID.
3. Install/update only this app to **0.5.0-dev.3**, retaining existing `/data`, `addons_access: read_only`, and `remote_control_enabled: false`. Keep `boot: manual` and both auto-updates disabled.
4. Start **Codex Deployment** manually; verify HTTP ingress, interactive ttyd terminal, healthy startup logs and mounted path mapping. Stable must remain unchanged (record before/after).

## New SQLite migration-64 acceptance (#43)

Before testing reconnect, validate real Codex startup in **Deployment** using the private temporary-filesystem fix. The original error is `state_5.sqlite`, migration 64, SQLite code 14. Prior testing in Stable showed the existing database was intact; do **not** delete or replace any state DB, WAL/SHM file, or session.

1. Read the live Developer App version and confirm it is **0.5.0-dev.3**, not Stable 0.4.36.
2. Confirm `/data/codex-home/users/anonymous/.codex/_sqlite_tmp` exists, is a directory (not symlink), mode 0700, and writable/traversable for Codex UID 22000. Do not print tokens or private history.
3. In the actual Codex terminal process and optional Remote Control process, verify `SQLITE_TMPDIR` and `TMPDIR` point to the same path. On a brand-new Codex process, check successful state initialization and a harmless session, including after an App restart.
4. For the SQLite temp workload use a **disposable fixture**; do not force migration of the real `state_5.sqlite` for testing.
5. Verify CLI can open existing sessions without data loss. If code 14 persists, retain DB and inspect filesystem/mount/permissions and the migration log. No automatic `codex doctor` repair or destructive file changes.

See [reproduction and safe workaround](../CODEX_SQLITE_TEMP_MIGRATION.md). The Stable app may need the temporary shell workaround independently; do not install the experimental Developer image over Stable.

## New startup failures reproduced in dev.2 (#45, PR #46)

The preceding Developer image failed before opening Codex because its UID 22000 check executed an unrelated Python `/usr/local/bin/test` requiring `pytest`. Once in the fallback shell, running `codex` encountered an executable-denied managed-daemon binary under `/data/codex-home/fallback/.codex/packages/app-server-daemon/releases/.staging*/bin/codex`.

Developer 0.5.0-dev.3 addresses both; **real HAOS acceptance is mandatory**:

1. Start Codex Deployment, make sure the normal CLI TUI opens automatically without a fallback shell, and confirm that neither `ModuleNotFoundError: pytest` nor `[ERROR] Codex SQLite temporary directory is not writable` appears.
2. Verify the private UID 22000 scratch directory is writable using the new `/bin/sh` checker and that its temporary probe is removed. Do not modify the real SQLite database.
3. Confirm the interactive TUI uses the supported `--no-daemon` mode and starts from the existing configured `CODEX_HOME`, not `/data/codex-home/fallback`. No `Permission denied` when executing a managed daemon under `/data`.
4. Check Codex login, harmless prompt, existing session list/resume and actual read-only HA MCP access. Then repeat app restart and browser reconnect checks.
5. Confirm AppArmor still restricts execution from writable `/data`. Do not grant `/data/** ix` to silence a failed daemon installation. Remote Control OFF by default; if enabled, separately verify the explicit sidecar starts from installed `/usr/local/bin/codex`.
6. Treat an error in either area as **FAIL**, capture sanitized logs, and stop promotion to Stable. Do not delete state, relax AppArmor or add `pytest` as a workaround.

## Functional test matrix (record PASS / FAIL / NOT RUN / MANUAL PENDING)
| Check | Steps | PASS requires |
| --- | --- | --- |
| Startup permission checker #45 | Normal CLI launch; no Python pytest wrapper; no fallback shell | PASS only with real HAOS CLI startup |\n| CLI background daemon #45 | Interactive Codex in `--no-daemon` mode under current AppArmor | No EACCES from writable `/data`; sidecar independent |\n| SQLite temporary workspace #43 | Real CLI state migration, restart, private TMPDIR/SQLITE_TMPDIR | No SQLite code 14; existing state preserved |\n| ttyd WebSocket #34 | Firefox F12, keep Codex visible >10 min, then background tab >6 min; exercise normal 1000 close and simulated disconnect where safe | Auto-reconnect without switching HA page; Enter fallback always works; no duplicate loops/timers |
| Session persistence | `session_persistence: true` **already in the user's stable app**; verify actual deployment setting; start harmless tmux/CLI task, disconnect/reconnect | Same session remains available; do not treat persistence as fix for transport |
| Mobile | iPhone HA Companion and (if available) Android; keyboard, modifiers, iOS Sel, scroll, foreground/background | No regression vs stable 0.4.8 accepted behavior, and reconnect works |
| SSH ACL #26 / mount #32 | **Only disposable fixture directories**; force unsupported ACL/chmod in isolated test; check file modes/ACL before/after | Startup survives foreign filesystem; .ssh key remains owner-private; no host permission sweep |
| /addons access #29 | Confirm read_only enforced in runtime with safe synthetic paths; optionally check explicit read_write opt-in only when permitted | No accidental real App source writes or false claim of host-level read-only mount |
| CLI models #15 | Check installed CLI version; `/model` options and fallback handling | Version `0.171.0`, usable model selection and no accidental default change |
| Home Assistant MCP | After valid Codex login, harmless read-only entity/state lookup and `ha-readonly core info` | Real MCP tool operation passes; mere registration insufficient |
| Remote Control #24 | First real `codex exec` must work without refresh-401; then UI switch OFF→ON with app restart, pair iOS only to disposable test project; restart, OFF | Real pairing and read/write disposable file succeeds; OFF shuts app-server; ttyd unaffected |
| Documentation / tooling #11/#14 | Check generated AGENTS.md, tool availability and mapped paths | Documented commands and path mapping correct |
| Security scope #12/#13 | Inspect manifest and mounted paths; no generic uploads exposed | No unauthorized `all_app_configs` mount, no upload service/extra port |
| Desktop edge scroll #25 | Select text beyond top/bottom viewport, check mouse/tmux/Alt behavior | Record limitation if still present; normal selection remains working |

**Browser diagnostic data:** record only close code, `wasClean`, `reason`, browser focus/visibility state, time, and relevant redacted HA logs. Never paste raw `/api/hassio_ingress/<session>` URLs, screenshots with tokens or `auth.json` into GitHub.

## Auth blocker and stop criteria
- Prior deployment `0.4.30-dev.2` returned HTTP 401 on Codex token refresh. A saved `codex login status` is **not** success; require a harmless real Codex invocation. A normal manual re-login may be needed. Keep credentials and pairing codes private.
- Stop on ambiguous app ID, missing backup/rollback, failed manifest, unexpected permissions, broken MQTT/KNX/HA automation, Codex auth failure, unstable ttyd or loss of existing sessions. Restore **deployment only**.
- No promotion or production installation based merely on green CI. Archive PASS/FAIL with evidence first.

## Production release gate
After all required tests pass, prepare a **separate PR from accepted deployment state to main**, assign stable version `0.5.0`, verify updated changelog, then perform another independent stable build/publish/manifest check. Production installation still requires explicit operator approval. See `docs/INSTALL_PRODUCTION_0_5_0_AFTER_ACCEPTANCE.md`.
