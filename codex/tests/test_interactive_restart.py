"""Guard the Home Assistant Codex terminal manual restart after Ctrl+C.

The tests use a fake image-installed CLI and a fake /addons policy helper.
No Home Assistant data, credentials or user databases are opened.
"""
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "Dockerfile"
SHELL = ROOT / "rootfs/usr/local/bin/codex-shell"
TUI = ROOT / "rootfs/usr/local/bin/codex-tui"


class InteractiveRestartTests(unittest.TestCase):
    def test_shared_launcher_is_executable_in_image(self):
        docker = DOCKERFILE.read_text(encoding="utf-8")
        shell = SHELL.read_text(encoding="utf-8")
        self.assertIn("    /usr/local/bin/codex-tui \\", docker)
        self.assertIn("    /usr/local/bin/codex-tui", shell)
        self.assertNotIn('    codex "' + '$' + '{codex_args[@]}"', shell)
        self.assertIn("run 'codex' or 'codex resume'", shell)
        for path in (SHELL, TUI):
            result = subprocess.run(
                ["bash", "-n", str(path)], text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_manual_tui_and_management_commands_are_dispatched_safely(self):
        docker = DOCKERFILE.read_text(encoding="utf-8")
        match = re.search(
            r"(?s)COPY <<'EOF' /etc/codex\.bashrc\n(.*?)\nEOF\n", docker
        )
        self.assertIsNotNone(match, "Cannot locate the Dockerfile bashrc")
        rc = match.group(1)

        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            bin_dir = base / "bin"
            bin_dir.mkdir()

            fake_codex = bin_dir / "codex"
            fake_codex.write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$@\"\n", encoding="utf-8"
            )
            fake_codex.chmod(0o755)

            fake_addons = base / "addons-guard.py"
            fake_addons.write_text(
                "print('[\"/homeassistant\"]')\n", encoding="utf-8"
            )
            launcher = base / "codex-tui"
            launcher.write_text(
                TUI.read_text(encoding="utf-8").replace(
                    "/usr/local/bin/codex-addons-sandbox", str(fake_addons)
                ),
                encoding="utf-8",
            )
            launcher.chmod(0o755)

            rcfile = base / "codex.bashrc"
            rcfile.write_text(
                rc.replace("/usr/local/bin/codex-tui", str(launcher)),
                encoding="utf-8",
            )

            home = base / "home"
            home.mkdir()
            env = os.environ.copy()
            env.update({
                "PATH": str(bin_dir) + os.pathsep + env.get("PATH", ""),
                "HOME": str(home),
                "CODEX_HOME": str(home / ".codex"),
                "CODEX_PERMISSIONS": "workspace",
                "CODEX_ENABLE_MCP": "false",
                "PS1": "",
            })

            def invoke(command):
                run = subprocess.run(
                    ["bash", "--noprofile", "--rcfile", str(rcfile), "-ic",
                     "codex " + command],
                    env=env, text=True, capture_output=True, check=False,
                )
                self.assertEqual(run.returncode, 0, run.stderr)
                return run.stdout.splitlines()

            for command in ("", "resume --last", "fork --last",
                            "--no-daemon", "--model sample-model"):
                args = invoke(command)
                self.assertEqual(args.count("--no-daemon"), 1, args)
                self.assertIn(
                    'sandbox_workspace_write.writable_roots=["/homeassistant"]',
                    args,
                )
                self.assertIn("check_for_update_on_startup=false", args)
                if command.startswith("resume"):
                    self.assertEqual(args[-2:], ["resume", "--last"])
                if command.startswith("fork"):
                    self.assertEqual(args[-2:], ["fork", "--last"])

            for command, expected in (
                ("--version", ["--version"]),
                ("--help", ["--help"]),
                ("login status", ["login", "status"]),
                ("exec check", ["exec", "check"]),
                ("mcp list", ["mcp", "list"]),
                ("app-server --help", ["app-server", "--help"]),
            ):
                self.assertEqual(invoke(command), expected, command)


if __name__ == "__main__":
    unittest.main()
