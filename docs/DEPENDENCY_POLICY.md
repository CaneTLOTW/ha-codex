# Dependency lifecycle and security updates

Tracking: #11. Reviewed 2026-11-22 against `codex/Dockerfile` and the automatic Codex CLI update workflow.

## Release policy

The app is an immutable prebuilt container. **Do not install runtime package updates** inside a running Home Assistant App: they are not reproducible and disappear when the app is recreated. Changes must be built, validated and published as a new multi-arch image.

Codex CLI updates are the **primary image rebuild trigger**. They update the pinned CLI version and release metadata through CI; package refreshes that occur during an image rebuild do not each need a separate App version.

## What is pinned and what is resolved at build time?

| Component | Current policy | Remarks |
| --- | --- | --- |
| OpenAI Codex CLI | Explicit `CODEX_VERSION` in Dockerfile | Updated through the scheduled workflow and verified at build |
| ttyd frontend/server | Explicit ttyd `1.7.7` source tag plus one canonical project patch | Never switch tags without patch, browser and security regression tests |
| Corepack | Exact package version `0.31.0` | Keep consistent with ttyd's Yarn lock |
| Alpine / Home Assistant Python base | Named base-image tag (not digest pinned) | Resolved anew during Docker builds |
| Alpine `apk` dependencies | Unpinned packages | Refreshed within chosen Alpine image's repositories |
| Home Assistant CLI | Latest release downloaded at build time | Record resolved CLI version in release evidence |
| `hass-mcp`, PyYAML, yamllint | PyPI-resolved during build | Record resolved versions in build evidence |

## Validation gates

1. Record the effective image digest, Codex version, HA CLI version and Python dependency versions.
2. Run Python/shell/YAML tests and the full ttyd patch/build test for both architectures before publishing.
3. Smoke-test Home Assistant ingress, MCP authentication and SSH private-key exclusions on an isolated test app.
4. Verify `amd64` and `aarch64` manifests before tagging stable. Never overwrite a published version tag with different bytes.
5. Keep installation and HA auto-update changes under explicit operator control.

## Security exception

If a critical vulnerability affects the base image, HA CLI or other bundled package between Codex releases, prepare a **separate patch release** even when `CODEX_VERSION` is unchanged. Document advisory, resolved dependency, compatibility tests and image digest. This exception should not trigger routine noisy releases.

## Reproducibility follow-up

For stronger reproducibility, record or pin the resolved Home Assistant CLI, Python packages and the base-image digest **as a coordinated build input set**; keep intentional periodic refreshes. This documentation does not silently switch current dependency resolution or enable a new updater.
