# Lovelace custom-card resource deployment

The Codex App provides a dedicated `ha_lovelace_resources` MCP server when its existing `enable_mcp` option is enabled. It is deliberately separate from the broad Home Assistant service MCP surface and exposes only:

- `ha_config_list_dashboard_resources`
- `ha_config_set_dashboard_resource`
- `ha_config_delete_dashboard_resource`
- `ha_config_rollback_dashboard_resource`

The server calls Home Assistant's authenticated native WebSocket resource API. The existing root helper reads the Supervisor token and passes it only to the server process. It is never emitted in MCP responses, logs, config files or backups. No direct writes to `.storage/lovelace_resources` are performed.

## Required deployment sequence

1. Install the JavaScript asset under `/homeassistant/www/<project>/` using the project's reviewed deployment procedure. This service only registers an already installed file.
2. Compute the exact URL from release and file bytes:

   ```text
   /local/<project>/<asset>.js?v=<release>-<first-12-hex-of-SHA256>
   ```

3. Call `ha_config_set_dashboard_resource` first with the path and `release`, leaving `dry_run=true`. It computes the hash from the file under `www`, checks the supplied version/hash if a versioned URL was supplied, refuses path traversal/external resources/HACS paths, and reports whether the operation would create or update.
4. After reviewing that preview, call the same tool with `dry_run=false`. It matches by normalized file path, refuses multiple registrations, does nothing if URL/type already match, and updates the existing ID when only the release/hash changes.
5. Before a write, the server stores only the affected resource's preimage and intended postimage under `/share/ha-lovelace-resource-backups/`, with directory/file permissions 0700/0600. It then performs a WebSocket create/update, lists resources again, and verifies the target. A failed verification triggers a targeted compensating rollback where possible.
6. Use `ha_config_list_dashboard_resources` for readback. Its output redacts query values whose parameter names look credential-like. Verify unrelated resources, especially HACS resources, are unchanged.
7. If rollback is needed, preview with `ha_config_rollback_dashboard_resource(backup_id=..., dry_run=true)`, then execute with `dry_run=false`. Delete is also dry-run by default and is restricted to ordinary `/local/` resources. `/local/community/` and `/hacsfiles/` are immutable through these tools.
8. Refresh the dashboard/browser cache after registration. A Home Assistant Core restart is not part of this workflow.

The server rejects versioned resources unless the SHA-256 prefix matches the actual local file. Sensitive query parameters in an existing resource prevent backup and mutation rather than being copied into a backup. Backups contain one resource at a time; they do not copy the global registry, which may contain unrelated private URLs.

## JANUS canary

The first target pair is tracked in [HA_heimdall#147](https://github.com/CaneTLOTW/HA_heimdall/issues/147) and JANUS_Development#31:

- `/local/janus/thermal-flow-card.js?v=0.4.2-88101d0e955e`
- `/local/janus/characterization-card.js?v=1.0.1-c442e40d3dc6`

Do not claim runtime acceptance until these exact URLs/types have been registered and read back via the MCP tools, duplicate checks are clean, non-target resources are unchanged, and the cards load after a browser refresh.
