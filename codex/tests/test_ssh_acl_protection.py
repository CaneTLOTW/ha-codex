import os
import pathlib
import subprocess
import tempfile
import unittest

HELPER = pathlib.Path(__file__).resolve().parents[1] / 'rootfs/usr/local/bin/codex-grant-access'


class GrantAccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.workspace = self.root / 'homeassistant'
        self.workspace.mkdir()
        self.ssh = self.workspace / '.ssh'
        self.ssh.mkdir(mode=0o700)
        self.key = self.ssh / 'id_ed25519'
        self.key.write_text('-----BEGIN OPENSSH PRIVATE KEY-----\n')
        self.key.chmod(0o600)
        (self.ssh / 'new.key').write_text('key')
        (self.workspace / '.storage').mkdir()
        (self.workspace / '.storage' / 'core.config').write_text('private')
        (self.workspace / 'secrets.yaml').write_text('secrets')
        (self.workspace / 'custom.pem').write_text('cert key')
        (self.workspace / 'id_rsa').write_text('key')
        (self.workspace / 'private0600').write_text('key')
        (self.workspace / 'private0600').chmod(0o600)
        (self.workspace / 'normal.yaml').write_text('good')
        (self.workspace / 'shell.sh').write_text('#!/bin/sh\n')
        (self.workspace / 'shell.sh').chmod(0o755)
        (self.workspace / 'linkedssh').symlink_to(self.ssh, target_is_directory=True)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.log = self.root / 'actions.log'
        fake = self.bin / 'setfacl'
        fake.write_text('#!/bin/sh\nprintf "ACL %s\\n" "$*" >> "$MOCK_LOG"\nexit "${MOCK_FAIL:-0}"\n')
        fake.chmod(0o755)
        fake = self.bin / 'chmod'
        fake.write_text('#!/bin/sh\nprintf "CHMOD %s\\n" "$*" >> "$MOCK_LOG"\n')
        fake.chmod(0o755)

    def run_helper(self, target, fail=False):
        env = os.environ.copy()
        env.update(PATH=str(self.bin) + ':' + env['PATH'], MOCK_LOG=str(self.log), MOCK_FAIL='1' if fail else '0')
        result = subprocess.run(['bash', str(HELPER), str(target)], text=True, capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.log.read_text() if self.log.exists() else ''

    def test_acl_prunes_private_paths_and_executable_is_preserved(self):
        log = self.run_helper(self.workspace)
        self.assertIn('normal.yaml', log)
        self.assertIn('secrets.yaml', log)
        self.assertIn('core.config', log)
        self.assertIn('g:root:rw- --', log)
        self.assertIn('shell.sh', log)
        self.assertIn('g:root:rwx --', log)
        self.assertNotIn('id_ed25519', log)
        self.assertNotIn('.ssh', log)
        self.assertNotIn('custom.pem', log)
        self.assertNotIn('id_rsa', log)
        self.assertNotIn('private0600', log)
        self.assertNotIn('linkedssh', log)
        self.assertNotIn(' -d ', log)

    def test_chmod_fallback_uses_same_exclusions(self):
        log = self.run_helper(self.workspace, fail=True)
        self.assertIn('CHMOD g+rwX', log)
        self.assertIn('normal.yaml', log)
        for excluded in ('id_ed25519', '.ssh', 'custom.pem', 'id_rsa', 'private0600', 'linkedssh'):
            self.assertNotIn('CHMOD g+rwX -- ' + str(self.workspace / excluded), log)

    def test_workdir_inside_ssh_and_symlink_to_ssh_are_skipped(self):
        self.assertEqual(self.run_helper(self.ssh), '')
        self.assertEqual(self.run_helper(self.workspace / 'linkedssh'), '')
        self.assertEqual(self.run_helper(self.key), '')

    def test_repeated_startups_do_not_touch_ssh(self):
        self.run_helper(self.workspace)
        self.log.unlink()
        log = self.run_helper(self.workspace)
        self.assertNotIn('.ssh', log)
        self.assertNotIn('id_ed25519', log)


if __name__ == '__main__':
    unittest.main()
