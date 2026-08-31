# Repository Instructions

This file contains instructions for agents working on this repository.

## Terminology and scope

- This repository publishes a **Home Assistant App** (formerly called an add-on), not a HACS integration.
- Use current Home Assistant **App** terminology in new documentation and code comments unless referring to a historical name, API field, or compatibility detail.
- HACS does not manage Home Assistant Apps/add-ons and is not a packaging or release target for this repository.
- The repository currently publishes one App: `codex/`.

## Before every release change

Update `codex/CHANGELOG.md` and bump `codex/config.yaml` when a change alters the published App image or App metadata. Documentation-only root changes that do not alter the App package do not require a release bump.

Follow the existing changelog format:

```markdown
## [VERSION] - YYYY-MM-DD

### Added/Changed/Fixed
- Description of change
```

## Project structure

- `repository.yaml` - Home Assistant App repository metadata
- `README.md` - Repository landing page, installation, update architecture, and support information
- `MIGRATION.md` - Migration notes for installations coming from other repositories
- `scripts/update-codex-version.sh` - Automatic Codex CLI/model-catalog update logic
- `.github/workflows/propose-codex-cli-update.yml` - Scheduled Codex CLI update workflow
- `.github/workflows/publish-codex.yml` - Multi-architecture BuildKit image publishing
- `.github/workflows/validate-codex.yml` - Regression, packaging, translation, patch, and image-build validation
- `codex/` - Codex Home Assistant App
  - `config.yaml` - App configuration and release version
  - `Dockerfile` - Single source of truth for the App image build
  - `README.md` - Detailed user/repository documentation
  - `DOCS.md` - Documentation shown in the Home Assistant App UI
  - `CHANGELOG.md` - Version history
  - `translations/` - Home Assistant App option translations
  - `apparmor.txt` - Security profile
  - `ttyd-mobile-keys/` - Maintained ttyd mobile frontend patch and notes

## Home Assistant build rules

- Follow current Home Assistant App guidance from `developers.home-assistant.io/docs/apps`.
- Do **not** reintroduce `codex/build.yaml`. Home Assistant's current BuildKit guidance makes the Dockerfile the build source of truth; legacy `build.yaml` support is transitional and scheduled for removal.
- Use the generic multi-architecture Home Assistant base image where possible.
- Use the composable `home-assistant/builder/actions/*` BuildKit actions, not the retired legacy `home-assistant/builder` action.
- Published images use the generic multi-architecture reference `ghcr.io/canetlotw/ha-codex:<version>`.
- Keep `io.hass.type=app` metadata current.
- Supported architectures are `amd64` and `aarch64`.

## Automatic Codex CLI updates

The scheduled update workflow is a core repository feature and must remain operational.

When a new `@openai/codex` release or visible model-catalog change is detected, `scripts/update-codex-version.sh` updates the pinned CLI version/model dropdown, increments the App patch version, updates the changelog, and the workflow commits the result to `main` before dispatching the image-publish workflow.

Do not replace this with runtime `npm install` behavior. Codex CLI updates are delivered as reproducible Home Assistant App image releases.

## Translation rules

- Every key in `codex/config.yaml` `schema:` must have a matching top-level entry under `configuration:` in every shipped translation file.
- Current shipped App UI languages are `en`, `de`, `es`, and `pt-BR`.
- The validation workflow enforces schema/translation key coverage.

## Version bumping

When making changes that require a new App release:

1. update `version` in `codex/config.yaml`;
2. add the release entry to `codex/CHANGELOG.md`;
3. run/verify the validation workflow;
4. merge only after the build and validation result is acceptable.

Automatic Codex CLI updates perform their own patch-version bump and changelog entry.

## Home Assistant runtime notes

- The App deliberately clears the base-image `ENTRYPOINT` and starts `/usr/local/bin/codex-start` directly.
- `init: true` therefore uses Home Assistant/Docker init rather than the base image's s6 entrypoint; do not change this merely because the Home Assistant base image contains s6-overlay.
- Keep folder mounts read-only unless write access is required. Current intended writes are `/homeassistant`, `/share`, and `/media`; `/ssl` and `/backup` remain read-only.
- Preserve the AppArmor profile and the unprivileged interactive `codex` user model.
