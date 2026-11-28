# Access to other Home Assistant app configuration (Issue #12)

## Current architecture

Stable since 0.5.1 and Deployment both map `/homeassistant`, `/share`, `/media`, `/ssl`, `/backup`, local App sources at `/addons`, and public App configuration folders at `/app_configs` (static read-only). The local-source `addons_access` setting is independent of `/app_configs`; `app_configs_visibility` controls guidance only, not actual access. AppArmor declarations alone cannot make files appear unless the Supervisor map mounts them.

As of 2026-11-22, official Home Assistant App configuration documentation uses the newer mount type `all_app_configs` with default target `/app_configs`. The older `all_addon_configs` name is still accepted as a legacy alias, historically mounted under `/addon_configs`, but generates a warning; **do not add deprecated names**. Use an explicit `path` only if compatibility with an older container path is actually required.

References:
- https://contributors.home-assistant.io/apps/reference/configuration/
- https://contributors.home-assistant.io/apps/reference/environment/

## Least-privilege decision

Other App configurations can contain long-lived tokens, passwords, and service credentials. Exposing the entire tree is a broad privilege change, even when read-only. The mount was shipped in Stable 0.5.1; do not widen it or imply that a guidance option revokes it. The remaining design question is whether a separate explicit install-time opt-in variant is needed.

Suggested future architecture:
1. First document concrete cross-app diagnostic use cases and whether data is obtainable through an authenticated Home Assistant API or app-specific MCP.
2. If a mount is truly necessary, evaluate a separate, explicitly installed developer/canary app with `{ type: all_app_configs, read_only: true }`, rather than silently widening the stable installation.
3. Treat read/write as a separate explicit admin decision requiring snapshots/rollback and strict path controls. No default RW.
4. Recognize that Supervisor mounts are defined in app metadata; a `false` runtime toggle does not remove a broad host mount. A UI option alone must not be described as host-level protection.
5. Update real AppArmor rules, agent guidance, file paths, and test fixtures together after deciding on the design.

## Acceptance

- Read-only tests cannot alter files even outside Codex sandbox.
- No credentials from other app folders are written to logs or Git issues.
- All authorized App projects still work when the mount is absent.
- Both app names and container paths are checked against the user's specific Supervisor version.
- Separate installation approval before any image rollout.

**Status:** existing static read-only mount documented; true opt-in architecture and real fixture acceptance remain open (#12/#51). No permission or mount change in this documentation update.
