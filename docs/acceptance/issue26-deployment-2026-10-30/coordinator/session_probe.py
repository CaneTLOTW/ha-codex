import asyncio, json, os, socket, pathlib, tempfile
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
root=pathlib.Path(__file__).parent
report={"hostname":socket.gethostname(),"uid":os.getuid(),"gid":os.getgid()}
try:
 p=root/"normal.yaml";old=p.read_text();p.write_text(old+"test_session_write: true\n");assert "test_session_write: true" in p.read_text();report["normal_file_read_write"]="PASS"
 report["executable_mode"]=oct((root/"executable.sh").stat().st_mode & 0o777)
 async def check():
  with tempfile.TemporaryFile(mode="w+") as errors:
   async with stdio_client(StdioServerParameters(command="/usr/local/bin/hass-mcp-wrapper",args=[]),errlog=errors) as (reader,writer):
    async with ClientSession(reader,writer) as session:
     await session.initialize();listed=await session.list_tools();report["mcp_tools_count"]=len(listed.tools)
     result=await session.call_tool("get_version",{})
     report["homeassistant_mcp"]="FAIL" if result.isError else "PASS"
     report["ha_version_response"]=[x.text for x in result.content if getattr(x,"type",None)=="text"]
 asyncio.run(asyncio.wait_for(check(),timeout=20))
except Exception as e:report["probe_error_type"]=type(e).__name__
(root/"session_result.json").write_text(json.dumps(report,indent=2)+"\n")
print("ISSUE26_SESSION_RESULT "+json.dumps(report),flush=True)
