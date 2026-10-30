# Authorized existing deployment route

User explicitly approved using the existing Deployment channel (go), superseding the earlier no-deployment-branch-change constraint. Stable/main and e6fb3748_codex remain excluded.

Base c79313b0c93c99ee448471a4659c5c10658a04a1, candidate d577b280293d3f24ddb1e0418d47d3d42b5aea1b, version0.4.10-dev.2. Four scoped files only; canonical ttyd patch unchanged. Public GHCR manifest lookup for dev.2 returned404 before publication (anonymous registry-issued pull grant, not Supervisor credentials; no token stored/printed).

Canary: feat/issue26-deployment-canary, workflow41022579641. One validation job then one amd64 build, no publication. Estimate ~3 rounded runner minutes from current PR validation7s/build112s; monitor and stop on failure, no retry loop. Manual observation deadline10min; cancel if hung. Billing quota unavailable with existing scopes.

Only after canary success: fast-forward deployment to same candidate; existing automated workflows perform validation+amd64 build and deployment init+amd64/aarch64 publish+manifest, estimated additional~9 rounded runner minutes from historical durations. No stable latest tag or main push. Verify all gates and version manifest before touching installed test instance.

Then use regular HA update.install for update.codex_deployment_update with backup=true if service access permits, only after latest_version confirms dev.2. Do not use raw Supervisor token, Docker replacement, host access or update stable. Stop/start only addon1e25a555_codex, never e6fb3748_codex. No automatic ACL repair, SSH automation trigger, or firmware. Verify runtime with available interfaces and label inaccessible logs/test-session-MCP unverified; leave stopped on test completion.
