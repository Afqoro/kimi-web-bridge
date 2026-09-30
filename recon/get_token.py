#!/usr/bin/env python3
"""CDP one-shot: dump token candidates from page storage."""
import json, urllib.request
from websocket import create_connection

tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9444/json').read())
tab = next(t for t in tabs if t['type'] == 'page' and 'kimi' in t['url'])
ws = create_connection(tab['webSocketDebuggerUrl'], timeout=15, suppress_origin=True)

def ev(expr):
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate',
                        'params': {'expression': expr, 'returnByValue': True}}))
    while True:
        m = json.loads(ws.recv())
        if m.get('id') == 1:
            return m

r = ev("JSON.stringify(Object.entries(localStorage).filter(([k,v])=>/token|auth|refresh/i.test(k)).map(([k,v])=>[k,v.slice(0,80)]))")
print('localStorage token-ish keys:', json.dumps(r['result']['result'].get('value'), indent=1))

r = ev("(function(){for (const [k,v] of Object.entries(localStorage)) { try { var o=JSON.parse(v); if(o && o.token && o.token.startsWith('v1.')) return k+' :: '+o.token; } catch(e){} } return 'not-found';})()")
print('FULL TOKEN:', r['result']['result'].get('value'))

r = ev("document.cookie")
print('cookies (non-httpOnly):', r['result']['result'].get('value')[:300])
