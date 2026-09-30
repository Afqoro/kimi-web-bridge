#!/usr/bin/env python3
"""Test TOOL_TYPE_DEVICE_TOOL + name field passthrough."""
import json, urllib.request, time

tok = json.load(open('/home/agentuser/apps/kimi-web-bridge/recon/tokens.json'))
at = tok['at']

inner = {
  "scenario": "SCENARIO_CHAT",
  "tools": [
    {"type": "TOOL_TYPE_DEVICE_TOOL", "name": "get_weather"},
  ],
  "message": {"role": "user", "blocks": [{"message_id": "", "text": {"content":
      "What is the weather in Jakarta? Use the get_weather tool."}}],
              "scenario": "SCENARIO_CHAT", "is_goal": False},
  "options": {"thinking": False, "enable_plugin": False,
              "reasoning_effort": "REASONING_EFFORT_LOW", "model": "k2d6-chat"},
  "project_id": ""
}
inner_b = json.dumps(inner, separators=(',', ':')).encode()
body = b'\x00' + len(inner_b).to_bytes(4, 'big') + inner_b
req = urllib.request.Request(
    'https://www.kimi.ai/apiv2/kimi.gateway.chat.v1.ChatService/Chat',
    data=body, method='POST', headers={
        'authorization': 'Bearer ' + at, 'content-type': 'application/connect+json',
        'x-msh-platform': 'web', 'x-msh-device-id': '7691245069365436681',
        'x-msh-session-id': '1731763799132339910',
        'referer': 'https://www.kimi.ai/', 'origin': 'https://www.kimi.ai',
        'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36',
    })
try:
    resp = urllib.request.urlopen(req, timeout=120)
except urllib.error.HTTPError as e:
    print('HTTP', e.code, e.read()[:500].decode(errors='replace'))
    raise SystemExit(1)
buf = b''
frames = []
while True:
    chunk = resp.read(65536)
    if not chunk:
        break
    buf += chunk
    while len(buf) >= 5:
        ln = int.from_bytes(buf[1:5], 'big')
        if len(buf) < 5 + ln:
            break
        frames.append(buf[5:5+ln]); buf = buf[5+ln:]
last_request_echo = None
text = []
tool_events = []
for p in frames:
    try:
        ev = json.loads(p)
    except Exception:
        continue
    s = json.dumps(ev)
    if 'lastRequest' in s:
        last_request_echo = ev
    m = ev.get('mask', '')
    b = ev.get('block') or {}
    if m in ('block.text', 'block.text.content') and b.get('text'):
        text.append(b['text'].get('content', ''))
    if 'tool' in s.lower() and 'lastRequest' not in s:
        tool_events.append(s[:400])
print('=== lastRequest echo ===')
print(json.dumps(last_request_echo, indent=1)[:800] if last_request_echo else 'none')
print('=== tool-ish events ===')
print('\n'.join(tool_events[:5]) if tool_events else 'none')
print('=== TEXT ===')
print(''.join(text)[:800])
