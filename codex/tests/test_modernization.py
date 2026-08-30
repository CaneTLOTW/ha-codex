import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


CODEX_DIR = Path(__file__).resolve().parents[1]
START = CODEX_DIR / "rootfs/usr/local/bin/codex-start"
SHELL = CODEX_DIR / "rootfs/usr/local/bin/codex-shell"
MERGE = CODEX_DIR / "rootfs/usr/local/bin/codex-merge-config"
PREPARE = CODEX_DIR / "rootfs/usr/local/bin/codex-prepare-mcp"
DOCKERFILE = CODEX_DIR / "Dockerfile"
TTYD_PATCH_DIR = CODEX_DIR / "ttyd-mobile-keys"
MOBILE_PATCH = TTYD_PATCH_DIR / "ttyd-1.7.7-mobile-keys.patch"
OLD_PATCH = CODEX_DIR / "ttyd-selection-clipboard.patch"


class ModernizationTests(unittest.TestCase):
    def run_merge(self, config, managed, enable_mcp="false"):
        return subprocess.run(
            [
                sys.executable,
                MERGE,
                config,
                "gpt-5.6-sol",
                enable_mcp,
                "workspace",
                "on-request",
                managed,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_explicit_mcp_false_is_preserved(self):
        start_text = START.read_text(encoding="utf-8")
        self.assertIn("enable_mcp=\"$(jq -r '.enable_mcp' /data/options.json)\"", start_text)
        self.assertNotIn(".enable_mcp // true", start_text)

    def test_mobile_terminal_patch_is_canonical_and_served(self):
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        start_text = START.read_text(encoding="utf-8")
        patch = MOBILE_PATCH.read_text(encoding="utf-8")

        patch_files = sorted(path.name for path in TTYD_PATCH_DIR.glob("*.patch"))
        self.assertEqual(patch_files, [MOBILE_PATCH.name])
        self.assertEqual(dockerfile.count("ttyd-mobile-keys/ttyd-1.7.7-mobile-keys.patch"), 1)
        self.assertIn("mobile-keys", patch)
        self.assertIn("Scroll one page up", patch)
        self.assertIn("transformInput", patch)
        self.assertIn("{ label: 'Enter', ariaLabel: 'Enter', value: '\\r' }", patch)
        self.assertIn("shiftLock", patch)
        self.assertIn("Shift lock", patch)
        self.assertIn("Hide software keyboard", patch)
        self.assertIn("public blur()", patch)
        self.assertIn("grid-template-columns: repeat(7, minmax(0, 1fr))", patch)
        self.assertIn("grid-template-rows: repeat(2, 38px)", patch)
        self.assertIn('meta name="viewport"', patch)
        self.assertIn("width=device-width", patch)
        self.assertIn("viewport-fit=cover", patch)
        self.assertIn("matchMedia", patch)
        self.assertIn("pointer: coarse", patch)
        self.assertNotIn("navigator.clipboard.readText()", patch)
        self.assertNotIn("Paste from clipboard (Ctrl Shift V)", patch)
        self.assertIn("yarn inline", dockerfile)
        self.assertIn(
            "install -D -m 0644 /tmp/ttyd-build/html/dist/inline.html /usr/share/ttyd/mobile-index.html",
            dockerfile,
        )
        self.assertIn("--index /usr/share/ttyd/mobile-index.html", start_text)
        self.assertIn("bind -n PPage copy-mode", dockerfile)
        self.assertFalse(OLD_PATCH.exists())

    def test_web_session_keeps_scrollback(self):
        shell_text = SHELL.read_text(encoding="utf-8")
        self.assertIn("tui.alternate_screen", shell_text)
        self.assertIn('"never"', shell_text)

    def test_prepare_mcp_keeps_bearer_value_out_of_server_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            options = root / "options.json"
            servers = root / "servers.json"
            environment = root / "environment.json"
            options.write_text(
                json.dumps(
                    {
                        "mcp_servers": [
                            {
                                "name": "example",
                                "url": "https://mcp.example.test/mcp",
                                "bearer_token": "secret-value",
                            }
                        ],
                        "environment_variables": [
                            {"name": "EXAMPLE_TENANT", "value": "home"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, PREPARE, options, servers, environment],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            server_data = json.loads(servers.read_text(encoding="utf-8"))
            env_data = json.loads(environment.read_text(encoding="utf-8"))
            self.assertNotIn("secret-value", servers.read_text(encoding="utf-8"))
            self.assertEqual(server_data[0]["bearer_token_env_var"], "CODEX_MCP_EXAMPLE_BEARER_TOKEN")
            self.assertIn(
                {"name": "CODEX_MCP_EXAMPLE_BEARER_TOKEN", "value": "secret-value"},
                env_data,
            )

    def test_merge_remote_mcp_and_disable_bundled_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            managed = root / "mcp.json"
            managed.write_text(
                json.dumps(
                    [
                        {
                            "name": "example",
                            "url": "https://mcp.example.test/mcp",
                            "bearer_token_env_var": "CODEX_MCP_EXAMPLE_BEARER_TOKEN",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_merge(config, managed)
            self.assertEqual(result.returncode, 0, result.stderr)
            parsed = tomllib.loads(config.read_text(encoding="utf-8"))
            self.assertNotIn("homeassistant", parsed["mcp_servers"])
            self.assertEqual(parsed["mcp_servers"]["example"]["url"], "https://mcp.example.test/mcp")

    def test_remote_mcp_restores_previous_same_name_user_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            managed = root / "mcp.json"
            config.write_text(
                '[mcp_servers.example]\ncommand = "old-mcp"\nargs = ["--user-config"]\n',
                encoding="utf-8",
            )
            managed.write_text(
                json.dumps([{"name": "example", "url": "https://managed.example.test/mcp"}]),
                encoding="utf-8",
            )

            managed_result = self.run_merge(config, managed)
            self.assertEqual(managed_result.returncode, 0, managed_result.stderr)
            managed_config = tomllib.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(
                managed_config["mcp_servers"]["example"]["url"],
                "https://managed.example.test/mcp",
            )
            self.assertNotIn("command", managed_config["mcp_servers"]["example"])

            managed.write_text("[]\n", encoding="utf-8")
            restore_result = self.run_merge(config, managed)
            self.assertEqual(restore_result.returncode, 0, restore_result.stderr)
            restored = tomllib.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(restored["mcp_servers"]["example"]["command"], "old-mcp")
            self.assertEqual(restored["mcp_servers"]["example"]["args"], ["--user-config"])
            self.assertNotIn("url", restored["mcp_servers"]["example"])


if __name__ == "__main__":
    unittest.main()
