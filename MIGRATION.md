# Migrating to CaneTLOTW/ha-codex

This repository originated from `kecksdigital/codex-hass`, but it is now maintained independently.

A matching Home Assistant App slug (`codex`) does **not** guarantee that two different App repositories are treated as the same installation. Home Assistant can assign repository-specific App identities and different persistent data directories. Do not assume that adding this repository will perform an in-place upgrade of an App installed from another repository.

## Before migrating

1. Create a full Home Assistant backup.
2. Keep the old Codex App installed until the new installation has been verified.
3. Record the old App's important settings.
4. Add `https://github.com/CaneTLOTW/ha-codex` under **Settings → Apps → App Store → Repositories**.
5. Install and start the new Codex App once so Home Assistant creates its data directory.
6. Check whether your previous Codex authentication and state are already visible. If not, use the host-level procedure below.

## Why a host-level copy can be necessary

Codex authentication, sessions, and generated user configuration are stored in the App's persistent data area. If Home Assistant created a new data identity for this repository, the old and new Apps can have separate directories even though both use the `codex` slug.

The exact HAOS Supervisor paths and generated App identifiers are installation-specific. Discover them; never copy example identifiers from documentation.

## HAOS debug SSH

Host-level Supervisor data is not available from a normal App terminal. On Home Assistant OS, use the HAOS debug SSH service on port `22222` when host-level access is required.

After configuring an authorized key through the HAOS `CONFIG` import mechanism, connect with:

```sh
ssh -i /path/to/haos_debug -p 22222 root@<home-assistant-host>
```

## Discover the App data directories

Stop both Codex Apps before copying data, then search the Supervisor data tree:

```sh
find /mnt/data/supervisor -type d -name '*_codex' -print
```

Inspect every result and identify the source belonging to the old repository and the target belonging to `CaneTLOTW/ha-codex`.

Assign the real paths:

```sh
OLD_DIR="/mnt/data/supervisor/<actual-old-codex-data-directory>"
NEW_DIR="/mnt/data/supervisor/<actual-new-codex-data-directory>"

test -d "$OLD_DIR" || { echo "Old Codex directory not found"; exit 1; }
test -d "$NEW_DIR" || { echo "New Codex directory not found"; exit 1; }
test "$OLD_DIR" != "$NEW_DIR" || { echo "Source and target are identical"; exit 1; }

printf 'Source: %s\nTarget: %s\n' "$OLD_DIR" "$NEW_DIR"
```

Do not continue until the printed paths have been checked manually.

## Back up the new target

Before replacing any target data:

```sh
BACKUP_DIR="${NEW_DIR}.backup-before-migration-$(date +%Y%m%d-%H%M%S)"
cp -a "$NEW_DIR" "$BACKUP_DIR"
du -sh "$NEW_DIR" "$BACKUP_DIR"
```

Keep this backup until the migrated App has been accepted.

## Copy the old persistent state

With both Apps stopped and the paths verified:

```sh
find "$NEW_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
cp -a "$OLD_DIR"/. "$NEW_DIR"/
```

The `/.` suffix preserves hidden files such as Codex authentication and configuration data.

Verify before starting the new App:

```sh
du -sh "$OLD_DIR" "$NEW_DIR"
diff -qr "$OLD_DIR" "$NEW_DIR" || true
find "$OLD_DIR" -type f | wc -l
find "$NEW_DIR" -type f | wc -l
```

## Acceptance checks

Start only the new App and verify:

- Codex authentication works.
- Previous conversations are visible through `codex resume` where expected.
- `/homeassistant` is accessible.
- Git/GitHub credentials or SSH state needed by your workflows still work.
- The bundled Home Assistant MCP server follows the `enable_mcp` option.
- Additional managed MCP servers start correctly if configured.
- Mobile/desktop terminal interaction behaves as expected.

Only remove the old App data or the migration backup after these checks pass.

## What differs from the original repository

This repository intentionally diverges from the original project in several areas:

- Codex CLI releases are pinned into App images and delivered through normal Home Assistant App updates instead of runtime npm updates.
- The selectable model list follows the bundled Codex CLI catalog.
- The ttyd frontend is built from source with maintained mobile terminal controls.
- The bundled Home Assistant MCP configuration can be disabled reliably.
- Additional remote Streamable HTTP MCP servers and explicit Codex environment variables can be managed from App options.
- Documentation, translations, tests, and release maintenance are handled independently here.

These differences are why migration is documented as a cross-repository migration rather than as a guaranteed in-place update.

## Rollback

If validation fails:

1. Stop the new App.
2. Restore the new App's pre-migration backup if you want to retry it.
3. Start the old App again, or restore the full Home Assistant backup if necessary.
4. Keep all source data until the rollback has been verified.
