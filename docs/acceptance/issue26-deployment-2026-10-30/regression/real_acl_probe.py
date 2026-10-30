#!/usr/bin/env python3
"""Disposable real ACL acceptance probe; never targets HA data."""
import os, pathlib, shutil, stat, subprocess, tempfile
helper=pathlib.Path('/share/ha-codex-issue26-deployment/codex/rootfs/usr/local/bin/codex-grant-access')
root=pathlib.Path(tempfile.mkdtemp(prefix='ha-codex-issue26-real-acl-'))
ws=root/'workspace'; ws.mkdir(); ssh=ws/'.ssh'; ssh.mkdir(mode=0o700)
key=ssh/'id_ed25519'; key.write_text('dummy'); key.chmod(0o600)
private=ws/'private0600'; private.write_text('dummy'); private.chmod(0o600)
outside=ws/'outside.key'; outside.write_text('dummy'); outside.chmod(0o644)
normal=ws/'normal.yaml'; normal.write_text('dummy')
script=ws/'executable.sh'; script.write_text('#!/bin/sh\nexit 0\n'); script.chmod(0o755)
nested=ssh/'nested'; nested.mkdir(); nested_file=nested/'inside.txt'; nested_file.write_text('dummy')
link=ws/'linkedssh'; link.symlink_to(ssh,target_is_directory=True)
def acl(path): return subprocess.check_output(['getfacl','-cp',str(path)],text=True)
outside_before=(stat.S_IMODE(outside.stat().st_mode),acl(outside))
def assert_no_acl(path):
    a=acl(path); assert 'default:' not in a and 'group:root:' not in a,(path,a)
for run in (1,2):
    r=subprocess.run(['bash',str(helper),str(ws)],capture_output=True,text=True)
    print(f'run={run} helper_rc={r.returncode} stdout={r.stdout!r} stderr={r.stderr!r}')
    assert r.returncode==0,r.stderr
    assert (stat.S_IMODE(ssh.stat().st_mode)==0o700 and stat.S_IMODE(key.stat().st_mode)==0o600 and stat.S_IMODE(private.stat().st_mode)==0o600)
    # Current uid owns these protected files; ownership itself may permit writes.
    assert not (stat.S_IMODE(ssh.stat().st_mode) & 0o020) and not (stat.S_IMODE(key.stat().st_mode) & 0o020) and not (stat.S_IMODE(private.stat().st_mode) & 0o020)
    assert os.access(normal,os.W_OK) and os.access(script,os.X_OK)
    assert 'default:' not in acl(ws)
    for q in (ssh,key,private,outside,nested,nested_file): assert_no_acl(q)
    assert (stat.S_IMODE(outside.stat().st_mode),acl(outside)) == outside_before
    for q in (normal,script):
        a=acl(q); assert 'group:root:' in a and 'default:' not in a,(q,a)
    print(f'run={run} owner_uid={os.getuid()} ssh_mode={stat.S_IMODE(ssh.stat().st_mode):04o} key_mode={stat.S_IMODE(key.stat().st_mode):04o} owner_private_mode={stat.S_IMODE(private.stat().st_mode):04o} normal_os_access_W_OK={os.access(normal,os.W_OK)} executable_os_access_X_OK={os.access(script,os.X_OK)}')
for q in (ssh,ssh/'nested',link,key,private,outside):
    r=subprocess.run(['bash',str(helper),str(q)],capture_output=True,text=True); assert r.returncode==0,r.stderr
    assert_no_acl(q)
    print(f'direct_target={q.relative_to(root)} rc={r.returncode} stderr={r.stderr!r}')
print('temporary_root='+str(root))
print('uid_limitation: checks ran as current Codex uid only; no distinct uid execution was attempted or established')
