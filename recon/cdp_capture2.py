#!/usr/bin/env python3
"""CDP capture via websocket-client lib. Args: DUR [send_text]"""
import json, sys, time, urllib.request
from websocket import create_connection

DUR = int(sys.argv[1]) if len(sys.argv) > 1 else 120
SEND_TEXT = sys.argv[2] if len(sys.argv) > 2 else None
LOG = '/tmp/kimi-ws-capture.log'

tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9444/json').read())
tab = next(t for t in tabs if t['type'] == 'page' and 'kimi' in t['url'])
print('tab:', tab['url'], flush=True)

ws = create_connection(tab['webSocketDebuggerUrl'], timeout=10, suppress_origin=True)
print('connected', flush=True)

log = open(LOG, 'w', buffering=1)
def emit(o):
    log.write(json.dumps(o, ensure_ascii=False) + '\n')

ws.send(json.dumps({'id': 1, 'method': 'Network.enable', 'params': {'maxPostDataSize': 65536}}))
ws.send(json.dumps({'id': 2, 'method': 'Page.enable'}))
print('Network+Page enabled', flush=True)

t0 = time.time()
reloaded = False
text_sent = False
n = 100
while time.time() - t0 < DUR:
    if not reloaded and time.time() - t0 > 1.5:
        ws.send(json.dumps({'id': 3, 'method': 'Page.reload'}))
        reloaded = True
        print('reload sent', flush=True)
    if SEND_TEXT and not text_sent and time.time() - t0 > 8:
        n += 1
        expr = json.dumps(SEND_TEXT)
        ws.send(json.dumps({'id': n, 'method': 'Runtime.evaluate',
                            'params': {'expression': expr, 'awaitPromise': False}}))
        text_sent = True
        print('test text injected:', SEND_TEXT[:40], flush=True)
    ws.settimeout(max(1, min(5, DUR - (time.time() - t0))))
    try:
        raw = ws.recv()
    except Exception as e:
        print('recv:', type(e).__name__, flush=True)
        continue
    if not raw:
        continue
    if isinstance(raw, bytes):
        raw = raw.decode(errors='replace')
    try:
        msg = json.loads(raw)
    except Exception:
        continue
    m = msg.get('method', '')
    if m == 'Network.webSocketCreated':
        p = msg['params']
        print('WS_CREATED:', p.get('url'), flush=True)
        emit({'ev': 'created', 'url': p.get('url'), 'wid': p.get('webSocketId')})
    elif m in ('Network.webSocketFrameSent', 'Network.webSocketFrameReceived'):
        p = msg['params']
        emit({'ev': 'sent' if 'Sent' in m else 'recv', 'wid': p['webSocketId'],
              'data': p['response']['payloadData']})
    elif m == 'Network.requestWillBeSent':
        p = msg['params']['request']
        url = p['url']
        if p['method'] == 'POST' or '/apiv2/' in url or 'chat' in url.lower() or 'completion' in url.lower():
            emit({'ev': 'req', 'method': p['method'], 'url': url,
                  'post': (p.get('postData') or '')[:8000],
                  'headers': {k: v for k, v in p.get('headers', {}).items()
                              if k.lower() in ('authorization', 'content-type', 'cookie',
                                               'x-msh-platform', 'x-msh-device-id',
                                               'x-msh-session-id', 'user-agent')}})

print('done, log:', LOG, flush=True)
