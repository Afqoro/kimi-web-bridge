#!/usr/bin/env python3
"""Test custom function tool call support in Chat payload."""
import json, urllib.request, sys, time

tok = json.load(open('/home/agentuser/apps/kimi-web-bridge/recon/tokens.json'))
at = tok['at']

inner = {
  "scenario": "SCENARIO_CHAT",
  "tools": [
    {"type": "TOOL_TYPE_FUNCTION", "function": {
        "name": "get_weather",
        "description": "Get current weather for a city",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}
    }},
  ],
  "message": {"role": "user", "blocks": [{"message_id": "", "text": {"content":
      "What is the weather in Jakarta right now? Use the get_weather tool."}}],
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
        'authorization': 'Bearer ' + at,
        'content-type': 'application/connect+json',
        'x-msh-platform': 'web',
        'x-msh-device-id': '7691245069365436681',
        'x-msh-session-id': '1731763799132339910',
        'referer': 'https://www.kimi.ai/',
        'origin': 'https://www.kimi.ai',
        'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36',
    })

try:
    resp = urllib.request.urlopen(req, timeout=180)
except urllib.error.HTTPError as e:
    print('HTTP', e.code, e.read()[:1500].decode(errors='replace'))
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
        frames.append((buf[0], buf[5:5+ln]))
        buf = buf[5+ln:]

print('total frames:', len(frames), flush=True)
seen_masks = {}
for i, (flag, p) in enumerate(frames):
    try:
        obj = json.loads(p)
    except Exception:
        print(i, 'RAW:', p[:150])
        continue
    mask = obj.get('mask', obj.get('op', '?'))
    seen_masks[mask] = seen_masks.get(mask, 0) + 1
    # print interesting ones fully
    s = json.dumps(obj, ensure_ascii=False)
    if any(k in s for k in ('tool', 'Tool', 'function', 'Function', 'search', 'Search')) or 'block.think' not in str(mask):
        if 'block.think.content' in str(mask):
            continue
        print('---', i, mask, flush=True)
        print(s[:1800], flush=True)
print('MASK COUNTS:', json.dumps(seen_masks, indent=1))
