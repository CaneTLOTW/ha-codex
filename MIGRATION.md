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
`0.3.3` as an update of the existing Codex App. The published image is:

```text
ghcr.io/canetlotw/ha-codex:0.3.3
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

## Enable HAOS debug SSH access

The normal terminal SSH connection reaches only the App container. Access to
the Supervisor and App data directories requires the Home Assistant OS debug
SSH service on port `22222`.

### Create an SSH key on Windows

Run these commands in PowerShell. The private key remains on the Windows PC:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.ssh"
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\haos_debug"
```

This creates `haos_debug` and `haos_debug.pub`. Never copy the private
`haos_debug` file to HAOS.

### Prepare the `CONFIG` device

HAOS imports the public key from a partition or device named `CONFIG`. Create a
file named exactly `authorized_keys` in its root directory. It must contain the
complete public key on one line and must not have a `.pub` or `.txt` suffix.

Replace the drive letter in `$configRoot` with the mounted `CONFIG` device:

```powershell
$configRoot = "E:\"
$publicKey = (Get-Content "$env:USERPROFILE\.ssh\haos_debug.pub" -Raw).Trim()
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText(
  (Join-Path $configRoot "authorized_keys"),
  "$publicKey`n",
  $utf8NoBom
)
```

The `CONFIG` device can be a USB drive or a virtual disk attached to the HAOS
VM. FAT, ext4, and NTFS are supported by HAOS.

### Import the key and connect to HAOS

Open the HAOS VM console and run this at the `ha >` prompt:

```text
os import
```

The full form is also valid:

```sh
ha os import
```

If required, reboot HAOS with the `CONFIG` device attached. Then connect from
PowerShell. Use the actual HAOS IP address or hostname; do not copy an example
address from this document:

```powershell
$haosHost = Read-Host "HAOS host IP or hostname"
ssh -i "$env:USERPROFILE\.ssh\haos_debug" -p 22222 root@$haosHost
```

At the first connection, confirm the host key. A successful session should
return `root` for:

```sh
whoami
pwd
```

For WinSCP, use SCP first with port `22222`, user `root`, no password, and the
private key `haos_debug`. The actual HAOS data path is discovered in the next
section and must not be assumed from another installation.

## Optional full host-level data migration

Use this procedure only when the new App received a different data directory
and the existing Codex state is not visible after the repository migration.
The procedure copies the complete App data directory, including hidden files,
SSH configuration, authentication state, and Codex sessions.

The HAOS host address is installation-specific. Set it once in PowerShell and
use the variable instead of copying an example address:

```powershell
$haosHost = Read-Host "HAOS host IP or hostname"
ssh -i "$env:USERPROFILE\.ssh\haos_debug" -p 22222 root@$haosHost
```

On the HAOS host, stop both Codex Apps through the Home Assistant UI. Do not
refer to a fixed Docker container name; verify dynamically that no Codex
container is still running:

```sh
docker ps --format '{{.Names}}\t{{.Image}}' | grep -i codex || true
```

Find the actual data directories. The parent path and hash prefix can differ
between installations:

```sh
find /mnt/data/supervisor -type d -name '*_codex' -print
```

Assign the paths from that output. Replace only the values inside the quotes:

```sh
OLD_DIR="/mnt/data/supervisor/<actual-data-path>/<old-id>_codex"
NEW_DIR="/mnt/data/supervisor/<actual-data-path>/<new-id>_codex"

test -d "$OLD_DIR" || { echo "Old Codex directory not found"; exit 1; }
test -d "$NEW_DIR" || { echo "New Codex directory not found"; exit 1; }
test "$OLD_DIR" != "$NEW_DIR" || { echo "Source and target are identical"; exit 1; }

printf 'Source: %s\nTarget: %s\n' "$OLD_DIR" "$NEW_DIR"
```

Create a recoverable backup of the new directory before replacing its
contents:

```sh
BACKUP_DIR="${NEW_DIR}.backup-before-migration-$(date +%Y%m%d-%H%M%S)"
cp -a "$NEW_DIR" "$BACKUP_DIR"
du -sh "$NEW_DIR" "$BACKUP_DIR"
```

Only after checking the printed source, target, and backup paths, replace the
target contents and copy the old state. The `/.` suffix preserves hidden files
without creating an additional source directory below the target:

```sh
find "$NEW_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
cp -a "$OLD_DIR"/. "$NEW_DIR"/
```

Verify the result before starting the new App:

```sh
du -sh "$OLD_DIR" "$NEW_DIR"
diff -qr "$OLD_DIR" "$NEW_DIR" || true
find "$OLD_DIR" -type f | wc -l
find "$NEW_DIR" -type f | wc -l
```

Start only the new Codex App from the Home Assistant UI. Keep the backup and
the old App stopped until authentication, GitHub SSH access, Codex sessions,
and the working directory have been checked. If the migration must be
reverted, stop the new App, move its directory aside, and restore the backup
directory after validating both paths again.

## What Changed

- Codex CLI `0.146.1` is installed while the image is built.
- iOS terminal scrolling and selection use documented ttyd/xterm client
  options; native clipboard access may still be restricted by the HA WebView.
- Desktop browsers automatically copy selected terminal text; keyboard
  shortcuts remain available as a fallback.
- Touch devices show a full-width terminal toolbar with scroll, copy, and paste
  fallbacks.
- Codex conversations remain available after an App restart or update and can
  be restored with `codex resume` or `codex resume <session-id>`.
- Runtime npm updates are disabled; the App no longer writes into `/usr/local`
  during startup.
- The image-installed executable is preferred over stale user-level launchers
  under `/data/codex-home/users/anonymous/.local/bin`.
- Existing App options, the `codex` slug, and the persistent Codex state paths
  remain compatible.

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

Home Assistant's **Auto update** option is the supported automation for future
Codex App versions and the Codex CLI versions included in them.

## Rollback

If the upgrade fails, stop the new App and restore the Home Assistant backup.
Keep the old App data until the new image and authentication have been checked.
