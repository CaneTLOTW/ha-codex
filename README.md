# Codex App for Home Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Run OpenAI Codex from the Home Assistant sidebar with a maintained, image-pinned Home Assistant App.

This repository publishes one Home Assistant App: **Codex**. It provides a browser terminal inside Home Assistant, starts in the Home Assistant configuration directory, and can connect Codex to Home Assistant and additional services through MCP.

## Project Status

This project started from the original [`kecksdigital/codex-hass`](https://github.com/kecksdigital/codex-hass) codebase but is now maintained as an **independent repository**.

The original upstream `main` has not received a commit since **May 30, 2026**, while fixes and feature pull requests remain open. It currently appears to be unmaintained. Useful upstream contributions are reviewed and selectively ported here rather than treating upstream `main` as the release source.

This repository does **not** claim repository-level or installation-level drop-in compatibility merely because both Apps use the `codex` slug. Home Assistant can assign different repository/App data identities. If you are moving an existing installation from another repository, read [MIGRATION.md](MIGRATION.md) and verify the actual App data directories before copying anything.

## Why This Repository

The original App could become unusable after a runtime npm update because writable Home Assistant mounts are not executable under the App security model, while the unprivileged terminal user cannot safely replace the image-installed CLI.

This repository therefore:

- pins the Codex CLI into the published container image;
- delivers CLI updates as normal Home Assistant App releases;
- keeps runtime npm updates out of the startup path;
- builds and tests a customized ttyd frontend for Home Assistant mobile use;
- maintains the Home Assistant MCP configuration without overwriting unrelated user settings;
- supports additional remote Streamable HTTP MCP servers and explicit Codex environment variables.

## Install

[![Add Repository](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FCaneTLOTW%2Fha-codex)

Manual installation:

1. Open **Settings → Apps → App Store** in Home Assistant.
2. Open **Repositories** from the three-dot menu.
3. Add `https://github.com/CaneTLOTW/ha-codex`.
4. Install **Codex**.
5. Start the App and open it from the sidebar.

## What You Get

- OpenAI Codex CLI running in Home Assistant.
- Prebuilt `amd64` and `aarch64` GHCR images.
- Direct access to `/homeassistant`, `/share`, and `/media`.
- Read-only access to `/ssl` and `/backup`.
- Bundled Home Assistant MCP integration for entity lookup and service calls.
- Optional additional remote Streamable HTTP MCP servers.
- Optional environment variables for Codex/MCP sessions.
- Persistent Codex authentication and settings under `/data/codex-home`.
- Model, sandbox, approval, MCP, terminal theme, and session-persistence controls in the Home Assistant UI.
- Touch-friendly mobile terminal controls with `Esc`, `Tab`, `Ctrl`, `Alt`, arrows, `PgUp`, and `PgDn`.
- Mobile swipe navigation and tmux copy-mode page navigation.
- Web-terminal Codex sessions that preserve output in xterm scrollback.

## Authentication

Codex authentication happens inside the terminal. Home Assistant does not need to store your OpenAI API key, ChatGPT session, or Codex access token in App options.

Credentials that you explicitly configure for an additional MCP server or as an environment variable are stored in Home Assistant App options and made available only to the Codex runtime environment. MCP bearer-token values are referenced from Codex configuration through generated environment-variable names rather than being written directly into `config.toml`.

## Defaults

- Model: `gpt-5.6-sol`; the selectable model list is maintained from the bundled Codex CLI catalog.
- Access: `workspace`.
- Approval policy: `on-request`.
- Session persistence: off by default; previous Codex conversations remain available through `codex resume`.
- Bundled Home Assistant MCP: on.
- Codex CLI updates: delivered through Home Assistant App versions, not runtime npm updates.

Use `full_access` only when broad local access inside the App container is intended. Use `codex_approval_policy: never` only when autonomous execution without per-action approval prompts is intended.

## Updates

A scheduled GitHub Actions workflow checks for newer `@openai/codex` releases. A new CLI version updates the image pin, increments the Home Assistant App version, and publishes new multi-architecture images.

The App uses:

```text
ghcr.io/canetlotw/ha-codex:<version>
```

Enable **Auto update** on the Codex App page if Home Assistant should install newly published App versions automatically.

## Documentation

- [Home Assistant App documentation](codex/DOCS.md)
- [Detailed repository guide](codex/README.md)
- [Migration notes](MIGRATION.md)

Useful Codex documentation:

- [Codex CLI](https://developers.openai.com/codex/cli)
- [Codex authentication](https://developers.openai.com/codex/auth)
- [Codex configuration](https://developers.openai.com/codex/config-basic)
- [Codex configuration reference](https://developers.openai.com/codex/config-reference)
- [Codex MCP configuration](https://developers.openai.com/codex/mcp)

## Support and Contributions

- [Issues](https://github.com/CaneTLOTW/ha-codex/issues)
- [Pull requests](https://github.com/CaneTLOTW/ha-codex/pulls)

Bug fixes and focused improvements are welcome. Contributions from the original repository are reviewed for compatibility with this repository's image-pinned update model and current Home Assistant App architecture.

## License

MIT License
