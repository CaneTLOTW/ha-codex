# `/addons` access in the Codex Home Assistant App

Home Assistant App mount permissions are part of static `config.yaml` metadata. They cannot be remounted read-only/read-write from an App option at runtime. To support both modes, the Codex App maps the Home Assistant local-App directory `/addons` with host-level read-write capability and applies the selected policy inside the Codex runtime.

## App option

`addons_access` supports:

- `read_only` (default): Codex may inspect local App sources but `/addons` is removed from every effective workspace writable-root setting.
- `read_write`: Codex may modify local App sources. In workspace mode `/addons` is added to the effective writable roots; filesystem access for the unprivileged Codex runtime user is prepared at App start.

## Interaction with Codex access level

Codex `danger-full-access` cannot exclude one filesystem path. Therefore, when `addons_access: read_only` is combined with `codex_permissions: full_access`, the App deliberately uses effective `workspace` mode for the Codex session. This fail-safe prevents the UI from claiming read-only `/addons` access while running an unrestricted Codex filesystem sandbox.

If full Codex access and writable local Apps are required, configure:

```yaml
codex_permissions: full_access
addons_access: read_write
```

If local Apps must stay read-only, use the default:

```yaml
addons_access: read_only
```

The App also refuses to use a working directory below `/addons` while the path is configured read-only and falls back to `/homeassistant`.

## Security boundary

The option controls Codex sessions. The diagnostic Bash shell that is opened after Codex itself exits is intentionally not presented as a Codex sandbox boundary. Home Assistant AppArmor remains active, and the App still runs interactive Codex as the unprivileged UID 22000 rather than root.
