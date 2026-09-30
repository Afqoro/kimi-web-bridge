#!/usr/bin/env python3
"""Decode protobuf descriptors from kimi _pb.js assets, grep TOOL_TYPE/SCENARIO enums."""
import re, base64, urllib.request, sys

UA = {'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36'}
html = open('/tmp/kimi-index.html').read()
assets = sorted(set(re.findall(r'assets/([a-zA-Z0-9_.-]*_pb[a-zA-Z0-9_.-]*\.js)', html)))
print('pb assets:', assets)

for a in assets:
    url = 'https://statics.kimi.ai/kimi-web-seo/assets/' + a
    try:
        js = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read().decode(errors='replace')
    except Exception as e:
        print(a, 'fetch fail', e)
        continue
    # find base64 blobs >= 200 chars
    blobs = re.findall(r'["\']([A-Za-z0-9+/=]{200,})["\']', js)
    found = set()
    for b in blobs:
        try:
            dec = base64.b64decode(b + '=' * (-len(b) % 4))
        except Exception:
            continue
        for m in re.findall(rb'TOOL_TYPE_[A-Z_]+', dec):
            found.add(m.decode())
        for m in re.findall(rb'SCENARIO_[A-Z_]+', dec):
            found.add(m.decode())
    if found:
        print(a, '->', sorted(found))
