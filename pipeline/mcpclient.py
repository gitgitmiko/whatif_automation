import json,subprocess,sys,os
class M:
    def __init__(s,cmd,err):
        s.p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=open(err,'w'),text=True);s.i=0
        s.rpc('initialize',{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"demo","version":"0"}})
        s.send({"jsonrpc":"2.0","method":"notifications/initialized"})
    def send(s,o): s.p.stdin.write(json.dumps(o)+"\n");s.p.stdin.flush()
    def rpc(s,m,p=None):
        s.i+=1;s.send({"jsonrpc":"2.0","id":s.i,"method":m,"params":p or {}})
        while True:
            r=json.loads(s.p.stdout.readline())
            if r.get('id')==s.i:return r
    def call(s,n,**a):
        r=s.rpc('tools/call',{"name":n,"arguments":a})
        if 'error' in r: print('RPCERR',n,r['error']);sys.exit(1)
        r=r['result']
        t=' '.join(c.get('text','') for c in r['content'])
        print(f"[{n}]{' ERROR' if r.get('isError') else ''} {t[:700]}")
        if r.get('isError'): sys.exit(1)
        return r.get('structuredContent') or json.loads(t)
