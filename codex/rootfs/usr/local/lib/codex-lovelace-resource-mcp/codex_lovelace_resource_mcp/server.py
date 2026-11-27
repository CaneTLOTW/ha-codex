"""Least-privilege stdio MCP server for Lovelace resource deployment."""

from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from mcp.server.fastmcp import FastMCP

from .api import HomeAssistantWebSocket, ResourceAPI
from .core import (
    RESOURCE_TYPES,
    ResourceError,
    BACKUP_ID_RE,
    asset_digest,
    create_backup,
    private_directory,
    public_resource,
    read_backup,
    read_private_file,
    require_unique_match,
    resource_snapshot,
    strict_local_path,
    update_backup_after,
    validate_versioned_asset,
    versioned_url_from_digest,
)

mcp = FastMCP("HA Lovelace Resource Manager")
_operation_lock = asyncio.Lock()
_api: ResourceAPI | None = None
WWW_ROOT = Path("/homeassistant/www")
BACKUP_DIR = Path("/data/codex-managed/lovelace-resource-backups")
TOKEN_FILE = Path("/tmp/codex/ha-token")


def _get_api() -> ResourceAPI:
    global _api
    if _api is None:
        try:
            with private_directory(TOKEN_FILE.parent) as fd:
                token = read_private_file(fd, TOKEN_FILE.name)
        except (OSError, ValueError):
            raise ResourceError("The private Supervisor credential is unavailable") from None
        _api = ResourceAPI(HomeAssistantWebSocket(base_url="http://supervisor/core", token=token))
    return _api


def _version_url(url: str, release: str | None, resource_type: str) -> tuple[str, str, str]:
    base_path = strict_local_path(url)
    query = urlsplit(url).query
    if query:
        _, digest = validate_versioned_asset(url, resource_type, WWW_ROOT)
        value = parse_qs(query)["v"][0]
        if release and not value.startswith(f"{release}-"):
            raise ResourceError("The URL release label does not match the requested release")
        return url, base_path, digest
    if not release:
        raise ResourceError("Supply release when URL has no version query")
    digest = asset_digest(WWW_ROOT, base_path)
    return versioned_url_from_digest(base_path, release, digest), base_path, digest


async def _current_resource(api: ResourceAPI, target: str, expected_id: str | None) -> dict | None:
    resources = await api.list()
    current = require_unique_match(resources, target)
    if expected_id is not None and any(
        row.get("id") == expected_id and row != current for row in resources
    ):
        raise ResourceError("Resource ID moved to another path; no rollback performed")
    return resource_snapshot(current) if current is not None else None


async def _rollback_record(record: dict) -> dict:
    # Every caller loads the schema-validated record from the private store.
    action, target = record["action"], record["target_path"]
    before, after = record["before"], record["after"]
    matched_id = (before or after)["id"]
    api = _get_api()
    current = await _current_resource(api, target, matched_id)
    if current is None and action == "create":
        return {"status": "already_absent", "target_path": target}
    if current is not None and current == before:
        return {"status": "already_restored", "resource": public_resource(current)}

    if action == "create":
        if matched_id is None or current != after:
            raise ResourceError("Rollback refused: cannot verify ownership of the created resource")
        asset_digest(WWW_ROOT, target)
        if await _current_resource(api, target, matched_id) != after:
            raise ResourceError("Rollback refused: created resource changed during verification")
        await api.delete(matched_id)
        if await _current_resource(api, target, matched_id) is not None:
            raise ResourceError("Rollback deletion could not be verified")
        return {"status": "created_resource_removed", "target_path": target}

    if action == "update":
        if current != after:
            raise ResourceError("Rollback refused: resource changed after the backup")
        asset_digest(WWW_ROOT, target)
        if await _current_resource(api, target, matched_id) != after:
            raise ResourceError("Rollback refused: resource changed during verification")
        await api.update(matched_id, before["url"], before["type"])
        expected = before
    else:
        if current is not None:
            if all(current[key] == before[key] for key in ("url", "type")):
                return {"status": "already_restored", "resource": public_resource(current)}
            raise ResourceError("Rollback refused: the deleted resource path was reused")
        asset_digest(WWW_ROOT, target)
        if await _current_resource(api, target, matched_id) is not None:
            raise ResourceError("Rollback refused: the deleted resource path was reused")
        restored = await api.create(before["url"], before["type"])
        expected = {**before, "id": restored["id"]}

    verified = await _current_resource(api, target, expected["id"])
    if verified != expected:
        raise ResourceError("Rollback readback did not match the saved preimage")
    return {"status": "restored", "resource": public_resource(verified)}


async def _failed_write(backup: Path) -> None:
    try:
        result = await _rollback_record(read_backup(backup))
    except Exception:
        raise ResourceError(
            f"Resource write failed and automatic rollback could not be verified. backup_id: {backup.stem}"
        ) from None
    raise ResourceError(
        f"Resource write failed. Verified recovery: {result['status']}. backup_id: {backup.stem}"
    ) from None


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
    versioned, target_path, digest = _version_url(url, release, resource_type)
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
        expected = resource_snapshot(existing) if existing is not None else None
        if await _current_resource(api, target_path, preview["id"]) != expected:
            raise ResourceError(f"Resource changed before the write. backup_id: {backup.stem}")
        try:
            if existing:
                await api.update(preview["id"], versioned, resource_type)
            else:
                changed = await api.create(versioned, resource_type)
                preview["id"] = changed["id"]
                update_backup_after(backup, preview)
            confirmed = await _current_resource(api, target_path, preview["id"])
            if confirmed != preview:
                raise ResourceError("Resource registry readback differs from the written ID, URL, or type")
            return {"status": operation + "d", "resource": public_resource(confirmed), "sha256": digest, "backup_id": backup.stem}
        except Exception:
            await _failed_write(backup)


@mcp.tool(name="ha_config_delete_dashboard_resource")
async def ha_config_delete_dashboard_resource(resource_id: str, dry_run: bool = True) -> dict:
    """Delete one unique non-HACS /local resource after a private backup."""
    async with _operation_lock:
        api = _get_api()
        resources = await api.list()
        target = next((item for item in resources if item.get("id") == resource_id), None)
        if not target:
            raise ResourceError("Resource ID was not found")
        target_path = strict_local_path(str(target.get("url", "")))
        asset_digest(WWW_ROOT, target_path)
        unique = require_unique_match(resources, target_path)
        if unique is None or unique.get("id") != resource_id:
            raise ResourceError("Resource is not the unique matching resource at its path")
        if dry_run:
            return {"status": "dry_run", "resource": public_resource(target)}
        backup = create_backup(BACKUP_DIR, "delete", target_path, target, None)
        if await _current_resource(api, target_path, resource_id) != resource_snapshot(target):
            raise ResourceError(f"Resource changed before deletion. backup_id: {backup.stem}")
        try:
            await api.delete(resource_id)
            if await _current_resource(api, target_path, resource_id) is not None:
                raise ResourceError("Delete readback still contains the target resource")
        except Exception:
            await _failed_write(backup)
        return {"status": "deleted", "backup_id": backup.stem, "target_path": target_path}


@mcp.tool(name="ha_config_rollback_dashboard_resource")
async def ha_config_rollback_dashboard_resource(backup_id: str, dry_run: bool = True) -> dict:
    """Restore a targeted resource preimage from its private backup."""
    if not BACKUP_ID_RE.fullmatch(backup_id):
        raise ResourceError("Invalid backup_id")
    async with _operation_lock:
        record = read_backup(BACKUP_DIR / f"{backup_id}.json")
        if dry_run:
            return {"status": "dry_run", "target_path": record["target_path"], "before": record["before"], "after": record["after"]}
        return await _rollback_record(record)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
