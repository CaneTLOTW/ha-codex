# Deployment channel migration candidate: 0.4.30-dev.1

This is a local preparation for the deployment channel, not a published image or
runtime acceptance. Normal merge parents: deployment `eb30efe651468ee86201acd68752bfbaa46afa61`
and stable `d46f306306e5281974399939da9455b0635e3f78`. Existing history and
`docs/acceptance/issue26-deployment-2026-10-30/` remain in the merge tree.

Runtime logic, Dockerfile, AppArmor, the SSH ACL helper and the canonical ttyd
patch follow stable 0.4.30. The channel manifest retains `Codex Deployment`,
`slug: codex`, experimental stage, manual boot and deployment panel title;
`repository.yaml` retains the deployment repository name. `publish-deployment`
continues to publish `-dev.N` and `deployment` tags, never `latest`.

## Access-policy change requiring runtime review

The older deployment mapped `/addons` writable and described it as writable.
The stable version also maps it at host level but introduces `addons_access` and
defaults to `read_only` within Codex. This candidate keeps that **safer stable
default**. A user who needs the previous local-App development workflow must
explicitly select `addons_access: read_write`; this is an operational behavior
change and must be checked before the deployment channel is updated. Such an
opt-in allows modifying all local App sources and may cause startup ACL grants;
it must not be silently inferred from the old mapping. `all_addon_configs` is
not added.

Independent review found that the stable `codex-addons-sandbox` root filter
uses lexical `PurePosixPath` checks. A synthetic read-only configuration with
`/homeassistant/../addons` and a temporary symlink to `/addons` was passed
through by the filter. No write against `/addons` or target Codex sandbox was
attempted, so actual sandbox bypass is **not established**. Verify canonical
path and symlink handling in an isolated test against the target Codex CLI and
resolve any confirmed security gap before accepting or publishing the migration.
The candidate retains the stable helper unchanged.

## Local checks and remaining gates

Run the full Python regression suite, shell syntax, YAML/translation checks and
the canonical ttyd patch application check on the isolated branch. Record their
results independently. No Python regression, local patch application or static
check substitutes for an amd64/aarch64 image build, published multi-architecture
manifest or real HA/iOS/desktop runtime acceptance.

Before moving `deployment`, review the source diff and both remote parent SHAs,
the `/addons` default, version and release workflow; then obtain the separately
required operator approval for deployment-channel update/publication. Build and
publish only using the approved channel/runbook, never move or publish `main`.
Confirm both architectures and manifest before installing the test App; verify
separate Supervisor IDs, session/MCP, toolchain, SSH ACL behavior and both
`addons_access` modes without modifying real SSH keys. Keep stable unchanged.

Rollback should use the last known deployment image and pre-update App backup;
do not rewrite branch history. Existing acceptance reports are historical,
including the independently documented `codex_apps` HTTP 401 finding.
