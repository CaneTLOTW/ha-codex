# Lovelace custom-card resource deployment

The Codex App provides a dedicated `ha_lovelace_resources` MCP server when its existing `enable_mcp` option is enabled. It is deliberately separate from the broad Home Assistant service MCP surface and exposes only:

- `ha_config_list_dashboard_resources`
- `ha_config_set_dashboard_resource`
- `ha_config_delete_dashboard_resource`
- `ha_config_rollback_dashboard_resource`

The server calls Home Assistant's authenticated native WebSocket resource API. The dedicated root helper accepts no arguments, starts an isolated interpreter from the image and discards the caller's environment. The server reads the Supervisor token from the private App runtime directory. It uses the token only to authenticate to the fixed Supervisor endpoint. It uses the API to manage Lovelace storage.

## Required deployment sequence

1. Install the JavaScript asset under `/homeassistant/www/<project>/` using the project's reviewed deployment procedure. This service only registers an already installed file.
2. Compute the exact URL from release and file bytes:

   ```text
   /local/<project>/<asset>.js?v=<release>-<first-12-hex-of-SHA256>
   ```

3. Call `ha_config_set_dashboard_resource` first with the path and `release`, leaving `dry_run=true`. It computes the hash from the file under `www`, checks the supplied version/hash if a versioned URL was supplied, refuses path traversal/external resources/HACS paths, and reports whether the operation would create or update.
4. After reviewing that preview, call the same tool with `dry_run=false`. It matches by normalized file path, refuses multiple registrations, does nothing if URL/type already match, and updates the existing ID when only the release/hash changes.
5. Before a write, the server stores the affected resource's preimage and intended postimage under `/data/codex-managed/lovelace-resource-backups/`, with root ownership and directory/file permissions 0700/0600. It checks that the preimage is still current, issues one write, records HA's acknowledgement and verifies ID, URL and type. A failure returns the backup ID without issuing a compensating write. Inspect the registry before making another change.
6. Use `ha_config_list_dashboard_resources` for readback. Its output redacts query values whose parameter names look credential-like. Verify unrelated resources, especially HACS resources, are unchanged.
7. If rollback is needed, pause other writers of the same resource and preview with `ha_config_rollback_dashboard_resource(backup_id=..., dry_run=true)`. Review the live state and proposed restore with the operator. After approval, pass `dry_run=false` and the returned `non_atomic_confirmation` in the same MCP session within 120 seconds. The confirmation is single use and bound to the previewed resource and asset. Start again with a fresh preview if the state changes. `manual_review_required` means the original write was unacknowledged and the server offers no write confirmation. Delete defaults to a dry run. The tools block mutations of `/local/community/` and `/hacsfiles/`.
8. Refresh the dashboard/browser cache after registration. A Home Assistant Core restart is not part of this workflow.

The server validates the current hash for new registrations. It accepts canonical local paths with regular assets and rejects symlinks. Backups contain only the targeted local resource. The server rejects existing URLs with query parameters other than a simple `v` cache key. It checks backup ownership, ancestry and metadata before using a record. Rollback restores registry metadata. A matching old asset version requires a separate file rollback. Restoring a deleted resource creates a new ID through the native API.

The native API provides no atomic conditional write. Explicit confirmation and the final read reject observed conflicts. A concurrent writer can still change the resource between that read and the write, or change it and restore identical metadata between reads. The MCP confirmation does not lock out HA clients or authenticate separate operator consent. Leave rollback in preview mode if other writers cannot be paused. A guarantee against concurrent writes requires a conditional mutation enforced by HA Core or mutual exclusion enforced for all writers.

Backups from 0.5.0-dev.12 in `/share/ha-lovelace-resource-backups/` are outside the helper's trust boundary. Keep them for review if needed. The corrected helper does not import or apply these records.

## JANUS canary

The first target pair is tracked in [HA_heimdall#147](https://github.com/CaneTLOTW/HA_heimdall/issues/147) and JANUS_Development#31:

- `/local/janus/thermal-flow-card.js?v=0.4.2-88101d0e955e`
- `/local/janus/characterization-card.js?v=1.0.1-c442e40d3dc6`

Do not claim runtime acceptance until these exact URLs/types have been registered and read back via the MCP tools, duplicate checks are clean, non-target resources are unchanged, and the cards load after a browser refresh.
