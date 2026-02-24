# Sena — Bug Fix Tracker

---

## ~~Bug 1 — Log Stack Grouping Is Broken~~ ✅ FIXED (PR #20)

> Two-pass `groupChatLogs` rewrite in `Logs.tsx`. Session-keyed buckets absorb all pipeline logs regardless of source. Groups sort by last child timestamp. Clear button added. Watermark strategy in `logs.py` avoids WinError 32 on Windows.

---

## ~~Bug 2 — Router Model Warms Up on First Message (40s Stall)~~ ✅ FIXED (PR #21)

> In `ModelRegistry.initialize()`, after `switch_to(FAST)`, the router model is now eagerly pre-loaded. If router and fast share the same model name, `_is_loaded = True` is set directly (no duplicate warm-up). Otherwise `await router_info.client.load()` is called at startup.

---

## ~~Bug 3 — Thought Process Stages Missing After Response (Stale Closure)~~ ✅ FIXED (PR #24)

> Added `liveStagesRef = useRef<ThinkingStage[]>([])` in `Chat.tsx`. Synced ref inside every `setLiveStages` updater call (WS handler + `finally` reset). Replaced `const capturedStages = [...liveStages]` with `const capturedStages = [...liveStagesRef.current]` in `sendMessage`. Removed `liveStages` from `useCallback` deps (ref is stable, never triggers recreation).

---

## ~~Bug 4 — ThinkingPanel Always Shows "Waiting…" (WebSocket Stage Events Never Arrive)~~ ✅ FIXED (PR #26)

> Wired `_ws_stage_callback` to the Sena singleton in `src/api/deps.py` after `initialize()`. The callback converts `ProcessingStage` enum values to strings and calls `ws_manager.broadcast_processing_update()`. Every `sena.process()` call now emits `processing_update` WebSocket frames.

---

## ~~Bug 4b-A — ThinkingPanel Disappeared Completely During Loading~~ ✅ FIXED (PR #28)

> Changed `if (stages.length === 0) return null` → `if (stages.length === 0 && !isLive) return null` so the panel renders immediately in live mode with zero stages (shows "Sena is thinking…"). Removed `liveStages.length > 0` gate from the live render site so `ThinkingPanel` always mounts during `loading`.

---

## ~~Bug 4b-B — Log Summarization Crashes (`LLMManager.get_instance`)~~ ✅ FIXED (PR #20)

> `LLMManager` is not a singleton — `get_instance()` does not exist. Fixed in `src/api/routes/logs.py` (part of the logs overhaul in PR #20): replaced `LLMManager.get_instance()` with `await get_sena()` then `sena._llm_manager.generate_simple()`, reusing the already-initialized shared LLM manager.

---

## Bug 5 — Sena Cannot Execute System Commands

**Status:** Not started

### Symptom
User asks Sena to "check my latency" or run a system task. Sena responds with "I am an AI and cannot interact with your system" — a hallucination that contradicts her actual extension capabilities.

### Root Cause (two parts)
- **Part A:** `INTENT_EXTENSION_MAPPING[IntentType.SYSTEM_COMMAND]` lists `["app_launcher", "system_info"]` — neither extension exists in `src/extensions/core/`. No tool result → LLM hallucinates.
- **Part B:** System prompt does not enumerate what system-level actions Sena can actually perform.

### Fix (three files)
- `src/extensions/core/system_command.py` — new extension (ping, traceroute, hostname, uptime, disk, memory, process list)
- `src/core/constants.py` — update `INTENT_EXTENSION_MAPPING[SYSTEM_COMMAND]` to `["system_command"]`
- `src/llm/prompts/system_prompts.py` — update capabilities block to list system command actions

---

## Verification Checklist

| # | Test | Expected |
|---|------|----------|
| 1 | Send a message, open Logs tab | Exactly one group per request; pipeline logs appear as children |
| 2 | Cold-start app, send first message | No 40s stall; model warm-up logs appear at startup |
| 3 | Send a message, watch ThinkingPanel | "Sena is thinking…" header appears immediately; stages populate as they arrive |
| 4 | Wait for response, click "Thought process" | Expands to show all captured stages — not empty |
| 5 | DevTools → WS → /ws | `processing_update` frames visible during every request |
| 6 | Expand log group, click Summarize | LLM summary returns; no `get_instance` error |
| 7 | Type "check my latency to google.com" | Sena runs ping, reports real RTT values |