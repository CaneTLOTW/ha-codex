"""Contract gates; live HAOS/iOS pairing needs separate acceptance."""
import subprocess
import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config.yaml"
DOCKERFILE = ROOT / "Dockerfile"
START = ROOT / "rootfs/usr/local/bin/codex-start"
SIDECAR = ROOT / "rootfs/usr/local/bin/codex-remote-control"


class RemoteControlTests(unittest.TestCase):
    def test_configuration_switch_and_all_translations(self):
        cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(cfg["version"], "0.4.30-dev.2")
        self.assertIs(cfg["options"]["remote_control_enabled"], False)
        self.assertEqual(cfg["schema"]["remote_control_enabled"], "bool")
        for path in (ROOT / "translations").glob("*.yaml"):
            t = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertIn("remote_control_enabled", t["configuration"])

    def test_disabled_mode_preserves_ttyd_exec(self):
        s = START.read_text(encoding="utf-8")
        self.assertIn(".remote_control_enabled // false", s)
        self.assertIn('if [[ "$remote_control_enabled" != "true" ]]; then', s)
        self.assertIn('exec ttyd "${ttyd_args[@]}"', s)
        self.assertIn("/usr/local/bin/codex-remote-control &", s)
        self.assertIn("trap 'stop_children; exit 143' TERM INT HUP", s)
        self.assertIn('wait "$ttyd_pid" || ttyd_status=$?', s)

    def test_official_unprivileged_sidecar(self):
        s = SIDECAR.read_text(encoding="utf-8")
        self.assertIn("su-exec 22000:0 env -u SUPERVISOR_TOKEN", s)
        self.assertIn("app-server --listen unix:// --remote-control", s)
        self.assertNotIn("remote-control start", s)
        self.assertNotIn("daemon/releases", s)
        self.assertIn("trap on_stop TERM INT HUP", s)
        self.assertIn("failures >= 5", s)
        self.assertIn('kill -TERM "$active_pid"', s)
        self.assertIn("codex-addons-sandbox", s)
        self.assertIn("codex-merge-config", s)
        self.assertIn("CODEX_MCP_ENVIRONMENT", s)
        self.assertIn("config_lock", s)
        self.assertIn("/usr/local/bin/codex-remote-control", DOCKERFILE.read_text(encoding="utf-8"))

    def test_bash_syntax(self):
        for script in (START, SIDECAR):
            run = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, f"{script}: {run.stderr}")


if __name__ == "__main__":
    unittest.main()
