# Working effectively with HA-Codex

Tracking: #14. This is an optional project workflow; neither a Git repository nor a project-specific `AGENTS.md` is required to start using Codex.

## Where things live

| Path | Meaning |
| --- | --- |
| `/homeassistant` | Home Assistant Core config (called `/config` inside HA Core) |
| `/share` and `/media` | Shared/media data; may contain external mounts |
| `/ssl` and `/backup` | Mapped read-only by the App |
| `/addons` | Local App source trees: host-level RW mount, Codex access controlled by `addons_access` |
| `/data` | Persistent private App data; current Codex state lives under `/data/codex-home` |

**Caution:** `addons_access: read_only` is enforced by the Codex sandbox/launch policy, not by a read-only mount on the host. A shell with broader privileges is not equivalent to an enforced sandbox. `addons_access: read_write` grants broad access to local App sources. Since Stable 0.5.1, public configuration directories of other Apps are statically mounted read-only at `/app_configs`. `app_configs_visibility` only controls guidance; files can still be read when hidden. Treat credentials as sensitive and never disclose them.

The container's own unmounted/temporary changes are ephemeral. Use managed persistent paths when the change must survive an image update.

## Tools built into the image

Codex CLI, Bash, Python 3.13, Node/npm, Git/`gh`, `ssh` (client), `curl`, `jq`, `yq`, `yamllint`, `rg`, `sqlite3`, `mosquitto_pub`/`mosquitto_sub`, `dig`, `nc`, `tree`, `rsync`, `tmux`, `7z`, `zip` and `unzip` are part of the current stable image. Home Assistant MCP and the dedicated [Lovelace resource MCP](../codex/docs/LOVELACE_RESOURCE_DEPLOYMENTS.md) are available when enabled. The latter requires a reviewed preview/confirmation and paused competing writers for mutation. The `ha-readonly` helper permits `core info`, `core check` and `core logs` only; the interactive user does not receive the raw Supervisor token. No inbound SSH server is included.

## Safe iterative workflow

1. **Inspect:** identify entities, scripts, config files and expected behavior. Read first.
2. **Plan:** describe edits, scope, risks and how to undo them.
3. **Change:** use a Git worktree/branch when possible; keep one concern per patch.
4. **Validate:** run targeted tests, `yamllint`, `ha-readonly core check` where appropriate, and ensure real HA/MCP results match expectations.
5. **Review:** inspect `git diff`, avoid leaking secrets in logs or commits.
6. **Apply / rollback:** make operational changes only after explicit approval; verify actual runtime and preserve a rollback path.

## Example project instructions

Put a project-specific `AGENTS.md` in the chosen project directory, for example:

```md
# Project instructions
- Read configuration and explain the proposed change before editing.
- Do not change security settings, networking or credentials without approval.
- Validate YAML and report the exact commands used.
- Show a diff, expected effect and rollback plan before applying changes.
- For Home Assistant Core, paths are relative to /homeassistant in this container.
```

Project instructions do not override actual file permissions, Home Assistant Supervisor restrictions or the user's approval policy. Keep security-sensitive values out of this file.

## Browser session behavior

`session_persistence: true` uses tmux to keep the shell process alive when a browser connection ends. **It does not stop ingress WebSocket disconnects**; transport-level recovery is tracked separately in #34.
