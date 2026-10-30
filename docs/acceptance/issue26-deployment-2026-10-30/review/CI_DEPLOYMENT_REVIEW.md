# Issue #26 deployment CI/deployment review

Date: 2026-10-30 (UTC)

## Scope and reviewed state

Read-only review of `/share/ha-codex-issue26-deployment`, based on deployment commit `c79313b0c93c99ee448471a4659c5c10658a04a1`. Candidate working tree contains the Issue #26 four-file hotfix: `codex/config.yaml`, `codex/rootfs/usr/local/bin/codex-start`, new `codex/rootfs/usr/local/bin/codex-grant-access`, and new `codex/tests/test_ssh_acl_protection.py`. The checkout already had those candidate changes; they were not modified by this review. No workflow was triggered, no source code or refs were changed, and nothing was pushed or released.

The candidate version is `0.4.10-dev.2`; the reviewed deployment base is `0.4.10-dev.1`. The canonical file `codex/ttyd-mobile-keys/ttyd-1.7.7-mobile-keys.patch` is unchanged versus `origin/deployment` (same blob SHA `92a31350b1b7da9d7cd9e443f0fcc6cc3071aab2`).

## Workflow behavior on deployment base

- `.github/workflows/validate-codex.yml`: push to `feat/**`, `chore/**`, or `deployment` (with configured relevant paths) starts `validate`; after it succeeds, `build-amd64` runs. Thus the proposed feature-branch canary is one validation job and one amd64 image build.
- `.github/workflows/publish-deployment.yml`: push to `deployment` (matching `codex/**` or the workflow file), or manual dispatch, starts deployment publication. The pipeline initializes a matrix, builds and pushes `amd64` and `aarch64` images, then publishes the multi-architecture manifest. It writes version tag `0.4.10-dev.2` and moving tag `deployment` to `ghcr.io/canetlotw/ha-codex`.
- `.github/workflows/publish-codex.yml`: automatic push trigger is only `main`, with matching paths; it publishes the stable version and `latest`. The reviewed candidate does not itself trigger this workflow while it remains on a feature branch/deployment channel.

There is therefore no stable `latest` tag mutation from the proposed feature-branch canary or the deployment workflow. Publishing deployment does replace the shared moving `deployment` tag by design. The immutable version tag is intended to be unique, but its current registry existence could not be established (see blockers below).

## Existing CI and deployment evidence

### PR #27, latest actual run

PR #27 (`fix(security): preserve SSH key permissions during Codex startup`) is open; head `d01d178ea5e1bbd2e6c7606a2efe03c8dca12c34`; base `main` at `c2661e04ee6b74b25e8759d74d8217523458bbed`.

Run [41018522757](https://github.com/CaneTLOTW/ha-codex/actions/runs/41018522757), event `pull_request`, completed successfully on 2026-10-30 07:13:15 UTC:

- `validate`: success, 07:11:12–07:11:19 UTC. Python regression tests, shell syntax, YAML/translation checks, canonical ttyd patch application, and whitespace check all passed.
- `build-amd64`: success, 07:11:22–07:13:14 UTC. The image build step passed.
- Failed job/step/log: none. No failure-log diagnosis is applicable.

This PR run is validation/build evidence for the PR head; it is not a deployment-branch publication and does not prove the candidate deployment commit’s two-architecture publication or runtime acceptance.

### Deployment base runs

At `c79313b`, the existing [validation run 34316490159](https://github.com/CaneTLOTW/ha-codex/actions/runs/34316490159) succeeded on 2026-09-09. `validate` ran approximately 14 seconds and `build-amd64` approximately 82 seconds.

The existing [deployment publish run 34316490156](https://github.com/CaneTLOTW/ha-codex/actions/runs/34316490156) succeeded on 2026-09-09. Initialize took about 4 seconds; amd64 and aarch64 build jobs took about 104 and 104 seconds respectively; manifest publication took about 14 seconds. Wall time was about 142 seconds because architecture builds ran concurrently. Both image pushes and manifest publication passed on that base revision.

These observed durations are historical runner durations, not a GitHub billing estimate. The candidate has not yet been run through either workflow.

## Canary and readiness assessment

The minimal proposed path is suitable as a gated canary:

1. Push candidate to a `feat/**` branch with changes under `codex/**`.
2. Confirm `validate` and the single `build-amd64` both pass; stop on any unexpected failure.
3. Only after that review, move the accepted candidate to the authorized deployment path, which expands publication to amd64 + aarch64 + manifest.
4. Verify the published version and deployment manifest, then perform runtime acceptance.

Static and single-architecture build readiness is supported by PR #27’s green run, but it is not conclusive for the exact candidate branch/tree. Full deployment build/publish readiness remains unproven until the canary and deployment workflow complete. Runtime acceptance remains outstanding. No production or `main` readiness is claimed.

## Billing and registry blockers

- GitHub Actions billing/quota: `gh api users/CaneTLOTW/settings/billing/actions` returned 404, and GitHub reported that the authenticated client needs the `user` scope. No quota/billing figures were available; no credential refresh or permission change was attempted.
- Registry tag existence: GHCR manifest HEAD requests for `0.4.10-dev.2` and `deployment` returned 401 requiring registry authentication. GitHub’s package versions endpoint returned 403 requiring `read:packages`. Consequently, whether `0.4.10-dev.2` already exists and whether it would collide cannot be verified from the current credentials. Confirm tag uniqueness and publication access before the deployment publish step.

## Conclusion

**Conditional canary readiness; not deployment-publish or runtime accepted.** Workflow routing provides the requested one-amd64 feature-branch canary before the deployment push fans out to two architectures. The known candidate version is newer than the reviewed deployment base and the canonical ttyd patch is unchanged. Proceeding to an actual deployment publish should be gated on the canary passing and a credentialed check that `0.4.10-dev.2` is unused. GitHub Actions quota/cost remains unverified because the available authenticated scope does not expose billing data.

## Coordinator follow-through

After this read-only review, the coordinator verified dev.2 tag absence via the public registry protocol, completed the one-amd64 canary, published both architectures and the manifest, and updated/tested the existing deployment instance through regular HA services. See ../REPORT.md for the final gates; the credential/budget limitations above describe the earlier review point.
