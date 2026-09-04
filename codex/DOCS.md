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

## Included command-line tools

The App image includes common tools for troubleshooting and project work:

- Python 3.13 (`python3`), Bash, Node.js and npm;
- Git and GitHub CLI (`gh`);
- OpenSSH **client** (`ssh`, `scp`, `sftp`), `curl` and OpenSSL;
- `jq`, `ripgrep` (`rg`), `grep`, `sed`, `gawk`, `find` and core utilities;
- `nano`, `vim` and `tmux`;
- p7zip / `7z`;
- Home Assistant CLI (`ha`), authenticated read-only wrapper (`ha-readonly`) and the bundled `hass-mcp` helper;
- `bubblewrap`, ACL tooling and the customized ttyd web terminal.

The image contains an SSH client, **not an SSH server**. It does not expose a separate inbound SSH service. Commands run inside the App container and remain subject to its AppArmor profile, mounted paths and selected Codex permission mode.

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

## Languages

The Home Assistant App configuration UI follows the Home Assistant language setting where a shipped translation is available. Current App option translations are English, German, Spanish, and Brazilian Portuguese.

## Terminal controls on Desktop and iOS

Desktop and mobile deliberately use different interaction paths. A narrow desktop browser window does not activate the touch toolbar; the mobile path requires actual touch capability and a mobile/touch platform signal.

| Interaction | Desktop / PC | iPhone / iPad |
| --- | --- | --- |
| Input | Physical keyboard and normal ttyd/xterm controls | Two-row touch toolbar plus the iOS software keyboard |
| Selection | Mouse drag | `Sel` mode, then native long-press/drag selection |
| Copy/Paste | Browser/OS context menu and normal terminal shortcuts | Native iOS Copy/Paste while `Sel` is active |
| Scrolling | Mouse wheel / terminal history | Vertical swipe or `PgUp` / `PgDn` |
| Software keyboard | Not applicable | `Kbd↑` shows it and `Kbd↓` hides it |
| Keyboard avoidance | Not active | Terminal automatically moves/resizes above the software keyboard |

### iOS mobile toolbar

<img width="360" alt="Codex terminal on iOS with mobile controls and keyboard avoidance" src="../docs/assets/ios-keyboard-avoidance-0.4.8.webp" />

*Anonymized stable `0.4.8` runtime screenshot with the iOS software keyboard open.*

```text
Enter  ←    ↓     ↑     →      Sel   PgUp  Kbd↑
Esc    Tab  Ctrl  Alt   Shift  ⇪     PgDn  Kbd↓
```

| Control | What it does |
| --- | --- |
| `Enter` | Sends Enter. It also follows ttyd's manual reconnect path after a disconnect. |
| `←` `↓` `↑` `→` | Sends the matching arrow key without forcing the software keyboard open. |
| `Sel` | Turns iOS-native selection mode on/off. While active, long-press or drag terminal text and use the native Copy/Paste actions. Turn it off again for normal input and swipe behavior. |
| `PgUp` / `PgDn` | Moves by one terminal page. With session persistence enabled, this uses tmux copy-mode navigation. |
| `Esc` | Sends Escape. |
| `Tab` | Sends Tab. |
| `Ctrl` / `Alt` / `Shift` | One-shot modifiers for the next eligible key. |
| `⇪` | Persistent Shift Lock; tap again to release. |
| `Kbd↑` | Focuses terminal input and opens the iOS software keyboard. |
| `Kbd↓` | Hides the software keyboard and returns the terminal to its normal full-height layout. |
| Vertical swipe | Performs page navigation without needing the software keyboard. |

### iOS selection, copy and paste

On iOS, `Sel` temporarily enables a DOM-backed native-selection mode. Long-press/drag terminal output to use the native selection handles and Copy action. Native Paste at the prompt is routed through xterm and inserted once. Leaving `Sel` restores the normal renderer, swipe navigation and terminal input behavior.

`Sel` and the keyboard controls are independent: `Kbd↑` / `Kbd↓` only show or hide the software keyboard and do not change selection mode.

### iOS software-keyboard avoidance

When the software keyboard opens, the usable visual viewport becomes shorter. The terminal detects that change, shortens the existing terminal host by the same amount, refits xterm and brings the active prompt into view. The terminal and toolbar therefore remain above the iOS keyboard instead of being covered by it.

When the keyboard closes or `Kbd↓` is used, the temporary height is removed and the terminal is fitted back to the normal Home Assistant ingress viewport.

The final iOS toolbar, native selection/copy/paste path, keyboard show/hide behavior and keyboard avoidance were accepted on-device for stable `0.4.8`. Desktop regression testing separately confirmed that the normal mouse/keyboard selection and input path remains intact.

### Android status / feedback requested

The general toolbar and paging implementation uses generic browser pointer/touch events and is expected to work on Android, but it has **not yet been validated on a real Android Companion/browser runtime**.

The current native `Sel` path is intentionally gated to Apple touch devices, so native selection/copy/paste through `Sel` is **not currently claimed for Android**.

Please report Android results in [GitHub issue #6](https://github.com/CaneTLOTW/ha-codex/issues/6), including device/Android version, Companion or browser version, toolbar/modifier behavior, paging/swipe, keyboard show/hide and copy/paste behavior.

The managed web session disables Codex's alternate screen so output remains available in xterm scrollback. The mobile frontend is maintained as one source patch against clean ttyd 1.7.7; no separate xterm fork or patch-on-patch chain is used.

## Automatic Codex CLI updates

The Codex CLI is pinned into the App image. Runtime npm updates are intentionally not part of App startup.

The repository automatically checks for a newer `@openai/codex` release every day. When a new CLI version or visible model-catalog change is found, the maintenance workflow refreshes the pinned CLI/model list, increments the Home Assistant App patch version, updates the changelog, and publishes signed `amd64`/`aarch64` images plus the generic multi-architecture manifest through the normal `codex/**` main-branch push trigger.

The resulting Codex CLI update therefore arrives as a normal Home Assistant App update instead of changing the running container in place. Enable Home Assistant **Auto update** on the App page if newly published App versions should be installed automatically.

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

### Mobile selection/copy/paste on iOS

Enable `Sel`, select text with the native iOS handles and use Copy/Paste. Disable `Sel` again when finished.

### The iOS keyboard covers the terminal

Current versions should automatically shorten/refit the terminal while the software keyboard is open. Use `Kbd↓` to close the keyboard and reset the terminal height, then `Kbd↑` to reopen it. If the prompt or toolbar is still covered, report the iOS version, Home Assistant Companion/browser version and orientation.

### Android mobile behavior

Android is still a requested test target. The generic toolbar/paging path should be tested now; the current native `Sel` path is Apple-only. Report results in [issue #6](https://github.com/CaneTLOTW/ha-codex/issues/6).
