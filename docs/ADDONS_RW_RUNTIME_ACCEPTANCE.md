# `/addons` read/write runtime acceptance

Target deployment version: `0.4.10-dev.1`

## Purpose

Verify that the Codex Deployment App can intentionally read and write local Home Assistant App source trees through the Supervisor `addons` mapping while retaining the current stable runtime baseline.

## Security scope

The mapping exposes the complete local App source tree at `/addons` with write access. A Codex session can therefore create, modify, rename, or delete source files for any local App. This is broader than access to one project and should be treated as privileged development/administration access.

`addons` is intentionally used here rather than `all_addon_configs`: the latter exposes installed Apps' public configuration directories under `/addon_configs`, not local App source trees.

## CI gates before runtime testing

- [ ] canonical ttyd patch applies cleanly
- [ ] Python/static/regression validation passes
- [ ] `amd64` image build passes
- [ ] `aarch64` image build passes
- [ ] deployment multi-architecture manifest publishes successfully

## Home Assistant runtime test

After Home Assistant offers `Codex Deployment 0.4.10-dev.1`, update the deployment App. Because `map:` and AppArmor are container metadata/security changes, test against the newly recreated container rather than relying on a restart of an older image.

Inside the Codex terminal:

```bash
ls -la /addons
```

Confirm that the expected local App source directories are visible.

Create and remove a harmless probe file in a chosen local test App directory, for example:

```bash
probe=/addons/<local-app>/.ha-codex-rw-probe
printf 'ha-codex addons rw probe\n' > "$probe"
cat "$probe"
rm "$probe"
```

Expected result:

- file creation succeeds;
- file content can be read back;
- file deletion succeeds;
- the probe does not remain after the test.

Then perform the intended source copy/update workflow and reload the Home Assistant App Store/repository as required by Home Assistant.

## Regression smoke

- [ ] Codex starts normally in `/homeassistant`
- [ ] Home Assistant MCP still works when enabled
- [ ] `/homeassistant`, `/share`, and `/media` retain write access
- [ ] `/ssl` and `/backup` remain read-only
- [ ] Desktop terminal behavior unchanged
- [ ] iOS toolbar/selection/keyboard behavior unchanged

## Promotion

Do not promote to `main` until the deployment image/manifest gates and Home Assistant runtime read/write probe have passed and promotion has been explicitly approved.
