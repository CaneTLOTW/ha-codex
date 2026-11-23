"""Developer-only prototype regressions; uses no Home Assistant user data."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config.yaml"
START = ROOT / "rootfs/usr/local/bin/codex-start"
TRANSFER = ROOT / "rootfs/usr/local/bin/codex-upload"
DOCKERFILE = ROOT / "Dockerfile"
APPARMOR = ROOT / "apparmor.txt"

class TransferAndAppConfigTests(unittest.TestCase):
    def test_options_and_mount_security(self):
        c = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(c["version"], "0.5.0-dev.10")
        self.assertEqual(c["name"], "Codex Deployment")
        self.assertIs(c["options"]["file_transfer_enabled"], False)
        self.assertEqual(c["options"]["app_configs_visibility"], "hidden_from_guidance")
        self.assertEqual(c["schema"]["file_transfer_enabled"], "bool")
        mount = [m for m in c["map"] if m["type"] == "all_app_configs"]
        self.assertEqual(mount, [{"type": "all_app_configs", "read_only": True,
                                  "path": "/app_configs"}])
        aa = APPARMOR.read_text(encoding="utf-8")
        self.assertIn("/app_configs/** r,", aa)
        self.assertNotIn("/app_configs/** rw", aa)
        start = START.read_text(encoding="utf-8")
        self.assertIn("enableTrzsz=", start)
        self.assertIn("file_transfer_enabled", start)
        self.assertIn("show_read_only", start)
        self.assertIn("instructions only", start)
        self.assertNotIn("grant_group_root_access /app_configs", start)
        for lang in ("de.yaml", "en.yaml", "es.yaml", "pt-BR.yaml"):
            options = yaml.safe_load((ROOT / "translations" / lang).read_text())["configuration"]
            self.assertIn("file_transfer_enabled", options)
            self.assertIn("app_configs_visibility", options)

    def test_pinned_package_and_private_upload_wrapper(self):
        docker = DOCKERFILE.read_text()
        self.assertIn("trzsz==1.1.7", docker)
        self.assertIn("&& trz -v", docker)
        self.assertIn("&& tsz -v", docker)
        self.assertIn("/usr/local/bin/codex-upload", docker)
        upload = TRANSFER.read_text()
        self.assertIn("CODEX_HOME", upload)
        self.assertIn("umask 077", upload)
        self.assertIn("exec trz -d", upload)
        self.assertIn("exec trz ", upload)
        for script in (START, TRANSFER):
            r = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_upload_opt_in_directory_and_symlink_refusal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bindir = root / "bin"
            bindir.mkdir()
            fake_id = bindir / "id"
            fake_id.write_text('#!/bin/sh\n[ "$1" = "-u" ] && { echo 22000; exit 0; }\nexit 1\n')
            fake_id.chmod(0o755)
            fake_trz = bindir / "trz"
            fake_trz.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$FAKE_TRZ_ARGS"\n')
            fake_trz.chmod(0o755)
            home = root / "home"
            home.mkdir()
            state = home / ".codex"
            state.mkdir()
            argfile = root / "args"
            env = os.environ.copy()
            env.update({"HOME": str(home), "CODEX_HOME": str(state),
                        "PATH": str(bindir) + os.pathsep + env.get("PATH", ""),
                        "FAKE_TRZ_ARGS": str(argfile)})
            def run(args, enabled):
                env["CODEX_FILE_TRANSFER_ENABLED"] = "true" if enabled else "false"
                return subprocess.run(["bash", str(TRANSFER), *args], env=env,
                                      capture_output=True, text=True)
            self.assertNotEqual(run([], False).returncode, 0)
            self.assertFalse(argfile.exists())
            result = run([], True)
            self.assertEqual(result.returncode, 0, result.stderr)
            target = state / "uploads"
            self.assertEqual(argfile.read_text().splitlines(), [str(target)])
            self.assertEqual(target.stat().st_mode & 0o777, 0o700)
            result = run(["--directory"], True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(argfile.read_text().splitlines(), ["-d", str(target)])
            target.rmdir()
            target.symlink_to(root, target_is_directory=True)
            self.assertNotEqual(run([], True).returncode, 0)

if __name__ == "__main__":
    unittest.main()
