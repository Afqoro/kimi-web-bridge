#!/usr/bin/env python3
"""From page context: GetAvailableModels + find refresh endpoint."""
import json, urllib.request
from websocket import create_connection

tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9444/json').read())
tab = next(t for t in tabs if t['type'] == 'page' and 'kimi' in t['url'])
ws = create_connection(tab['webSocketDebuggerUrl'], timeout=20, suppress_origin=True)
_id = [0]
def ev(expr):
    _id[0] += 1
    ws.send(json.dumps({'id': _id[0], 'method': 'Runtime.evaluate',
                        'params': {'expression': expr, 'returnByValue': True, 'awaitPromise': True}}))
    while True:
        m = json.loads(ws.recv())
        if m.get('id') == _id[0]:
            return m

r = ev("""(async function(){
  const at = localStorage.getItem('access_token');
  const resp = await fetch('/apiv2/kimi.gateway.config.v1.ConfigService/GetAvailableModels', {
    method:'POST', headers:{'content-type':'application/json','authorization':'Bearer '+at,
    'x-msh-platform':'web'}, body:'{}'});
  return await resp.text();
})()""")
print('=== GetAvailableModels ===')
print(str(r['result']['result'].get('value'))[:3000])

r = ev("""(function(){
  // search webpack chunks for refresh endpoint strings
  const hits = [];
  for (const k of Object.keys(window)) { try { if (k.toLowerCase().includes('webpack')) hits.push(k); } catch(e){} }
  return performance.getEntriesByType('resource').map(e=>e.name).filter(u=>u.includes('.js') && u.includes('kimi')).slice(0,50).join('\n');
})()""")
print('=== JS resources ===')
print(str(r['result']['result'].get('value'))[:3000])
