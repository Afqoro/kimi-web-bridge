#!/usr/bin/env python3
"""Parse request_pb + chat_pb descriptors: dump ALL strings in order with field numbers,
reconstructing message/field structure for ChatRequest.tools."""
import re, base64, urllib.request, sys
sys.setrecursionlimit(10000)

UA = {'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36'}

WIRE = {0: 'varint', 1: '64bit', 2: 'len', 5: '32bit'}

def parse(buf, out, depth=0):
    i = 0
    while i < len(buf):
        try:
            key = 0; shift = 0
            while True:
                b = buf[i]; i += 1
                key |= (b & 0x7F) << shift
                shift += 7
                if not (b & 0x80):
                    break
            fnum, wtype = key >> 3, key & 7
            if wtype == 0:
                v = 0; shift = 0
                while True:
                    b = buf[i]; i += 1
                    v |= (b & 0x7F) << shift
                    shift += 7
                    if not (b & 0x80):
                        break
                out.append((depth, fnum, 'v', v))
            elif wtype == 1:
                out.append((depth, fnum, 'b', buf[i:i+8])); i += 8
            elif wtype == 2:
                ln = 0; shift = 0
                while True:
                    b = buf[i]; i += 1
                    ln |= (b & 0x7F) << shift
                    shift += 7
                    if not (b & 0x80):
                        break
                data = buf[i:i+ln]; i += ln
                try:
                    s = data.decode('utf-8')
                    printable = all(32 <= ord(c) < 127 or c in '\n\t' for c in s)
                except Exception:
                    printable = False
                if printable and len(s) > 0:
                    out.append((depth, fnum, 's', s))
                elif len(data) > 4:
                    sub = []
                    parse(data, sub, depth+1)
                    if sub:
                        out.append((depth, fnum, 'm', sub))
                    else:
                        out.append((depth, fnum, 'b', data))
            elif wtype == 5:
                out.append((depth, fnum, 'b', buf[i:i+4])); i += 4
            else:
                return
        except IndexError:
            return

def dump(sub, indent=0):
    for d, f, t, v in sub:
        pad = '  ' * d
        if t == 's':
            print(f'{pad}f{f}: {v!r}')
        elif t == 'v':
            print(f'{pad}f{f}: {v}')
        elif t == 'm':
            print(f'{pad}f{f}: {{')
            dump(v, indent+1)
            print(f'{pad}}}')

for asset in ('request_pb-D_qcsGu7.js', 'chat_pb-BVNUO0QV.js'):
    js = urllib.request.urlopen(urllib.request.Request(
        'https://statics.kimi.ai/kimi-web-seo/assets/' + asset, headers=UA), timeout=20).read().decode(errors='replace')
    blobs = re.findall(r'["\']([A-Za-z0-9+/=]{200,})["\']', js)
    for bi, b in enumerate(blobs):
        dec = base64.b64decode(b + '=' * (-len(b) % 4))
        if b'ChatRequest' not in dec and b'Tool' not in dec:
            continue
        if asset.startswith('request') and b'ChatRequest' not in dec:
            continue
        print(f'===== {asset} blob {bi} len={len(dec)} =====')
        top = []
        parse(dec, top)
        dump(top)
        print()
