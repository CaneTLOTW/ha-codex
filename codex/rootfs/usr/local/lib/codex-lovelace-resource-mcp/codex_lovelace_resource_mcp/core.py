"""Safe URL, backup, upsert and rollback rules for Lovelace resources."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from uuid import uuid4

RESOURCE_TYPES = {"module", "js", "css", "html"}
VERSION_RE = re.compile(r"^(.+)-([0-9a-f]{12,64})$")
SENSITIVE_QUERY_RE = re.compile(r"token|secret|password|auth|signature|credential|key", re.I)
BACKUP_ID_RE = re.compile(r"[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}")
RESOURCE_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,128}")
LOCAL_PATH_RE = re.compile(r"/local/(?:[A-Za-z0-9._~-]+/)*[A-Za-z0-9._~-]+")
DIR_FLAGS = os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW
READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
MAX_BACKUP_BYTES = 16384


class ResourceError(ValueError):
    """An unsafe or ambiguous resource operation."""


def safe_url(url: str) -> str:
    """Redact query values that might contain credentials before returning data."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return "[invalid URL]"
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
    try:
        parts = urlsplit(url)
    except ValueError:
        raise ResourceError("Resource URL is invalid") from None
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
    path = strict_local_path(url)
    query = parse_qs(urlsplit(url).query, keep_blank_values=True)
    if set(query) != {"v"} or len(query["v"]) != 1:
        raise ResourceError("Versioned resources must have exactly one ?v=<release>-<sha256-prefix>")
    match = VERSION_RE.fullmatch(query["v"][0])
    if not match:
        raise ResourceError("Resource version must end in a 12-64 character lowercase SHA-256 prefix")
    digest = asset_digest(www_root, path)
    if not digest.startswith(match.group(2)):
        raise ResourceError("URL SHA-256 prefix does not match the local asset")
    return path, digest


def strict_local_path(url: str) -> str:
    path = canonical_local_path(url)
    if url.split("?", 1)[0] != path or not LOCAL_PATH_RE.fullmatch(path):
        raise ResourceError("Resource URL must use a canonical /local/ path")
    return path


def asset_digest(www_root: Path, path: str) -> str:
    """Open each path component without following links in the editable mount."""
    if strict_local_path(path) != path:
        raise ResourceError("Expected a canonical asset path")
    candidate = www_root / path.removeprefix("/local/")
    try:
        with open_directory(candidate.parent) as parent_fd:
            fd = os.open(candidate.name, READ_FLAGS, dir_fd=parent_fd)
            with os.fdopen(fd, "rb") as asset:
                info = os.fstat(asset.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise ResourceError("Local card asset must be a regular, unlinked file")
                return hashlib.file_digest(asset, "sha256").hexdigest()
    except OSError:
        raise ResourceError("Local card asset is unavailable or uses a symlink") from None


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


@contextmanager
def open_directory(path: Path, *, trusted: bool = False, create: bool = False):
    """Walk with directory descriptors so path swaps cannot redirect an open."""
    if path.anchor != "/" or ".." in path.parts:
        raise ResourceError("Expected an absolute directory without traversal")
    fd = os.open("/", DIR_FLAGS)
    try:
        if trusted:
            _check_directory(fd)
        for index, name in enumerate(path.parts[1:], start=1):
            if create and index == len(path.parts) - 1:
                try:
                    os.mkdir(name, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            child = os.open(name, DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = child
            if trusted:
                _check_directory(fd)
        yield fd
    finally:
        os.close(fd)


def _check_directory(fd: int) -> None:
    info = os.fstat(fd)
    writable = info.st_mode & 0o022
    # A root-owned sticky directory (such as /tmp) prevents users from
    # replacing the next component, whose ownership is also checked.
    sticky_root = info.st_uid == 0 and info.st_mode & stat.S_ISVTX
    if info.st_uid not in {0, os.geteuid()} or (writable and not sticky_root):
        raise ResourceError("Private path has untrusted directory ancestry")


@contextmanager
def private_directory(path: Path, *, create: bool = False):
    with open_directory(path, trusted=True, create=create) as fd:
        info = os.fstat(fd)
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise ResourceError("Private directory must belong to the helper with mode 0700")
        yield fd


def read_private_file(directory_fd: int, name: str) -> str:
    fd = os.open(name, READ_FLAGS, dir_fd=directory_fd)
    with os.fdopen(fd, "r", encoding="utf-8") as handle:
        info = os.fstat(handle.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_size > MAX_BACKUP_BYTES):
            raise ResourceError("Private file ownership, mode, type, or size is invalid")
        return handle.read(MAX_BACKUP_BYTES)


def resource_snapshot(resource: dict) -> dict:
    return {
        "id": resource.get("id"), "url": resource.get("url"),
        "type": resource.get("type", resource.get("res_type")),
    }


def _validate_snapshot(item: dict, target: str, *, allow_pending_id: bool = False) -> None:
    if not isinstance(item, dict) or set(item) != {"id", "url", "type"}:
        raise ResourceError("Resource backup snapshot fields are invalid")
    resource_id = item["id"]
    if not (resource_id is None and allow_pending_id) and (
        not isinstance(resource_id, str) or not RESOURCE_ID_RE.fullmatch(resource_id)
    ):
        raise ResourceError("Resource backup contains an invalid resource ID")
    if not isinstance(item["type"], str) or item["type"] not in RESOURCE_TYPES:
        raise ResourceError("Resource backup contains an unsupported resource type")
    url = item["url"]
    if not isinstance(url, str) or len(url) > 1024 or strict_local_path(url) != target:
        raise ResourceError("Resource backup URL does not match the protected local target")
    query = urlsplit(url).query
    if "?" in url and not re.fullmatch(r"v=[0-9A-Za-z](?:[0-9A-Za-z._+-]|%2B)*", query):
        raise ResourceError("Resource backup URL has an unsupported or sensitive query")


def validate_backup(record: dict, backup_id: str) -> None:
    if (not BACKUP_ID_RE.fullmatch(backup_id) or not isinstance(record, dict)
            or set(record) != {"schema", "backup_id", "created_at", "action", "target_path", "before", "after", "acknowledged"}
            or type(record["schema"]) is not int or record["schema"] != 2
            or type(record["acknowledged"]) is not bool
            or record["backup_id"] != backup_id or not isinstance(record["created_at"], str)):
        raise ResourceError("Resource backup metadata is invalid")
    action, target, before, after = (record[key] for key in ("action", "target_path", "before", "after"))
    if (action not in ("create", "update", "delete") or not isinstance(target, str)
            or strict_local_path(target) != target):
        raise ResourceError("Resource backup operation or target is invalid")
    if action == "create":
        if before is not None:
            raise ResourceError("Create backup must not have a preimage")
    else:
        _validate_snapshot(before, target)
    if action == "delete":
        if after is not None:
            raise ResourceError("Delete backup must not have a postimage")
    else:
        pending_create = action == "create" and not record["acknowledged"]
        _validate_snapshot(after, target, allow_pending_id=pending_create)
        if pending_create and after["id"] is not None:
            raise ResourceError("Unacknowledged create must not have a resource ID")
        if action == "update" and before["id"] != after["id"]:
            raise ResourceError("Update backup must keep the resource ID")


def read_backup(path: Path) -> dict:
    if path.name != f"{path.stem}.json" or not BACKUP_ID_RE.fullmatch(path.stem):
        raise ResourceError("Invalid backup_id")
    try:
        with private_directory(path.parent) as fd:
            record = json.loads(read_private_file(fd, path.name))
        validate_backup(record, path.stem)
        return record
    except (ValueError, OSError, RecursionError) as error:
        if isinstance(error, ResourceError):
            raise
        raise ResourceError("Resource backup is absent, unreadable, or invalid") from None


def _write_json_private(path: Path, data: dict) -> None:
    validate_backup(data, path.stem)
    try:
        with private_directory(path.parent, create=True) as directory_fd:
            name = f".backup-{uuid4().hex}"
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, ensure_ascii=False, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(name, path.name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
                sync_fd = os.open(".", os.O_RDONLY | os.O_DIRECTORY, dir_fd=directory_fd)
                try:
                    os.fsync(sync_fd)
                finally:
                    os.close(sync_fd)
            finally:
                try:
                    os.unlink(name, dir_fd=directory_fd)
                except FileNotFoundError:
                    pass
    except OSError:
        raise ResourceError("Cannot write the private resource backup") from None


def create_backup(backup_dir: Path, action: str, target_path: str, before: dict | None, after: dict | None) -> Path:
    """Persist only the targeted resource preimage and intended postimage."""
    backup_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:12]}"
    path = backup_dir / f"{backup_id}.json"
    _write_json_private(
        path,
        {
            "schema": 2,
            "backup_id": backup_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "target_path": target_path,
            "before": resource_snapshot(before) if before is not None else None,
            "after": resource_snapshot(after) if after is not None else None,
            "acknowledged": False,
        },
    )
    return path


def acknowledge_backup(path: Path, *, created_id: str | None = None) -> None:
    """Persist a successful response from HA before offering writable rollback."""
    data = read_backup(path)
    if (data["action"] == "create") != (created_id is not None):
        raise ResourceError("An acknowledged create requires the ID returned by Home Assistant")
    if created_id is not None:
        data["after"]["id"] = created_id
    data["acknowledged"] = True
    _write_json_private(path, data)


def versioned_url(path: str, release: str, content: bytes) -> str:
    """Build a stable version query from release label and actual asset bytes."""
    return versioned_url_from_digest(path, release, hashlib.sha256(content).hexdigest())


def versioned_url_from_digest(path: str, release: str, digest: str) -> str:
    if not release or not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._+-]{0,100}", release):
        raise ResourceError("Invalid release label")
    return f"{strict_local_path(path)}?v={release.replace('+', '%2B')}-{digest[:12]}"
