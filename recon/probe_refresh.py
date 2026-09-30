#!/usr/bin/env python3
"""Probe candidate refresh-token endpoints with refresh_token Bearer."""
import json, urllib.request, time

tok = json.load(open('/home/agentuser/apps/kimi-web-bridge/recon/tokens.json'))
rt = tok['rt']

candidates = [
    '/apiv2/kimi.gateway.account.v1.AuthService/RefreshToken',
    '/apiv2/kimi.gateway.account.v1.TokenService/Refresh',
    '/apiv2/kimi.gateway.account.v1.TokenService/RefreshToken',
    '/apiv2/kimi.gateway.account.v1.UserService/RefreshToken',
    '/apiv2/kimi.gateway.auth.v1.AuthService/RefreshToken',
    '/apiv2/kimi.gateway.account.v1.SessionService/Refresh',
    '/apiv2/kimi.gateway.account.v1.CredentialService/Refresh',
]
body = json.dumps({"refresh_token": rt}).encode()
UA = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36'

for path in candidates:
    for auth in [('Bearer ' + rt), ('Bearer ' + tok['at'])]:
        req = urllib.request.Request('https://www.kimi.ai' + path, data=body, method='POST', headers={
            'authorization': auth, 'content-type': 'application/json',
            'x-msh-platform': 'web', 'referer': 'https://www.kimi.ai/',
            'origin': 'https://www.kimi.ai', 'user-agent': UA})
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            print('200!!', path, 'auth=', auth[:15], resp.read()[:300])
            raise SystemExit(0)
        except urllib.error.HTTPError as e:
            print(e.code, path, auth[:12], e.read()[:120].decode(errors='replace'))
        except Exception as e:
            print('ERR', path, e)
        time.sleep(0.3)
