# Stable 0.5.3: upgrade and rollback

## Before updating

- Stable 0.5.3 is the local Lovelace resource MCP release, retaining Codex CLI 0.172.0 and the 0.5.1 upload and terminal improvements. Review [changelog](../codex/CHANGELOG.md) and [resource workflow](../codex/docs/LOVELACE_RESOURCE_DEPLOYMENTS.md).
- Verify both architecture publishing jobs and the multiarch manifest for version 0.5.3. Back up only the Stable App's data/options and preserve a verified restore path to the previous version; do not overwrite Deployment state or credentials.
- Check current App identity, running version, available update and settings in Home Assistant. Review static read-only /app_configs visibility and existing /addons launch policy. Keep current auto-update settings.
- Do not run competing resource writers from Stable and Deployment simultaneously. The resource API is non-atomic across independent HA clients.

## Update and verify

1. In Home Assistant Settings → Apps → App Store, refresh repository metadata if needed and select the existing Stable **Codex** App (not Codex Deployment or HACS). Update only after operator approval.
2. Verify installed version 0.5.3, existing App ID, settings, authentication, session history, ingress, CLI 0.172.0 and startup log. No Home Assistant Core restart is required.
3. With MCP enabled, check both managed servers and discover the four resource tools in a fresh Stable Codex session. Perform a read-only list first. Do not repeat the already successful Developer canary unless a regression or independent acceptance need requires it. Any write requires separately approved preview/confirmation, backup and paused competing writers.
4. Report installed version, state, digest where accessible and PASS/FAIL/BLOCKED in the release tracking issue. No unrelated project deployments or automatic changes to other Apps.

## Rollback

If Stable fails startup or loses expected behavior, stop the affected App, preserve evidence and restore its targeted pre-update App backup with the prior image using the supported Supervisor restore path. Do not modify Core storage, copy credentials between channels or change unrelated resources. Resource registry rollback is separate from App rollback: use the documented resource preview/confirm flow with the correct original asset bytes and targeted backup record. Never automatically compensate after an uncertain HA write.
