# Sena — Bug Fix Instructions (Next Context Window)

This file is a precise engineering instruction list. Read it top-to-bottom before touching any file.
Each fix is self-contained. Implement them in order. Do not skip diagnosis steps.

---

## Context You Must Load First

Before implementing, read these files in full so you have the complete picture:

| File | Why |
|------|-----|
| `src/api/deps.py` | Where Sena is instantiated — Bug 4 fix goes here |
| `src/api/routes/chat.py` | Full chat pipeline — confirms WS is never called |
| `src/core/sena.py` | `process()`, `stream()`, `_on_stage_change()`, `set_stage_callback()` |
| `src/core/constants.py` | `INTENT_EXTENSION_MAPPING`, `IntentType`, `ModelType` |
| `src/llm/manager.py` | `generate()`, `stream()`, `classify_intent()` |
| `src/llm/models/model_registry.py` | `initialize()`, `switch_to()` — Bug 2 fix goes here |
| `src/llm/router.py` | `_llm_classify()`, circuit-breaker logic |
| `src/extensions/core/` | Directory listing — only file_search.py and web_search.py exist |
| `src/ui/behind-the-sena/src/tabs/Chat.tsx` | Full file — Bugs 1, 3 fixes go here |
| `src/ui/behind-the-sena/src/tabs/Logs.tsx` | Full file — Bug 1 fix goes here |
| `src/api/websocket/manager.py` | `broadcast_processing_update()` signature |

---

## ~~Bug 1 — Log Stack Grouping Is Broken~~ ✅ FIXED

> **Fixed:** Two-pass `groupChatLogs` rewrite in `Logs.tsx`. Session-keyed buckets absorb all pipeline logs (memory, LLM, extensions) while a request window is open. Groups sort by last child timestamp. Clear button added via `POST /api/v1/logs/clear`.
> **Fixed (amendment 2):** `clear_logs()` in `src/api/routes/logs.py` now uses a **watermark strategy** — records `_cleared_at = datetime.now()` instead of touching the file. `_load_logs()` skips any entry with timestamp ≤ `_cleared_at` and breaks early (newest-first iteration). Session files (not held open) are still deleted. No `WinError 32`, no silent failures.

### Symptom
- One chat request produces 2–6 duplicate "Chat: gaming" parent rows in the Logs tab.
- Non-chat pipeline logs (memory, LLM, extensions) are not grouped under their request parent.
- Expanded groups sometimes contain only 1–2 children instead of the full pipeline trace.

### Root Cause
`groupChatLogs` in `Logs.tsx` creates a **new partial group** for any log from `src.api.routes.chat`
that arrives outside a `START/END` boundary (i.e., after a non-chat log breaks the `current` accumulator).
This splits a single request into N partial groups.
It also only groups `src.api.routes.chat`-sourced lines — all other pipeline logs
(memory, router, LLM, extensions, personality) that carry the same `session_id` are left as orphans.

### Fix — `src/ui/behind-the-sena/src/tabs/Logs.tsx`

Replace `groupChatLogs` entirely with a two-pass algorithm:

**Pass 1 — collect all groups keyed by session_id:**
```
Map<sessionId, { entries: LogEntry[], level, startTimestamp }>
```
- Walk entries sorted oldest-first.
- For each entry, call `extractSessionId(entry)` (already exists).
- If a session_id is found, push the entry into that session's bucket.
  - If the bucket doesn't exist yet, create it with this entry as the start.
  - Track the worst log level seen.
- If no session_id is extractable AND the entry source includes `src.api.routes.chat`,
  treat it as belonging to the most-recently-opened bucket (fallback for logs emitted before the
  session_id is known, e.g., the very first "CHAT REQUEST START" line).
- If no session_id and not a chat-source line, leave it as a standalone entry.

**Pass 2 — build output array:**
- For each session bucket: create a group parent row:
  - `id`: `chat-group-{sessionId}`
  - `timestamp`: earliest child timestamp
  - `level`: worst level in bucket
  - `message`: `buildChatSummary(bucket.metadata)` (already exists)
  - `children`: all bucket entries sorted oldest-first
  - `kind`: `"chat"`
- Append all standalone (non-grouped) entries as-is.
- Sort the final array newest-first.

**Additional requirement:** remove the `isChat` guard that currently restricts grouping to
`src.api.routes.chat` sources. Any entry with a `session_id` matching an open group should be
pulled into that group, regardless of source.

---

## Bug 2 — Router Model Warms Up on First Message; Causes 40-Second Stall

### Symptom
Log shows `Warming up model mistral:7b-instruct...` ~40 seconds after the first message is sent.
The first response is delayed by the full model-load time.
User reports "the router model answered" — this is because the router model finishes loading
and its Ollama slot is warm when the generate call hits, while FAST is the same underlying model
but a separate OllamaClient instance that must also warm up.

### Root Cause
`model_registry.initialize()` calls `switch_to(ModelType.FAST)` only.
The router model OllamaClient is never loaded at startup.
On first `_llm_classify` call, `router_model.is_loaded` is `False` so `load()` is called,
triggering a full Ollama warm-up that blocks the first request.

### Fix — `src/llm/models/model_registry.py`

In `initialize()`, after `switch_to(ModelType.FAST)`, add:

```python
# Eagerly warm the router model so the first classify() call is not delayed.
# If the router model name is identical to the fast model name, we can skip
# the Ollama warm-up (the model is already hot) and just mark it loaded.
if ModelType.ROUTER in self._models:
    router_info = self._models[ModelType.ROUTER]
    fast_info = self._models.get(ModelType.FAST)
    if fast_info and router_info.config.name == fast_info.config.name:
        # Same underlying model — no second warm-up needed.
        router_info.client._is_loaded = True
        logger.info(
            f"Router model shares name with fast model ({router_info.config.name}) "
            "— skipping duplicate warm-up."
        )
    else:
        try:
            logger.info("Pre-loading router model at startup...")
            await router_info.client.load()
            logger.info("Router model pre-loaded successfully.")
        except Exception as e:
            logger.warning(f"Router model pre-load failed (non-fatal): {e}")
```

No other changes to `model_registry.py` are needed.

---

## Bug 3 — Thought Process Stages Missing After Response (Stale Closure)

### Symptom
After Sena responds, the "Thought process" panel on the message shows zero stages,
even though the live panel showed them during processing.
User cannot open/review the thought process after the response arrives.

### Root Cause
In `sendMessage` in `Chat.tsx`:
```typescript
const capturedStages = [...liveStages]; // stale closure
```
`liveStages` here is the value captured when `sendMessage` was last created by `useCallback`.
React state updates are asynchronous; by the time `await fetchJson(...)` resolves, `liveStages`
in the closure is still the snapshot from the previous render, not the current accumulated stages.

### Fix — `src/ui/behind-the-sena/src/tabs/Chat.tsx`

1. Add a ref alongside the state:
```typescript
const liveStagesRef = useRef<ThinkingStage[]>([]);
```

2. Wherever `setLiveStages` is called (the WS `handleMessage` handler AND the `finally` reset),
   keep the ref in sync:
```typescript
// In handleMessage, replace:
setLiveStages((prev) => [...prev, newStage]);
// With:
setLiveStages((prev) => {
  const next = [...prev, newStage];
  liveStagesRef.current = next;
  return next;
});

// In the finally block reset:
setLiveStages([]);
liveStagesRef.current = [];
```

3. In `sendMessage`, replace the stale capture with the ref:
```typescript
// Replace:
const capturedStages = [...liveStages];
// With:
const capturedStages = [...liveStagesRef.current];
```

4. Add `liveStagesRef` to the `useCallback` dependency array — refs are stable so this is a
   no-op for re-creation, but it makes the dependency explicit.

---

## Bug 4 — ThinkingPanel Always Shows "Waiting…" (WebSocket Stage Events Never Arrive)

### Symptom
The ThinkingPanel always shows "Waiting for processing stages…" and never populates
with actual stage entries, even after the response arrives.
No `processing_update` events are visible in the browser's DevTools WS inspector.

### Root Cause
**Critical wiring gap:** `set_stage_callback` is never called on the Sena instance.

In `src/api/deps.py`, `get_sena()` does:
```python
_sena_instance = Sena()
await _sena_instance.initialize()
# ← nothing here to wire stages to WebSocket
```

Inside `sena.process()`, `_on_stage_change` fires — but `self._stage_callback` is `None`,
so the call is a silent no-op. The WebSocket manager's `broadcast_processing_update` is never invoked.

### Fix — `src/api/deps.py`

After `await _sena_instance.initialize()`, add the wiring:

```python
from src.api.websocket.manager import ws_manager
from src.core.constants import ProcessingStage

async def _ws_stage_callback(stage: ProcessingStage, details: str = "") -> None:
    stage_str = stage.value if isinstance(stage, ProcessingStage) else str(stage)
    await ws_manager.broadcast_processing_update(stage_str, details)

_sena_instance.set_stage_callback(_ws_stage_callback)
logger.info("Sena stage callback wired to WebSocket manager.")
```

That is the entire fix. No other file needs to change for this bug.

**Verify after fix:**
- Open DevTools → Network → WS → `/ws` connection.
- Send a message. You should see JSON frames:
  `{"type":"processing_update","data":{"stage":"intent_classification","details":"..."}}`
  arriving before the HTTP response completes.
- The ThinkingPanel should populate in real-time.

---

## Bug 5 — Sena Cannot Execute System Commands (Latency Check, Scripts, etc.)

### Symptom
User asks Sena to "check my latency" or run a system task.
Sena responds with "I am an AI and cannot interact with your system in real-time" — a hallucination
that contradicts her actual capabilities.

### Root Cause (two parts)

**Part A:** `INTENT_EXTENSION_MAPPING[IntentType.SYSTEM_COMMAND]` in `src/core/constants.py` lists
`["app_launcher", "system_info"]`. Neither extension exists in `src/extensions/core/`.
When `_execute_extensions` runs, it finds nothing, injects no output, and Sena has no tool result
to reason about — so she falls back to hallucination.

**Part B:** The system prompt does not clearly enumerate what system-level actions Sena can
actually perform. The LLM has no concrete evidence she has shell execution capability.

### Fix — Three changes required

---

#### Fix 5A — Create `src/extensions/core/system_command.py`

New file. Must follow the extension interface contract from `copilot-instructions.md`.

```python
VERSION = "1.0.0"
METADATA = {
    "name": "System Command",
    "description": (
        "Executes safe, read-only system commands on the local machine. "
        "Supports network diagnostics (ping, tracert/traceroute, nslookup, ipconfig/ifconfig), "
        "system info queries (hostname, uptime, disk usage, memory), "
        "and process listing. Never executes write or destructive commands."
    ),
    "author": "Sena",
    "parameters": {
        "user_input": {
            "type": "str",
            "description": "The user's natural-language request describing the system task.",
        }
    },
    "requires": [],
}

import asyncio
import platform
import re
import shlex
import subprocess
from typing import Optional

# ---------------------------------------------------------------------------
# Allowlist of safe, read-only commands
# Key: canonical name  Value: (windows_cmd, unix_cmd, description)
# ---------------------------------------------------------------------------
_COMMANDS: dict[str, tuple[list[str], list[str], str]] = {
    "ping": (
        ["ping", "-n", "4", "{target}"],
        ["ping", "-c", "4", "{target}"],
        "Send 4 ICMP echo requests to a host and report round-trip times.",
    ),
    "traceroute": (
        ["tracert", "{target}"],
        ["traceroute", "-m", "20", "{target}"],
        "Trace the network path to a host.",
    ),
    "nslookup": (
        ["nslookup", "{target}"],
        ["nslookup", "{target}"],
        "Query DNS for a hostname or IP address.",
    ),
    "ipconfig": (
        ["ipconfig"],
        ["ifconfig"],
        "Show network interface configuration.",
    ),
    "hostname": (
        ["hostname"],
        ["hostname"],
        "Print the machine's hostname.",
    ),
    "disk_usage": (
        ["wmic", "logicaldisk", "get", "size,freespace,caption"],
        ["df", "-h"],
        "Report disk space usage.",
    ),
    "memory": (
        ["wmic", "OS", "get", "TotalVisibleMemorySize,FreePhysicalMemory"],
        ["free", "-h"],
        "Report physical memory usage.",
    ),
    "uptime": (
        ["net", "statistics", "server"],
        ["uptime"],
        "Show how long the system has been running.",
    ),
    "processes": (
        ["tasklist", "/fo", "table"],
        ["ps", "aux", "--sort=-%mem"],
        "List running processes.",
    ),
    "netstat": (
        ["netstat", "-n"],
        ["netstat", "-n"],
        "Show active network connections.",
    ),
}

# Keywords that map user language to a canonical command name
_KEYWORD_MAP: dict[str, str] = {
    "ping": "ping",
    "latency": "ping",
    "lag": "ping",
    "response time": "ping",
    "traceroute": "traceroute",
    "tracert": "traceroute",
    "trace route": "traceroute",
    "nslookup": "nslookup",
    "dns": "nslookup",
    "resolve": "nslookup",
    "ip config": "ipconfig",
    "ipconfig": "ipconfig",
    "ifconfig": "ipconfig",
    "network config": "ipconfig",
    "network interface": "ipconfig",
    "hostname": "hostname",
    "computer name": "hostname",
    "disk": "disk_usage",
    "storage": "disk_usage",
    "free space": "disk_usage",
    "disk usage": "disk_usage",
    "memory": "memory",
    "ram": "memory",
    "uptime": "uptime",
    "boot time": "uptime",
    "processes": "processes",
    "running processes": "processes",
    "task list": "processes",
    "netstat": "netstat",
    "connections": "netstat",
    "open ports": "netstat",
}

# Default target for network commands when none is specified
_DEFAULT_TARGET = "8.8.8.8"

# Regex to extract an explicit hostname/IP from user input
_TARGET_RE = re.compile(
    r"(?:to|for|against|check|test|ping|trace|lookup)\s+([a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}|"
    r"\d{1,3}(?:\.\d{1,3}){3})",
    re.IGNORECASE,
)


def _detect_command(user_input: str) -> tuple[Optional[str], Optional[str]]:
    """Return (canonical_command_name, target) or (None, None) if unrecognised."""
    text = user_input.lower()
    cmd = None
    for keyword, canonical in _KEYWORD_MAP.items():
        if keyword in text:
            cmd = canonical
            break
    if cmd is None:
        return None, None

    target = _DEFAULT_TARGET
    match = _TARGET_RE.search(user_input)
    if match:
        target = match.group(1)

    return cmd, target


def validate(user_input: str, **kwargs) -> tuple[bool, str]:
    cmd, _ = _detect_command(user_input)
    if cmd is None:
        return (
            False,
            f"Could not identify a supported system command. "
            f"Supported operations: {', '.join(sorted(set(_KEYWORD_MAP.values())))}.",
        )
    return True, ""


def execute(user_input: str, context: dict, **kwargs) -> str:
    """Execute the detected system command synchronously and return output."""
    cmd_name, target = _detect_command(user_input)
    if cmd_name is None:
        return "Could not determine which system command to run."

    is_windows = platform.system().lower() == "windows"
    win_template, unix_template, description = _COMMANDS[cmd_name]
    template = win_template if is_windows else unix_template

    # Substitute {target} placeholder safely (no shell injection possible because
    # we use subprocess list form, not shell=True).
    argv = [part.replace("{target}", target) for part in template]

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=30,
            # Never use shell=True — prevents injection via target.
            shell=False,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        output = stdout or stderr or "(no output)"
        # Trim very long outputs
        if len(output) > 3000:
            output = output[:3000] + "\n... (output truncated)"
        return f"[{description}]\n{output}"
    except subprocess.TimeoutExpired:
        return f"Command timed out after 30 seconds: {' '.join(argv)}"
    except FileNotFoundError:
        return (
            f"Command not found: {argv[0]}. "
            "It may not be installed on this system."
        )
    except Exception as exc:
        return f"Command failed: {exc}"
```

---

#### Fix 5B — Update `src/core/constants.py`

Change the `INTENT_EXTENSION_MAPPING` entry for `SYSTEM_COMMAND`:
```python
# Before:
IntentType.SYSTEM_COMMAND: ["app_launcher", "system_info"],
# After:
IntentType.SYSTEM_COMMAND: ["system_command"],
```

Also add new intent keywords to `IntentRouter._quick_classify` in `src/llm/router.py`
so "check my latency", "ping google", "show disk space" etc. get classified as SYSTEM_COMMAND
without needing the router LLM:

Add a `_system_command_keywords` set to `__init__`:
```python
self._system_command_keywords = {
    "ping",
    "latency",
    "traceroute",
    "tracert",
    "nslookup",
    "ipconfig",
    "ifconfig",
    "netstat",
    "disk space",
    "disk usage",
    "free space",
    "ram usage",
    "memory usage",
    "cpu usage",
    "running processes",
    "task list",
    "system info",
    "uptime",
    "hostname",
    "my ip",
    "network config",
    "check connection",
    "internet speed",
    "open ports",
    "run script",
    "run command",
    "execute",
    "shell",
    "terminal",
    "cmd",
    "powershell",
    "bash",
}
```

Add a quick-classify check in `_quick_classify` (insert before the "questions" check):
```python
# Check system commands
for keyword in self._system_command_keywords:
    if keyword in input_lower:
        return self._create_result(IntentType.SYSTEM_COMMAND, confidence=0.88)
```

---

#### Fix 5C — Update system prompt

In `src/llm/prompts/system_prompts.py`, ensure the capabilities block explicitly tells the LLM:

- Sena CAN execute system commands via the `system_command` extension.
- When a user asks for a network check, latency measurement, disk space, etc., Sena MUST use the
  extension result rather than claiming she cannot interact with the system.
- Add a rule: "Never say you cannot interact with the local system. If the system_command extension
  returned output, report that output faithfully and interpret it for the user."

Find the function that builds the capabilities block (likely `build_system_prompt` or similar) and
append this rule to the static rules section. If the system prompt is a plain string constant,
add it as an explicit capability bullet point.

---

## Verification Checklist

After all fixes are applied:

| # | Test | Expected |
|---|------|----------|
| 1 | Send a message, open Logs tab | Exactly ONE group per request. All pipeline logs (memory, LLM, extensions) appear as children of that group. No orphan rows for the same session. |
| 2 | Cold-start app, send first message | No 40-second stall. Model warmup logs appear at app startup, not on first message. |
| 3 | Send message, watch ThinkingPanel | Panel populates with intent_classification, memory_retrieval, llm_processing stages in real time. |
| 4 | Wait for response, click "Thought process" toggle | Expands to show all captured stages. Not empty. |
| 5 | Type "check my latency to google.com" | Sena runs ping, reports RTT values from actual output. Does NOT say "I can't do that". |
| 6 | DevTools → WS → /ws | `processing_update` frames visible during every request. |

---

## Files Modified Summary

| File | Bug |
|------|-----|
| `src/api/deps.py` | Bug 4 — wire stage callback to ws_manager |
| `src/llm/models/model_registry.py` | Bug 2 — pre-load router model at startup |
| `src/core/constants.py` | Bug 5B — INTENT_EXTENSION_MAPPING fix |
| `src/llm/router.py` | Bug 5B — system_command quick-classify keywords |
| `src/llm/prompts/system_prompts.py` | Bug 5C — capabilities block update |
| `src/extensions/core/system_command.py` | Bug 5A — new extension (create from scratch) |
| `src/ui/behind-the-sena/src/tabs/Chat.tsx` | Bug 3 — liveStagesRef stale closure fix |
| `src/ui/behind-the-sena/src/tabs/Logs.tsx` | Bug 1 — groupChatLogs two-pass rewrite |

---

*Last updated: February 2026 — authored by diagnosis session prior to implementation context.*