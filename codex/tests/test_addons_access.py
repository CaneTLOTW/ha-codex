import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CODEX_DIR = Path(__file__).resolve().parents[1]
CONFIG = CODEX_DIR / "config.yaml"
APPARMOR = CODEX_DIR / "apparmor.txt"
START = CODEX_DIR / "rootfs/usr/local/bin/codex-start"
SHELL = CODEX_DIR / "rootfs/usr/local/bin/codex-shell"
HELPER = CODEX_DIR / "rootfs/usr/local/bin/codex-addons-sandbox"


class AddonsAccessTests(unittest.TestCase):
    def run_helper(self, config_text: str, mode: str):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.toml"
            config.write_text(config_text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, HELPER, config, mode],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_home_assistant_mount_and_option_are_present(self):
        config = CONFIG.read_text(encoding="utf-8")
        self.assertIn("- type: addons", config)
        self.assertIn("addons_access: read_only", config)
        self.assertIn("addons_access: list(read_only|read_write)", config)

    def test_apparmor_allows_runtime_policy_to_offer_both_modes(self):
        profile = APPARMOR.read_text(encoding="utf-8")
        self.assertIn("/addons/ r,", profile)
        self.assertIn("/addons/** rwk,", profile)

    def test_read_only_removes_addons_and_parent_writable_roots(self):
        result = self.run_helper(
            '[sandbox_workspace_write]\nwritable_roots = ["/share", "/addons/subdir", "/"]\n',
            "read_only",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), ["/share"])
        self.assertIn("Removing writable root", result.stderr)

    def test_read_write_preserves_other_roots_and_adds_addons(self):
        result = self.run_helper(
            '[sandbox_workspace_write]\nwritable_roots = ["/share", "/addons"]\n',
            "read_write",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), ["/share", "/addons"])

    def test_startup_fail_safe_downgrades_full_access_for_read_only_addons(self):
        start = START.read_text(encoding="utf-8")
        self.assertIn('addons_access="$(jq -r', start)
        self.assertIn('codex_permissions="workspace"', start)
        self.assertIn("effective Codex access is reduced from full_access to workspace", start)
        self.assertIn('grant_group_root_access /addons', start)
        self.assertIn("/addons|/addons/*", start)

    def test_shell_applies_effective_writable_roots_override(self):
        shell = SHELL.read_text(encoding="utf-8")
        self.assertIn("codex-addons-sandbox", shell)
        self.assertIn("sandbox_workspace_write.writable_roots=", shell)
        self.assertIn("/data/codex-managed/addons-access", shell)


if __name__ == "__main__":
    unittest.main()
