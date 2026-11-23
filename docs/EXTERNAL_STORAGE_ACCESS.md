# External mounts and filesystem permissions (Issue #32)

Home Assistant 2026.11 can present externally mounted storage beneath `/media` or `/share` (including exFAT volumes that cannot implement POSIX ACLs). Older HA-Codex versions recursively modified the permissions of every path during app startup; unsupported `setfacl` and `chmod` operations could terminate the app before the ttyd terminal opened.

## Behavior in this candidate

- The existing filtered access helper uses `find -xdev` for both ACL and chmod passes, avoiding traversal into a different filesystem nested below each requested root.
- Protected SSH keys and owner-private files remain excluded.
- If both ACL and chmod operations fail, the app emits a warning and continues startup rather than becoming unavailable.
- A directory that rejects permission changes may remain inaccessible to Codex. This is preferable to changing arbitrary external-storage permissions or failing the entire app.
- The helper still prepares normal writable workspaces. No extra mount or host privilege is introduced.

## Test / rollout

1. Run `python3 -m unittest discover -s codex/tests -v` and check `bash -n codex/rootfs/usr/local/bin/codex-grant-access`.
2. Verify actual startup with a separate, disposable exFAT fixture mounted under `/share` or `/media`; confirm the terminal opens and permissions on the external volume do not change.
3. Verify an ordinary Home Assistant workspace still permits file edits, and that the SSH-key regression tests continue to pass.
4. Test only through a reviewed image/canary. Do not install or merge into stable without runtime acceptance.

**Caveat:** `-xdev` distinguishes filesystem device boundaries, but does not promise to detect bind mounts on the same device. A broader architecture that avoids recursive mass permission changes entirely remains desirable.
