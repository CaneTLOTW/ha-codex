import json
import runpy
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
addons_sandbox = runpy.run_path(str(HELPER))


class AddonsAccessTests(unittest.TestCase):
    @staticmethod
    def isolated_helper(directory: Path, addons_root: Path) -> Path:
        # Substitute only the protected-root constant in a temporary helper copy.
        source = HELPER.read_text(encoding="utf-8")
        marker = 'ADDONS = Path("/addons")'
        if source.count(marker) != 1:
            raise AssertionError("protected-root declaration changed")
        copy = directory / "isolated-helper.py"
        copy.write_text(source.replace(marker, f"ADDONS = Path({str(addons_root)!r})", 1), encoding="utf-8")
        return copy

    def run_helper(self, config_text: str, mode: str, addons_root: Path):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.toml"
            config.write_text(config_text, encoding="utf-8")
            helper = self.isolated_helper(Path(tmp), addons_root)
            return subprocess.run(
                [sys.executable, helper, config, mode],
                capture_output=True,
                text=True,
                check=False,
            )

    @staticmethod
    def roots_config(*roots: Path | str) -> str:
        values = ", ".join(json.dumps(str(root)) for root in roots)
        return f"[sandbox_workspace_write]\nwritable_roots = [{values}]\n"

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
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            addons = base / "fake-addons"
            addons.mkdir()
            (addons / "subdir").mkdir()
            share = base / "share"
            share.mkdir()

            result = self.run_helper(
                self.roots_config(share, addons / "subdir", base, "relative-root"),
                "read_only",
                addons,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), [str(share.resolve())])
            self.assertIn("Removing writable root", result.stderr)
            self.assertIn("Removing relative writable root", result.stderr)

    def test_read_write_preserves_other_roots_and_adds_addons(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            addons = base / "fake-addons"
            addons.mkdir()
            share = base / "share"
            share.mkdir()
            share_alias = base / "share-alias"
            share_alias.symlink_to(share, target_is_directory=True)
            addons_alias = base / "addons-alias"
            addons_alias.symlink_to(addons, target_is_directory=True)

            result = self.run_helper(
                self.roots_config(share, share_alias, addons_alias, addons),
                "read_write",
                addons,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), [str(share.resolve()), str(addons.resolve())])

    def test_cli_rejects_nonexistent_roots_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            addons = base / "fake-addons"
            addons.mkdir()
            missing = base / "created-later"
            loop = base / "loop"
            loop.symlink_to(loop)
            file_root = base / "not-a-directory"
            file_root.write_text("fixture", encoding="utf-8")

            result = self.run_helper(self.roots_config(missing, loop, file_root), "read_only", addons)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), [])
            self.assertIn("Removing unresolvable writable root", result.stderr)

    def test_read_only_filters_dotdot_symlink_and_parent_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            addons = base / "fake-addons"
            addons.mkdir()
            (addons / "child").mkdir()
            (base / "alias").symlink_to(addons, target_is_directory=True)
            unrelated = base / "unrelated"
            unrelated.mkdir()
            (base / "unrelated-alias").symlink_to(unrelated, target_is_directory=True)

            roots = [
                str(addons / "child"),
                f"{base}/unrelated/../fake-addons/child",
                str(base / "alias" / "child"),
                str(base),
                str(base.parent),
                str(base / "unrelated-alias"),
                "relative-root",
            ]
            filtered = addons_sandbox["filter_roots"](roots, "read_only", addons)

            self.assertEqual(filtered, [str(unrelated)])

    def test_working_directory_guard_resolves_dotdot_and_symlinks_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            addons = base / "fake-addons"
            addons.mkdir()
            child = addons / "child"
            child.mkdir()
            safe = base / "safe"
            safe.mkdir()
            (base / "unrelated").mkdir()
            (base / "addons-alias").symlink_to(addons, target_is_directory=True)
            (base / "outside-alias").symlink_to(safe, target_is_directory=True)
            broken = base / "broken"
            broken.symlink_to(base / "missing", target_is_directory=True)
            loop_a, loop_b = base / "loop-a", base / "loop-b"
            loop_a.symlink_to(loop_b)
            loop_b.symlink_to(loop_a)

            for path in (
                str(child),
                f"{base}/addons-alias/child",
                f"{base}/unrelated/../fake-addons/child",
                f"{base}/outside-alias/../fake-addons/child",
                str(base),
                f"{base}/..",
            ):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    addons_sandbox["resolve_working_directory"](path, addons, "read_only")

            resolved_safe = addons_sandbox["resolve_working_directory"](str(base / "outside-alias"), addons)
            self.assertEqual(resolved_safe, safe.resolve())
            self.assertEqual(
                addons_sandbox["resolve_working_directory"](str(base / "addons-alias" / "child"), addons, "read_write"),
                child.resolve(),
            )
            for path in (str(base), str(base.parent)):
                with self.subTest(path=path, mode="read_write"), self.assertRaises(ValueError):
                    addons_sandbox["resolve_working_directory"](path, addons, "read_write")
            for path in (str(broken), str(loop_a), str(base / "missing")):
                with self.subTest(path=path), self.assertRaises((OSError, RuntimeError)):
                    addons_sandbox["resolve_working_directory"](path, addons)

    def test_working_directory_cli_uses_canonical_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            addons = base / "fake-addons"
            addons.mkdir()
            (base / "alias").symlink_to(addons, target_is_directory=True)
            safe = base / "safe"
            safe.mkdir()
            helper = self.isolated_helper(base, addons)
            blocked = subprocess.run(
                [sys.executable, helper, "--resolve-working-directory", str(base / "alias"), "read_only"],
                capture_output=True, text=True, check=False,
            )
            allowed = subprocess.run(
                [sys.executable, helper, "--resolve-working-directory", str(safe), "read_only"],
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            self.assertEqual(allowed.stdout.strip(), str(safe.resolve()))

    def test_startup_fail_safe_downgrades_full_access_for_read_only_addons(self):
        start = START.read_text(encoding="utf-8")
        self.assertIn('addons_access="$(jq -r', start)
        self.assertIn('codex_permissions="workspace"', start)
        self.assertIn("effective Codex access is reduced from full_access to workspace", start)
        self.assertIn('grant_group_root_access /addons', start)
        self.assertIn("/addons|/addons/*", start)
        guard = start.index("--resolve-working-directory")
        grant_workdir = start.index('grant_group_root_access "$work_dir"')
        self.assertLess(guard, grant_workdir)
        self.assertIn('exit 1', start[guard:grant_workdir])

    def test_shell_applies_effective_writable_roots_override(self):
        shell = SHELL.read_text(encoding="utf-8")
        self.assertIn("codex-addons-sandbox", shell)
        self.assertIn("sandbox_workspace_write.writable_roots=", shell)
        self.assertIn("/data/codex-managed/addons-access", shell)


if __name__ == "__main__":
    unittest.main()
