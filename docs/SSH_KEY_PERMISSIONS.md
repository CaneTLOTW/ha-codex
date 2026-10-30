# SSH key permissions: security hotfix (Issue #26)

The Codex App historically ran recursive `setfacl -R -m g:root:rwx`,
`setfacl -R -d -m g:root:rwx`, or `chmod -R g+rwX` against
`/homeassistant` (Home Assistant Core's `/config`), `/share`, `/media`,
optional `/addons`, and the configured working directory. This could
cause OpenSSH to reject private keys with **bad permissions**.

## What the hotfix changes

- Prunes all `.ssh` directories (and a few other conventional private-key
  directories) before both access-ACL and chmod operations.
- Excludes common private-key filenames such as `id_*`, `*.pem`,
  `*.key`, `*.p12`, `*.pfx`, and `*.ppk`, including outside `.ssh`.
- Excludes files with owner-only permissions such as `0600`.
- Resolves the requested work directory to protect an explicit path or
  symlink that points into `.ssh`.
- Does not follow symlinks while traversing the mount.
- No longer creates default ACLs on directories, because new SSH
  directories and keys could otherwise inherit broad group access.
- Retains ordinary workspace access for existing files, with a filtered
  `chmod` fallback if ACL updates fail.

**Scope limitation:** This is a stopgap, not full privilege separation.
Custom-named SSH keys outside `.ssh` with permissive original modes might
not be recognized; users should protect such paths separately. Existing
default ACLs from older releases are **not** removed automatically.
Files created later by a different user may no longer become group-writable
automatically; this is intentional until a narrower access architecture
is implemented.

## Repair previously affected keys (manual and opt-in)

Perform these steps in an environment with access to the **Home Assistant
Core config path** and suitable privileges, after installing the fixed app.
Replace the example key filename if necessary.

First **inspect** the actual owner, mode and ACL, including any parent
directory that may have inherited default ACLs:

```sh
stat -c '%u:%g %a %n' /config /config/.ssh /config/.ssh/id_ed25519
getfacl -p /config /config/.ssh /config/.ssh/id_ed25519
```

If an unwanted *named* `group:root` ACL was added to the SSH directory
or private key, remove only that entry. If a default `group:root` ACL
was added to `.ssh`, remove that entry as well:

```sh
setfacl -x g:root /config/.ssh/id_ed25519
setfacl -x g:root /config/.ssh
setfacl -d -x g:root /config/.ssh
chmod 700 /config/.ssh
chmod 600 /config/.ssh/id_ed25519
```

Apply only the commands relevant to ACL entries actually present. Other
intentionally configured ACLs may need to be preserved. Check the resulting
`getfacl` output and test the original HA SSH automation.

**Important:** An old default `group:root` ACL on `/config` or any
other ancestor could still be inherited by subsequently created `.ssh`
directories. Inspect each affected parent and remove a particular default
ACL entry **only if** it was created by the old Codex startup logic and
is not required by another service. Do **not** recursively reset the
permissions of the entire Home Assistant configuration.

## Validation

```sh
python3 -m unittest discover -s codex/tests -p 'test_ssh_acl_protection.py' -v
bash -n codex/rootfs/usr/local/bin/codex-grant-access
bash -n codex/rootfs/usr/local/bin/codex-start
```

The regression tests cover `.ssh` pruning, private key names, owner-only
files, symlinked work directories, repeated starts, default-ACL avoidance,
regular workspace access, and both ACL and chmod fallback paths.
