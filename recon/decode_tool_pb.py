#!/usr/bin/env python3
"""Extract all strings from chat_status_pb descriptor blob, ordered, with context around Tool.
Protobuf FileDescriptorProto: strings appear as type names, field names, json names.
"""
import re, base64, urllib.request

UA = {'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36'}
js = urllib.request.urlopen(urllib.request.Request(
    'https://statics.kimi.ai/kimi-web-seo/assets/chat_status_pb-C4X2ppn4.js', headers=UA), timeout=20).read().decode(errors='replace')

blobs = re.findall(r'["\']([A-Za-z0-9+/=]{200,})["\']', js)
print('blobs:', len(blobs))

# protobuf wire parser for strings (field type 2) — walk recursively
def parse(buf, depth=0, out=None, path=''):
    if out is None:
        out = []
    i = 0
    while i < len(buf):
        try:
            # varint key
            key = 0; shift = 0
            while True:
                b = buf[i]; i += 1
                key |= (b & 0x7F) << shift
                shift += 7
                if not (b & 0x80):
                    break
            fnum, wtype = key >> 3, key & 7
            if wtype == 0:  # varint
                while buf[i] & 0x80:
                    i += 1
                i += 1
            elif wtype == 1:
                i += 8
            elif wtype == 2:  # length-delimited
                ln = 0; shift = 0
                while True:
                    b = buf[i]; i += 1
                    ln |= (b & 0x7F) << shift
                    shift += 7
                    if not (b & 0x80):
                        break
                data = buf[i:i+ln]
                i += ln
                # printable string?
                try:
                    s = data.decode('utf-8')
                    printable = all(32 <= ord(c) < 127 or c in '\n\t' for c in s)
                except Exception:
                    printable = False
                if printable and len(s) > 0:
                    out.append((fnum, s))
                elif len(data) > 4:
                    # try recurse into submessage
                    parse(data, depth+1, out)
            elif wtype == 5:
                i += 4
            else:
                break
        except IndexError:
            break
    return out

for bi, b in enumerate(blobs):
    dec = base64.b64decode(b + '=' * (-len(b) % 4))
    if b'TOOL_TYPE_FUNCTION' not in dec:
        continue
    print(f'--- blob {bi} contains TOOL_TYPE_FUNCTION, len={len(dec)} ---')
    strs = parse(dec)
    # print strings in order, focused around Tool/function
    interesting = ['tool', 'Tool', 'function', 'Function', 'name', 'description', 'parameters',
                   'builtin', 'plugin', 'json', 'schema', 'kimi']
    for idx, (fnum, s) in enumerate(strs):
        low = s.lower()
        if any(k in low for k in interesting) and len(s) < 80:
            print(f'{idx:4d} f{fnum}: {s}')
