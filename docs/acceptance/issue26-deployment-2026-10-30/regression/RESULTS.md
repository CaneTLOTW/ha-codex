# Issue 26 deployment branch regression acceptance

Candidate: `work/issue26-deployment-hotfix`, based on deployment `c79313b0c93c99ee448471a4659c5c10658a04a1` (`0.4.10-dev.2`). Production `e6fb3748_codex/main` was not accessed or modified.

## Results

- Python regression suite: PASS, 17 tests, 0 failures/skips.
- Shell syntax: PASS for version updater, startup/session/shell scripts, and new grant helper.
- YAML parsing: PASS for repository metadata, App config, and all 5 translation files.
- Repository hygiene: PASS, `git diff --check`; legacy `codex/build.yaml` absent.
- Real filesystem ACL and fallback probes: PASS, each exercised twice against disposable `/tmp` fixtures and the candidate helper. `.ssh` remained `0700`, key/private fixtures `0600`, normal files became writable, executables retained execute permission, and no default ACLs were installed. Genuine `setfacl` failure invoked filtered chmod successfully while protected metadata remained unchanged.

Complete stdout/stderr for the repeated probes: `probe-output.txt`. Adapted source probes are retained alongside it. Machine-readable snapshots are in `chmod_missing_setfacl_before_after.json` and `real_setfacl_failure_before_after.json`.

## Limits

Probes ran as UID 22000; distinct-UID behavior is unverified. All fixture data was disposable. No production paths, SSH contents, live permissions, restarts, repairs, tokens, or remote access were used. CI architecture builds, publishing, and runtime acceptance were not part of this local gate.
