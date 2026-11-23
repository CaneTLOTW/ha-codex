# Changelog

All notable changes to this project will be documented in this file.

## [0.5.0-dev.8] - 2026-11-23

### Fixed (Developer HAOS screenshot upload permission follow-up)
- After the real Firefox/HAOS test of dev.7, screenshot clipboard events and the authenticated WebSocket flow work, and normal text Ctrl+V remains functional. PNG upload is rejected as `UPLOAD_PERMISSIONS` before reaching the running Codex TUI.
- Explicitly permit **read-only traversal of the /data directory itself** in the Developer AppArmor profile (`/data/ r,`). The existing `/data/** rwk,` covers descendants but not necessarily the parent directory opened using `open("/data", O_DIRECTORY|O_NOFOLLOW)` in our upload security implementation. This is the suspected permission denial, to be confirmed on HAOS.
- Preserve fixed private upload directory, UID 22000, mode-0700 directory/0600 file, O_NOFOLLOW and exclusive random basenames; no new mounts, network ports, elevated capabilities, or execute access on /data.
- Extend regression checks to prevent removal of `/data/ r,`. Stable 0.5.0 unchanged. Successful build alone does not establish real screenshot attachment acceptance.

## [0.5.0-dev.7] - 2026-11-23

### Fixed (Developer follow-up; HAOS acceptance pending)
- Fix two escaped frontend literals in the original screenshot-paste transport: PNG upload ACK path regex and bracketed-paste terminal ESC bytes. These could block attachment even after a server upload succeeded.
- Stop Ctrl+V keydown from reaching the TUI while still allowing native browser paste events; avoid Codex attempting the unreachable X11 clipboard inside HAOS.
- Distinguish restricted server-side upload failure categories (invalid PNG, missing/private upload directory, permissions, full/read-only storage, disabled socket) in browser feedback without exposing image bytes, absolute paths, authentication, or HA ingress URLs.
- Based on actual Firefox/HAOS failure of dev.6: browser reports `Screenshot upload rejected` and Codex reports `X11 server connection timed out`. The precise server-side rejection cause is not yet established; this build supplies category feedback for the next test.
- Stable 0.5.0 is unchanged. Do not claim screenshot attachment acceptance before a real HAOS image-content test.

## [0.5.0-dev.6] - 2026-11-23

### Added (Developer experiment)
- Support **direct Ctrl+V of PNG screenshots in the running Codex terminal** without first exiting the TUI, using the same authenticated ttyd WebSocket as terminal input. Captured PNG bytes are capped at 10 MiB, saved under the current private Codex user state with unpredictable mode-0600 filenames, and the generated absolute path is pasted using the terminal's bracketed-paste protocol.
- Reuse the image-path paste handler already included in the bundled Codex CLI 0.171.0 (verified against upstream tag `rust-v0.171.0`). The user can add a question before pressing Enter; the screenshot alone is never automatically submitted.
- `clipboard_image_paste` Developer option (default ON, can be disabled), with DE/EN/ES/PT-BR translations and regression tests. Normal text paste, manual file/folder uploads through `trzsz`, and existing ttyd mobile-selection and reconnect paths remain available.
- No extra HTTP endpoint, port, proxy, image upload server, new Supervisor capabilities or AppArmor privileges. WebSocket transfer is gated both in the browser and on the ttyd server, and can only save PNG screenshots into a fixed private directory.

### Acceptance limitations
- Image attachment and recognition must be confirmed on the operator's actual Home Assistant + Windows Firefox browser; automated CI only validates source, image C code, typescript and bundled runtime build.
- PNG screenshot paste is targeted first. JPEG/WebP clipboard images, direct non-image Ctrl+V and a paperclip picker inside the running TUI are follow-on enhancements.
- Each copied screenshot persists as a private file in Codex state. Do not upload secrets; retention/quota management will be reviewed after practical acceptance.
- Stable `main` remains on 0.5.0; no Stable upgrade is included. The separate RO mount of other Apps' public configuration from dev.5 is unchanged and is not disabled by the agent-guidance preference.

## [0.5.0-dev.5] - 2026-11-23

### Experimental additions
- Add opt-in ttyd 1.7.7 `trzsz` file transfer (server package pinned to 1.1.7), enabling upload of images and arbitrary files via browser file picker after `Ctrl+C` and `codex-upload`. `codex-upload --directory` supports directories. Uploads use per-user private Codex state. The `file_transfer_enabled` App option defaults OFF (#13).
- Mount other Home Assistant Apps' **public configuration folders** at `/app_configs` read-only, **Developer only**, with an `app_configs_visibility` guidance preference. This preference does not revoke the static Supervisor mount or hide secrets from app processes; turning it off is not a security control (#12).
- Add translated App options, explicit security notes and end-to-end HAOS acceptance test plan for Firefox LAN ingress, HTTPS browser behavior, file integrity, directories, non-regression and rollback.

### Deliberately not implemented yet
- Clipboard image `Ctrl+V` directly into an active Codex prompt, an always-visible Upload button, and attaching received images to the active conversation are follow-up UX work, not guaranteed by ttyd's transport.
- Desktop selection edge-scrolling (#25) and real Android device acceptance (#6) remain separate. The original desktop reporter was asked whether they are willing to test an eventual candidate; Android volunteers have been requested before assigning tests.
- No extra public port, no read-write access to /app_configs and no Stable release changes.

### Release gate
- Requires combined static/unit tests, AMD64/AARCH64 publish and signed multiarch manifest, then actual Firefox/HAOS Developer test with retained Codex login and sessions. Do not infer browser upload support from successful CI alone.

## [0.5.0-dev.4] - 2026-11-23

### Fixed
- Fix the manual `codex` command after Ctrl+C exits the Home Assistant terminal UI. The automatic first launch used `--no-daemon`, but the interactive fallback Bash shell started an unmodified Codex CLI and hit AppArmor's intended non-executable `/data` boundary, returning `Permission denied (os error 13)` (#47).
- Use one shared image-installed TUI launcher for both the initial ttyd session and subsequent interactive `codex`, `codex resume`, `codex fork`, and supported TUI options. It consistently preserves `--no-daemon`, model/session configuration and the `addons_access` writable-roots guard.
- Leave CLI management operations (e.g. `codex login`, `codex exec`, `codex mcp`, `codex app-server`, `codex --version`) unmodified in the interactive shell.
- Add a fake-CLI regression test that exercises the actual Dockerfile Bash startup configuration and verifies the manual restart, resume/fork arguments, no duplicate daemon flags, `/addons` restrictions and pass-through commands.

### Acceptance
- Test Ctrl+C → `codex` → Ctrl+C → `codex resume --last` repeatedly on a real HAOS Developer instance. Confirm history, SQLite temporary directory, session identity and Home Assistant MCP remain intact and that neither the CLI daemon execution denial nor the earlier SQLite startup error reappears.
- Require successful combined CI, AMD64/AARCH64 image publication and signed multiarch manifest before Developer installation. Stable `main` and production remain untouched until a separate approval.

## [0.5.0-dev.3] - 2026-11-22

### Fixed
- Fix a startup regression introduced in dev.2: `su-exec ... test` resolved a Python wrapper at `/usr/local/bin/test` that imports unavailable `pytest`, incorrectly reporting the SQLite scratch directory as unwritable. Replaced it with a shared POSIX-shell verifier using built-in tests plus a disposable `mktemp` write probe for terminal and Remote Control (#45).
- Avoid the new Codex CLI's managed background daemon installation under writable `/data` for the interactive ttyd terminal, using the officially supported `--no-daemon` mode. The Home Assistant AppArmor profile intentionally has no execute rights for `/data/**`; do not loosen that boundary. The optional Remote Control sidecar remains separate and off by default.
- Add a test that poisons `PATH` with a broken external `test` executable, ensures the real temp-directory checker still works and rejects symlinks/non-directories, and checks the AppArmor no-execute rule.

### Acceptance
- Requires a fresh successful CI run and both-architecture signed multiarch publication. A successful build does **not** establish real Home Assistant OS operation.
- Verify the normal Codex profile opens without entering a fallback shell, creates no unintended files, and retains existing history; inspect SQLite migration, auth/MCP and reconnect behavior.
- If a daemon-mode feature is actually needed later, evaluate a safe architecture rather than granting execution from all of `/data`. Stable remains 0.4.36 until separately accepted.

## [0.5.0-dev.2] - 2026-11-22

### Fixed
- Initialize a persistent private SQLite temporary directory under each Codex user home and pass `SQLITE_TMPDIR` plus `TMPDIR` into both the interactive Codex session and optional Remote Control sidecar. This persists the proven workaround for CLI 0.171.0 migration 64 / SQLite error code 14 across app restarts (#43).
- Verify that the directory is not a symlink, is accessible by the unprivileged Codex UID and has mode 0700; do not edit, replace, delete or migrate the existing state_5.sqlite database.
- Regression-test the environment/permission contract and preserve user-provided explicit environment overrides.

### Notes
- Stable remains at 0.4.36 until separately approved; developer 0.5.0-dev.2 requires new CI, AMD64/AARCH64 publish/manifest, and actual HAOS runtime acceptance before production promotion.
- This addresses the demonstrated temporary-filesystem failure mode; further SQLite diagnostics are required if state initialization still fails despite the writable temporary directory.

## [0.5.0-dev.1] - 2026-11-22

### Fixed
- Recover automatically from Home Assistant ingress ttyd WebSocket disconnects, including close code 1000, with bounded exponential retry, visibility-triggered retry, and Enter fallback (#34, draft #35).
- Avoid permission traversal into external filesystems and continue with explicit warnings when both ACL and chmod fail (#32, draft #36).
- Preserve canonicalized /addons writable-root checks and protected SSH-key exclusions from the earlier deployment safety preparation.

### Added
- Carry forward the optional official Remote Control app-server with Home Assistant UI switch (disabled by default), independent of the ttyd terminal (#24).
- Refresh the bundled OpenAI Codex CLI to 0.171.0 and the current stable model catalog.
- Add current Home Assistant 2026.11 App Store vs Marketplace guidance and test/rollout acceptance plans.
- Add reviewed documentation/acceptance matrices for Android, other-App configuration mounts, image upload, terminal edge-scroll, dependency lifecycle, model selection, project workflow and ecosystem comparison (#6, #11-16, #25).

### Release gates
- This is an **experimental deployment-channel candidate**. It requires both architecture builds, multiarch manifest publication and real HAOS/desktop/iOS testing. CI success does not count as runtime acceptance.
- Remote Control real pairing and live Codex/MCP authentication previously failed due to a token-refresh HTTP 401; a manual re-login/acceptance remains required.
- No image upload server, extra other-App configuration mount, or new desktop selection engine was enabled without separate security/hardware review.
- Stable production Codex and its update settings remain unchanged.

## [0.4.36] - 2026-11-20

### Changed
- Update bundled OpenAI Codex CLI to 0.171.0.

## [0.4.35] - 2026-11-18

### Changed
- Update bundled OpenAI Codex CLI to 0.170.0.

## [0.4.34] - 2026-11-13

### Changed
- Update bundled OpenAI Codex CLI to 0.169.0.

## [0.4.33] - 2026-11-12

### Changed
- Update bundled OpenAI Codex CLI to 0.167.2.

## [0.4.32] - 2026-11-11

### Changed
- Update bundled OpenAI Codex CLI to 0.167.1.

## [0.4.31] - 2026-11-06

### Changed
- Update bundled OpenAI Codex CLI to 0.167.0.

## [0.4.30] - 2026-10-30

### Changed
- Update bundled OpenAI Codex CLI to 0.166.0.

## [0.4.29] - 2026-10-30

### Fixed
- Avoid changing SSH private-key and owner-only file permissions when preparing Codex workspace access (Issue #26).
- Prune protected SSH and other key directories, skip common private-key filenames, and avoid following symlinked workspaces into protected paths.
- Stop creating recursive default group ACLs that could otherwise be inherited by newly created SSH keys; preserve the filtered chmod fallback.

### Notes
- Existing unwanted ACLs are not automatically repaired. Refer to `docs/SSH_KEY_PERMISSIONS.md` for targeted manual checks.
- The existing Codex runtime UID and Supervisor/MCP integration remain unchanged; the broader permissions architecture will be reviewed separately.

## [0.4.28] - 2026-10-28

### Changed
- Update bundled OpenAI Codex CLI to 0.165.0.

## [0.4.27] - 2026-10-23

### Changed
- Update bundled OpenAI Codex CLI to 0.164.0.

## [0.4.26] - 2026-10-16

### Changed
- Update bundled OpenAI Codex CLI to 0.163.0.

## [0.4.25] - 2026-10-10

### Changed
- Update bundled OpenAI Codex CLI to 0.162.1.

## [0.4.24] - 2026-10-09

### Changed
- Update bundled OpenAI Codex CLI to 0.162.0.

## [0.4.23] - 2026-10-08

### Changed
- Update bundled OpenAI Codex CLI to 0.161.0.

## [0.4.22] - 2026-10-06

### Changed
- Update bundled OpenAI Codex CLI to 0.160.1.

## [0.4.21] - 2026-10-02

### Changed
- Update bundled OpenAI Codex CLI to 0.160.0.

## [0.4.20] - 2026-10-01

### Changed
- Update bundled OpenAI Codex CLI to 0.159.3.

## [0.4.19] - 2026-09-30

### Changed
- Update bundled OpenAI Codex CLI to 0.159.2.

## [0.4.18] - 2026-09-29

### Changed
- Update bundled OpenAI Codex CLI to 0.159.0.

## [0.4.17] - 2026-09-28

### Changed
- Update bundled OpenAI Codex CLI to 0.158.0.

## [0.4.16] - 2026-09-26

### Changed
- Update bundled OpenAI Codex CLI to 0.157.1.

## [0.4.15] - 2026-09-25

### Changed
- Update bundled OpenAI Codex CLI to 0.157.0.

## [0.4.14] - 2026-09-23

### Changed
- Update bundled OpenAI Codex CLI to 0.156.1.

## [0.4.13] - 2026-09-19

### Changed
- Update bundled OpenAI Codex CLI to 0.155.1.

## [0.4.12] - 2026-09-18

### Changed
- Update bundled OpenAI Codex CLI to 0.155.0.

## [0.4.11] - 2026-09-10

### Changed
- Update bundled OpenAI Codex CLI to 0.154.0.

## [0.4.9] - 2026-09-05

### Changed
- Update bundled OpenAI Codex CLI to 0.153.4.

## [0.4.8] - 2026-09-04

### Added
- Add hardened iOS native terminal selection/paste handling and touch-only mobile terminal controls.
- Add software-keyboard avoidance so the active terminal prompt remains visible above the iPhone/iPad keyboard in Home Assistant ingress.
- Add read-only Home Assistant diagnostic helpers and expanded in-container troubleshooting tooling for Codex sessions.

### Fixed
- Preserve the accepted Desktop wheel, text-selection, clipboard, right-click, and reconnect behavior while keeping mobile-only handling isolated.
- Canonicalize the ttyd 1.7.7 mobile patch with typed Visual Viewport handling and remove the temporary dev.12 Gate 5 build workaround.

### Changed
- Promote the iPhone- and Desktop-accepted `0.4.4-dev.12` deployment state to stable while retaining the newer stable Codex CLI version.

## [0.4.7] - 2026-09-04

### Changed
- Update bundled OpenAI Codex CLI to 0.153.2.

## [0.4.6] - 2026-09-03

### Changed
- Update bundled OpenAI Codex CLI to 0.153.0.

## [0.4.5] - 2026-09-02

### Changed
- Update bundled OpenAI Codex CLI to 0.152.1.

## [0.4.4] - 2026-09-01

### Changed
- Update bundled OpenAI Codex CLI to 0.152.0.

## [0.4.3] - 2026-08-31

### Changed
- Add dedicated project branding for the Home Assistant App with separate 128×128 icon and 250×100 horizontal logo assets.
- Keep editable SVG masters and a reproducible renderer for the presentation assets.
- Adjust horizontal logo typography so `HA CODEX` and `TERMINAL AUTOMATION` remain fully inside the 250×100 canvas.

## [0.4.2] - 2026-08-31

### Changed
- Document Android mobile-terminal status explicitly: the generic toolbar/paging path is expected to work but still needs real-device feedback, while native `Sel` selection/copy/paste remains Apple-only for now.
- Add a dedicated Android runtime feedback tracker and link it from repository and App documentation.
- Document the command-line toolset included in the App image, including Python 3.13, Git/GitHub CLI, OpenSSH client, Home Assistant CLI, editors, search/data utilities, Node/npm, tmux and archive tooling.
- Clarify that the image contains an outbound SSH client but does not expose an inbound SSH server.

## [0.4.1] - 2026-08-31

### Changed
- Align App image packaging with current Home Assistant BuildKit guidance: use the supported multi-arch `base-python:3.13-alpine3.24` base directly from the Dockerfile and remove the legacy `build.yaml` path.
- Update the composable Home Assistant builder actions to `2026.06.0`, publish current `io.hass.type=app` metadata, and keep signed `amd64`/`aarch64` images plus the generic multi-arch manifest.
- Expand CI to reject legacy `build.yaml`, validate all App translation files against the current configuration schema, and build directly from the Dockerfile.
- Document the automatic Codex CLI/model-catalog update pipeline, supported App UI languages, and the distinction between Home Assistant Apps and HACS.

## [0.4.0] - 2026-08-30

### Added
- Add touch-friendly mobile terminal controls based on the upstream ttyd 1.7.7 mobile-controls work: `Esc`, `Tab`, one-shot `Ctrl`/`Alt`, arrow keys, `PgUp`, `PgDn`, and vertical swipe navigation.
- Add tmux page-navigation bindings and keep managed web-session output in xterm scrollback by disabling Codex's alternate screen for the App session.
- Add managed remote Streamable HTTP MCP servers with reversible merge behavior for pre-existing same-name user configuration.
- Add explicit Codex session environment variables and bearer-token environment indirection so bearer values are not written directly into `config.toml`.
- Add German Home Assistant App translations and current English translations for all managed options.
- Add `DOCS.md` for Home Assistant App documentation and a pull-request validation workflow covering Python tests, shell syntax, YAML parsing, ttyd patch applicability, and an amd64 image build.

### Fixed
- Preserve an explicit `enable_mcp: false` option instead of treating `false` as the default `true`; disabling the bundled MCP server now reliably removes the App-managed `homeassistant` entry.

### Changed
- Replace the earlier mixed touch/automatic-selection-copy ttyd patch with a clean ttyd 1.7.7 mobile-controls patch; desktop clipboard and selection behavior are left to ttyd/xterm rather than coupled to mobile gestures.
- Use the current structured Home Assistant App mount schema and explicitly map `homeassistant_config` to `/homeassistant`; remove the unused `addon_config` mount.
- Document this repository as independently maintained rather than claiming cross-repository drop-in compatibility based on the shared `codex` slug.
- Rewrite migration guidance around actual Home Assistant repository/App data identities instead of assuming an in-place repository switch.

## [0.3.15] - 2026-08-29

### Changed
- Update bundled OpenAI Codex CLI to 0.151.0.

## [0.3.14] - 2026-08-27

### Changed
- Update bundled OpenAI Codex CLI to 0.150.1.

## [0.3.13] - 2026-08-24

### Changed
- Update bundled OpenAI Codex CLI to 0.149.1.

## [0.3.12] - 2026-08-21

### Changed
- Update bundled OpenAI Codex CLI to 0.149.0.

## [0.3.11] - 2026-08-19

### Changed
- Update bundled OpenAI Codex CLI to 0.148.0.

## [0.3.10] - 2026-08-13

### Fixed
- Capture iOS touch gestures from their first movement so Home Assistant does
  not take over terminal scrolling.
- Do not trigger selected-text copying after an intentional touch scroll.

## [0.3.9] - 2026-08-13

### Fixed
- Copy selected terminal text directly on mouse or touch release.
- Keep touch scrolling inside the terminal on iOS instead of scrolling the parent view.

## [0.3.8] - 2026-08-13

### Fixed
- Include ttyd's libwebsockets UV event-loop module in the final App image.

## [0.3.7] - 2026-08-13

### Added
- Add a Home Assistant model dropdown populated from the current Codex CLI catalog.
- Refresh the dropdown automatically when the CLI update workflow detects new models.

## [0.3.6] - 2026-08-13

### Fixed
- Include ttyd's libwebsockets runtime dependencies in the final App image.

### Note
- The Codex update workflow refreshes the model dropdown from the CLI's bundled model catalog.

## [0.3.5] - 2026-08-13

### Changed
- Removed obsolete runtime Codex CLI update options from the App configuration.
- Documented Home Assistant Add-on Store updates as the supported update path.

## [0.3.4] - 2026-08-13

### Added
- Automatically copy selected terminal text through the browser Clipboard API.

### Fixed
- Keep the legacy copy fallback for browsers and Home Assistant WebViews that deny direct clipboard access.

## [0.3.3] - 2026-08-13

### Fixed
- Avoid overriding the browser's right-click behavior, improving native Windows text selection and clipboard access.

## [0.3.2] - 2026-08-07

### Changed
- Update bundled OpenAI Codex CLI to 0.147.0.
### Fixed
- Improve iOS terminal scrolling and selection behavior through documented ttyd/xterm client options.
- Use the canvas renderer for more reliable Safari and iOS rendering.

## [0.3.1] - 2026-08-06

### Changed
- Update bundled OpenAI Codex CLI to 0.146.1.

## [0.3.0] - 2026-08-06

### Fixed
- Pin the Codex CLI in the image build instead of updating it at App startup.
- Prefer the executable image-installed CLI over stale user-level npm launchers.
- Keep the existing add-on slug, options, and persistent state paths for a compatible upgrade.
- Retain `auto_update_codex` only for configuration compatibility; runtime npm updates are disabled.

## [0.2.15] - 2026-05-31

### Fixed
- Stopped exposing `/root/.npm` as the runtime npm cache so Codex CLI updates no longer fail with `EACCES` after the terminal drops to the unprivileged `codex` user
- Gave interactive Codex sessions a persistent user-owned npm cache and global prefix under the persistent Codex user home so `npm install -g @openai/codex@latest` works from the terminal and stays on `PATH`
- Isolated optional startup-time root CLI updates to a temporary root-owned npm cache instead of reusing the interactive session cache

## [0.2.14] - 2026-05-24

### Added
- Installed `bubblewrap` so Codex workspace sandbox mode has the Linux sandbox runtime it expects

### Fixed
- Added a default `BUILD_FROM` value to silence Docker's invalid default build-arg warning while preserving Home Assistant's per-architecture build argument override

## [0.2.13] - 2026-05-24

### Fixed
- Repair saved Codex UI state when `tui.model_availability_nux` is stored as a table/map instead of the integer expected by current Codex CLI versions
- Back up semantically repaired config files as `config.toml.repaired.bak`

## [0.2.12] - 2026-05-24

### Fixed
- Quote TOML table keys for project paths such as `/homeassistant` so generated `config.toml` remains valid after Codex records trusted projects
- Repair legacy invalid `[projects./homeassistant]` config sections by backing up the bad file and rewriting them as `[projects."/homeassistant"]`
- Re-run Codex config merge and repair before every Codex launch from the terminal shell, including retries after Codex exits

## [0.2.11] - 2026-05-24

### Added
- Added a `codex_approval_policy` App option with `on-request`, `untrusted`, and `never` choices
- Documented autonomous mode using `codex_permissions: full_access` together with `codex_approval_policy: never`

### Changed
- Generate Codex `approval_policy` from the App option so users can disable per-action approval prompts when they explicitly choose autonomous mode

## [0.2.10] - 2026-05-24

### Added
- Added a GitHub Actions workflow to publish prebuilt `amd64` and `aarch64` Codex App images to GitHub Container Registry
- Added the `image` field so Home Assistant pulls `ghcr.io/kecksdigital/codex-hass:<version>` instead of building locally

### Fixed
- Passed the per-architecture Home Assistant base image into the GHCR build workflow so Docker builds do not rely on local Supervisor build arguments

### Changed
- Documented the difference between Home Assistant App updates and optional Codex CLI startup updates

## [0.2.9] - 2026-05-24

### Changed
- Rewrote the Codex documentation as a standalone Home Assistant App guide with first-run authentication, model, access, MCP, persistence, and update guidance
- Changed new installs to start with `session_persistence` disabled for a cleaner first sign-in flow
- Reduced tmux history, ttyd client count, and ttyd scrollback for safer startup on smaller Home Assistant systems
- Increased healthcheck startup grace and capped Node heap usage to improve reliability during heavier Codex CLI starts

### Added
- Added optional bounded Codex CLI startup updates with `auto_update_codex` and `codex_update_timeout`
- Added startup validation for the generated Codex config when the installed CLI exposes `codex debug prompt-input`
- Added SHA256 verification for downloaded `ttyd` binaries

### Fixed
- Sanitized terminal font size and update timeout values before using them in startup commands
- Prevented optional Codex CLI runtime updates from inheriting the Home Assistant Supervisor token
- Removed unnecessary `net_admin` from the AppArmor profile

## [0.2.8] - 2026-05-24

### Changed
- Set the starter `default_model` add-on option to `gpt-5.4` instead of leaving Codex to choose its current default
- Added a `codex_permissions` add-on option with `workspace` and `full_access` choices
- Generate Codex `sandbox_mode` from the add-on option, mapping `full_access` to `danger-full-access`
- Documented how to change the model and access level from Home Assistant options

## [0.2.7] - 2026-05-24

### Fixed
- Pre-created the unprivileged Codex runtime user at image build time instead of trying to run `adduser` inside Home Assistant AppArmor at terminal connection time
- Kept the terminal open with an unprivileged diagnostic shell if session startup fails, instead of letting ttyd fall back to its restart prompt
- Made direct-ttyd mode explicitly use the shared `anonymous` Codex home instead of partially emulating per-user runtime accounts
- Moved the tmux socket into the managed Codex state directory and made generated Codex config writable by the runtime user
- Serialized startup config generation and atomically replaced `config.toml` to avoid races when multiple terminals connect
- Added base terminfo data for tmux compatibility with `xterm-256color`

## [0.2.6] - 2026-05-24

### Fixed
- Restored direct ttyd ingress serving on port 7681 so the WebSocket console works behind Home Assistant ingress
- Removed the nginx proxy and ttyd auth-header mode that caused `/ws` 502 responses and ttyd restart prompts
- Updated the healthcheck to probe ttyd directly after removing nginx from the runtime path
- Updated documentation to describe the current shared direct-ttyd ingress identity accurately

### Changed
- Start Codex automatically when the Web UI opens so unauthenticated users are taken directly into the Codex sign-in flow
- Retry Codex by default when startup exits before completion, with an explicit diagnostic shell escape

## [0.2.5] - 2026-05-24

### Fixed
- Fixed the per-user tmux launcher so ttyd opens an interactive shell instead of falling back to its restart prompt
- Added visible session startup errors in the browser terminal when the shell wrapper fails before bash starts

## [0.2.4] - 2026-05-24

### Changed
- Reduced nginx health-check log noise so Web UI proxy errors are easier to see

## [0.2.3] - 2026-05-24

### Fixed
- Switched the nginx upstream from a Unix socket to `127.0.0.1:7682` so ttyd no longer depends on socket permission compatibility
- Expanded the ingress allowlist from a single hard-coded Supervisor IP to private network ranges used by Home Assistant installations

## [0.2.2] - 2026-05-24

### Fixed
- Allowed AppArmor execution of `/usr/sbin/nginx` so the hardened ingress proxy can start correctly
- Moved Codex startup validation out of `/tmp` to avoid Codex helper-binary warnings during MCP config checks

## [0.2.1] - 2026-05-24

### Changed
- Rewrote the Codex documentation to explain installation, per-user sessions, MCP wiring, persistence, and everyday usage more clearly
- Replaced upstream repository links and metadata with the `kecksdigital/codex-hass` repository
- Updated the add-on branding, description, and panel icon so the Codex add-on no longer ships with Claude-oriented presentation

## [0.2.0] - 2026-05-23

### Added
- Per-user Codex homes under `/data/codex-home/users/<ha-user-id>/.codex`
- Dedicated Unix users for each Home Assistant ingress user before the shell starts
- Per-user tmux session isolation keyed by the Home Assistant ingress user id
- Reverse-proxied ingress terminal with nginx in front of ttyd and ttyd bound to a local Unix socket
- `hass-mcp-wrapper` and a privileged root helper so the Supervisor token stays out of the interactive shell
- Non-destructive merging of add-on-managed Codex defaults into each user's `~/.codex/config.toml`
- One-time backup of legacy shared Codex state from `/homeassistant/.codex-home` without auto-assigning it to a user

### Changed
- Moved persistent Codex state out of `/homeassistant` and into `/data/codex-home`
- Removed the shared global ttyd/tmux session model in favor of per-user sessions
- Added startup validation for the generated per-user Codex MCP configuration
- Removed inherited `docker_api` and `full_access` privileges from the Codex add-on

## [0.1.0] - 2026-05-23

### Added
- Initial Codex add-on release alongside the existing Claude Code add-on
- OpenAI Codex CLI installed during image build with `codex --version` validation
- Home Assistant ingress terminal powered by ttyd on port 7681
- Persistent Codex home directory at `/homeassistant/.codex-home`
- Generated `~/.codex/AGENTS.md` with Home Assistant path mapping, log guidance, and MCP notes
- Generated `~/.codex/config.toml` with optional default model selection and Home Assistant MCP wiring
- Session persistence via tmux with the `codex` session name
- Initial architecture support for amd64 and aarch64

### Changed
- Removed Playwright MCP and Claude-specific runtime behavior from the new Codex add-on
- Removed inherited Modbus/serial tooling and UART access from the Codex v1 scope
