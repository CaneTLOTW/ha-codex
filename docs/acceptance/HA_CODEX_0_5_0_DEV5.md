# Home Assistant Codex Developer 0.5.0-dev.5 — transfer and App config acceptance

**This is an experimental Developer image, NOT a Stable release.** Stable `main` remains at `0.5.0` and must not be updated from this branch.

## Scope and known limitations

1. ttyd 1.7.7 has a built-in `enableTrzsz` browser transfer handler. A pinned server-side Python `trzsz==1.1.7` provides `trz` and `tsz`. The new option `file_transfer_enabled` defaults **false**, and enabling it requires saving options and restarting **Codex Deployment**.
2. In the normal ttyd terminal, first exit the Codex TUI with Ctrl+C and type **`codex-upload`**. The browser should open a picker. For directories use `codex-upload --directory`; files of any type may be selected. Transfers land in `/data/codex-home/users/anonymous/.codex/uploads`, an owned private directory mode 0700. The operator must verify uploaded files are mode 0600 and that no symlink escape occurs.
3. **Screenshot Ctrl+V inside the Codex TUI is not implemented** by this prototype. A first test proves file transport, not image attachment to an active prompt. The operator can tell Codex to open an uploaded file by absolute path, but its image-analysis ability must be validated in a real session. A direct clipboard handler / GUI upload button will require a later separate PR, potentially using the same protocol.
4. Browsers may restrict file picking, dragging and clipboard access when Home Assistant is accessed through **non-HTTPS LAN URLs**. Test in Firefox on the normal HA ingress URL first, and separately using a properly configured HTTPS origin if the picker fails. No unauthenticated host ports are added.
5. The Developer image has a **static read-only Supervisor mount** of public App configuration directories at `/app_configs`. This is NOT Unraid Docker appdata, nor the private data of other HA Apps. `app_configs_visibility` is **only an agent-guidance preference**: `hidden_from_guidance` (default) hides its description, `show_read_only` documents the path. **The mount remains accessible to shell/app processes in either setting**; it is not a security or consent barrier. Truly revoking the mount requires switching to an App image without the static mount. Never promise otherwise.
6. Secrets in public App config files can still be read; use dummy files/test fixtures and do not paste private App configs into GitHub or logs. No `/app_configs` permission grant, AppArmor write permission, or new RW mounts are permitted in this test. No Stable rollout without explicit separate operator approval.

## Tests — record PASS, FAIL, NOT RUN, BLOCKED

| Check | Procedure | Required evidence |
| --- | --- | --- |
| App isolation | Confirm live Supervisor ID, repository `#deployment`, installed image `0.5.0-dev.5`, backup; Stable remains `0.5.0` | Before/after versions/options |
| Disabled default | With `file_transfer_enabled=false`, run `codex-upload` in shell | Clear disabled warning; no transfer |
| Browser file picker | Enable transfer; restart only Developer; Ctrl+C → `codex-upload` | Picker appears, choose disposable PNG, confirm exact private path, file bytes and mode |
| Arbitrary files | Repeat with a text file, ZIP, and filename containing spaces | Binary-identical SHA256, no path escape |
| Folder transfer | `codex-upload --directory` with a harmless test folder | Expected nested file paths, no traversal, safe permissions |
| Browser details | Firefox regular LAN HTTP ingress; separately HTTPS origin if available; Chrome optional | Record browser, origin security (HTTP/HTTPS), errors; no raw ingress token |
| Session use | `codex` → ask agent to inspect the uploaded file path | Correctly reads text file; verify separately whether PNG can be visualized |
| Clipboard limitation | Paste an image with Ctrl+V | Record current behavior; do not mark as supported |
| Config-mount RO | In Developer, `ls /app_configs` and read only a harmless fixture | Paths visible even when UI guidance hidden; writes refused by mount |
| Visibility toggle | Change `app_configs_visibility` to show_read_only and restart | AGENTS.md guidance changes, permissions do NOT |
| Core regressions | Ctrl+C→codex→resume; SQLite state; MCP read-only call; WebSocket reconnect, iOS Sel/copy | No regressions |
| External volunteer | Ask original desktop scroll reporter whether they can test #25; solicit voluntary Android tester for #6 | Consent/reply first; no false Android acceptance |

## Rollback

Do not change Stable. On Developer failure, disable `file_transfer_enabled`, revert to the previously accepted `0.5.0-dev.4` image if needed, and preserve Developer state. If RO App config mount is considered too broad, **turning off app_configs_visibility is not sufficient**: stop using this Dev image and use a build without the mount. Never delete session history or widen AppArmor to fix a UI transfer failure.

References: Issue #13 (uploads), #12 (other App configuration), #25 (edge-scroll), #6 (Android), and Stable production #41 (already accepted).
