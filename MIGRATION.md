# Migration To CaneTLOTW HA Codex

## Source

This is a compatible fork of the original add-on:

```text
https://github.com/kecksdigital/codex-hass
```

The original project remains the upstream source for the add-on structure and
the existing `codex` data layout. This repository adds the image-pinned CLI
update fix described below.

Add this repository to Home Assistant under Settings -> Apps -> App Store ->
Repositories:

```text
https://github.com/CaneTLOTW/ha-codex
```

The add-on keeps the existing slug `codex`, so Home Assistant can treat version
`0.3.1` as an update of the existing Codex App. The published image is:

```text
ghcr.io/canetlotw/ha-codex:0.3.1
```

## Installation-specific paths

The Home Assistant OS data directory and the hash prefix of an App data
directory are installation-specific. Do not copy the example container or
directory names from another system. Find the actual Codex data directories on
the HAOS host first:

```sh
find /mnt/data/supervisor -type d -name '*_codex' -print
```

After identifying the old and new directories, assign their real paths and
validate them before copying:

```sh
OLD_DIR="/mnt/data/supervisor/<actual-data-path>/<old-id>_codex"
NEW_DIR="/mnt/data/supervisor/<actual-data-path>/<new-id>_codex"

test -d "$OLD_DIR" || { echo "Old Codex directory not found"; exit 1; }
test -d "$NEW_DIR" || { echo "New Codex directory not found"; exit 1; }
test "$OLD_DIR" != "$NEW_DIR" || { echo "Source and target are identical"; exit 1; }

printf 'Source: %s\nTarget: %s\n' "$OLD_DIR" "$NEW_DIR"
```

Stop both Codex Apps before copying. Container names are also dynamic, so use
the running-container list only as a check:

```sh
docker ps --format '{{.Names}}\t{{.Image}}' | grep -i codex || true
```

The source and target values must be checked manually before running any
cleanup or copy command. Keep the target backup until the new App has been
verified.

## What Changed

- Codex CLI `0.146.1` is installed while the image is built.
- Runtime npm updates are disabled; the App no longer writes into `/usr/local`
  during startup.
- The image-installed executable is preferred over stale user-level launchers
  under `/data/codex-home/users/anonymous/.local/bin`.
- Existing App options, the `codex` slug, and the persistent Codex state paths
  remain compatible.
- `auto_update_codex` remains accepted for old configurations, but only emits
  a warning because App image updates are now the supported update mechanism.

## Upgrade

1. Create a full Home Assistant backup.
2. Stop the old Codex App, but do not uninstall it.
3. Add the repository URL above and refresh the App Store.
4. Install the `0.3.1` update for the existing Codex App.
5. Start the App and verify the CLI version with `codex --version`.
6. Verify that `/homeassistant` files, login state, MCP, and the working
   directory are available.
7. On the Codex App page, enable Home Assistant's **Auto update** option if
   future published App images should install automatically.

Do not run `npm install -g @openai/codex` inside the App. Future Codex CLI
updates are published as new App image versions.

Home Assistant's **Auto update** option is the supported automation. It is
separate from `auto_update_codex`, which remains only for configuration
compatibility and must stay disabled.

## Rollback

If the upgrade fails, stop the new App and restore the Home Assistant backup.
Keep the old App data until the new image and authentication have been checked.
