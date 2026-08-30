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
MOBILE_PATCH = CODEX_DIR / "ttyd-mobile-keys/ttyd-1.7.7-mobile-keys.patch"
OLD_PATCH = CODEX_DIR / "ttyd-selection-clipboard.patch"


class ModernizationTests(unittest.TestCase):
    def test_explicit_mcp_false_is_preserved(self):
        start_text = START.read_text(encoding="utf-8")
        self.assertIn("enable_mcp=\"$(jq -r '.enable_mcp' /data/options.json)\"", start_text)
        self.assertNotIn(".enable_mcp // true", start_text)

    def test_mobile_terminal_patch_is_canonical(self):
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        patch = MOBILE_PATCH.read_text(encoding="utf-8")
        self.assertIn("ttyd-mobile-keys/ttyd-1.7.7-mobile-keys.patch", dockerfile)
        self.assertIn("mobile-keys", patch)
        self.assertIn("Scroll one page up", patch)
        self.assertIn("transformInput", patch)
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
            result = subprocess.run(
                [
                    sys.executable,
                    MERGE,
                    config,
                    "gpt-5.6-sol",
                    "false",
                    "workspace",
                    "on-request",
                    managed,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            parsed = tomllib.loads(config.read_text(encoding="utf-8"))
            self.assertNotIn("homeassistant", parsed["mcp_servers"])
            self.assertEqual(parsed["mcp_servers"]["example"]["url"], "https://mcp.example.test/mcp")


if __name__ == "__main__":
    unittest.main()
