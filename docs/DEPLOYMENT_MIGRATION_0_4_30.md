# Deployment channel migration candidate: 0.4.30-dev.1

This is a local preparation for the deployment channel, not a published image or
runtime acceptance. Normal merge parents: deployment `eb30efe651468ee86201acd68752bfbaa46afa61`
and stable `d46f306306e5281974399939da9455b0635e3f78`. Existing history and
`docs/acceptance/issue26-deployment-2026-10-30/` remain in the merge tree.

The runtime is based on stable 0.4.30 with a focused local path-filter and
working-directory correction described below. Dockerfile, AppArmor, SSH ACL
helper and canonical ttyd patch follow stable. The channel manifest retains `Codex Deployment`,
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

Independent review found that the stable `codex-addons-sandbox` root filter and
startup working-directory guard used lexical path checks. The local candidate
now resolves existing directories once before comparison and use, rejects
relative/missing/cyclic roots, checks ancestors in both access modes and falls
back safely when the working directory is invalid. Synthetic CLI and helper regressions cover the
corrected filtering. Existing configurations that use relative, non-directory or
not-yet-created writable roots need adjustment; see `ADDONS_ACCESS.md`.

No write against real `/addons` or other production targets was attempted.
The model-free `codex sandbox` canary in synthetic directories could not start:
`bwrap` reported no permission to create a user namespace. Therefore neither
actual sandbox enforcement nor a successful escape was established. A suitable
isolated runtime must test the corrected policy end-to-end, including mutable
aliases/bind-mount equivalents and replacement between path validation and use,
before security acceptance or publication.

## Local checks and remaining gates

Local validation: 27 Python tests pass, shell syntax and Python compilation pass,
HA YAML/translation checks pass, whitespace checks pass, and the canonical ttyd
patch applies to clean upstream 1.7.7. The 0.4.30 stable publish passed amd64,
aarch64 and manifest jobs, but it predates the candidate's security changes.
The base-image registry manifest lists both architectures. This environment has
no Docker/Podman/BuildKit socket or usable nested user namespace, so actual
candidate amd64/aarch64 builds and real sandbox enforcement are **NOT RUN**.
No image was published, installed or started. A static check or historical build
does not replace candidate builds or real HA/iOS/desktop runtime acceptance.

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
