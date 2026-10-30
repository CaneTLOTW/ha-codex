"""Use the test add-on's ordinary tty endpoint; no auth headers or credentials."""
import asyncio,json,pathlib,re,shlex,websockets
OUT=pathlib.Path(__file__).parent
BASE=json.loads((OUT/'runtime_fixture_before.json').read_text())
FIXTURE=pathlib.Path(BASE['root'])
RESULT=FIXTURE/'session_result.json'
URI='ws://1e25a555-codex:7681/ws'
report={'endpoint':URI,'credentials_read':False,'authentication_headers_spoofed':False}
def clean(s):
 return re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',s)
async def collect(ws,seconds):
 end=asyncio.get_running_loop().time()+seconds;chunks=[]
 while asyncio.get_running_loop().time()<end:
  try:
   m=await asyncio.wait_for(ws.recv(),min(1,end-asyncio.get_running_loop().time()))
   if isinstance(m,bytes) and m[:1]==b'0':chunks.append(m[1:].decode(errors='replace'))
  except asyncio.TimeoutError:pass
 return clean(''.join(chunks))
async def main():
 try:
  async with websockets.connect(URI,origin='http://1e25a555-codex:7681',subprotocols=['tty'],open_timeout=5) as ws:
   await ws.send(json.dumps({'AuthToken':'','columns':120,'rows':36}).encode())
   text=await collect(ws,5)
   report['codex_apps_401_observed']='codex_apps' in text and '401' in text
   for _ in range(2):
    await ws.send(b'0\x04');text+=await collect(ws,3)
    if 'Codex closed. Starting a shell' in text:break
    if "type 'shell' for a diagnostic shell" in text:
     await ws.send(b'0shell\r');text+=await collect(ws,2);break
   shell_ready=('Codex closed. Starting a shell' in text or "type 'shell' for a diagnostic shell" in text)
   report['diagnostic_shell_ready']=shell_ready
   if shell_ready:
    await ws.send(('0python3 '+shlex.quote(str(FIXTURE/'session_probe.py'))+'\r').encode())
    end=asyncio.get_running_loop().time()+30
    while asyncio.get_running_loop().time()<end and not RESULT.exists():
     await collect(ws,1)
    if RESULT.exists():report['session_result']=json.loads(RESULT.read_text())
    else:report['session_probe']='NO_RESULT'
    await ws.send(b'0exit\r')
 except Exception as e:report['error_type']=type(e).__name__
 (OUT/'terminal_session.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report),flush=True)
asyncio.run(main())
