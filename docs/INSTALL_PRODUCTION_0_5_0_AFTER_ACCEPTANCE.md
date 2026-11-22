# Production installation Auftrag — HA-Codex 0.5.0 (HOLD until developer acceptance)

**Status:** PREPARED, **NOT APPROVED TO EXECUTE**. This is an installation checklist, not authorization to merge code, publish Stable or update a Home Assistant app.

## Preconditions
- Developer `0.5.0-dev.3` has been built and published on `deployment` (both `amd64`, `aarch64`, and multiarch manifest), installed in **Codex Deployment**, and passed the complete runtime acceptance in `docs/acceptance/HA_CODEX_0_5_0_DEV3.md`.
- The operator has verified real Firefox/HA ingress reconnect reliability without sidebar switching; both foreground and background cases, with the original close code **1000** reproduced.
- The developer runtime has completed a real Codex ChatGPT token refresh, a real Home Assistant MCP call, and a real iOS Remote-Control pairing with a disposable test project. If Remote Control is intentionally deferred for a partial release, obtain a separate explicit scope decision rather than silently claiming PASS.
- No regressions to SSH key ACLs, /addons policy, iOS Sel, desktop copy/paste, HA App Store installation or external-media startup.
- Stable main source receives a reviewed **separate** versioned promotion PR; its exact commit hash and changelog are approved; stable `0.5.0` amd64/aarch64 images and multiarch manifest are published and verified with matching image digests.

## Read-only production preflight
1. Identify by exact *live* Supervisor IDs the Stable **Codex** and Developer **Codex Deployment** instances and their repositories. Avoid relying on historical prefixes from 2026-11-04.
2. Record installed versions, `/data` ownership, current options (especially `session_persistence`, `enable_mcp`, `addons_access`, `remote_control_enabled` where present), auto-update flags, boot mode and image digests.
3. Back up Stable App data and configuration, verify backup can be restored independently, and note previous known-good Stable image digest/version.
4. Confirm the Stable `0.5.0` image appears in **Settings → Apps → App Store**, not the integrated HACS Marketplace.
5. Check Home Assistant Core/Supervisor version and ensure no conflicting extension, mount or active user session could obscure the test.

## Execute only after explicit approval
1. Take a final Stable snapshot. Do not mix Stable and Developer persistent state.
2. Update **Stable Codex only** to the approved `0.5.0` image. Preserve current user options and auth. Keep `auto_update: false` unless independently changed by the operator.
3. Restart only Stable Codex; verify ingress, tmux session persistence, read-only MCP call, CLI `0.171.0` (or exact CLI version accepted during promotion), model options, and no 401.
4. Verify WebSocket reconnect after a controlled disconnect, without abandoning the HA sidebar; confirm no production task was lost.
5. Verify Stable app source and `main` remain the expected signed release. Keep `deployment` separate and preferably boot manual. Confirm both app identities/versions after the operation.

## Rollback
- If any critical runtime test fails, stop only Stable Codex and restore its pre-upgrade image/config/data from the verified backup.
- Do not force-push branches, change HA-wide proxy settings, relax AppArmor, alter real SSH keys, turn on auto-update, or copy Developer auth/data to production as an improvised repair.
- Record exact failed check, sanitized log evidence, rollback version/digest and resulting state. Any second attempt requires a new approved fix/candidate.

## Completion record
- Reviewed Stable PR/commit: ____
- Developer acceptance record and operator approval: ____
- Stable image manifest/digest: ____
- Pre-upgrade Stable app ID/version/options backup: ____
- Post-upgrade Stable app ID/version/CLI: ____
- WebSocket, MCP, Auth, Remote Control, permissions, iOS/Desktop test results: ____
- Rollback evidence and final sign-off: ____
