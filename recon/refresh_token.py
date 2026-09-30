#!/usr/bin/env python3
"""Reload kimi.ai tab, wait, dump fresh access_token."""
import json, time, urllib.request
from websocket import create_connection

tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9444/json').read())
tab = next(t for t in tabs if t['type'] == 'page' and 'kimi' in t['url'])
ws = create_connection(tab['webSocketDebuggerUrl'], timeout=15, suppress_origin=True)

def cmd(i, method, params=None):
    ws.send(json.dumps({'id': i, 'method': method, 'params': params or {}}))

def wait_result(rid):
    while True:
        m = json.loads(ws.recv())
        if m.get('id') == rid:
            return m

cmd(1, 'Page.reload')
print('reload sent, waiting 12s...', flush=True)
time.sleep(12)
cmd(2, 'Runtime.evaluate', {'expression': "localStorage.getItem('access_token')", 'returnByValue': True})
r = wait_result(2)
at = r['result']['result']['value']
if not at:
    print('no token after reload')
    raise SystemExit(1)
# update tokens.json
import base64
tokpath = '/home/agentuser/apps/kimi-web-bridge/recon/tokens.json'
tok = json.load(open(tokpath))
tok['at'] = at
tok['fetched_at'] = time.time()
open(tokpath, 'w').write(json.dumps(tok, indent=1))
pad = at.split('.')[1] + '=' * (-len(at.split('.')[1]) % 4)
pl = json.loads(base64.urlsafe_b64decode(pad))
print('fresh token, exp-iat =', pl['exp'] - pl['iat'], 's; now-iat =', int(time.time()) - pl['iat'])
