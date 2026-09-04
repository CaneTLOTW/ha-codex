# Codex App for Home Assistant

Codex App puts the OpenAI Codex CLI inside Home Assistant so you can inspect, edit, and troubleshoot Home Assistant configuration from the sidebar.

For the Home Assistant App documentation shown in the App UI, see [DOCS.md](DOCS.md).

## How It Works

1. Home Assistant opens Codex through ingress.
2. A customized ttyd 1.7.7 build serves the browser terminal on port `7681`.
3. The terminal starts in `/homeassistant`.
4. Codex state is persisted under `/data/codex-home/users/anonymous/.codex`.
5. Managed defaults are merged into `~/.codex/config.toml` without deleting unrelated user configuration.
6. The App generates `~/.codex/AGENTS.md` with Home Assistant path and MCP guidance.
7. The bundled `homeassistant` MCP server is added when `enable_mcp` is enabled.
8. Additional remote Streamable HTTP MCP servers can be managed from App options.
9. On touch devices and narrow screens, ttyd provides a two-row mobile key bar and page navigation; native `Sel` selection mode is currently Apple-specific.

OpenAI authentication stays in Codex's persistent home. Credentials explicitly configured for remote MCP servers or environment variables are stored in Home Assistant App options and supplied to the Codex process environment.

## Install

1. Add `https://github.com/CaneTLOTW/ha-codex` to **Settings → Apps → App Store → Repositories**.
2. Install **Codex**.
3. Review the App options.
4. Start the App.
5. Open **Codex** from the Home Assistant sidebar.

The App is published as prebuilt multi-architecture GHCR images.

## First Sign-In

Codex starts automatically when the terminal opens. If normal browser authentication cannot complete from the Home Assistant container, use device authentication:

```bash
codex login --device-auth
```

Codex caches the login in its persistent home.

## Paths

| Path | Purpose | Access |
| --- | --- | --- |
| `/homeassistant` | Home Assistant configuration | read-write |
| `/share` | Shared Home Assistant files | read-write |
| `/media` | Media files | read-write |
| `/ssl` | SSL certificates | read-only |
| `/backup` | Backups | read-only |

When documentation or a prompt refers to Home Assistant Core `/config`, use `/homeassistant` inside this App.

## Bundled command-line tools

The published image includes a practical development and troubleshooting environment so Codex can do more than edit YAML:

| Area | Included tools |
| --- | --- |
| Scripting/runtime | Python 3.13 (`python3`), Bash, Node.js, npm |
| Source control | Git, GitHub CLI (`gh`) |
| Remote/network | OpenSSH **client** (`ssh`/`scp`/`sftp`), `curl`, OpenSSL |
| Data/search | `jq`, `ripgrep` (`rg`), `grep`, `sed`, `gawk`, `find` and GNU/core utilities |
| Editors/session | `nano`, `vim`, `tmux` |
| Archives | p7zip / `7z` |
| Home Assistant | Home Assistant CLI binary (`ha`), authenticated read-only wrapper (`ha-readonly`), bundled `hass-mcp` helper |
| Sandbox/support | `bubblewrap`, ACL tools, customized ttyd |

The App contains an **SSH client only**. It does not run or expose an inbound SSH server. All commands execute inside the App container and are constrained by its AppArmor profile, mounted Home Assistant paths and the selected Codex permission mode.

The interactive Codex shell intentionally does **not** receive the Supervisor token. The raw `ha` CLI is present for completeness, but authenticated Core diagnostics are exposed through the narrow `ha-readonly` wrapper instead. It permits only `ha-readonly core info`, `ha-readonly core check`, and `ha-readonly core logs`; mutations remain unavailable through that wrapper. Entity/state work should normally use the managed `homeassistant` MCP server.

## Mobile Terminal

The App builds ttyd 1.7.7 from source with one canonical mobile-controls patch. On touch devices and narrow screens the toolbar is a fixed two-row grid:

```text
Enter  ←    ↓     ↑     →      Sel   PgUp  Kbd↑
Esc    Tab  Ctrl  Alt   Shift  ⇪     PgDn  Kbd↓
```

`Ctrl`, `Alt`, and `Shift` are one-shot modifiers; `⇪` is persistent Shift Lock. The arrow and page keys work without opening the software keyboard, while `Kbd↑` and `Kbd↓` explicitly show or hide it. Vertical swipes perform page navigation. With `session_persistence` enabled, `PgUp`/`PgDn` and swipes integrate with tmux copy mode.

`Sel` is an opt-in iOS-native text-selection mode. It temporarily switches the terminal to DOM-rendered rows, enables native WebKit selection/callouts, and keeps xterm's helper textarea available for native Paste. This allows long-press selection, Copy, and Paste on iPhone/iPad without using `navigator.clipboard.readText()`. Leaving `Sel` restores the configured renderer and normal swipe/input behavior.

### Android status

The toolbar itself uses generic pointer/touch events and the paging/swipe path is not gated to Apple devices. Toolbar buttons, modifiers, page navigation, keyboard show/hide, swipe paging and tmux integration are therefore **expected to work on Android**, but this has not yet been verified on a real Android Home Assistant Companion/browser runtime.

Native `Sel` mode is intentionally different: the maintained ttyd patch currently enables its native-touch selection path only for Apple touch devices. Android native selection/copy/paste through `Sel` is **not currently supported or claimed**.

Android runtime feedback is requested in [issue #6](https://github.com/CaneTLOTW/ha-codex/issues/6). A useful test report includes Android/device version, Home Assistant Companion or browser version, orientation, toolbar/modifier results, paging/swipe behavior, keyboard show/hide and copy/paste behavior.

The managed web session starts Codex with `tui.alternate_screen="never"` so previous output remains available in xterm scrollback. Toolbar `Enter` also follows ttyd's manual reconnect path when the WebSocket is disconnected, and embedded Home Assistant ingress avoids adding a duplicate iOS bottom safe-area inset.

The mobile implementation is kept in `ttyd-mobile-keys/ttyd-1.7.7-mobile-keys.patch`, applied directly to clean ttyd 1.7.7. There is no patch-on-patch chain or separate xterm fork. Desktop text selection, native browser context menus, and normal ttyd/xterm clipboard shortcuts remain separate from the mobile selection mode.

The `0.4.0` mobile path was validated on-device with Home Assistant Companion on iPhone using Codex CLI `0.151.0`, `gpt-5.6-sol`, and `/homeassistant` as the working directory.

## App Options

| Option | Default | Purpose |
| --- | --- | --- |
| `enable_mcp` | `true` | Manage the bundled `homeassistant` MCP server |
| `terminal_font_size` | `14` | Web-terminal font size, clamped to `10-24` |
| `terminal_theme` | `dark` | Dark or light terminal theme |
| `working_directory` | `/homeassistant` | Starting directory |
| `session_persistence` | `false` | Reattach the terminal through tmux |
| `default_model` | `gpt-5.6-sol` | Managed startup model; choices follow the bundled CLI catalog |
| `codex_permissions` | `workspace` | Codex sandbox profile |
| `codex_approval_policy` | `on-request` | Codex action-approval policy |
| `mcp_servers` | `[]` | Additional remote Streamable HTTP MCP servers |
| `environment_variables` | `[]` | Additional variables supplied to Codex sessions |

## Home Assistant MCP

When `enable_mcp` is `true`, the App manages a `homeassistant` MCP entry using `/usr/local/bin/hass-mcp-wrapper`.

The Home Assistant Supervisor token is not exported into the interactive shell. It is written to a protected runtime file and used only through the privileged helper path for the bundled Home Assistant MCP server.

An explicit `enable_mcp: false` is preserved. Disabling the option removes the App-managed `homeassistant` MCP entry rather than silently replacing `false` with the default `true`.

## Additional MCP Servers

Remote Streamable HTTP MCP servers can be configured in App options:

```yaml
mcp_servers:
  - name: example
    url: https://mcp.example.com/mcp
    bearer_token: your-token
```

Rules:

- names must be unique;
- `homeassistant` is reserved;
- URLs must begin with `http://` or `https://`;
- bearer tokens are optional.

A supplied bearer token is placed in a generated runtime environment variable and Codex receives only the variable name through `bearer_token_env_var` in `config.toml`.

Managed MCP entries are reversible. If App management replaces a same-name user-defined server, the previous user configuration is restored when App management for that server is removed.

## Environment Variables

Additional environment variables can be configured explicitly:

```yaml
environment_variables:
  - name: EXAMPLE_TENANT
    value: home
```

Variable names are validated. Values are available to the Codex runtime, so only configure credentials intended for Codex or its MCP servers.

## Models and Access

`default_model` controls only the startup default. Use `/model` inside Codex to switch during a session.

`codex_permissions` maps as follows:

| Option | Codex setting |
| --- | --- |
| `workspace` | `workspace-write` |
| `full_access` | `danger-full-access` |

`codex_approval_policy` supports `on-request`, `untrusted`, and `never`.

For autonomous operation you may deliberately combine:

```yaml
codex_permissions: full_access
codex_approval_policy: never
```

This removes the local Codex sandbox and per-action approval prompts inside the resources exposed to the App.

## Persistence

Codex user state is stored under:

```text
/data/codex-home/users/anonymous/.codex
```

Project-specific Codex configuration belongs in:

```text
/homeassistant/.codex/config.toml
```

Project instructions belong in:

```text
/homeassistant/AGENTS.md
```

Codex project configuration is loaded only for trusted projects.

## Session Persistence

With `session_persistence: true`, ttyd attaches to a tmux session. Browser refreshes and disconnects can then reattach to the same terminal process.

Codex conversations themselves survive independently and can be reopened with:

```bash
codex resume
```

Useful tmux controls include `Ctrl+b [` for copy mode and `q` to leave copy mode. The mobile `PgUp` and `PgDn` controls are also mapped to tmux copy-mode navigation.

## Codex CLI Updates

The Codex CLI is pinned during image build. Runtime npm updates are intentionally disabled.

A scheduled GitHub Actions workflow checks for new `@openai/codex` releases, updates the image pin and model catalog, increments the App version, and publishes a new GHCR image. Home Assistant **Auto update** can install those App releases automatically.

## Migration

This repository is maintained independently from the repository it originally derived from. A matching `codex` slug does not guarantee that Home Assistant treats two repository entries as one installation or assigns them the same data directory.

Read [../MIGRATION.md](../MIGRATION.md) before moving an existing installation between repositories.

## Troubleshooting

### MCP remains enabled after switching it off

Save `enable_mcp: false` and restart the App. Current versions preserve the explicit false value and remove the managed bundled MCP entry.

### An additional MCP server does not appear

Check that its name is unique, its URL begins with `http://` or `https://`, and the App was restarted after changing options.

### Project config is ignored

Confirm the file is `/homeassistant/.codex/config.toml` and that `/homeassistant` is trusted by Codex.

### Terminal output disappears when Codex redraws

The managed web session disables the alternate screen. If the behavior persists, verify that you are using the Codex session opened automatically by the App rather than a separately launched CLI with custom TUI settings.

### Mobile copy/paste is awkward on iOS

Enable `Sel`, long-press terminal text for the native selection handles, then use the native Copy action. For Paste, use the native iOS Paste action at the prompt while `Sel` is active. Leave `Sel` when finished to restore normal terminal swipe/input behavior.

### What about Android copy/paste?

Android is still an explicit feedback/test area. The generic toolbar should be testable now, but the current native `Sel` path is Apple-only. Please report Android behavior in [issue #6](https://github.com/CaneTLOTW/ha-codex/issues/6).

## References

- [Codex CLI](https://developers.openai.com/codex/cli)
- [Codex authentication](https://developers.openai.com/codex/auth)
- [Codex configuration](https://developers.openai.com/codex/config-basic)
- [Codex configuration reference](https://developers.openai.com/codex/config-reference)
- [Codex MCP](https://developers.openai.com/codex/mcp)

## Support

- [Repository](https://github.com/CaneTLOTW/ha-codex)
- [Issues](https://github.com/CaneTLOTW/ha-codex/issues)
