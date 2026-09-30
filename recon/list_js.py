#!/usr/bin/env python3
"""List all loaded JS resources from kimi.ai page."""
import json, urllib.request
from websocket import create_connection

tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9444/json').read())
tab = next(t for t in tabs if t['type'] == 'page' and 'kimi' in t['url'])
ws = create_connection(tab['webSocketDebuggerUrl'], timeout=20, suppress_origin=True)
ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {
    'expression': "performance.getEntriesByType('resource').map(e=>e.name).filter(n=>n.endsWith('.js')).join('\n')",
    'returnByValue': True}}))
while True:
    m = json.loads(ws.recv())
    if m.get('id') == 1:
        print(m['result']['result'].get('value'))
        break
