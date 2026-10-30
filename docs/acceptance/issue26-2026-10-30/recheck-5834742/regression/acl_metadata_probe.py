#!/usr/bin/env python3
"""Disposable machine-readable ACL preservation probe; never targets HA data."""
import json
import os
import pathlib
import stat
import subprocess
import tempfile

helper = pathlib.Path(__file__).resolve().parents[5] / "codex/rootfs/usr/local/bin/codex-grant-access"
root = pathlib.Path(tempfile.mkdtemp(prefix="issue26-acl-metadata-"))
ws = root / "workspace"
ws.mkdir()
ssh = ws / ".ssh"
ssh.mkdir(mode=0o700)
key = ssh / "id_ed25519"
key.write_text("fixture only")
key.chmod(0o600)
nested = ssh / "nested"
nested.mkdir()
(nested / "inside.txt").write_text("fixture only")
private = ws / "private0600"
private.write_text("fixture only")
private.chmod(0o600)
outside_key = ws / "outside.key"
outside_key.write_text("fixture only")
outside_key.chmod(0o644)
normal = ws / "normal.yaml"
normal.write_text("fixture only")
executable = ws / "run.sh"
executable.write_text("#!/bin/sh\nexit 0\n")
executable.chmod(0o755)
link = ws / "linkedssh"
link.symlink_to(ssh, target_is_directory=True)

def acl(path):
    return subprocess.check_output(["getfacl", "-cp", str(path)], text=True).strip()

def snapshot():
    paths = [ws, ssh, nested, key, nested / "inside.txt", private,
             outside_key, normal, executable]
    result = {}
    for path in paths:
        info = path.stat()
        result[str(path.relative_to(root))] = {
            "mode": f"{stat.S_IMODE(info.st_mode):04o}",
            "uid": info.st_uid,
            "gid": info.st_gid,
            "acl": acl(path),
        }
    result[str(link.relative_to(root))] = {
        "is_symlink": link.is_symlink(),
        "target": os.readlink(link),
        "lstat_mode": f"{stat.S_IMODE(link.lstat().st_mode):04o}",
    }
    return result

# Set a nontrivial ACL on the protected key to verify exact preservation.
subprocess.run(["setfacl", "-m", "g:root:r--", str(key)], check=True)
before = snapshot()
records = {"uid": os.getuid(), "before": before, "runs": []}
for run in (1, 2):
    proc = subprocess.run(["bash", str(helper), str(ws)], capture_output=True, text=True)
    after = snapshot()
    assert proc.returncode == 0, proc.stderr
    for rel in ("workspace/.ssh", "workspace/.ssh/nested", "workspace/.ssh/id_ed25519",
                "workspace/.ssh/nested/inside.txt", "workspace/private0600",
                "workspace/outside.key"):
        assert after[rel] == before[rel], (rel, before[rel], after[rel])
    assert "default:" not in after["workspace"]["acl"]
    assert "default:" not in after["workspace/.ssh"]["acl"]
    assert "group:root:rw-" in after["workspace/normal.yaml"]["acl"]
    assert "group:root:rwx" in after["workspace/run.sh"]["acl"]
    assert stat.S_IMODE(normal.stat().st_mode) & 0o200
    assert stat.S_IMODE(executable.stat().st_mode) & 0o100
    records["runs"].append({"run": run, "returncode": proc.returncode,
                            "stderr": proc.stderr, "after": after})
with open(pathlib.Path(__file__).with_name("acl_metadata_before_after.json"), "w") as out:
    json.dump(records, out, indent=2, sort_keys=True)
    out.write("\n")
print(json.dumps({"result": "PASS", "uid": os.getuid(), "runs": 2,
                  "protected_paths_unchanged": True,
                  "preexisting_protected_acl_preserved": True,
                  "default_acls_absent": True,
                  "normal_yaml_group_acl": "rw-",
                  "executable_group_acl": "rwx",
                  "evidence": "acl_metadata_before_after.json"}, sort_keys=True))
