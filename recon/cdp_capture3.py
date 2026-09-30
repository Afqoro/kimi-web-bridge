#!/usr/bin/env python3
"""CDP capture v3: WS frames (incl. binary/opcode) + REST, reload, auto-send test chat.
Usage: cdp_capture3.py DUR [chat_text]
"""
import json, sys, time, urllib.request, base64
from websocket import create_connection

DUR = int(sys.argv[1]) if len(sys.argv) > 1 else 120
CHAT = sys.argv[2] if len(sys.argv) > 2 else 'Reply with exactly one word: hello'
LOG = '/tmp/kimi-ws-capture.log'

tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9444/json').read())
tab = next(t for t in tabs if t['type'] == 'page' and 'kimi' in t['url'])
print('tab:', tab['url'], flush=True)

ws = create_connection(tab['webSocketDebuggerUrl'], timeout=10, suppress_origin=True)
log = open(LOG, 'w', buffering=1)
def emit(o):
    log.write(json.dumps(o, ensure_ascii=False) + '\n')

_id = [100]
def cmd(method, params=None, cb=None):
    _id[0] += 1
    ws.send(json.dumps({'id': _id[0], 'method': method, 'params': params or {}}))
    return _id[0]

cmd('Network.enable', {'maxPostDataSize': 65536})
cmd('Page.enable')
cmd('Runtime.enable')
print('domains enabled', flush=True)

t0 = time.time()
reloaded = sent_chat = False
pending = {}

while time.time() - t0 < DUR:
    el = time.time() - t0
    if not reloaded and el > 1.5:
        cmd('Page.reload')
        reloaded = True
        print('reload sent', flush=True)
    if not sent_chat and el > 12:
        # focus editor, type, press Enter
        cmd('Runtime.evaluate', {'expression':
            "(function(){var el=document.querySelector('[contenteditable=\"true\"]');"
            "if(!el)return 'no-editor'; el.focus(); return 'focused';})()"})
        time.sleep(0.5)
        cmd('Input.insertText', {'text': CHAT})
        time.sleep(0.5)
        cmd('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Enter',
            'code': 'Enter', 'windowsVirtualKeyCode': 13, 'nativeVirtualKeyCode': 13})
        cmd('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Enter',
            'code': 'Enter', 'windowsVirtualKeyCode': 13, 'nativeVirtualKeyCode': 13})
        sent_chat = True
        print('chat injected:', CHAT[:50], flush=True)
    ws.settimeout(max(1, min(5, DUR - el)))
    try:
        raw = ws.recv()
    except Exception as e:
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
        resp = p.get('response', {})
        op = resp.get('opcode', 1)
        data = resp.get('payloadData', '')
        entry = {'ev': 'ws_sent' if 'Sent' in m else 'ws_recv', 'op': op,
                 'wid': p.get('webSocketId', 0), 'len': len(data)}
        if op == 1:
            entry['data'] = data[:20000]
        else:
            # binary: CDP gives base64? try decode marker
            try:
                dec = base64.b64decode(data)
                entry['b64_head'] = dec[:120].hex()
                entry['b64_full'] = dec.hex()
            except Exception:
                entry['raw_head'] = data[:200]
        emit(entry)
    elif m == 'Network.requestWillBeSent':
        p = msg['params']['request']
        url = p['url']
        if ('volces' in url or 'statics' in url or '.js' in url or '.css' in url
                or '.png' in url or '.woff' in url):
            continue
        h = {k: v for k, v in p.get('headers', {}).items()
             if k.lower() in ('authorization', 'content-type', 'cookie', 'referer',
                              'x-msh-platform', 'x-msh-device-id', 'x-msh-session-id')}
        emit({'ev': 'req', 'method': p['method'], 'url': url,
              'post': (p.get('postData') or '')[:12000], 'headers': h})

print('done, log:', LOG, flush=True)
