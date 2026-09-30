#!/usr/bin/env python3
"""Dump full access_token from kimi.ai page + save for replay."""
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

r = ev("JSON.stringify({at: localStorage.getItem('access_token'), rt: localStorage.getItem('refresh_token')})")
val = json.loads(r['result']['result']['value'])
open('/home/agentuser/apps/kimi-web-bridge/recon/tokens.json', 'w').write(json.dumps(val, indent=1))
at = val.get('at', '')
print('access_token len:', len(at))
print('head:', at[:40], '... tail:', at[-20:])
print('refresh len:', len(val.get('rt', '')))
# decode JWT payload
import base64
parts = at.split('.')
if len(parts) >= 2:
    pad = parts[1] + '=' * (-len(parts[1]) % 4)
    payload = json.loads(base64.urlsafe_b64decode(pad))
    print('JWT payload:', json.dumps(payload, indent=1)[:800])
