# Stable Codex 0.5.1 — Upgrade and verification

**Release authorization:** The operator requested publication of Stable `0.5.1` on 24 November 2026 after reviewing the Developer screenshot, desktop upload and mobile picker workflow. **Publishing the GitHub release does not install it in the user's Home Assistant.**

## Scope
- Promote the tested Developer `0.5.0-dev.11` runtime to Stable `0.5.1`.
- Preserve Stable App **Codex** identity, slug, automatic boot, Home Assistant ingress, user settings and persistent state. Do not copy Developer App data to Stable.
- Ctrl+V screenshot paste and direct file uploads default ON; legacy trzsz transfer and Remote Control default OFF.
- New visibility: public configuration directories of other Apps are mapped read-only under `/app_configs`. `app_configs_visibility` changes guidance, **not** the mount or its access rights.
- Private uploads remain on disk: 10 MiB/file and maximum 24 files/selection. No automatic cleanup policy.

## Before installing in Home Assistant
1. Read back the actual Stable Codex App ID, current version/digest, source repository, options and auto-update settings. Identify the separate Developer instance without assuming historical IDs.
2. Create and verify a recoverable backup of Stable App `/data`, auth, SQLite history, existing sessions and options. Record known-good prior image/digest and rollback route.
3. In **Settings → Apps → App Store**, verify the **Stable Codex 0.5.1** offer. HACS Marketplace is a different component.
4. Confirm the user accepts the added static read-only `/app_configs` visibility. No hidden extra permissions, no Remote Control opt-in, no elevated AppArmor execution rights.
5. Stop/restart only the Stable Codex instance when performing the user-controlled update. Do not modify Home Assistant or the separate Codex Deployment instance.

## After installing
1. Confirm stable name, correct 0.5.1 image, retained login/config/MCP, no SQLite code 14, no daemon permission errors.
2. Windows Firefox: Win+Shift+S → Ctrl+V in **running** Codex → `[Image #1]` and correct actual picture interpretation. Confirm ordinary text Ctrl+V still works.
3. Desktop: collapse/reopen the slim Upload dock; select TXT/YAML/PDF, ask Codex to read it, check drag-and-drop and folder picker.
4. iPhone: tap **📎** once, select an image or file in the native Photos/Camera/Files chooser, confirm successful upload and actual content read; verify original 2×8 mobile key layout, Sel, keyboard show/hide and cancellation.
5. Confirm no automatic command submission, no extra exposed web port, file bounds and private storage. Note that uploaded files persist until manual removal.
6. Test Ctrl+C → `codex` → `codex resume --last` and Ingress reconnect; tmux persistence only if enabled.

## Rollback
If there are critical auth, SQLite, permission or Ingress failures, stop only Stable Codex and restore the known-good image, options and backed-up persistent data. Do not delete state databases, relax AppArmor executable access, or mix Developer data into Stable.

## Completion record
- PR and merged Stable commit:
- Signed amd64/aarch64 image/manifest digest:
- Previous version, backup, options and rollback image:
- New version actually installed on Home Assistant:
- Screenshot/text paste, desktop file upload, iPhone picker and MCP/reconnect test outcomes:
