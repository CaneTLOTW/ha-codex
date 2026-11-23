# Codex CLI 0.171.0: SQLite migration error 14 on HAOS

Issue: #43. First reproduced 2026-11-20/21 in **Stable Codex**, again 2026-11-22 with `state_5.sqlite` and migration 64.

## Symptom

```text
Codex couldn't start because its local database appears to be damaged
Location: /data/codex-home/users/anonymous/.codex/state_5.sqlite
while executing migration 64: (code: 14) unable to open database file
```

The wording is misleading in this case. Prior checks established the existing database was integral, space and permissions looked correct, and a **brand-new isolated database** also failed (migration 23). A writable private SQLite temporary directory fixed startup without replacing the DB or its sessions.

## Immediate recovery on Stable 0.4.36

When the ttyd session offers `Press Enter to retry Codex, or type 'shell'`, enter `shell` and run:

```bash
D=/data/codex-home/users/anonymous/.codex
mkdir -p "$D/_sqlite_tmp"
chmod 700 "$D/_sqlite_tmp"
export SQLITE_TMPDIR="$D/_sqlite_tmp"
export TMPDIR="$D/_sqlite_tmp"
codex
```

Use the exact existing `anonymous` home for a normal direct-ingress Codex session. This modifies **no database**. The exports last only in the current shell.

For a persistent **no-image-update** workaround in the Home Assistant UI, under **Settings → Apps → Codex → Configuration → Environment variables** create two entries:

| Name | Value |
| --- | --- |
| `SQLITE_TMPDIR` | `/data/codex-home/users/anonymous/.codex/_sqlite_tmp` |
| `TMPDIR` | `/data/codex-home/users/anonymous/.codex/_sqlite_tmp` |

Create the target directory and set 0700 permissions as shown above *before* switching to the UI configuration. Save the options and restart **only the affected Stable Codex App**. With `session_persistence: true`, an existing tmux process may retain its old environment until the App restarts. Do not change user credentials or `CODEX_SQLITE_HOME`.

## Permanent developer fix

In the post-0.5.0-dev.1 developer candidate, the managed ttyd session and optional native Remote Control sidecar create/validate an owner-private, mode-0700 `$CODEX_HOME/_sqlite_tmp` and export both `SQLITE_TMPDIR` and `TMPDIR`. Existing explicit `environment_variables` can still override them if the operator deliberately configured a different location.

Do **not** delete `state_5.sqlite`, associated WAL/SHM files or Codex `sessions`. Do not switch `CODEX_SQLITE_HOME` unless testing an isolated disposable database.

## Runtime acceptance

1. Read actual Codex App name/version: verify Stable vs Deployment independently.
2. Check writable/owned `_sqlite_tmp`, then confirm ttyd Codex CLI real startup and project/session readback (not merely `codex --version`).
3. Restart **only Deployment**, reconnect, confirm `TMPDIR` and `SQLITE_TMPDIR` are present in a fresh interactive Codex process and test a harmless new session.
4. With Remote Control enabled, verify real `codex exec` and app-server startup using the same private temp directory; iOS pairing remains a separate manual gate.
5. If code 14 persists with a writable temp directory, keep diagnostic data intact and obtain the full error chain and filesystem/mount evidence instead of deleting the state DB.

Reference: [SQLite temporary files and environment search order](https://sqlite.org/tempfiles.html).
