"""Safe URL, backup, upsert and rollback rules for Lovelace resources."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from uuid import uuid4

RESOURCE_TYPES = {"module", "js", "css", "html"}
VERSION_RE = re.compile(r"^(.+)-([0-9a-f]{12,64})$")
SENSITIVE_QUERY_RE = re.compile(r"token|secret|password|auth|signature|credential|key", re.I)


class ResourceError(ValueError):
    """An unsafe or ambiguous resource operation."""


def safe_url(url: str) -> str:
    """Redact query values that might contain credentials before returning data."""
    parts = urlsplit(url)
    if not parts.query:
        return url
    pairs = []
    for pair in parts.query.split("&"):
        key, sep, value = pair.partition("=")
        if SENSITIVE_QUERY_RE.search(unquote(key)):
            replacement = "[redacted]" if sep else ""
            pairs.append(f"{key}={replacement}")
        else:
            pairs.append(pair)
    return parts._replace(query="&".join(pairs)).geturl()


def canonical_local_path(url: str) -> str:
    """Validate and return a normalized /local path; reject HACS and traversal."""
    parts = urlsplit(url)
    if parts.scheme or parts.netloc or parts.fragment or not parts.path.startswith("/local/"):
        raise ResourceError("Only local /local/ resources are manageable")
    decoded = unquote(parts.path)
    if "\\" in decoded or any(segment in {".", ".."} for segment in decoded.split("/")):
        raise ResourceError("Resource path contains traversal or backslash")
    normalized = "/" + "/".join(part for part in decoded.split("/") if part)
    if normalized == "/local/community" or normalized.startswith("/local/community/"):
        raise ResourceError("HACS community resources are protected")
    if normalized == "/local" or normalized.endswith("/"):
        raise ResourceError("Resource URL must identify a file")
    return normalized


def validate_versioned_asset(url: str, resource_type: str, www_root: Path) -> tuple[str, str]:
    """Validate a release/hash URL against the actual local asset bytes."""
    if resource_type not in RESOURCE_TYPES:
        raise ResourceError("Unsupported Lovelace resource type")
    path = canonical_local_path(url)
    query = parse_qs(urlsplit(url).query, keep_blank_values=True)
    if set(query) != {"v"} or len(query["v"]) != 1:
        raise ResourceError("Versioned resources must have exactly one ?v=<release>-<sha256-prefix>")
    match = VERSION_RE.fullmatch(query["v"][0])
    if not match:
        raise ResourceError("Resource version must end in a 12-64 character lowercase SHA-256 prefix")
    root = www_root.resolve(strict=True)
    candidate = (root / path.removeprefix("/local/")).resolve(strict=True)
    try:
        candidate.relative_to(root)
    except ValueError as err:
        raise ResourceError("Resolved asset escapes the Home Assistant www directory") from err
    if not candidate.is_file():
        raise ResourceError("Versioned asset is not a regular file")
    digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
    if not digest.startswith(match.group(2)):
        raise ResourceError("URL SHA-256 prefix does not match the local asset")
    return path, digest


def matching_resources(resources: list[dict], target_path: str) -> list[dict]:
    matches = []
    for item in resources:
        url = item.get("url")
        if not isinstance(url, str):
            continue
        try:
            path = canonical_local_path(url)
        except ResourceError:
            continue
        if path == target_path:
            matches.append(item)
    return matches


def require_unique_match(resources: list[dict], target_path: str) -> dict | None:
    matches = matching_resources(resources, target_path)
    if len(matches) > 1:
        raise ResourceError(f"Duplicate Lovelace resources exist for {target_path}; no mutation performed")
    return matches[0] if matches else None


def public_resource(item: dict) -> dict:
    """Return only resource metadata, redacting potentially secret query values."""
    return {
        "id": item.get("id"),
        "url": safe_url(str(item.get("url", ""))),
        "type": item.get("type", item.get("res_type")),
    }


def _write_json_private(path: Path, data: dict) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    fd, temp_name = tempfile.mkstemp(prefix=".resource-backup-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def create_backup(backup_dir: Path, action: str, target_path: str, before: dict | None, after: dict) -> Path:
    """Persist only the targeted resource preimage and intended postimage."""
    if before and SENSITIVE_QUERY_RE.search(urlsplit(str(before.get("url", ""))).query):
        raise ResourceError("Resource has a sensitive query parameter and cannot be backed up safely")
    backup_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:12]}"
    path = backup_dir / f"{backup_id}.json"
    _write_json_private(
        path,
        {
            "schema": 1,
            "backup_id": backup_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "target_path": target_path,
            "before": public_resource(before) if before else None,
            "after": {"id": after.get("id"), "url": after.get("url"), "type": after.get("type")},
        },
    )
    return path


def update_backup_after(path: Path, resource: dict) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["after"] = {"id": resource.get("id"), "url": resource.get("url"), "type": resource.get("type")}
    _write_json_private(path, data)


def versioned_url(path: str, release: str, content: bytes) -> str:
    """Build a stable version query from release label and actual asset bytes."""
    if not release or not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._+-]*", release):
        raise ResourceError("Invalid release label")
    normalized = canonical_local_path(path)
    digest = hashlib.sha256(content).hexdigest()
    return f"{normalized}?v={release}-{digest[:12]}"
