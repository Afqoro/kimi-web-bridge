#!/usr/bin/env python3
"""Force token refresh: blank access_token, reload, capture the refresh request."""
import json, time, urllib.request
from websocket import create_connection

tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9444/json').read())
tab = next(t for t in tabs if t['type'] == 'page' and 'kimi' in t['url'])
ws = create_connection(tab['webSocketDebuggerUrl'], timeout=20, suppress_origin=True)
_id = [0]
def cmd(method, params=None):
    _id[0] += 1
    ws.send(json.dumps({'id': _id[0], 'method': method, 'params': params or {}}))

cmd('Network.enable', {'maxPostDataSize': 65536})
cmd('Page.enable')
cmd('Runtime.enable')
time.sleep(0.5)

# blank the access_token, keep refresh_token
cmd('Runtime.evaluate', {'expression':
    "localStorage.setItem('access_token',''); 'blanked'", 'returnByValue': True})
print('access_token blanked, reloading...', flush=True)
time.sleep(0.5)
cmd('Page.reload')

log = open('/tmp/kimi-refresh-capture.log', 'w', buffering=1)
t0 = time.time()
while time.time() - t0 < 40:
    ws.settimeout(max(1, min(5, 40 - (time.time() - t0))))
    try:
        raw = ws.recv()
    except Exception:
        continue
    if isinstance(raw, bytes):
        raw = raw.decode(errors='replace')
    try:
        msg = json.loads(raw)
    except Exception:
        continue
    m = msg.get('method', '')
    if m == 'Network.requestWillBeSent':
        p = msg['params']['request']
        url = p['url']
        if 'volces' in url or 'google' in url or 'statics' in url or 'apitd' in url:
            continue
        entry = {'method': p['method'], 'url': url,
                 'post': (p.get('postData') or '')[:2000]}
        # capture auth-related headers
        hh = {k: v for k, v in p.get('headers', {}).items()
              if k.lower() in ('authorization', 'content-type')}
        entry['headers'] = hh
        log.write(json.dumps(entry) + '\n')
        if 'token' in url.lower() or 'auth' in url.lower() or 'login' in url.lower() or 'session' in url.lower():
            print('INTERESTING:', p['method'], url, flush=True)
            print('  post:', (p.get('postData') or '')[:300], flush=True)
print('capture done', flush=True)
