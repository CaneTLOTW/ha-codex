"""Least-privilege stdio MCP server for Lovelace resource deployment."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from secrets import compare_digest, token_urlsafe
from time import monotonic
from urllib.parse import parse_qs, urlsplit

from mcp.server.fastmcp import FastMCP

from .api import HomeAssistantWebSocket, ResourceAPI
from .core import (
    BACKUP_ID_RE,
    RESOURCE_TYPES,
    ResourceError,
    acknowledge_backup,
    asset_digest,
    create_backup,
    private_directory,
    public_resource,
    read_backup,
    read_private_file,
    require_unique_match,
    resource_snapshot,
    strict_local_path,
    validate_versioned_asset,
    versioned_url_from_digest,
)

mcp = FastMCP("HA Lovelace Resource Manager")
_operation_lock = asyncio.Lock()
_api: ResourceAPI | None = None
WWW_ROOT = Path("/homeassistant/www")
BACKUP_DIR = Path("/data/codex-managed/lovelace-resource-backups")
TOKEN_FILE = Path("/tmp/codex/ha-token")
CONFIRMATION_TTL_SECONDS = 120


@dataclass(frozen=True)
class RollbackPlan:
    operation: str
    target: str
    expected_id: str | None
    current: dict | None
    restore: dict | None
    asset_sha256: str | None = None


@dataclass(frozen=True)
class PendingRollback:
    backup_id: str
    confirmation: str
    expires_at: float
    plan: RollbackPlan


_pending_rollback: PendingRollback | None = None


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
        raise ResourceError("Resource ID moved to another path")
    return resource_snapshot(current) if current is not None else None


async def _rollback_plan(api: ResourceAPI, record: dict) -> RollbackPlan:
    action, target = record["action"], record["target_path"]
    before, after = record["before"], record["after"]
    expected_id = (before or after)["id"]
    current = await _current_resource(api, target, expected_id)
    if current is None and action == "create":
        return RollbackPlan("already_absent", target, expected_id, current, before)
    if current is not None and current == before:
        return RollbackPlan("already_restored", target, expected_id, current, before)
    if not record["acknowledged"]:
        return RollbackPlan("manual_review_required", target, expected_id, current, before)

    if action == "create":
        if current != after:
            raise ResourceError("Rollback refused: created resource changed after the backup")
        operation = "delete"
    elif action == "update":
        if current != after:
            raise ResourceError("Rollback refused: resource changed after the backup")
        operation = "update"
    else:
        if current is not None:
            if all(current[key] == before[key] for key in ("url", "type")):
                return RollbackPlan("already_restored", target, expected_id, current, before)
            raise ResourceError("Rollback refused: the deleted resource path was reused")
        operation = "create"
    return RollbackPlan(operation, target, expected_id, current, before, asset_digest(WWW_ROOT, target))


async def _apply_rollback(api: ResourceAPI, plan: RollbackPlan, pending: PendingRollback) -> dict:
    # HA has no conditional mutation. This final read is the last check the
    # client can make. The operator must arrange exclusive access to this target.
    if await _current_resource(api, plan.target, plan.expected_id) != plan.current:
        raise ResourceError("Rollback refused: resource changed during verification")
    if monotonic() >= pending.expires_at:
        raise ResourceError("Rollback confirmation expired. Request a fresh preview.")
    try:
        if plan.operation == "delete":
            await api.delete(plan.expected_id)
            if await _current_resource(api, plan.target, plan.expected_id) is not None:
                raise ResourceError("Rollback deletion could not be verified")
            return {"status": "created_resource_removed", "target_path": plan.target}

        expected = plan.restore
        if plan.operation == "update":
            await api.update(plan.expected_id, expected["url"], expected["type"])
        else:
            restored = await api.create(expected["url"], expected["type"])
            expected = {**expected, "id": restored["id"]}
        verified = await _current_resource(api, plan.target, expected["id"])
        if verified != expected:
            raise ResourceError("Rollback readback did not match the preimage")
        return {"status": "restored", "resource": public_resource(verified)}
    except Exception:
        raise ResourceError(
            f"Rollback outcome could not be verified. No further writes attempted. "
            f"backup_id: {pending.backup_id}. Review the registry before retrying."
        ) from None


async def _verify_preimage(api: ResourceAPI, target: str, expected: dict | None, backup: Path) -> None:
    try:
        current = await _current_resource(api, target, expected["id"] if expected else None)
    except Exception:
        raise ResourceError(f"Prewrite check failed. No write attempted. backup_id: {backup.stem}") from None
    if current != expected:
        raise ResourceError(f"Resource changed before the write. No write attempted. backup_id: {backup.stem}")


def _unverified_write(backup: Path) -> ResourceError:
    return ResourceError(
        f"Resource write outcome could not be verified. No automatic rollback attempted. "
        f"backup_id: {backup.stem}. Start with a fresh rollback preview."
    )


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
        await _verify_preimage(api, target_path, expected, backup)
        try:
            if existing:
                changed = await api.update(preview["id"], versioned, resource_type)
                created_id = None
            else:
                changed = await api.create(versioned, resource_type)
                preview["id"] = created_id = changed["id"]
            if resource_snapshot(changed) != preview:
                raise ResourceError("Home Assistant did not acknowledge the expected resource")
            acknowledge_backup(backup, created_id=created_id)
            confirmed = await _current_resource(api, target_path, preview["id"])
            if confirmed != preview:
                raise ResourceError("Resource registry readback differs from the written ID, URL, or type")
            return {"status": operation + "d", "resource": public_resource(confirmed), "sha256": digest, "backup_id": backup.stem}
        except Exception:
            raise _unverified_write(backup) from None


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
        await _verify_preimage(api, target_path, resource_snapshot(target), backup)
        try:
            await api.delete(resource_id)
            acknowledge_backup(backup)
            if await _current_resource(api, target_path, resource_id) is not None:
                raise ResourceError("Delete readback still contains the target resource")
        except Exception:
            raise _unverified_write(backup) from None
        return {"status": "deleted", "backup_id": backup.stem, "target_path": target_path}


@mcp.tool(name="ha_config_rollback_dashboard_resource")
async def ha_config_rollback_dashboard_resource(
    backup_id: str,
    dry_run: bool = True,
    non_atomic_confirmation: str | None = None,
) -> dict:
    """Preview live rollback. Apply only with operator consent and the fresh confirmation."""
    global _pending_rollback
    if not BACKUP_ID_RE.fullmatch(backup_id):
        raise ResourceError("Invalid backup_id")
    async with _operation_lock:
        record = read_backup(BACKUP_DIR / f"{backup_id}.json")
        if dry_run:
            _pending_rollback = None
            plan = await _rollback_plan(_get_api(), record)
            result = {
                "status": plan.operation,
                "backup_id": backup_id,
                "target_path": plan.target,
                "current": public_resource(plan.current) if plan.current else None,
                "restore": plan.restore,
                "original_write_acknowledged": record["acknowledged"],
            }
            if plan.operation not in {"create", "update", "delete"}:
                return result
            confirmation = token_urlsafe(24)
            _pending_rollback = PendingRollback(
                backup_id, confirmation, monotonic() + CONFIRMATION_TTL_SECONDS, plan
            )
            return {
                **result,
                "status": "dry_run",
                "operation": plan.operation,
                "asset_sha256": plan.asset_sha256,
                "non_atomic_confirmation": confirmation,
                "expires_in_seconds": CONFIRMATION_TTL_SECONDS,
                "warning": "HA writes are not atomic. Stop other writers and obtain operator approval before confirming.",
            }

        pending = _pending_rollback
        if (pending is None or pending.backup_id != backup_id
                or not isinstance(non_atomic_confirmation, str) or not non_atomic_confirmation.isascii()
                or not compare_digest(pending.confirmation, non_atomic_confirmation)):
            raise ResourceError("A fresh rollback preview and its non_atomic_confirmation are required")
        _pending_rollback = None
        if monotonic() >= pending.expires_at:
            raise ResourceError("Rollback confirmation expired. Request a fresh preview.")
        api = _get_api()
        plan = await _rollback_plan(api, record)
        if plan != pending.plan:
            raise ResourceError("Rollback target changed since the preview. Request a fresh preview.")
        return await _apply_rollback(api, plan, pending)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
