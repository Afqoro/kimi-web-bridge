#!/usr/bin/env python3
"""Multi-turn + 30-tool Hermes-style request test against kimi-web-bridge :18770."""
import json, urllib.request, time

BRIDGE = 'http://localhost:18770/v1/chat/completions'

# --- 30 tools ala Hermes ---
def tool(name, desc, props, req=None):
    return {"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": props,
                       "required": req or []}}}

TOOLS = [
    tool("terminal", "Run a shell command on the VPS", {"command": {"type": "string"}, "timeout": {"type": "integer"}}, ["command"]),
    tool("read_file", "Read file content", {"path": {"type": "string"}}, ["path"]),
    tool("write_file", "Write file", {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
    tool("patch", "Patch a file section", {"path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"}}, ["path", "old_string", "new_string"]),
    tool("web_search", "Web search", {"query": {"type": "string"}}, ["query"]),
    tool("web_extract", "Extract page content by URL", {"url": {"type": "string"}}, ["url"]),
    tool("vision_analyze", "Analyze image with vision model", {"image_url": {"type": "string"}, "prompt": {"type": "string"}}, ["image_url", "prompt"]),
    tool("memory", "Persist memory notes", {"content": {"type": "string"}}, ["content"]),
    tool("skill_view", "Load a skill by name", {"name": {"type": "string"}}, ["name"]),
    tool("skills_list", "List available skills", {}),
    tool("skill_manage", "Create/patch/delete a skill", {"action": {"type": "string"}, "name": {"type": "string"}}, ["action", "name"]),
    tool("execute_code", "Run Python code sandboxed", {"code": {"type": "string"}}, ["code"]),
    tool("delegate_task", "Delegate a subtask to another agent", {"task": {"type": "string"}}, ["task"]),
    tool("clarify", "Ask user a clarifying question", {"question": {"type": "string"}}, ["question"]),
    tool("text_to_speech", "TTS audio from text", {"text": {"type": "string"}}, ["text"]),
    tool("browser_exec", "Execute JS in managed browser", {"code": {"type": "string"}}, ["code"]),
    tool("browser_vault_unlock", "Unlock credential vault", {"passphrase": {"type": "string"}}, ["passphrase"]),
    tool("browser_vault_list", "List vault entries", {}),
    tool("tool_search", "Search tool registry", {"query": {"type": "string"}}, ["query"]),
    tool("tool_call", "Invoke tool by name dynamically", {"name": {"type": "string"}, "arguments": {"type": "object"}}, ["name"]),
    tool("tool_describe", "Describe a tool's schema", {"name": {"type": "string"}}, ["name"]),
    tool("process", "Manage background process", {"action": {"type": "string"}, "session_id": {"type": "string"}}, ["action"]),
    tool("cron", "Schedule recurring jobs", {"action": {"type": "string"}, "schedule": {"type": "string"}}, ["action"]),
    tool("email_send", "Send email", {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, ["to", "subject"]),
    tool("telegram_send", "Send telegram message", {"text": {"type": "string"}}, ["text"]),
    tool("git_status", "Git working tree status", {"repo": {"type": "string"}}, ["repo"]),
    tool("docker_ps", "List docker containers", {}),
    tool("system_stats", "CPU/mem/disk usage", {}),
    tool("tailscale_status", "Tailscale node status", {}),
    tool("pm2_list", "List pm2 processes", {}),
]

SYSTEM = "You are Hermes Agent running on a VPS. Use the provided tools to accomplish tasks. Prefer terminal for shell ops.\n\nCurrent time: 2026-09-30 17:45 CST."

M1 = [{"role": "system", "content": SYSTEM},
      {"role": "user", "content": "Check how much free disk space is on this machine using the appropriate tool."}]

def chat(messages):
    body = json.dumps({"model": "kimi-k2", "messages": messages, "tools": TOOLS}).encode()
    req = urllib.request.Request(BRIDGE, data=body, method='POST',
                                 headers={'content-type': 'application/json'})
    t0 = time.time()
    resp = urllib.request.urlopen(req, timeout=300)
    r = json.loads(resp.read())
    r['_elapsed'] = round(time.time() - t0, 1)
    return r

# turn 1: expect tool_calls
t1 = chat(M1)
ch = t1['choices'][0]
print('=== TURN 1 === elapsed', t1['_elapsed'], 's | finish:', ch['finish_reason'])
msg = ch['message']
print('content:', (msg.get('content') or '')[:200])
tcs = msg.get('tool_calls') or []
print('tool_calls:', [(t['function']['name'], t['function']['arguments'][:80]) for t in tcs])
assert ch['finish_reason'] == 'tool_calls' and tcs, 'FAIL: no tool call on turn 1'

# turn 2: feed tool result, expect final answer
M2 = M1 + [msg,
    {"role": "tool", "tool_call_id": tcs[0]['id'],
     "content": "Filesystem      Size  Used Avail Use% Mounted on\n/dev/vda1        40G   31G  9.1G  78% /\ntmpfs           2.0G     0  2.0G   0% /dev/shm"}]
t2 = chat(M2)
ch2 = t2['choices'][0]
print('=== TURN 2 === elapsed', t2['_elapsed'], 's | finish:', ch2['finish_reason'])
print('content:', (ch2['message'].get('content') or '')[:300])
print('spurious tool_calls:', bool(ch2['message'].get('tool_calls')))

ok = ch2['finish_reason'] == 'stop' and '9.1' in (ch2['message'].get('content') or '')
print('E2E MULTI-TURN:', 'PASS' if ok else 'FAIL')
