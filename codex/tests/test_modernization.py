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
SESSION = CODEX_DIR / "rootfs/usr/local/bin/codex-session"
MERGE = CODEX_DIR / "rootfs/usr/local/bin/codex-merge-config"
PREPARE = CODEX_DIR / "rootfs/usr/local/bin/codex-prepare-mcp"
DOCKERFILE = CODEX_DIR / "Dockerfile"
TTYD_PATCH_DIR = CODEX_DIR / "ttyd-mobile-keys"
MOBILE_PATCH = TTYD_PATCH_DIR / "ttyd-1.7.7-mobile-keys.patch"
OLD_PATCH = CODEX_DIR / "ttyd-selection-clipboard.patch"
HA_READONLY = CODEX_DIR / "rootfs/usr/local/bin/ha-readonly"
HA_READONLY_ROOT = CODEX_DIR / "rootfs/usr/local/bin/ha-readonly-root-helper"
SUDOERS = CODEX_DIR / "rootfs/etc/sudoers.d/codex-hass-mcp"


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

    def test_runtime_codex_self_update_is_disabled(self):
        shell_text = SHELL.read_text(encoding="utf-8")
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            managed = root / "mcp.json"
            config.write_text("check_for_update_on_startup = true\n", encoding="utf-8")
            managed.write_text("[]\n", encoding="utf-8")
            result = self.run_merge(config, managed)
            self.assertEqual(result.returncode, 0, result.stderr)
            parsed = tomllib.loads(config.read_text(encoding="utf-8"))
            self.assertIs(parsed["check_for_update_on_startup"], False)
        self.assertIn("check_for_update_on_startup=false", shell_text)
        self.assertRegex(dockerfile, r"(?m)^ARG CODEX_VERSION=\d+\.\d+\.\d+$")
        self.assertIn("npm install -g @openai/codex@${CODEX_VERSION}", dockerfile)
        self.assertNotIn("npm install -g @openai/codex@latest", dockerfile)

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
        self.assertIn("Show software keyboard", patch)
        self.assertIn("public blur()", patch)
        self.assertIn("public showKeyboard()", patch)
        self.assertIn("if (!this.isModifierInput(data)) return data;", patch)
        self.assertIn("mobileKeys.slice(2, 7).map(this.renderMobileKey)", patch)
        self.assertIn("mobileKeys.slice(7, 8).map(this.renderMobileKey)", patch)
        self.assertIn("mobileKeys.slice(8, 9).map(this.renderMobileKey)", patch)
        self.assertIn("requestManualReconnect", patch)
        self.assertIn("data === '\\r'", patch)
        self.assertIn("ttyd-embedded", patch)
        self.assertIn("padding-bottom: 5px", patch)
        self.assertIn("Native text selection and paste mode", patch)
        self.assertIn("toggleNativeSelection", patch)
        self.assertIn("shouldUseNativeTouchSelection", patch)
        self.assertIn("shouldUseTouchControls", patch)
        self.assertIn("maxTouchPoints", patch)
        self.assertIn("Android|iPhone|iPad|iPod", patch)
        self.assertIn("userAgentData?.mobile", patch)
        self.assertIn("coarsePrimaryPointer", patch)
        self.assertIn("this.touchControls && (", patch)
        self.assertIn("if (!this.touchControls) this.container = c as HTMLElement;", patch)
        self.assertIn("if (this.touchControls) {", patch)
        self.assertIn("const selectionMode = this.xterm.toggleNativeSelection();", patch)
        self.assertIn("this.setState({ selectionMode });", patch)
        self.assertIn("private pressKeyboardDismiss(event: PointerEvent)", patch)
        self.assertIn("this.xterm.blur();", patch)
        self.assertIn("private pressKeyboardShow(event: PointerEvent)", patch)
        self.assertIn("this.xterm.showKeyboard();", patch)
        self.assertIn("ttyd-native-touch-selection", patch)
        self.assertIn("this.terminal.paste(text)", patch)
        self.assertIn("Selection unavailable", patch)
        self.assertIn("this.setRendererType(this.nativeSelectionMode ? 'dom' : this.requestedRenderer)", patch)
        self.assertIn("grid-template-columns: repeat(8, minmax(0, 1fr))", patch)
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
        # Desktop keeps the upstream ttyd/xterm parent DOM; the mobile wrapper is rendered only on detected touch devices.
        self.assertIn("class={this.touchControls ? 'ttyd-touch-controls' : undefined}", patch)
        self.assertIn("if (!this.touchControls) this.container = c as HTMLElement;", patch)
        self.assertNotIn("if (!window.matchMedia('(hover: none), (pointer: coarse), (max-width: 768px)').matches)", patch)

    def test_readonly_ha_helper_and_agent_guidance(self):
        root = HA_READONLY_ROOT.read_text(encoding="utf-8")
        wrapper = HA_READONLY.read_text(encoding="utf-8")
        sudoers = SUDOERS.read_text(encoding="utf-8")
        start_text = START.read_text(encoding="utf-8")
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")

        self.assertIn("ha-readonly-root-helper", wrapper)
        self.assertIn('[[ $# -eq 2 ]] || deny', root)
        self.assertIn('[[ "$1" == "core" ]] || deny', root)
        self.assertIn("info|check|logs", root)
        self.assertIn("SUPERVISOR_TOKEN=", root)
        self.assertIn("exec /usr/local/bin/ha", root)
        self.assertIn("ha-readonly-root-helper", sudoers)
        self.assertIn("ha-readonly core info", start_text)
        self.assertIn("ha-readonly core check", start_text)
        self.assertIn("ha-readonly core logs", start_text)
        self.assertIn("Supervisor token is intentionally removed", start_text)
        self.assertIn("ha-readonly", dockerfile)

    def test_web_session_keeps_scrollback(self):
        shell_text = SHELL.read_text(encoding="utf-8")
        self.assertIn("tui.alternate_screen", shell_text)
        self.assertIn('"never"', shell_text)

    def test_persistent_ttyd_session_keeps_wheel_and_prefers_desktop_selection(self):
        session_text = SESSION.read_text(encoding="utf-8")
        patch = MOBILE_PATCH.read_text(encoding="utf-8")
        self.assertIn('tmux -S "$tmux_socket" set-option -g mouse on', session_text)
        self.assertIn('unbind-key -n MouseDown3Pane', session_text)
        self.assertIn('unbind-key -n M-MouseDown3Pane', session_text)
        self.assertIn('tmux -S "$tmux_socket" attach-session -t codex', session_text)
        self.assertIn("installDesktopSelectionPreference", patch)
        self.assertIn("desktopSelectionActive", patch)
        self.assertIn("Object.defineProperty(event, 'shiftKey'", patch)
        self.assertIn("mouseEvent.button !== 0 || mouseEvent.altKey", patch)
        self.assertIn("window.matchMedia?.('(hover: none) and (pointer: coarse)')", patch)
        self.assertIn("installDesktopSelectionPreference", patch)
        self.assertIn("Object.defineProperty(event, 'shiftKey'", patch)
        self.assertIn("stopImmediatePropagation", patch)
        self.assertIn("beforeInputFallback", patch)
        self.assertIn("inputEvent.inputType !== 'insertFromPaste'", patch)
        self.assertIn("xterm-char-measure-element", patch)
        self.assertIn("xterm-width-cache-measure-container", patch)
        self.assertIn("if (!this.nativeSelectionMode) this.terminal.focus();", patch)
        self.assertNotIn("if (this.nativeSelectionMode) this.terminal.blur();", patch)
        self.assertNotIn("installDesktopShiftSelectionScroll", patch)
        self.assertNotIn("desktopSelectionAnchor", patch)

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
