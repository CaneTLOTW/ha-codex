"""Regression checks for SSH key permissions during Codex startup.

Tests operate solely on disposable paths. ACL assertions use the actual
setfacl/getfacl tools when available. The chmod fallback is exercised by
hiding setfacl's command lookup inside bash, without creating executable mocks.
This also works when /tmp and /share forbid executing freshly written files.
"""

import os
import pathlib
import shutil
import stat
import subprocess
import tempfile
import unittest

HELPER = pathlib.Path(__file__).resolve().parents[1] / "rootfs/usr/local/bin/codex-grant-access"


def mode(path):
    return stat.S_IMODE(path.stat().st_mode)


class GrantAccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.workspace = self.root / "homeassistant"
        self.workspace.mkdir()

        self.ssh = self.workspace / ".ssh"
        self.ssh.mkdir()
        self.ssh.chmod(0o700)
        self.key = self.ssh / "id_ed25519"
        self.key.write_text("fixture, not a real private key")
        self.key.chmod(0o600)
        self.nested = self.ssh / "nested"
        self.nested.mkdir()
        (self.nested / "inside.txt").write_text("protected")

        self.private = self.workspace / "private0600"
        self.private.write_text("owner-private")
        self.private.chmod(0o600)

        self.outside = [
            self.workspace / "custom.pem",
            self.workspace / "id_rsa",
            self.workspace / "another.key",
        ]
        for path in self.outside:
            path.write_text("fixture")
            path.chmod(0o644)

        self.normal = self.workspace / "normal.yaml"
        self.normal.write_text("hello")
        self.normal.chmod(0o644)
        self.script = self.workspace / "shell.sh"
        self.script.write_text("#!/bin/sh\nexit 0\n")
        self.script.chmod(0o755)
        self.secrets = self.workspace / "secrets.yaml"
        self.secrets.write_text("fixture")
        self.secrets.chmod(0o644)
        self.storage = self.workspace / ".storage"
        self.storage.mkdir()
        self.storage_file = self.storage / "core.config"
        self.storage_file.write_text("fixture")
        self.storage_file.chmod(0o644)

        self.link = self.workspace / "linkedssh"
        self.link.symlink_to(self.ssh, target_is_directory=True)

    def invoke(self, target, fallback=False):
        if fallback:
            # No mock binaries: only make the lookup of setfacl fail.
            # Everything else, including chmod, is the actual system command.
            script = (
                'command() { if [[ "$#" -eq 2 && "$1" == "-v" && "$2" == "setfacl" ]]; '
                'then return 1; fi; builtin command "$@"; }\n'
                'source "$1" "$2"\n'
            )
            args = ["bash", "-c", script, "acl-test", str(HELPER), str(target)]
        else:
            args = ["bash", str(HELPER), str(target)]
        result = subprocess.run(args, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def acl(self, path):
        return subprocess.check_output(
            ["getfacl", "-cp", str(path)], text=True
        )

    def protected_snapshot(self):
        paths = [self.ssh, self.nested, self.key, self.nested / "inside.txt",
                 self.private, *self.outside]
        result = {str(path): (mode(path), path.stat().st_uid, path.stat().st_gid)
                  for path in paths}
        if shutil.which("getfacl"):
            result = {name: (*fields, self.acl(name)) for name, fields in result.items()}
        result[str(self.link)] = (
            self.link.lstat().st_mode, os.readlink(self.link)
        )
        return result

    def require_acls(self):
        if not shutil.which("setfacl") or not shutil.which("getfacl"):
            self.skipTest("real setfacl/getfacl tools unavailable")

    def test_acl_prunes_private_paths_and_executable_is_preserved(self):
        self.require_acls()
        before = self.protected_snapshot()
        for _ in range(2):
            self.invoke(self.workspace)
            self.assertEqual(self.protected_snapshot(), before)
            self.assertIn("group:root:rw-", self.acl(self.normal))
            self.assertIn("group:root:rw-", self.acl(self.secrets))
            self.assertIn("group:root:rw-", self.acl(self.storage_file))
            self.assertIn("group:root:rwx", self.acl(self.script))
            self.assertNotIn("default:", self.acl(self.workspace))
            self.assertNotIn("default:", self.acl(self.storage))

    def test_chmod_fallback_uses_same_exclusions(self):
        before = self.protected_snapshot()
        for _ in range(2):
            self.invoke(self.workspace, fallback=True)
            self.assertEqual(self.protected_snapshot(), before)
            self.assertEqual(mode(self.normal), 0o664)
            self.assertEqual(mode(self.script), 0o775)
            self.assertEqual(mode(self.secrets), 0o664)
            self.assertEqual(mode(self.storage_file), 0o664)

    def test_workdir_inside_ssh_and_symlink_to_ssh_are_skipped(self):
        before = self.protected_snapshot()
        for target in (self.ssh, self.nested, self.key, self.link):
            self.invoke(target)
            self.invoke(target, fallback=True)
            self.assertEqual(self.protected_snapshot(), before)

    def test_real_chmod_fallback_keeps_private_modes(self):
        self.invoke(self.workspace, fallback=True)
        self.assertEqual(mode(self.ssh), 0o700)
        self.assertEqual(mode(self.key), 0o600)
        self.assertEqual(mode(self.private), 0o600)
        self.assertEqual(mode(self.normal), 0o664)
        self.assertTrue(mode(self.script) & stat.S_IXGRP)

    def test_repeated_startups_do_not_touch_ssh(self):
        before = self.protected_snapshot()
        for _ in range(2):
            self.invoke(self.workspace, fallback=True)
            self.assertEqual(self.protected_snapshot(), before)


if __name__ == "__main__":
    unittest.main()
