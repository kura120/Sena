# Sena — Bug Fix Tracker

---

## ~~Bug 1 — Log Stack Grouping Is Broken~~ FIXED (PR #20)

> Two-pass `groupChatLogs` rewrite in `Logs.tsx`. Session-keyed buckets absorb all pipeline logs regardless of source. Clear button added. Watermark strategy in `logs.py` avoids WinError 32 on Windows.

---

## ~~Bug 2 — Router Model Warms Up on First Message (40s Stall)~~ FIXED (PR #21)

> In `ModelRegistry.initialize()`, after `switch_to(FAST)`, router model is eagerly pre-loaded. If router and fast share the same model name, `_is_loaded = True` is set directly (no duplicate warm-up).

---

## ~~Bug 3 — Thought Process Stages Missing After Response (Stale Closure)~~ FIXED (PR #30)

> Added `liveStagesRef = useRef<ThinkingStage[]>([])` in `Chat.tsx`. Synced ref inside every `setLiveStages` updater call. Replaced stale `[...liveStages]` capture with `[...liveStagesRef.current]` in `sendMessage`.

---

## ~~Bug 4 — ThinkingPanel Always Shows "Waiting" (WebSocket Stage Events Never Arrive)~~ FIXED (PR #26)

> Wired `_ws_stage_callback` to the Sena singleton in `src/api/deps.py` after `initialize()`. Every `sena.process()` call now emits `processing_update` WebSocket frames.

---

## ~~Bug 4b-A — ThinkingPanel Disappeared Completely During Loading~~ FIXED (PR #30)

> Changed `if (stages.length === 0) return null` to `if (stages.length === 0 && !isLive) return null`. Removed `liveStages.length > 0` gate so panel always mounts during loading and shows "Sena is thinking..." immediately.

---

## Bug 4b-B — Log Summarization Crashes (LLMManager.get_instance)

**Status:** Open — PR #20 pending approval

### Symptom
`Log summarization failed: type object 'LLMManager' has no attribute 'get_instance'`

### Fix — `src/api/routes/logs.py`
Replace `LLMManager.get_instance()` with `sena = await get_sena()` then `sena._llm_manager.generate_simple(...)`.

---

## Bug 5 — Sena Cannot Execute System Commands

**Status:** Not started

### Symptom
User asks "check my latency" and Sena says "I am an AI and cannot interact with your system" (hallucination).

### Root Cause
- `INTENT_EXTENSION_MAPPING[SYSTEM_COMMAND]` maps to `["app_launcher", "system_info"]` — neither exists in `src/extensions/core/`.
- System prompt does not enumerate real system capabilities.

### Fix (three files)
- Create `src/extensions/core/system_command.py` — ping, traceroute, nslookup, ipconfig, hostname, disk, memory, uptime, processes
- `src/core/constants.py` — update `INTENT_EXTENSION_MAPPING[SYSTEM_COMMAND]` to `["system_command"]`
- `src/llm/prompts/system_prompts.py` — add system command capabilities to prompt block

---

## Verification Checklist

| # | Test | Expected |
|---|------|----------|
| 1 | Send a message, open Logs tab | Exactly one group per request; pipeline logs appear as children |
| 2 | Cold-start app, send first message | No 40s stall; model warm-up logs appear at startup |
| 3 | Send a message, watch ThinkingPanel | "Sena is thinking..." header appears immediately; stages populate as they arrive |
| 4 | Wait for response, click "Thought process" | Expands to show all captured stages — not empty |
| 5 | DevTools > WS > /ws | `processing_update` frames visible during every request |
| 6 | Expand log group, click Summarize | LLM summary returns; no `get_instance` error |
| 7 | Type "check my latency to google.com" | Sena runs ping, reports real RTT values |