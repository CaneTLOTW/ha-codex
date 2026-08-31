# Release channels

HA Codex uses two Home Assistant App update channels.

## Stable (`main`)

Repository URL:

`https://github.com/CaneTLOTW/ha-codex#main`

- App name: `Codex`
- Stage: stable (default)
- Stable versions use normal release versions such as `0.4.3` or `0.4.4`.
- `.github/workflows/publish-codex.yml` publishes the version tag and `latest`.
- `main` must only receive changes that have passed deployment-channel runtime acceptance.

## Deployment (`deployment`)

Repository URL:

`https://github.com/CaneTLOTW/ha-codex#deployment`

- Repository name: `CaneTLOTW HA Codex (Deployment)`
- App name: `Codex Deployment`
- Stage: `experimental`
- Boot mode: `manual` so stable and deployment installations do not unexpectedly start together.
- Deployment versions use `X.Y.Z-dev.N`, for example `0.4.4-dev.1`.
- `.github/workflows/publish-deployment.yml` publishes the version tag and the moving `deployment` tag.
- It never publishes `latest`.

Home Assistant treats the branch-qualified repository URLs as separate repository channels. The app slug can therefore remain `codex`; app identity is scoped to the repository.

## Development flow

1. Feature/fix work starts on a dedicated branch.
2. CI must pass on the feature/fix branch.
3. Accepted feature/fix work is integrated into `deployment`, not directly into `main`.
4. Increment the deployment version (`-dev.N`) for every Home Assistant-testable deployment build.
5. GitHub Actions publishes the multi-architecture deployment image to GHCR.
6. Home Assistant detects the new deployment version through its normal App update mechanism.
7. Runtime acceptance is performed against the `Codex Deployment` installation.
8. After acceptance, promote the deployment state to `main`, change the version to the stable release number, and publish via the stable workflow.

## Promotion rules

- Never publish a deployment build with the `latest` tag.
- Never use a stable version number for code that has not passed deployment runtime acceptance.
- Do not merge old or divergent feature branches into `deployment` merely because they exist; integrate only explicitly selected current work.
- Stable and deployment may be installed side by side. Keep deployment on manual boot and normally run only the instance being tested.
