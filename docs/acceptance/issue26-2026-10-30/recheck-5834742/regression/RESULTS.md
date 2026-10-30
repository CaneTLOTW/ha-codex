# Issue 26 regression/security recheck — 5834742

**Regression/security sub-gate: PASS.**

Source: `issue26-local-test` at `5834742e21c21a23bb7ec8a9630f7f1e912cebf1`.

## Results

- `python3 -m unittest discover -s codex/tests -v`: PASS, 22 tests, 0 failures, 0 skips. Full output is in `unittest-discovery.txt`.
- Updated SSH ACL tests make meaningful filesystem assertions on disposable fixtures: repeated ACL snapshots, protected `.ssh`/nested/key and owner-private paths, key-like files outside `.ssh`, symlink/direct targets, ordinary files, executable mode, default ACL absence, and real chmod fallback. They do not use fake-success test doubles.
- Real `setfacl`/`getfacl` isolated probe: PASS twice. `.ssh` remained 0700, private fixture keys/files remained 0600, ordinary YAML remained writable, executable status remained intact, protected paths/key-like files were skipped, and no default ACLs were created. Probe output: `real_acl_probe.log`.
- Machine-readable before/after ACL/mode/owner snapshots: PASS twice. A deliberately preexisting ACL on the disposable protected key remained unchanged; protected paths retained exact metadata, while ordinary YAML and the executable received the expected ACL entries. Evidence: `acl_metadata_before_after.json` and `acl_metadata_probe.log`.
- Missing-`setfacl` fallback: PASS twice. The shell-scoped `command -v setfacl` override selected real chmod; no mock executable was created. Normal file became 0664, executable 0775, `.ssh` stayed 0700, and private fixtures stayed 0600. Machine-readable before/after snapshots: `chmod_missing_setfacl_before_after.json`.
- Startup-equivalent `setfacl`-present-but-failing branch: PASS twice. The probe verified `__issue26_nonexistent_group__` is absent and exported the scoped `find()` function into a child Bash that ran the unchanged helper as a script with `-x`. The wrapper uses ordinary `command find` so it bypasses the exported function and invokes real GNU find, while capturing only that command's status. Each run produced three genuine `setfacl` failures (`Invalid argument`), ACL-pass GNU find status 1, chmod-pass GNU find status 0, and helper status 0 after the real chmod fallback. Normal YAML became 0664 and writable; executable became 0775 and remained executable; `.ssh` stayed 0700, key/private files stayed 0600, protected metadata including a preexisting `g:root:---` key ACL stayed unchanged, and no default ACLs appeared. Per-run xtrace/stderr and machine-readable snapshots: `real_setfacl_failure_before_after.json`; probe summary: `real_setfacl_failure_probe.log`.

## Required limit

An earlier probe sourced the helper inside `if source ...`, suppressing `errexit` across the sourced helper; that evidence is superseded. The first child-script probe then exposed a second harness issue: `builtin command find` exited under `set -e` before its local status guard could capture the failure. A minimal no-filesystem shell repro confirmed guarded `builtin command false` exits with status 1, while guarded ordinary `command false` captures status 1 and continues. The wrapper was changed to ordinary `command find` (which bypasses shell functions), preserving the helper's normal child-script `set -e` behavior. The failure branch then passed twice with xtrace and asserted ACL pass 1, chmod pass 0, and helper status 0. No product or test code was changed.

All probes used temporary fixture data under `/tmp`; no real SSH key contents, production paths, or HA permissions were read or changed. Distinct-UID behavior is unverified; probes ran as UID 22000. No source or test files were changed.

## Acceptance implication

All requested regression/security checks pass, including both repeated fallback branches under the unchanged helper's startup-equivalent child execution. This is the regression/security sub-gate result only; the coordinator combines it with the independent source, metadata, and other acceptance gates to decide **READY FOR TEST INSTALLATION** or **BLOCKED**.
