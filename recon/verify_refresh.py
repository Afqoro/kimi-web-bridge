#!/usr/bin/env python3
"""Verify RefreshToken replay from raw Python (no browser)."""
import json, urllib.request, base64, time

tok = json.load(open('/home/agentuser/apps/kimi-web-bridge/recon/tokens.json'))
rt = tok['rt']

req = urllib.request.Request(
    'https://auth.kimi.ai/api/account.gateway.v1.AuthService/RefreshToken',
    data=json.dumps({"refresh_token": rt}).encode(), method='POST',
    headers={
        'content-type': 'application/json',
        'origin': 'https://www.kimi.ai',
        'referer': 'https://www.kimi.ai/',
        'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36',
    })
try:
    resp = urllib.request.urlopen(req, timeout=20)
    body = json.loads(resp.read())
except urllib.error.HTTPError as e:
    print('HTTP', e.code, e.read()[:500].decode(errors='replace'))
    raise SystemExit(1)

print('status:', resp.status)
print('keys:', list(body.keys()))
# find tokens — could be nested
def find_tokens(o, path=''):
    out = []
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str) and v.count('.') == 2 and v.startswith('eyJ'):
                out.append((path + k, v))
            else:
                out.extend(find_tokens(v, path + k + '.'))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out.extend(find_tokens(v, path + str(i) + '.'))
    return out

toks = find_tokens(body)
for name, val in toks:
    pl = val.split('.')[1]
    pl += '=' * (-len(pl) % 4)
    payload = json.loads(base64.urlsafe_b64decode(pl))
    typ = payload.get('typ', '?')
    ttl = payload['exp'] - time.time()
    print(f'{name}: typ={typ} ttl={round(ttl)}s len={len(val)}')

# save new tokens if we got both
new_at = next((v for n, v in toks if 'access' in n.lower() or 'at' == n.split('.')[-1]), None)
new_rt = next((v for n, v in toks if 'refresh' in n.lower() or 'rt' == n.split('.')[-1]), None)
print('access found:', bool(new_at), '| refresh found:', bool(new_rt))
if new_at:
    tok['at'] = new_at
    tok['fetched_at'] = time.time()
    if new_rt:
        tok['rt'] = new_rt
    open('/home/agentuser/apps/kimi-web-bridge/recon/tokens.json', 'w').write(json.dumps(tok, indent=1))
    open('/home/agentuser/apps/kimi-web-bridge/tokens.json', 'w').write(json.dumps(tok, indent=1))
    print('tokens.json updated!')
