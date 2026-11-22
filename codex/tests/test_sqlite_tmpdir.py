"""Regression contract for Codex's private SQLite scratch-directory setup.

These checks do not open or modify any real Home Assistant /data state.
Live Codex migration testing remains a separate HAOS acceptance gate.
"""
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / "rootfs/usr/local/bin/codex-session"
REMOTE = ROOT / "rootfs/usr/local/bin/codex-remote-control"
CHECKER = ROOT / "rootfs/usr/local/bin/codex-check-sqlite-tmpdir"
SHELL = ROOT / "rootfs/usr/local/bin/codex-shell"
APPARMOR = ROOT / "apparmor.txt"


class SqliteTmpdirTests(unittest.TestCase):
    def test_both_runtime_paths_create_and_secure_private_tmpdir(self):
        session = SESSION.read_text(encoding="utf-8")
        remote = REMOTE.read_text(encoding="utf-8")
        self.assertIn('sqlite_tmpdir="${user_codex_home}/_sqlite_tmp"', session)
        self.assertIn('sqlite_tmpdir="${codex_home}/_sqlite_tmp"', remote)
        for script in (session, remote):
            self.assertIn('[[ -L "$sqlite_tmpdir" ]]', script)
            self.assertIn('"$sqlite_tmpdir"', script)
            self.assertIn('chmod 700', script)
            self.assertIn('/bin/sh /usr/local/bin/codex-check-sqlite-tmpdir "$sqlite_tmpdir"', script)
            self.assertNotIn(' test -w "$sqlite_tmpdir"', script)
            self.assertNotIn(' test -x "$sqlite_tmpdir"', script)
            self.assertIn('"SQLITE_TMPDIR=$sqlite_tmpdir"', script)
            self.assertIn('"TMPDIR=$sqlite_tmpdir"', script)
            self.assertNotIn("CODEX_SQLITE_HOME=", script)
            self.assertNotIn('rm -f "${codex_home}/state_5.sqlite"', script)
            self.assertNotIn('rm -f "${user_codex_home}/state_5.sqlite"', script)

    def test_environment_variables_are_passed_into_codex_as_user(self):
        session = SESSION.read_text(encoding="utf-8")
        remote = REMOTE.read_text(encoding="utf-8")
        self.assertIn('env "${session_env[@]}"', session)
        self.assertIn('tmux_env=(su-exec "$session_uid:$session_gid" env', session)
        self.assertIn('su-exec 22000:0 env -u SUPERVISOR_TOKEN "${remote_env[@]}"', remote)
        # Explicit user-provided environment variables remain supported.
        self.assertIn('session_env+=("$env_name=$env_value")', session)
        self.assertIn('remote_env+=("$env_name=$env_value")', remote)

    def test_bash_syntax(self):
        for script in (SESSION, REMOTE):
            run = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, f"{script}: {run.stderr}")
        run = subprocess.run(["/bin/sh", "-n", str(CHECKER)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_checker_ignores_shadowed_test_entrypoint(self):
        helper = CHECKER.read_text(encoding="utf-8")
        self.assertIn('[ -d "$scratch" ]', helper)
        self.assertIn('[ -w "$scratch" ]', helper)
        self.assertIn('[ -x "$scratch" ]', helper)
        self.assertIn('mktemp "$scratch/.sqlite-write-probe.XXXXXXXX"', helper)

        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            bin_dir = base / "bin"
            bin_dir.mkdir()
            fake_test = bin_dir / "test"
            fake_test.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
            fake_test.chmod(0o755)
            scratch = base / "private-sqlite-tmp"
            scratch.mkdir(mode=0o700)

            env = os.environ.copy()
            env["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
            good = subprocess.run(
                ["/bin/sh", str(CHECKER), str(scratch)],
                env=env, capture_output=True, text=True, check=False,
            )
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertFalse(list(scratch.glob(".sqlite-write-probe.*")))

            # Do not accept an executable regular file or an aliased symlink.
            bad = base / "not-a-directory"
            bad.write_text("irrelevant", encoding="utf-8")
            link = base / "symlink-directory"
            link.symlink_to(scratch, target_is_directory=True)
            for candidate in (bad, link):
                result = subprocess.run(
                    ["/bin/sh", str(CHECKER), str(candidate)],
                    env=env, capture_output=True, text=True, check=False,
                )
                self.assertNotEqual(result.returncode, 0, str(candidate))

    def test_interactive_codex_does_not_execute_daemon_from_writable_data(self):
        shell = SHELL.read_text(encoding="utf-8")
        apparmor = APPARMOR.read_text(encoding="utf-8")
        remote = REMOTE.read_text(encoding="utf-8")
        self.assertIn("      --no-daemon", shell)
        self.assertIn('    codex "${codex_args[@]}"', shell)
        self.assertIn("  /data/** rwk,", apparmor)
        self.assertNotRegex(apparmor, r"(?m)^\s*/data/.*[ix][^#]*,")
        # Remote Control starts its explicit app-server from the pinned CLI,
        # not the TUI's downloaded managed background daemon.
        self.assertIn("app-server --listen unix:// --remote-control", remote)

    def test_isolated_sqlite_temp_workload_keeps_existing_db(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            private_dir = root / ".codex" / "_sqlite_tmp"
            private_dir.mkdir(parents=True)
            private_dir.chmod(0o700)
            database = root / ".codex" / "fixture.sqlite"
            env = os.environ.copy()
            env["SQLITE_TMPDIR"] = str(private_dir)
            env["TMPDIR"] = str(private_dir)
            code = (
                "import sqlite3, sys; "
                "d=sqlite3.connect(sys.argv[1]); "
                "d.execute('CREATE TABLE IF NOT EXISTS sample (v)'); "
                "d.execute('INSERT INTO sample (v) VALUES (1)'); "
                "d.execute('CREATE TEMP TABLE scratch AS SELECT v FROM sample'); "
                "assert d.execute('SELECT v FROM scratch').fetchone()[0] == 1; "
                "d.commit(); d.close()"
            )
            result = subprocess.run(
                [sys.executable, "-c", code, str(database)],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(database.exists())
            with sqlite3.connect(database) as con:
                self.assertEqual(con.execute("SELECT count(*) FROM sample").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
