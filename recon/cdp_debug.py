#!/usr/bin/env python3
"""CDP debug: connect, enable Network, print EVERY raw frame with timestamps."""
import json, socket, base64, os, sys, time, urllib.request

DUR = int(sys.argv[1]) if len(sys.argv) > 1 else 30

tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9444/json').read())
tab = next(t for t in tabs if t['type'] == 'page' and 'kimi' in t['url'])
path = tab['webSocketDebuggerUrl'].split('9444')[1]
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
    chunk = s.recv(4096)
    if not chunk:
        print('closed during handshake', flush=True); sys.exit(1)
    buf += chunk
hdrs, _, rest = buf.partition(b'\r\n\r\n')
buf = rest
print('handshake ok, leftover bytes:', len(buf), flush=True)

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
    return opcode, recv_exact(ln)

send_frame(json.dumps({'id': 1, 'method': 'Network.enable'}).encode())
print('sent Network.enable, reading...', flush=True)

t0 = time.time()
while time.time() - t0 < DUR:
    s.settimeout(max(1, min(5, DUR - (time.time() - t0))))
    try:
        opcode, payload = recv_frame()
    except socket.timeout:
        print('  (timeout, still alive)', flush=True)
        continue
    except ConnectionError as e:
        print('TCP CLOSED at t=%.1fs' % (time.time() - t0), flush=True)
        break
    head = payload[:150].decode(errors='replace').replace('\n', ' ')
    print('t=%.1f op=%d len=%d | %s' % (time.time() - t0, opcode, len(payload), head), flush=True)
print('debug done', flush=True)
