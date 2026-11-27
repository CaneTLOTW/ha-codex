import asyncio
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch


CODEX_DIR = Path(__file__).resolve().parents[1]
RESOURCE_PACKAGE = CODEX_DIR / "rootfs/usr/local/lib/codex-lovelace-resource-mcp"
sys.path.insert(0, str(RESOURCE_PACKAGE))

from codex_lovelace_resource_mcp import core, server  # noqa: E402
from codex_lovelace_resource_mcp.api import ResourceAPI, websocket_url  # noqa: E402


class FakeResourceAPI:
    def __init__(self, resources=None):
        self.resources = list(resources or [])
        self.writes = []
        self.next_id = 1

    async def list(self):
        return [dict(item) for item in self.resources]

    async def create(self, url, resource_type):
        self.writes.append(("create", url, resource_type))
        item = {"id": f"resource-{self.next_id}", "url": url, "type": resource_type}
        self.next_id += 1
        self.resources.append(item)
        return dict(item)

    async def update(self, resource_id, url, resource_type):
        self.writes.append(("update", resource_id, url, resource_type))
        for item in self.resources:
            if item["id"] == resource_id:
                item.update({"url": url, "type": resource_type})
                return dict(item)
        raise core.ResourceError("missing resource")

    async def delete(self, resource_id):
        self.writes.append(("delete", resource_id))
        self.resources = [item for item in self.resources if item["id"] != resource_id]


class LovelaceResourceCoreTests(unittest.TestCase):
    def test_local_path_normalization_and_hacs_protection(self):
        self.assertEqual(core.canonical_local_path("/local/janus/card.js?v=1.0.0-aabbccddeeff"), "/local/janus/card.js")
        for value in (
            "/local/community/card.js",
            "/local/community/x/card.js",
            "/local/a/../card.js",
            "/hacsfiles/card.js",
            "https://example.invalid/card.js",
        ):
            with self.subTest(value=value), self.assertRaises(core.ResourceError):
                core.canonical_local_path(value)

    def test_version_hash_must_match_file(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp)
            (root / "card.js").write_bytes(b"customElements.define('x-card', class {});")
            digest = hashlib.sha256((root / "card.js").read_bytes()).hexdigest()
            url = f"/local/card.js?v=1.2.3-{digest[:12]}"
            self.assertEqual(core.validate_versioned_asset(url, "module", root), ("/local/card.js", digest))
            with self.assertRaisesRegex(core.ResourceError, "does not match"):
                core.validate_versioned_asset("/local/card.js?v=1.2.3-000000000000", "module", root)

    def test_same_path_duplicate_is_rejected(self):
        rows = [
            {"id": "a", "url": "/local/a.js?v=1.0.0-aaaaaaaaaaaa", "type": "module"},
            {"id": "b", "url": "/local/a.js?v=1.0.1-bbbbbbbbbbbb", "type": "module"},
        ]
        with self.assertRaisesRegex(core.ResourceError, "Duplicate"):
            core.require_unique_match(rows, "/local/a.js")

    def test_backup_is_targeted_private_and_redacts_sensitive_url(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            directory = Path(tmp) / "backups"
            before = {"id": "r1", "url": "/local/a.js?v=1.0.0-aaaaaaaaaaaa", "type": "module"}
            path = core.create_backup(directory, "update", "/local/a.js", before, {"id": "r1", "url": "/local/a.js?v=1.1.0-bbbbbbbbbbbb", "type": "module"})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            backup = json.loads(path.read_text())
            self.assertEqual(backup["before"], before)
            self.assertNotIn("resources", backup)
            self.assertEqual(core.safe_url("https://example.invalid/?access_token=secret"), "https://example.invalid/?access_token=[redacted]")

    def test_sensitive_preimage_is_not_persisted(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            with self.assertRaisesRegex(core.ResourceError, "sensitive"):
                core.create_backup(
                    Path(tmp),
                    "update",
                    "/local/card.js",
                    {"id": "x", "url": "/local/card.js?access_token=secret", "type": "module"},
                    {"url": "/local/card.js?v=1.0.0-aaaaaaaaaaaa", "type": "module"},
                )

    def test_versioned_url_uses_release_and_sha_prefix(self):
        content = b"card bytes"
        digest = hashlib.sha256(content).hexdigest()
        self.assertEqual(core.versioned_url("/local/janus/card.js", "0.4.2", content), f"/local/janus/card.js?v=0.4.2-{digest[:12]}")

    def test_private_backup_refuses_writable_and_symlinked_ancestors(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp)
            parent = root / "parent"
            parent.mkdir(mode=0o700)
            target = parent / "backups"
            after = {"id": None, "url": "/local/a.js?v=1-aaaaaaaaaaaa", "type": "module"}
            record = core.create_backup(target, "create", "/local/a.js", None, after)
            parent.chmod(0o770)
            with self.assertRaisesRegex(core.ResourceError, "ancestry"):
                core.read_backup(record)
            with self.assertRaisesRegex(core.ResourceError, "ancestry"):
                core.create_backup(target, "create", "/local/a.js", None, after)
            parent.chmod(0o700)
            self.assertEqual(core.read_backup(record)["after"], after)
            alias = root / "alias"
            alias.symlink_to(parent, target_is_directory=True)
            with self.assertRaises(core.ResourceError):
                core.read_backup(alias / "backups" / record.name)
            sibling = root / "record.json"
            record.rename(sibling)
            record.symlink_to(sibling)
            with self.assertRaises(core.ResourceError):
                core.read_backup(record)
            record.unlink()
            sibling.rename(record)
            record.chmod(0o640)
            with self.assertRaisesRegex(core.ResourceError, "ownership, mode, type, or size"):
                core.read_backup(record)
            record.chmod(0o600)
            real_stat = os.fstat

            def multiple_links(fd):
                actual = real_stat(fd)
                if actual.st_ino != record.stat().st_ino:
                    return actual
                fields = list(actual)
                fields[3] = 2  # st_nlink
                return os.stat_result(fields)

            with patch.object(core.os, "fstat", side_effect=multiple_links):
                with self.assertRaisesRegex(core.ResourceError, "ownership, mode, type, or size"):
                    core.read_backup(record)

    def test_asset_symlinks_and_noncanonical_paths_are_rejected(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp)
            original = root / "asset.js"
            original.write_bytes(b"fixture")
            (root / "link.js").symlink_to(original)
            (root / "dirlink").symlink_to(root, target_is_directory=True)
            for path in ("/local/link.js", "/local/dirlink/asset.js", "/local/%61sset.js"):
                with self.subTest(path=path), self.assertRaises(core.ResourceError):
                    core.asset_digest(root, path)


class LovelaceResourceToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="/tmp")
        root = Path(self.temp.name)
        self.www = root / "www"
        (self.www / "janus").mkdir(parents=True)
        self.asset = self.www / "janus" / "card.js"
        self.asset.write_bytes(b"customElements.define('janus-card', class {});")
        self.backups = root / "backups"
        self.original_www = server.WWW_ROOT
        self.original_backups = server.BACKUP_DIR
        self.original_api = server._api
        server._pending_rollback = None
        server.WWW_ROOT = self.www
        server.BACKUP_DIR = self.backups
        self.hacs = {"id": "hacs-1", "url": "/local/community/card-mod/card-mod.js?v=3", "type": "module"}
        self.fake = FakeResourceAPI([dict(self.hacs)])
        server._api = self.fake

    def tearDown(self):
        server.WWW_ROOT = self.original_www
        server.BACKUP_DIR = self.original_backups
        server._api = self.original_api
        server._pending_rollback = None
        self.temp.cleanup()

    def run_async(self, coro):
        return asyncio.run(coro)

    def preview_rollback(self, backup_id):
        return self.run_async(server.ha_config_rollback_dashboard_resource(backup_id))

    def confirm_rollback(self, backup_id, preview):
        return self.run_async(server.ha_config_rollback_dashboard_resource(
            backup_id, dry_run=False, non_atomic_confirmation=preview["non_atomic_confirmation"]
        ))

    @property
    def expected_url(self):
        digest = hashlib.sha256(self.asset.read_bytes()).hexdigest()
        return f"/local/janus/card.js?v=0.4.2-{digest[:12]}"

    def test_dry_run_has_no_write_or_backup(self):
        result = self.run_async(server.ha_config_set_dashboard_resource("/local/janus/card.js", release="0.4.2"))
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(self.fake.writes, [])
        self.assertFalse(self.backups.exists())

    def test_upsert_create_is_idempotent_and_preserves_hacs(self):
        result = self.run_async(server.ha_config_set_dashboard_resource("/local/janus/card.js", release="0.4.2", dry_run=False))
        self.assertEqual(result["status"], "created")
        self.assertEqual(result["resource"]["url"], self.expected_url)
        self.assertEqual(len(list(self.backups.glob("*.json"))), 1)
        count_after_create = len(self.fake.writes)
        repeated = self.run_async(server.ha_config_set_dashboard_resource("/local/janus/card.js", release="0.4.2", dry_run=False))
        self.assertEqual(repeated["status"], "unchanged")
        self.assertEqual(len(self.fake.writes), count_after_create)
        self.assertEqual(self.fake.resources[0], self.hacs)
        self.assertEqual(len([r for r in self.fake.resources if r["url"].startswith("/local/janus/")]), 1)

    def test_upsert_updates_same_path_resource_and_uses_preimage_for_rollback(self):
        old = {"id": "flow", "url": "/local/janus/card.js?v=0.2.2-aaaaaaaaaaaa", "type": "module"}
        self.fake.resources.append(dict(old))
        result = self.run_async(server.ha_config_set_dashboard_resource("/local/janus/card.js", release="0.4.2", dry_run=False))
        self.assertEqual(result["status"], "updated")
        self.assertEqual(next(r for r in self.fake.resources if r["id"] == "flow")["url"], self.expected_url)
        backup_id = result["backup_id"]
        preview = self.preview_rollback(backup_id)
        self.assertEqual(preview["current"]["url"], self.expected_url)
        self.assertEqual(preview["restore"], old)
        self.assertEqual(len(self.fake.writes), 1)
        rolled = self.confirm_rollback(backup_id, preview)
        self.assertEqual(rolled["status"], "restored")
        restored = next(r for r in self.fake.resources if r["id"] == "flow")
        self.assertEqual(restored["url"], old["url"])
        self.assertEqual(self.fake.resources[0], self.hacs)

    def test_duplicate_path_aborts_before_write(self):
        self.fake.resources.extend([
            {"id": "one", "url": "/local/janus/card.js?v=1-aaaaaaaaaaaa", "type": "module"},
            {"id": "two", "url": "/local/janus/card.js?v=2-bbbbbbbbbbbb", "type": "module"},
        ])
        with self.assertRaisesRegex(core.ResourceError, "Duplicate"):
            self.run_async(server.ha_config_set_dashboard_resource("/local/janus/card.js", release="0.4.2", dry_run=False))
        self.assertEqual(self.fake.writes, [])

    def test_rollback_validates_record_before_any_api_write(self):
        created = self.run_async(server.ha_config_set_dashboard_resource("/local/janus/card.js", release="0.4.2", dry_run=False))
        backup_id = created["backup_id"]
        path = self.backups / f"{backup_id}.json"
        valid = json.loads(path.read_text())
        mutations = (
            {"target_path": "/local/another.js"},
            {"after": {**valid["after"], "type": "unsupported"}},
            {"after": {**valid["after"], "id": "../bad"}},
            {"target_path": "/local/community/fixture.js"},
            {"before": valid["after"]},
        )
        for mutation in mutations:
            path.write_text(json.dumps({**valid, **mutation}))
            with self.subTest(mutation=mutation), self.assertRaises(core.ResourceError):
                self.preview_rollback(backup_id)
        self.assertEqual(len(self.fake.writes), 1)

    def test_failed_update_preserves_concurrent_postimage_and_reports_backup_id(self):
        old = {"id": "flow", "url": "/local/janus/card.js?v=1-aaaaaaaaaaaa", "type": "module"}
        concurrent = {**old, "url": "/local/janus/card.js?v=3-cccccccccccc", "type": "js"}
        self.fake.resources.append(dict(old))
        original_update = self.fake.update

        async def competing_update(*args):
            result = await original_update(*args)
            self.fake.resources[1] = dict(concurrent)
            return result

        self.fake.update = competing_update
        with self.assertRaisesRegex(core.ResourceError, "No automatic rollback attempted") as failure:
            self.run_async(server.ha_config_set_dashboard_resource("/local/janus/card.js", release="0.4.2", dry_run=False))
        backup_id = next(self.backups.glob("*.json")).stem
        self.assertIn(backup_id, str(failure.exception))
        self.assertEqual(self.fake.resources[1], concurrent)
        self.assertEqual(len(self.fake.writes), 1)
        with self.assertRaisesRegex(core.ResourceError, "changed after the backup"):
            self.preview_rollback(backup_id)
        self.assertEqual(len(self.fake.writes), 1)

    def test_failed_readback_preserves_acknowledged_update_until_explicit_rollback(self):
        old = {"id": "flow", "url": "/local/janus/card.js?v=1-aaaaaaaaaaaa", "type": "module"}
        self.fake.resources.append(dict(old))
        original_list = self.fake.list
        reads = 0

        async def transient_error():
            nonlocal reads
            reads += 1
            if reads == 3:
                raise TimeoutError
            return await original_list()

        self.fake.list = transient_error
        with self.assertRaisesRegex(core.ResourceError, "No automatic rollback attempted") as failure:
            self.run_async(server.ha_config_set_dashboard_resource("/local/janus/card.js", release="0.4.2", dry_run=False))
        backup_id = next(self.backups.glob("*.json")).stem
        self.assertIn(backup_id, str(failure.exception))
        self.assertEqual(self.fake.resources[1]["url"], self.expected_url)
        self.assertEqual(len(self.fake.writes), 1)
        preview = self.preview_rollback(backup_id)
        self.assertTrue(preview["original_write_acknowledged"])
        self.assertEqual(preview["operation"], "update")
        self.confirm_rollback(backup_id, preview)
        self.assertEqual(self.fake.resources[1], old)
        self.assertEqual(len(self.fake.writes), 2)

    def test_unconfirmed_create_does_not_delete_an_unidentified_resource(self):
        original_create = self.fake.create

        async def create_without_ack(*args):
            await original_create(*args)
            raise TimeoutError

        self.fake.create = create_without_ack
        with self.assertRaisesRegex(core.ResourceError, "No automatic rollback attempted"):
            self.run_async(server.ha_config_set_dashboard_resource("/local/janus/card.js", release="0.4.2", dry_run=False))
        self.assertEqual(len(self.fake.writes), 1)
        self.assertEqual(self.fake.resources[1]["url"], self.expected_url)
        preview = self.preview_rollback(next(self.backups.glob("*.json")).stem)
        self.assertEqual(preview["status"], "manual_review_required")
        self.assertNotIn("non_atomic_confirmation", preview)

    def test_unacknowledged_update_cannot_be_rolled_back_even_at_requested_url(self):
        self.fake.resources.append({"id": "flow", "url": "/local/janus/card.js", "type": "module"})
        original_update = self.fake.update

        async def update_without_ack(*args):
            await original_update(*args)
            raise TimeoutError

        self.fake.update = update_without_ack
        with self.assertRaisesRegex(core.ResourceError, "No automatic rollback attempted"):
            self.run_async(server.ha_config_set_dashboard_resource("/local/janus/card.js", release="0.4.2", dry_run=False))
        backup_id = next(self.backups.glob("*.json")).stem
        preview = self.preview_rollback(backup_id)
        self.assertEqual(preview["status"], "manual_review_required")
        self.assertEqual(preview["current"]["url"], self.expected_url)
        self.assertNotIn("non_atomic_confirmation", preview)
        self.assertEqual(len(self.fake.writes), 1)

    def test_failed_delete_readback_does_not_recreate_the_resource(self):
        self.fake.resources.append({"id": "flow", "url": self.expected_url, "type": "module"})
        original_list = self.fake.list
        reads = 0

        async def transient_error():
            nonlocal reads
            reads += 1
            if reads == 3:
                raise TimeoutError
            return await original_list()

        self.fake.list = transient_error
        with self.assertRaisesRegex(core.ResourceError, "No automatic rollback attempted") as failure:
            self.run_async(server.ha_config_delete_dashboard_resource("flow", dry_run=False))
        backup_id = next(self.backups.glob("*.json")).stem
        self.assertIn(backup_id, str(failure.exception))
        self.assertEqual(self.fake.writes, [("delete", "flow")])
        self.assertEqual(self.fake.resources, [self.hacs])
        self.assertEqual(self.preview_rollback(backup_id)["operation"], "create")

    def test_confirmation_rejects_missing_wrong_expired_and_reused_tokens(self):
        created = self.run_async(server.ha_config_set_dashboard_resource("/local/janus/card.js", release="0.4.2", dry_run=False))
        backup_id = created["backup_id"]
        with self.assertRaisesRegex(core.ResourceError, "fresh rollback preview"):
            self.run_async(server.ha_config_rollback_dashboard_resource(backup_id, dry_run=False))
        with patch.object(server, "monotonic", return_value=100):
            preview = self.preview_rollback(backup_id)
        with self.assertRaisesRegex(core.ResourceError, "fresh rollback preview"):
            self.confirm_rollback(backup_id, {"non_atomic_confirmation": "wrong"})
        with patch.object(server, "monotonic", return_value=100 + preview["expires_in_seconds"]):
            with self.assertRaisesRegex(core.ResourceError, "expired"):
                self.confirm_rollback(backup_id, preview)
        self.assertEqual(len(self.fake.writes), 1)
        preview = self.preview_rollback(backup_id)
        self.confirm_rollback(backup_id, preview)
        with self.assertRaisesRegex(core.ResourceError, "fresh rollback preview"):
            self.confirm_rollback(backup_id, preview)
        self.assertEqual(len(self.fake.writes), 2)

    def test_confirmation_refuses_resource_change_on_final_read(self):
        self.fake.resources.append({"id": "flow", "url": "/local/janus/card.js", "type": "module"})
        updated = self.run_async(server.ha_config_set_dashboard_resource("/local/janus/card.js", release="0.4.2", dry_run=False))
        backup_id = updated["backup_id"]
        preview = self.preview_rollback(backup_id)
        original_list = self.fake.list
        reads = 0

        async def concurrent_edit():
            nonlocal reads
            reads += 1
            if reads == 2:
                self.fake.resources[1]["type"] = "js"
            return await original_list()

        self.fake.list = concurrent_edit
        with self.assertRaisesRegex(core.ResourceError, "changed during verification"):
            self.confirm_rollback(backup_id, preview)
        self.assertEqual(self.fake.resources[1]["type"], "js")
        self.assertEqual(len(self.fake.writes), 1)

    def test_confirmation_is_bound_to_previewed_asset(self):
        created = self.run_async(server.ha_config_set_dashboard_resource("/local/janus/card.js", release="0.4.2", dry_run=False))
        backup_id = created["backup_id"]
        preview = self.preview_rollback(backup_id)
        self.asset.write_bytes(b"Changed since preview")
        with self.assertRaisesRegex(core.ResourceError, "changed since the preview"):
            self.confirm_rollback(backup_id, preview)
        self.assertEqual(len(self.fake.writes), 1)

    def test_create_rollback_checks_identity_and_verifies_delete(self):
        result = self.run_async(server.ha_config_set_dashboard_resource("/local/janus/card.js", release="0.4.2", dry_run=False))
        backup_id = result["backup_id"]
        path = self.backups / f"{backup_id}.json"
        self.assertEqual(core.read_backup(path)["after"]["id"], result["resource"]["id"])
        rolled = self.confirm_rollback(backup_id, self.preview_rollback(backup_id))
        self.assertEqual(rolled["status"], "created_resource_removed")
        self.assertEqual(self.fake.resources, [self.hacs])
        repeated = self.preview_rollback(backup_id)
        self.assertEqual(repeated["status"], "already_absent")

    def test_delete_and_rollback_restore_url_and_type(self):
        self.fake.resources.append({"id": "flow", "url": self.expected_url, "type": "module"})
        deleted = self.run_async(server.ha_config_delete_dashboard_resource("flow", dry_run=False))
        backup_id = deleted["backup_id"]
        restored = self.confirm_rollback(backup_id, self.preview_rollback(backup_id))
        self.assertEqual(restored["resource"]["url"], self.expected_url)
        self.assertEqual(restored["resource"]["type"], "module")
        self.assertEqual(self.fake.resources[0], self.hacs)
        repeated = self.preview_rollback(backup_id)
        self.assertEqual(repeated["status"], "already_restored")

    def test_delete_default_is_dry_run_and_hacs_delete_is_blocked(self):
        with self.assertRaises(core.ResourceError):
            self.run_async(server.ha_config_delete_dashboard_resource("hacs-1", dry_run=False))
        self.assertEqual(self.fake.writes, [])
        resource = {"id": "custom", "url": self.expected_url, "type": "module"}
        self.fake.resources.append(resource)
        preview = self.run_async(server.ha_config_delete_dashboard_resource("custom"))
        self.assertEqual(preview["status"], "dry_run")
        self.assertEqual(self.fake.writes, [])

    def test_delete_refuses_alias_of_hacs_asset(self):
        hacs_dir = self.www / "community"
        hacs_dir.mkdir()
        shared_asset = hacs_dir / "fixture.js"
        shared_asset.write_bytes(b"fixture")
        (self.www / "alias.js").symlink_to(shared_asset)
        self.fake.resources.append({"id": "alias", "url": "/local/alias.js", "type": "module"})
        with self.assertRaisesRegex(core.ResourceError, "symlink"):
            self.run_async(server.ha_config_delete_dashboard_resource("alias", dry_run=False))
        self.assertEqual(self.fake.writes, [])

    def test_native_websocket_endpoint_path(self):
        self.assertEqual(websocket_url("http://supervisor/core"), "ws://supervisor/core/api/websocket")
        self.assertEqual(websocket_url("https://ha.example/base/"), "wss://ha.example/base/api/websocket")

    def test_resource_api_uses_native_lovelace_crud_messages(self):
        class RecordingClient:
            def __init__(self):
                self.commands = []

            async def request(self, command):
                self.commands.append(command)
                if command["type"] == "lovelace/resources":
                    return []
                return {"id": command.get("resource_id", "new-id"), "url": command.get("url"), "type": command.get("res_type")}

        async def scenario():
            client = RecordingClient()
            api = ResourceAPI(client)
            await api.list()
            await api.create("/local/a.js?v=1.0.0-aaaaaaaaaaaa", "module")
            await api.update("r1", "/local/a.js?v=1.1.0-bbbbbbbbbbbb", "module")
            await api.delete("r1")
            return client.commands

        commands = self.run_async(scenario())
        self.assertEqual([item["type"] for item in commands], [
            "lovelace/resources",
            "lovelace/resources/create",
            "lovelace/resources/update",
            "lovelace/resources/delete",
        ])
        self.assertEqual(commands[1]["res_type"], "module")
        self.assertEqual(commands[2]["resource_id"], "r1")

    def test_stdio_mcp_exposes_required_scoped_tools(self):
        init = {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
        }
        initialized = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        listing = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        env = dict(os.environ)
        env.update({"PYTHONPATH": str(RESOURCE_PACKAGE), "HA_TOKEN": "do-not-print-test-token", "HA_URL": "http://127.0.0.1:1"})
        process = subprocess.Popen(
            [sys.executable, "-IB", str(RESOURCE_PACKAGE / "launch.py")],
            cwd=self.temp.name,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        try:
            assert process.stdin and process.stdout
            process.stdin.write(json.dumps(init) + "\n")
            process.stdin.flush()
            initialize_response = json.loads(process.stdout.readline())
            self.assertEqual(initialize_response["id"], 1)
            process.stdin.write(json.dumps(initialized) + "\n" + json.dumps(listing) + "\n")
            process.stdin.flush()
            tool_response = json.loads(process.stdout.readline())
            self.assertEqual(tool_response["id"], 2)
            names = {item["name"] for item in tool_response["result"]["tools"]}
        finally:
            if process.stdin:
                process.stdin.close()
            process.terminate()
            _, stderr = process.communicate(timeout=5)
        self.assertNotIn("do-not-print-test-token", stderr)
        self.assertTrue({
            "ha_config_list_dashboard_resources",
            "ha_config_set_dashboard_resource",
            "ha_config_delete_dashboard_resource",
            "ha_config_rollback_dashboard_resource",
        }.issubset(names))

    def test_runtime_dependencies_are_pinned_to_audited_versions(self):
        dockerfile = (CODEX_DIR / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("hass-mcp==0.6.2", dockerfile)
        self.assertIn("mcp==1.30.0", dockerfile)
        self.assertIn("websockets==17.4", dockerfile)

    def test_privileged_launcher_uses_fixed_isolated_entry_point(self):
        rootfs = CODEX_DIR / "rootfs"
        wrapper = (rootfs / "usr/local/bin/lovelace-resource-mcp-wrapper").read_text()
        launcher = (rootfs / "usr/local/bin/lovelace-resource-mcp-root-helper").read_text()
        sudoers = (rootfs / "etc/sudoers.d/codex-hass-mcp").read_text()
        legacy = (rootfs / "usr/local/bin/hass-mcp-root-helper").read_text()
        self.assertIn('NOSETENV: /usr/local/bin/lovelace-resource-mcp-root-helper ""', sudoers)
        self.assertIn("sudo /usr/local/bin/lovelace-resource-mcp-root-helper", wrapper)
        self.assertIn("/usr/bin/env -i", launcher)
        self.assertIn("python3 -IB /usr/local/lib/codex-lovelace-resource-mcp/launch.py", launcher)
        self.assertNotIn("lovelace-resource-mcp", legacy)
        result = subprocess.run(
            [sys.executable, "-IB", "-c", "import json, sys; print(json.dumps(sys.path))"],
            cwd=self.temp.name,
            env={**os.environ, "PYTHONPATH": str(self.www)},
            capture_output=True, check=True, text=True,
        )
        self.assertFalse({self.temp.name, str(self.www), ""} & set(json.loads(result.stdout)))

    def test_app_config_manages_scoped_server_and_restores_user_entry(self):
        merge = CODEX_DIR / "rootfs/usr/local/bin/codex-merge-config"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            managed = root / "mcp.json"
            managed.write_text("[]\n", encoding="utf-8")
            config.write_text(
                '[mcp_servers.ha_lovelace_resources]\ncommand = "user-server"\nargs = ["--custom"]\n\n'
                '[mcp_servers.other]\nurl = "https://example.invalid/mcp"\n',
                encoding="utf-8",
            )

            def run(enabled):
                return subprocess.run(
                    [sys.executable, str(merge), str(config), "gpt-6.2-sol", str(enabled).lower(), "workspace", "on-request", str(managed)],
                    text=True,
                    capture_output=True,
                    check=False,
                )

            original = tomllib.loads(config.read_text(encoding="utf-8"))["mcp_servers"]
            disabled_before_enable = run(False)
            self.assertEqual(disabled_before_enable.returncode, 0, disabled_before_enable.stderr)
            self.assertEqual(tomllib.loads(config.read_text(encoding="utf-8"))["mcp_servers"], original)

            enabled = run(True)
            self.assertEqual(enabled.returncode, 0, enabled.stderr)
            parsed = tomllib.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(parsed["mcp_servers"]["ha_lovelace_resources"]["command"], "/usr/local/bin/lovelace-resource-mcp-wrapper")
            self.assertEqual(parsed["mcp_servers"]["ha_lovelace_resources"]["args"], [])
            self.assertEqual(parsed["mcp_servers"]["other"]["url"], "https://example.invalid/mcp")

            disabled = run(False)
            self.assertEqual(disabled.returncode, 0, disabled.stderr)
            restored = tomllib.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(restored["mcp_servers"]["ha_lovelace_resources"]["command"], "user-server")
            self.assertEqual(restored["mcp_servers"]["ha_lovelace_resources"]["args"], ["--custom"])
            self.assertEqual(restored["mcp_servers"]["other"]["url"], "https://example.invalid/mcp")
            repeated = run(False)
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            self.assertEqual(tomllib.loads(config.read_text(encoding="utf-8"))["mcp_servers"], original)


if __name__ == "__main__":
    unittest.main()
