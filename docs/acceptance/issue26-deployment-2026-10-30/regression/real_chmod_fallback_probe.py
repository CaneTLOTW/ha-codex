#!/usr/bin/env python3
"""Real chmod fallback check of unchanged helper; all data is disposable."""
import json, os, pathlib, stat, subprocess, tempfile
helper='/share/ha-codex-issue26-deployment/codex/rootfs/usr/local/bin/codex-grant-access'
root=pathlib.Path(tempfile.mkdtemp(prefix='ha-codex-issue26-chmod-fallback-'))
ws=root/'workspace'; ws.mkdir(); ssh=ws/'.ssh'; ssh.mkdir(mode=0o700)
key=ssh/'id_ed25519'; key.write_text('dummy'); key.chmod(0o600)
private=ws/'private0600'; private.write_text('dummy'); private.chmod(0o600)
normal=ws/'normal.yaml'; normal.write_text('dummy'); normal.chmod(0o644)
exe=ws/'executable.sh'; exe.write_text('#!/bin/sh\nexit 0\n'); exe.chmod(0o755)
def acl(path): return subprocess.check_output(['getfacl','-cp',str(path)],text=True)
def no_acl(path):
    a=acl(path); assert 'default:' not in a and 'group:root:' not in a,(path,a)
for p in (ws,ssh,key,private,normal,exe): no_acl(p)
def snapshot(paths):
    result={}
    for p in paths:
        info=p.stat()
        result[str(p.relative_to(root))]={
            'mode':f'{stat.S_IMODE(info.st_mode):04o}', 'uid':info.st_uid,
            'gid':info.st_gid, 'acl':acl(p)}
    return result
paths=(ws,ssh,key,private,normal,exe)
before=snapshot(paths)
records={'result':'PASS','uid':os.getuid(),'before':before,'runs':[]}
for run in (1,2):
    # Intercept only command -v setfacl; delegate every other command builtin.
    shell='command() { if [[ "$#" -eq 2 && "$1" == "-v" && "$2" == "setfacl" ]]; then return 1; fi; builtin command "$@"; }\nsource "$1" "$2"\n'
    r=subprocess.run(['bash','-c',shell,'fallback-probe',helper,str(ws)],capture_output=True,text=True)
    print(f'run={run} rc={r.returncode} stdout={r.stdout!r} stderr={r.stderr!r}')
    assert r.returncode==0,r.stderr
    assert stat.S_IMODE(normal.stat().st_mode)==0o664 and stat.S_IMODE(exe.stat().st_mode)==0o775
    assert os.access(normal,os.W_OK) and os.access(exe,os.X_OK)
    assert stat.S_IMODE(ssh.stat().st_mode)==0o700 and stat.S_IMODE(key.stat().st_mode)==0o600 and stat.S_IMODE(private.stat().st_mode)==0o600
    for q in (ws,ssh,key,private): no_acl(q)
    after=snapshot(paths)
    for q in (ssh,key,private):
        name=str(q.relative_to(root))
        assert after[name]==before[name],(name,before[name],after[name])
    assert 'default:' not in after['workspace']['acl']
    assert 'group:root:rw-' not in after['workspace/normal.yaml']['acl']
    assert 'group:root:rwx' not in after['workspace/executable.sh']['acl']
    records['runs'].append({'run':run,'fallback':'chmod','after':after,
                            'normal_writable':os.access(normal,os.W_OK),
                            'executable':os.access(exe,os.X_OK),
                            'warning':r.stderr})
    print(f'run={run} owner_uid={os.getuid()} normal_mode={stat.S_IMODE(normal.stat().st_mode):04o} normal_W_OK={os.access(normal,os.W_OK)} executable_mode={stat.S_IMODE(exe.stat().st_mode):04o} executable_X_OK={os.access(exe,os.X_OK)} ssh_mode={stat.S_IMODE(ssh.stat().st_mode):04o} key_mode={stat.S_IMODE(key.stat().st_mode):04o} private_mode={stat.S_IMODE(private.stat().st_mode):04o}')
with open(pathlib.Path(__file__).with_name('chmod_missing_setfacl_before_after.json'),'w') as out:
    json.dump(records,out,indent=2,sort_keys=True); out.write('\n')
print('temporary_root='+str(root))
print('uid_limitation: checks ran as current Codex uid only; distinct UID behavior is unverified')
