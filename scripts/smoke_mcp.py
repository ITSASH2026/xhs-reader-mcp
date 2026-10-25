"""Check a local MCP instance without fetching or saving source content."""
import json
from pathlib import Path
import urllib.request
import urllib.error

ROOT=Path(__file__).resolve().parents[1]


def main():
    token=(ROOT/'private/token.txt').read_text().strip()
    port=5556
    env=ROOT/'.env'
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith('MCP_PORT='):
                port=int(line.split('=',1)[1])
    url=f'http://127.0.0.1:{port}/mcp'
    session=None
    def call(body,credential):
        nonlocal session
        headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream','MCP-Protocol-Version':'2025-03-26'}
        if credential:headers['Authorization']='Bearer '+credential
        if session:headers['Mcp-Session-Id']=session
        request=urllib.request.Request(url,json.dumps(body).encode(),headers=headers)
        try:
            with urllib.request.urlopen(request,timeout=20) as response:
                session=response.headers.get('Mcp-Session-Id',session)
                raw=response.read().decode()
                if raw.startswith(('data:','event:')):
                    raw='\n'.join(line[6:] for line in raw.splitlines() if line.startswith('data: '))
                return response.status,json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as exc:
            return exc.code,{}
    initialize={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'source-release-smoke','version':'1'}}}
    for credential in (None,'invalid-example-token'):
        status,_=call(initialize,credential)
        if status not in (401,403):raise RuntimeError('Invalid credentials were not rejected.')
    status,result=call(initialize,token)
    if status!=200 or 'result' not in result:raise RuntimeError('Authenticated initialization failed.')
    call({'jsonrpc':'2.0','method':'notifications/initialized'},token)
    status,result=call({'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}},token)
    expected={'get_detail_data','download_detail','read_xhs_video','get_xhs_video_result','get_xhs_comments'}
    tools=result.get('result',{}).get('tools',[])
    if status!=200 or {tool['name'] for tool in tools}!=expected:raise RuntimeError('Tool catalog mismatch.')
    comments=next(tool for tool in tools if tool['name']=='get_xhs_comments')
    if comments['inputSchema']['properties']['limit'].get('default')!=20:raise RuntimeError('Comment default mismatch.')
    print('MCP smoke check passed: authentication, five tools, default comment limit 20. No public note requested.')


if __name__=='__main__':
    main()
