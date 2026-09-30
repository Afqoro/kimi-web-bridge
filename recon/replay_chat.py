#!/usr/bin/env python3
"""Replay ChatService/Chat with captured token. Envelope connect+json."""
import json, urllib.request, sys, time

tok = json.load(open('/home/agentuser/apps/kimi-web-bridge/recon/tokens.json'))
at = tok['at']

text = sys.argv[1] if len(sys.argv) > 1 else 'Reply with exactly one word: hello'
model = sys.argv[2] if len(sys.argv) > 2 else 'k2d6-chat'

inner = {
  "scenario": "SCENARIO_CHAT",
  "tools": [{"type": "TOOL_TYPE_SEARCH", "search": {}}, {"type": "TOOL_TYPE_CRON_JOB"}],
  "message": {"role": "user", "blocks": [{"message_id": "", "text": {"content": text}}],
              "scenario": "SCENARIO_CHAT", "is_goal": False},
  "options": {"thinking": True, "enable_plugin": True,
              "reasoning_effort": "REASONING_EFFORT_LOW", "model": model},
  "project_id": ""
}
inner_b = json.dumps(inner, separators=(',', ':')).encode()
# connect unary envelope: flag(1)=0x00 + len(4 BE) + msg
body = b'\x00' + len(inner_b).to_bytes(4, 'big') + inner_b

req = urllib.request.Request(
    'https://www.kimi.ai/apiv2/kimi.gateway.chat.v1.ChatService/Chat',
    data=body, method='POST', headers={
        'authorization': 'Bearer ' + at,
        'content-type': 'application/connect+json',
        'x-msh-platform': 'web',
        'x-msh-device-id': '7691245069365436681',
        'x-msh-session-id': '1731763799132339910',
        'referer': 'https://www.kimi.ai/',
        'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36',
        'origin': 'https://www.kimi.ai',
    })

t0 = time.time()
try:
    resp = urllib.request.urlopen(req, timeout=120)
    ct = resp.headers.get('content-type', '')
    print('status:', resp.status, 'content-type:', ct, flush=True)
    n = 0
    while True:
        chunk = resp.read(65536)
        if not chunk:
            break
        n += len(chunk)
        print('CHUNK t=%.1f:' % (time.time() - t0), chunk[:600], flush=True)
    print('total bytes:', n)
except urllib.error.HTTPError as e:
    print('HTTP', e.code)
    print(e.read()[:2000].decode(errors='replace'))
