# Codex App documentation

Codex runs the OpenAI Codex CLI inside a Home Assistant App and exposes it through Home Assistant ingress.

## First start

1. Start the App.
2. Open **Codex** from the Home Assistant sidebar.
3. Sign in to Codex using the authentication method offered by the CLI.
4. Use `/homeassistant` as the Home Assistant configuration directory.

The App keeps Codex authentication and user configuration under `/data/codex-home` so they survive App restarts and image updates.

## Mounted paths

| Path | Access | Purpose |
| --- | --- | --- |
| `/homeassistant` | read-write | Home Assistant configuration |
| `/share` | read-write | Home Assistant shared files |
| `/media` | read-write | Home Assistant media |
| `/ssl` | read-only | Home Assistant SSL files |
| `/backup` | read-only | Home Assistant backups |

Inside this App, `/homeassistant` corresponds to the Home Assistant Core `/config` directory.

## App options

### Home Assistant MCP

`enable_mcp` controls the bundled `homeassistant` MCP server. When enabled, Codex can use the managed MCP helper to query Home Assistant and call services.

Disabling `enable_mcp` removes only the App-managed `homeassistant` MCP entry. Unrelated user MCP configuration is preserved.

### Additional MCP servers

`mcp_servers` adds remote Streamable HTTP MCP servers:

```yaml
mcp_servers:
  - name: example
    url: https://mcp.example.com/mcp
    bearer_token: your-token
```

Rules:

- `name` must be unique.
- `homeassistant` is reserved for the bundled server.
- `url` must start with `http://` or `https://`.
- `bearer_token` is optional.

When a bearer token is supplied, the App generates an environment-variable name such as `CODEX_MCP_EXAMPLE_BEARER_TOKEN` and references that name from Codex `config.toml`. The token value itself is supplied through the Codex process environment.

If App management later removes a remote MCP server that replaced a same-name user-defined entry, the previous user entry is restored.

### Environment variables

`environment_variables` adds explicitly configured variables to Codex sessions:

```yaml
environment_variables:
  - name: EXAMPLE_TENANT
    value: home
```

Names must use normal environment-variable syntax. Values are stored in Home Assistant App options, so only configure credentials that Codex or its MCP servers are intended to use.

### Model and permissions

- `default_model` chooses the managed startup model.
- `codex_permissions: workspace` maps to Codex `workspace-write`.
- `codex_permissions: full_access` maps to `danger-full-access`.
- `codex_approval_policy` supports `on-request`, `untrusted`, and `never`.

The App merges these managed settings into the persistent user configuration without removing unrelated Codex settings.

### Session persistence

With `session_persistence: true`, the terminal uses tmux so the terminal session can survive browser refreshes and reconnects.

Codex conversations are stored independently of tmux and can be restored with:

```text
codex resume
```

## Mobile terminal controls

On touch devices and narrow screens the terminal provides:

```text
Esc  Tab  Ctrl  Alt  ←  ↓  ↑  →  PgUp  PgDn
```

`Ctrl` and `Alt` are one-shot modifiers for the next key. Vertical swipe gestures perform page navigation. With tmux persistence enabled, `PgUp` and `PgDn` integrate with tmux copy mode.

The managed web session disables Codex's alternate screen so output remains available in the xterm scrollback. Desktop selection, browser context menus, and normal terminal/browser clipboard shortcuts remain handled by ttyd/xterm instead of a separate custom clipboard patch.

## Codex CLI updates

The Codex CLI is pinned into the App image. Runtime npm updates are intentionally not part of App startup.

New Codex CLI releases are delivered through new Home Assistant App versions and GHCR images. Enable Home Assistant **Auto update** on the App page if desired.

## Migration from another repository

A matching App slug does not guarantee that two Home Assistant repositories share the same App installation identity or data directory. Read the repository-level [MIGRATION.md](../MIGRATION.md) before moving an existing installation.

## Troubleshooting

### MCP is still present after disabling it

Restart the App after saving `enable_mcp: false`. The App removes its managed `homeassistant` MCP entry during configuration merge.

### Additional MCP server is missing

Check that:

1. its name is unique;
2. the URL starts with `http://` or `https://`;
3. the App was restarted after editing the options.

### Project configuration is ignored

Use `/homeassistant/.codex/config.toml` and make sure `/homeassistant` is trusted by Codex before relying on project-specific configuration.

### Mobile scrolling

Use vertical swipes or the `PgUp`/`PgDn` controls. With session persistence enabled, page navigation enters or uses tmux copy mode.
