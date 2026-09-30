#!/usr/bin/env python3
"""Replay Chat + parse connect envelope frames fully."""
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
        'origin': 'https://www.kimi.ai',
        'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36',
    })

resp = urllib.request.urlopen(req, timeout=180)
buf = b''
frames = []
t0 = time.time()
while True:
    chunk = resp.read(1)
    if not chunk:
        break
    buf += chunk
    if len(buf) >= 5:
        ln = int.from_bytes(buf[1:5], 'big')
        if len(buf) >= 5 + ln:
            flag = buf[0]
            payload = buf[5:5+ln]
            frames.append((flag, payload))
            buf = b''

print('total frames:', len(frames), flush=True)
for i, (flag, p) in enumerate(frames):
    try:
        obj = json.loads(p)
    except Exception:
        print(i, 'flag=', flag, 'RAW:', p[:200])
        continue
    s = json.dumps(obj, ensure_ascii=False)
    print('---', i, 'flag=', flag, 'len=', len(s), flush=True)
    print(s[:2500], flush=True)
