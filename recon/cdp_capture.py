#!/usr/bin/env python3
"""CDP capture v2: verbose frames, close reasons, HTTP API requests, WS events."""
import json, socket, base64, os, sys, time, urllib.request

DUR = int(sys.argv[1]) if len(sys.argv) > 1 else 120
LOG = '/tmp/kimi-ws-capture.log'

tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9444/json').read())
tab = next(t for t in tabs if t['type'] == 'page' and 'kimi' in t['url'])
ws_url = tab['webSocketDebuggerUrl']
path = ws_url.split('9444')[1]
print('tab:', tab['url'], flush=True)

host, port = '127.0.0.1', 9444
s = socket.create_connection((host, port), timeout=10)
key = base64.b64encode(os.urandom(16)).decode()
req = ('GET ' + path + ' HTTP/1.1\r\nHost: ' + host + ':' + str(port) +
       '\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: ' + key +
       '\r\nSec-WebSocket-Version: 13\r\n\r\n')
s.sendall(req.encode())
buf = b''
while b'\r\n\r\n' not in buf:
    buf += s.recv(4096)
hdrs = buf.split(b'\r\n\r\n')[0].decode(errors='replace')
print('handshake:\n' + hdrs, flush=True)
buf = buf.split(b'\r\n\r\n', 1)[1]  # trim: keep only post-handshake bytes

def send_frame(payload, opcode=1):
    mask = os.urandom(4)
    hdr = bytes([0x80 | opcode])
    n = len(payload)
    if n < 126:
        hdr += bytes([0x80 | n])
    elif n < 65536:
        hdr += bytes([0x80 | 126]) + n.to_bytes(2, 'big')
    else:
        hdr += bytes([0x80 | 127]) + n.to_bytes(8, 'big')
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    s.sendall(hdr + masked)

def recv_exact(n):
    global buf
    while len(buf) < n:
        chunk = s.recv(65536)
        if not chunk:
            raise ConnectionError('tcp closed')
        buf += chunk
    out, buf = buf[:n], buf[n:]
    return out

def recv_frame():
    b = recv_exact(2)
    b1, b2 = b[0], b[1]
    opcode = b1 & 0x0F
    ln = b2 & 0x7F
    if ln == 126:
        ln = int.from_bytes(recv_exact(2), 'big')
    elif ln == 127:
        ln = int.from_bytes(recv_exact(8), 'big')
    payload = recv_exact(ln)
    return opcode, payload

log = open(LOG, 'w', buffering=1)
def emit(obj):
    log.write(json.dumps(obj, ensure_ascii=False) + '\n')

def send_cmd(id, method, params=None):
    m = {'id': id, 'method': method}
    if params:
        m['params'] = params
    send_frame(json.dumps(m).encode())

t0 = time.time()
n = 10
def cmd(method, params=None):
    global n
    n += 1
    send_cmd(n, method, params)

cmd('Network.enable', {'maxPostDataSize': 65536})
cmd('Page.enable')
timer = None

def do_reload():
    cmd('Page.reload', {'ignoreCache': False})
    print('reload sent', flush=True)

print('capturing', DUR, 's; reload in 2s', flush=True)
while time.time() - t0 < DUR:
    if timer is None and time.time() - t0 > 2:
        do_reload()
        timer = 1
    s.settimeout(max(1, min(5, DUR - (time.time() - t0))))
    try:
        opcode, payload = recv_frame()
    except socket.timeout:
        continue
    except (ConnectionError, OSError) as e:
        print('socket err:', e, flush=True)
        break
    if opcode == 9:
        send_frame(payload, opcode=10)
        continue
    if opcode == 8:
        code = int.from_bytes(payload[:2], 'big') if len(payload) >= 2 else 0
        reason = payload[2:].decode(errors='replace')
        print('CLOSE frame: code=', code, 'reason=', reason, flush=True)
        break
    if opcode != 1:
        print('opcode', opcode, 'len', len(payload), flush=True)
        continue
    try:
        msg = json.loads(payload)
    except Exception as e:
        print('json fail:', e, 'head:', payload[:120], flush=True)
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
        if p['method'] == 'POST' or '/api/' in url or 'chat' in url.lower():
            emit({'ev': 'req', 'method': p['method'], 'url': url,
                  'post': (p.get('postData') or '')[:8000],
                  'headers': {k: v for k, v in p.get('headers', {}).items()
                              if k.lower() in ('authorization', 'content-type', 'cookie', 'x-msh-platform', 'x-msh-device-id', 'x-msh-session-id', 'user-agent')}})

print('done, log:', LOG, os.path.getsize(LOG), 'bytes', flush=True)
