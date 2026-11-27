"""Least-privilege stdio MCP server for Lovelace resource deployment."""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from mcp.server.fastmcp import FastMCP

from .api import HomeAssistantWebSocket, ResourceAPI
from .core import (
    RESOURCE_TYPES,
    ResourceError,
    canonical_local_path,
    create_backup,
    public_resource,
    require_unique_match,
    update_backup_after,
    validate_versioned_asset,
    versioned_url,
)

mcp = FastMCP("HA Lovelace Resource Manager")
_operation_lock = asyncio.Lock()
_api: ResourceAPI | None = None
WWW_ROOT = Path(os.environ.get("HA_CONFIG_DIR", "/homeassistant")) / "www"
BACKUP_DIR = Path(os.environ.get("HA_RESOURCE_BACKUP_DIR", "/share/ha-lovelace-resource-backups"))
BACKUP_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}$")


def _get_api() -> ResourceAPI:
    global _api
    if _api is None:
        _api = ResourceAPI(HomeAssistantWebSocket())
    return _api


def _version_url(url: str, release: str | None) -> tuple[str, str, str]:
    parts = urlsplit(url)
    base_path = canonical_local_path(url)
    if parts.query:
        _, digest = validate_versioned_asset(url, "module", WWW_ROOT)
        value = parse_qs(parts.query).get("v", [""])[0]
        if release and not value.startswith(f"{release}-"):
            raise ResourceError("The URL release label does not match the requested release")
        return url, base_path, digest
    if not release:
        raise ResourceError("Supply release when URL has no version query")
    asset = (WWW_ROOT.resolve(strict=True) / base_path.removeprefix("/local/")).resolve(strict=True)
    asset.relative_to(WWW_ROOT.resolve(strict=True))
    if not asset.is_file():
        raise ResourceError("Local card asset is not a regular file")
    content = asset.read_bytes()
    versioned = versioned_url(base_path, release, content)
    _, digest = validate_versioned_asset(versioned, "module", WWW_ROOT)
    return versioned, base_path, digest


def _rollback_record(record: dict) -> dict:
    before = record.get("before")
    after = record.get("after") or {}
    api = _get_api()
    resources = asyncio.get_event_loop().run_until_complete(api.list())
    target = record["target_path"]
    current = require_unique_match(resources, target)
    if before:
        if current and current.get("id") == before.get("id"):
            if current.get("url") == before.get("url") and current.get("type", current.get("res_type")) == before.get("type"):
                return {"status": "already_restored", "resource": public_resource(current)}
            restored = asyncio.get_event_loop().run_until_complete(
                api.update(before["id"], before["url"], before["type"])
            )
            check = asyncio.get_event_loop().run_until_complete(api.list())
            after_restore = require_unique_match(check, target)
            if not after_restore or after_restore.get("url") != before["url"]:
                raise ResourceError("Rollback readback did not match the saved preimage")
            return {"status": "restored", "resource": public_resource(restored)}
        if current:
            raise ResourceError("Rollback refused: target now belongs to another resource")
        restored = asyncio.get_event_loop().run_until_complete(
            api.create(before["url"], before["type"])
        )
        check = asyncio.get_event_loop().run_until_complete(api.list())
        after_restore = require_unique_match(check, target)
        if not after_restore or after_restore.get("url") != before["url"]:
            raise ResourceError("Rollback create readback did not match the saved preimage")
        return {"status": "restored", "resource": public_resource(restored)}
    if current:
        if current.get("url") != after.get("url") or current.get("type", current.get("res_type")) != after.get("type"):
            raise ResourceError("Rollback refused: created resource changed after the backup")
        asyncio.get_event_loop().run_until_complete(api.delete(current["id"]))
    return {"status": "created_resource_removed" if current else "already_absent", "target_path": target}


@mcp.tool(name="ha_config_list_dashboard_resources")
async def ha_config_list_dashboard_resources() -> dict:
    """List registered resources. Sensitive query values are redacted from output."""
    async with _operation_lock:
        resources = await _get_api().list()
    return {"count": len(resources), "resources": [public_resource(item) for item in resources]}


@mcp.tool(name="ha_config_set_dashboard_resource")
async def ha_config_set_dashboard_resource(
    url: str,
    resource_type: str = "module",
    release: str | None = None,
    resource_id: str | None = None,
    dry_run: bool = True,
) -> dict:
    """Hash-version and idempotently create/update a validated local resource."""
    if resource_type not in RESOURCE_TYPES:
        raise ResourceError("Unsupported resource type")
    versioned, target_path, digest = _version_url(url, release)
    validate_versioned_asset(versioned, resource_type, WWW_ROOT)
    async with _operation_lock:
        api = _get_api()
        resources = await api.list()
        existing = require_unique_match(resources, target_path)
        if resource_id and (not existing or existing.get("id") != resource_id):
            raise ResourceError("resource_id does not identify the unique resource at this path")
        if existing and existing.get("url") == versioned and existing.get("type", existing.get("res_type")) == resource_type:
            return {"status": "unchanged", "resource": public_resource(existing), "sha256": digest}
        operation = "update" if existing else "create"
        preview = {"url": versioned, "type": resource_type, "id": existing.get("id") if existing else None}
        if dry_run:
            return {"status": "dry_run", "operation": operation, "before": public_resource(existing) if existing else None, "after": preview, "sha256": digest}
        backup = create_backup(BACKUP_DIR, operation, target_path, existing, preview)
        try:
            changed = await (api.update(existing["id"], versioned, resource_type) if existing else api.create(versioned, resource_type))
            readback = await api.list()
            confirmed = require_unique_match(readback, target_path)
            if not confirmed or confirmed.get("url") != versioned or confirmed.get("type", confirmed.get("res_type")) != resource_type:
                raise ResourceError("Resource registry readback differs from the requested URL/type")
            update_backup_after(backup, confirmed)
            return {"status": operation + "d", "resource": public_resource(confirmed), "sha256": digest, "backup_id": backup.stem}
        except Exception as err:
            record = json.loads(backup.read_text(encoding="utf-8"))
            if operation == "create":
                created = changed if "changed" in locals() and isinstance(changed, dict) else {}
                update_backup_after(backup, {**record["after"], "id": created.get("id")})
            try:
                result = await asyncio.to_thread(_rollback_sync, record)
            except Exception:
                raise ResourceError("Resource write failed; automatic rollback could not be verified. Use the recorded backup_id.") from None
            raise ResourceError(f"Resource write failed and was rolled back ({result.get('status')}); no token or URL details logged") from None


def _rollback_sync(record: dict) -> dict:
    """Bridge the sync compensation routine to a dedicated fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return _rollback_record(record)
    finally:
        loop.close()


@mcp.tool(name="ha_config_delete_dashboard_resource")
async def ha_config_delete_dashboard_resource(resource_id: str, dry_run: bool = True) -> dict:
    """Delete one unique non-HACS /local resource after a private backup."""
    async with _operation_lock:
        api = _get_api()
        resources = await api.list()
        target = next((item for item in resources if item.get("id") == resource_id), None)
        if not target:
            raise ResourceError("Resource ID was not found")
        target_path = canonical_local_path(str(target.get("url", "")))
        unique = require_unique_match(resources, target_path)
        if unique is None or unique.get("id") != resource_id:
            raise ResourceError("Resource is not the unique matching resource at its path")
        if dry_run:
            return {"status": "dry_run", "resource": public_resource(target)}
        backup = create_backup(BACKUP_DIR, "delete", target_path, target, {})
        try:
            await api.delete(resource_id)
            readback = await api.list()
            remaining = require_unique_match(readback, target_path)
            if remaining is not None:
                raise ResourceError("Delete readback still contains the target resource")
        except Exception:
            try:
                record = json.loads(backup.read_text(encoding="utf-8"))
                result = await asyncio.to_thread(_rollback_sync, record)
            except Exception:
                raise ResourceError(f"Delete readback failed; restore from backup_id {backup.stem}") from None
            raise ResourceError(f"Delete failed and was rolled back ({result.get('status')}); backup_id {backup.stem}") from None
        return {"status": "deleted", "backup_id": backup.stem, "target_path": target_path}


def require_matches(resources: list[dict], target_path: str) -> list[dict]:
    from .core import matching_resources
    return matching_resources(resources, target_path)


@mcp.tool(name="ha_config_rollback_dashboard_resource")
async def ha_config_rollback_dashboard_resource(backup_id: str, dry_run: bool = True) -> dict:
    """Restore a targeted resource preimage from its private backup."""
    if not BACKUP_ID_RE.fullmatch(backup_id):
        raise ResourceError("Invalid backup_id")
    path = BACKUP_DIR / f"{backup_id}.json"
    if not path.is_file():
        raise ResourceError("Resource backup was not found")
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("backup_id") != backup_id or record.get("schema") != 1:
        raise ResourceError("Resource backup metadata is invalid")
    if dry_run:
        return {"status": "dry_run", "target_path": record["target_path"], "before": record.get("before"), "after": record.get("after")}
    async with _operation_lock:
        result = await asyncio.to_thread(_rollback_sync, record)
    return result


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
