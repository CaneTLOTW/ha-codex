#!/usr/bin/env python3
"""Exercise genuine setfacl failure and helper chmod fallback on temp fixtures."""
import json
import os
import pathlib
import stat
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[5]
HELPER = ROOT / "codex/rootfs/usr/local/bin/codex-grant-access"
INVALID_GROUP = "__issue26_nonexistent_group__"

if subprocess.run(["getent", "group", INVALID_GROUP], capture_output=True).returncode == 0:
    raise SystemExit(f"refusing to run: injected group already exists: {INVALID_GROUP}")

tmp = pathlib.Path(tempfile.mkdtemp(prefix="issue26-real-setfacl-failure-"))
workspace = tmp / "workspace"
workspace.mkdir()
ssh = workspace / ".ssh"
ssh.mkdir(mode=0o700)
key = ssh / "id_ed25519"
key.write_text("fixture only")
key.chmod(0o600)
nested = ssh / "nested"
nested.mkdir()
(nested / "inside.txt").write_text("fixture only")
private = workspace / "private0600"
private.write_text("fixture only")
private.chmod(0o600)
outside_key = workspace / "outside.key"
outside_key.write_text("fixture only")
outside_key.chmod(0o644)
normal = workspace / "normal.yaml"
normal.write_text("fixture only")
normal.chmod(0o644)
executable = workspace / "run.sh"
executable.write_text("#!/bin/sh\nexit 0\n")
executable.chmod(0o755)
link = workspace / "linkedssh"
link.symlink_to(ssh, target_is_directory=True)

def contained(path):
    resolved = pathlib.Path(path).resolve()
    assert resolved == tmp or tmp in resolved.parents, (resolved, tmp)

def acl(path):
    return subprocess.check_output(["getfacl", "-cp", str(path)], text=True).strip()

def snapshot(path):
    contained(path)
    info = pathlib.Path(path).stat()
    return {"mode": f"{stat.S_IMODE(info.st_mode):04o}", "uid": info.st_uid,
            "gid": info.st_gid, "acl": acl(path)}

# Deliberate preexisting protected ACL: preservation is checked byte-for-byte.
subprocess.run(["setfacl", "-m", "g:root:---", str(key)], check=True)
protected = [ssh, nested, key, nested / "inside.txt", private, outside_key]
protected_before = {str(p.relative_to(tmp)): snapshot(p) for p in protected}
link_before = {"is_symlink": link.is_symlink(), "target": os.readlink(link),
               "lstat_mode": f"{stat.S_IMODE(link.lstat().st_mode):04o}"}

# find() delegates to the real GNU find. Only ACL group operands after a
# -exec setfacl are replaced, causing genuine setfacl invocations to fail.
# Exporting this function injects it into the helper's child Bash process; the
# unchanged helper runs as a script, with its normal set -e behavior.
shell = r'''function find() {
  local -a argv=("$@")
  local i injected=0
  for ((i=0; i<${#argv[@]}; i++)); do
    if [[ "${argv[i]}" == setfacl ]]; then
      for ((j=i+1; j<${#argv[@]}; j++)); do
        case "${argv[j]}" in
          g:root:rwx) argv[j]="g:__issue26_nonexistent_group__:rwx"; injected=$((injected+1)); break ;;
          g:root:rw-) argv[j]="g:__issue26_nonexistent_group__:rw-"; injected=$((injected+1)); break ;;
        esac
      done
    fi
  done
  if ((injected > 0)); then
    printf 'INJECTED_REAL_FIND acl_operands=%d\n' "$injected" >&2
  fi
  if command find "${argv[@]}"; then rc=0; else rc=$?; fi
  if ((injected > 0)); then
    printf 'REAL_GNU_FIND_ACL_RC=%d\n' "$rc" >&2
  else
    for arg in "${argv[@]}"; do
      if [[ "$arg" == chmod ]]; then
        printf 'REAL_GNU_FIND_CHMOD_RC=%d\n' "$rc" >&2
        break
      fi
    done
  fi
  return "$rc"
}
command -v setfacl >/dev/null 2>&1 || exit 98
export -f find
bash -x "$1" "$2"
'''

evidence = {"result": "PASS", "uid": os.getuid(), "fixture_root": str(tmp),
            "helper": str(HELPER), "helper_execution": "child bash script; exported find function",
            "find": "real GNU find via builtin command; scoped arguments only",
            "setfacl": subprocess.check_output(
                ["bash", "-c", "command -v setfacl"], text=True).strip(),
            "injected_group_absent": True, "injected_group": INVALID_GROUP,
            "injection": "find function changes only g:root:rwx/rw- operands following -exec setfacl",
            "protected_before": protected_before, "symlink_before": link_before,
            "runs": []}

for run in (1, 2):
    # Source helper against the explicitly asserted temporary workspace target.
    proc = subprocess.run(["bash", "-c", shell, "issue26-real-failure",
                           str(HELPER), str(workspace)], capture_output=True, text=True)
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    assert "INJECTED_REAL_FIND" in proc.stderr, proc.stderr
    assert "REAL_GNU_FIND_ACL_RC=1" in proc.stderr, proc.stderr
    assert "REAL_GNU_FIND_CHMOD_RC=0" in proc.stderr, proc.stderr
    assert proc.stderr.count("setfacl: Option -m: Invalid argument") == 3, proc.stderr
    assert INVALID_GROUP in proc.stderr or "Invalid argument" in proc.stderr, proc.stderr
    assert "falling back to filtered chmod" in proc.stderr, proc.stderr
    after = {str(p.relative_to(tmp)): snapshot(p) for p in protected}
    assert after == protected_before, (protected_before, after)
    assert stat.S_IMODE(key.stat().st_mode) == 0o600
    assert {"is_symlink": link.is_symlink(), "target": os.readlink(link),
            "lstat_mode": f"{stat.S_IMODE(link.lstat().st_mode):04o}"} == link_before
    assert stat.S_IMODE(normal.stat().st_mode) == 0o664
    assert stat.S_IMODE(executable.stat().st_mode) == 0o775
    assert os.access(normal, os.W_OK)
    assert os.access(executable, os.X_OK)
    for p in [workspace, ssh, nested, key, private, outside_key, normal, executable]:
        assert "default:" not in acl(p), (p, acl(p))
    evidence["runs"].append({
        "run": run, "helper_returncode": proc.returncode,
        "setfacl_failure_observed": True,
        "setfacl_failed_batches": 3,
        "gnu_find_acl_returncode": 1,
        "gnu_find_chmod_returncode": 0,
        "stderr": proc.stderr,
        "protected_after": after,
        "normal_yaml": snapshot(normal), "executable": snapshot(executable),
        "ssh_mode": f"{stat.S_IMODE(ssh.stat().st_mode):04o}",
        "key_mode": f"{stat.S_IMODE(key.stat().st_mode):04o}",
        "private_mode": f"{stat.S_IMODE(private.stat().st_mode):04o}",
        "writable": os.access(normal, os.W_OK),
        "executable": {"metadata": snapshot(executable),
                       "runnable_permission": os.access(executable, os.X_OK)},
    })

(HERE / "real_setfacl_failure_before_after.json").write_text(
    json.dumps(evidence, indent=2, sort_keys=True) + "\n")
print(json.dumps({"result": "PASS", "runs": 2, "helper_fallback": "real chmod",
                  "real_setfacl_invoked_and_failed": True,
                  "protected_metadata_unchanged": True,
                  "normal_yaml": "0644 -> 0664, writable",
                  "executable": "0755 -> 0775, executable",
                  "default_acls": "absent",
                  "evidence": "real_setfacl_failure_before_after.json"}, sort_keys=True))
