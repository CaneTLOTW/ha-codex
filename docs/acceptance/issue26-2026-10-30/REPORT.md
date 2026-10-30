# Issue 26 / PR 27 — Home Assistant local acceptance, 2026-10-30

Result: **PARTIAL; source suite FAIL; Supervisor installation BLOCKED; test-add-on runtime NOT TESTED.** No production add-on changes, permission repairs, merge, release, or new CI/build jobs.

## Source and installation inventory

- Tested branch `issue26-local-test`, source HEAD `ee5e4133d2ee2eae7d07353942dd423697fd0d37`.
- PR #27 HEAD `27869782850d8537f13129ade48448b4a703fcd9`, draft/open/unmerged. Runtime code/tests/Dockerfile are identical between these commits; differences are the isolated manifest and acceptance runbook.
- Current remote deployment HEAD `c79313b0c93c99ee448471a4659c5c10658a04a1`, version `0.4.10-dev.1`; no reset or update performed.
- Current remote main HEAD `c2661e04ee6b74b25e8759d74d8217523458bbed`; untouched.
- Production `e6fb3748_codex`, installed/latest `0.4.28`, update auto_update=false. Confirmed through live HA update attributes and targeted device registry. This session's container hostname `e6fb3748-codex` confirms active production runtime.
- Second installation `1e25a555_codex`, Codex Deployment, installed/latest `0.4.10-dev.1`, auto_update=false. Current running/stopped state cannot be established through available interfaces: corresponding state/switch entities are integration-disabled. An update entity state `off` means no update, not stopped.
- No test entry surfaced in targeted HA Codex entities/registry; this is not a complete Supervisor store inventory. Final full test slug and repository collision check are **unverified**, not guessed.
- HA Core `2026.10.4`, amd64.

Manifest checked: name `Codex SSH Hotfix Test`, slug `codex_issue26`, version `0.4.28-test.26.1`, boot `manual`, stage `experimental`, no `image` key. Dockerfile includes `COPY rootfs/ /`; startup invokes grant helper through bash. Distinct own `/data` is intended but cannot be runtime-verified before installation.

## Acceptance matrix

| Check | Result | Evidence / limit |
| --- | --- | --- |
| Bash syntax: codex-start, codex-grant-access | PASS | `bash -n` on both scripts |
| Entire unchanged Python regression suite | FAIL | 22 run: 19 pass, 2 failures, 1 error; full baseline log attached |
| Mock ACL pruning test | FAIL | Empty mocked action log |
| Mock chmod fallback test | FAIL | Empty mocked action log |
| Mock repeated-start test | FAIL | Missing actions.log (FileNotFoundError) |
| Real setfacl/getfacl, helper twice | PASS, isolated | Protected modes/ACLs unchanged; ordinary files receive ACLs; no default ACLs added |
| Real chmod missing-setfacl fallback twice | PASS, isolated | Genuine chmod; normal 0644→0664, executable 0755→0775, SSH 0700/key0600 unchanged |
| Owner-private / outside key / symlink / nested SSH targets | PASS, isolated | Supplemental real ACL probe and baseline tests; no production target passed to helper |
| Existing SSH permissions/ACL inventory | PASS, read-only | baseline_metadata.json; final comparison identical for all 12 paths |
| Current production MCP | PASS | HA get_version and entity reads; NOT test-instance MCP |
| Current Core SSH bad-permissions log search | No matches | Available filtered log window only; not an SSH authentication test |
| Supervisor-managed test build/install | BLOCKED / NOT TESTED | No authenticated add-on management client; source gate also red |
| Test add-on start / stop / second start | NOT TESTED | Not installed by this run |
| Test add-on actual SSH / ordinary workspace / MCP | NOT TESTED | Isolated helper probes cannot establish add-on runtime acceptance |
| Test stop/cleanup | NOT APPLICABLE | Nothing installed/started; no existing installation removed |

### Test commands and diagnosis

```sh
bash -n codex/rootfs/usr/local/bin/codex-start
bash -n codex/rootfs/usr/local/bin/codex-grant-access
python3 -m unittest discover -s codex/tests -v
python3 /share/ha-codex-issue26-evidence/real_acl_probe.py
python3 /share/ha-codex-issue26-evidence/real_chmod_fallback_probe.py
```

Three baseline errors share an observed environment restriction: newly created executable mock scripts under /tmp (also reproduced under /share) cannot be directly executed (PermissionError/Errno13), despite mode0755 and correct PATH resolution. Do not claim a particular mount option: a noexec-like restriction was observed; its exact enforcement origin is unverified. Helper calls returned zero with empty output and no actions.log, so mocked-command tests cannot provide acceptance here. The baseline real-chmod test passing does not prove its mock failure path actually executed.

The supplemental fallback probe avoids mock executables: a scoped bash function makes only `command -v setfacl` return unavailable, then sources the unchanged helper and invokes real chmod. This verifies the missing-tool fallback branch, **not a real setfacl failure in a built container**. No product/test source was modified to turn the suite green. No privileged or distinct-UID process was used; ordinary access checks ran as current UID22000 (the owner), not as a separate target add-on user.

Full scripts and logs are attached here. Probe paths point to the exact tested checkout and disposable fixtures. Python execution through the interpreter is intentional. Baseline suite remains FAIL; do not waive the runbook's fail-closed source gate on the strength of supplemental probes.

## Existing permissions and unchanged data

`/homeassistant/.ssh` is absent. Known current SSH state is under `/data/codex-home/users/anonymous/.ssh`: directory0700, config and two private keys0600, no named/default ACLs on these private paths. No private/public key contents were read, copied or printed.

The HA mount and `/homeassistant/remote/optolink-splitter` already have named/default `group:root:rwx` ACLs; configuration.yaml and known_hosts already have named root access ACLs. These are **pre-existing findings**, not automatically repaired. Detailed owner/mode/ACL metadata only is attached. Final comparison with baseline passed for all captured paths. A prior damaged ancestor ACL may still affect future files even with this hotfix.

Production remains active, existing versions unchanged, and current production MCP remains available. Exact full production container/image/options fingerprints and Deployment running state were not accessible; do not claim full fingerprint verification. No production add-on update/restart/service call, no source installation into /addons, and no HA configuration changes were made.

## Supervisor blocker and precise UI continuation

Available HA MCP tools expose state/services/dashboards and HA restart, not add-on store/repository/install/build/log management. `ha-readonly` allows only Core info/check/logs; `hass-mcp --help` exposes MCP-server startup, not a generic privileged Supervisor client. Anonymous GET `http://supervisor/addons` returns HTTP401. No Docker client/socket interface was available and no bypass was attempted. No token extraction, direct host access, raw token-backed CLI, or new management integration.

**Do not install until the source gate is resolved** in a supported test environment or the fixture execution issue is corrected and the full unchanged/approved suite is green. Next operator UI action after that prerequisite:

1. Settings → Add-ons (Apps) → Add-on Store → menu → Repositories.
2. Add `https://github.com/CaneTLOTW/ha-codex#issue26-local-test` as an additional test source. Do not remove/edit the existing stable or `#deployment` repository; stop if HA indicates replacement/conflict.
3. Refresh and open exactly **Codex SSH Hotfix Test**, version **0.4.28-test.26.1**; verify isolated source and record actual full Supervisor slug. If ambiguous/colliding, stop.
4. Click **Install** for that item only; Supervisor should build its Dockerfile, not pull the production GHCR image. Leave **Start on boot disabled** and keep independent `/data`.
5. Resume runtime acceptance: metadata baseline before/after each of two starts, logs, scratch YAML access and MCP from the test session. Stop test add-on when finished; do not remove it without user approval.

No automatic permission repairs are part of these steps. Do not invoke the production SSH automation without separate explicit permission; this run only searched existing logs read-only.

## Residual risks / required follow-up

- Entire regression gate remains red in this runtime; mock-based assertions have not passed here.
- No actual Supervisor build, install, two-start acceptance, distinct-UID access, test-session MCP, or SSH authentication verified.
- Existing default ACL inheritance persists; repair requires a separate scoped opt-in decision.
- Custom-named keys outside protected directories with permissive modes can escape filename/owner-private filtering.
- Files created later by another UID may not be writable now that the helper no longer adds default ACLs.
- Broad group-root workspace access still exists; this is a stopgap, not privilege separation.
- Store/repository collision status and actual test full slug remain unknown until permitted Supervisor/UI inspection.

No merge/release; Issue26 must remain open pending genuine runtime acceptance and reporter confirmation. This documentation-only commit does not change the source under test. No reload or HA restart is pending from this run.
