# Sena — Fix & Feature Instructions (Next Context Window)

Read this file top-to-bottom before touching any file.
Implement items in the order listed. One PR per item unless noted.
ALWAYS REFER TO [Rules](RULES.md)
---

## Context You Must Load First

| File | Why |
|------|-----|
| `src/ui/behind-the-sena/src/tabs/Chat.tsx` | All UI bugs live here |
| `src/ui/behind-the-sena/src/utils/websocket.ts` | Singleton WS already implemented — just not used by Chat |
| `src/core/sena.py` | Pipeline orchestrator — reasoning step, extension injection, memory unification |
| `src/core/constants.py` | ModelType, ProcessingStage enums |
| `src/core/bootstrapper.py` | Ollama check — must delegate to OllamaProcessManager |
| `src/core/local_domain.py` | Already built, not wired — needs calling from server startup |
| `src/core/elevation.py` | Already built, not wired — document intended usage |
| `src/config/settings.py` | Add reasoning_model config, OllamaProcessConfig, fix ollama_keep_alive type, remove dead fields |
| `src/llm/models/model_registry.py` | Register + warm reasoning model |
| `src/llm/models/ollama_client.py` | keep_alive type already handled at runtime — verify |
| `src/llm/router.py` | Race condition — bypasses per-model locking |
| `src/llm/manager.py` | Caches embedding client correctly — verify it's used everywhere |
| `src/memory/retrieval.py` | `extract_learnings()` is heuristic-only — replace with LLM-based extraction |
| `src/memory/embeddings.py` | Creates a new uninitialized `LLMManager` on every call — inject shared instance |
| `src/memory/long_term.py` | No deduplication before insert — add similarity check before storing |
| `src/memory/manager.py` | ChromaDB in requirements but never wired — use it or remove it |
| `src/api/server.py` | CORS wide-open — must use configured origins |
| `src/api/websocket/manager.py` | Add llm_thinking event type |
| `src/llm/prompts/` | Add reasoning_prompts.py |
| `src/memory/manager.py` | mem0 blocks event loop — fix async path |
| `src/memory/mem0_client.py` | Synchronous httpx call in async context, wrong logger — full rewrite or removal |

---

## ═══════════════════════════════════════════════
## BACKEND BUGS — Fix before any feature work
## ═══════════════════════════════════════════════

---

## Backend Bug 1 — Router Bypasses Per-Model Locking (Race Condition)

**Status:** ✅ DONE — `_llm_classify()` now uses `get_client()` with full circuit-breaker; per-model lock honoured
**Priority:** CRITICAL — breaks MAS concurrency
**File:** `src/llm/router.py`

### Symptom
Two concurrent requests arriving when the ROUTER model is not yet loaded will both
call `router_model.load()` simultaneously. The per-model `asyncio.Lock` in `ModelInfo`
is completely bypassed. This is the primary reason concurrent usage of multiple models
fails unpredictably.

### Root Cause
`_llm_classify()` uses `self._registry.get_model(ModelType.ROUTER)` which returns the raw
`BaseLLM` client without going through `ModelInfo.ensure_loaded()`. It then calls
`await router_model.load()` directly — skipping the double-checked locking mechanism that
was specifically built to prevent this exact race.

```python
# CURRENT (wrong) — in router.py _llm_classify():
router_model = self._registry.get_model(ModelType.ROUTER)
# ...
elif not router_model.is_loaded:
    await router_model.load()   # ← direct call, NO per-model lock
```

### Fix
Replace the entire model-access block in `_llm_classify()` with `get_client()`, wrapping
the circuit-breaker logic around the call rather than around a manual `load()`:

```python
# CORRECT
try:
    # Circuit breaker: if the router has failed recently, skip to fast model
    if time.monotonic() < self._router_circuit_open_until:
        logger.debug("Router circuit open — falling back to fast model")
        router_model = await self._registry.get_client(ModelType.FAST)
    else:
        try:
            router_model = await self._registry.get_client(ModelType.ROUTER)
            self._router_failure_count = 0  # reset on success
        except Exception as load_err:
            self._router_failure_count += 1
            logger.warning(f"Router model load failed ({self._router_failure_count}): {load_err}")
            if self._router_failure_count >= self._CIRCUIT_FAILURE_THRESHOLD:
                self._router_circuit_open_until = time.monotonic() + self._CIRCUIT_COOLDOWN
                logger.warning("Router circuit opened for 300s — using fast model")
            router_model = await self._registry.get_client(ModelType.FAST)
except Exception:
    return self._create_result(IntentType.GENERAL_CONVERSATION, confidence=0.3)
```

`get_client()` calls `ModelInfo.ensure_loaded()` which has the per-model lock.
Remove the old `get_model()` call and the manual `is_loaded` check entirely.

---

## Backend Bug 2 — Extension Results Are Never Injected Into the LLM Context

**Status:** ✅ DONE — `process()` and `stream()` both inject `ctx.extension_results` into `ctx.memory_context` before `generate()`
**Priority:** HIGH — extensions silently have zero effect on responses
**File:** `src/core/sena.py`

### Symptom
Extensions execute, produce output, but that output never reaches the LLM. The model
generates its response as if no extensions ran. No error is raised — the failure is silent.

### Root Cause
At the end of `_execute_extensions()`, `ext_lines` is built but never returned or appended
to context. The comment `"# This will be picked up by _retrieve_memory callers"` is wrong —
nothing picks it up:

```python
# CURRENT (wrong) — builds ext_lines then drops them
ext_lines = ["Extension results:"]
for name, result in successful.items():
    ext_lines.append(f"- {name}: {result.get('output', '')}")
# ext_lines is never returned or attached to anything
logger.debug(f"Extension results ready for context injection: {list(successful.keys())}")
return results   # results dict has outputs but caller never injects them into messages
```

### Fix
`_execute_extensions()` should return the extension output string alongside the results dict,
OR `sena.process()` / `sena.stream()` should inject `ctx.extension_results` into the message
list after the method returns. The cleanest fix is in the caller:

```python
# In process() / stream(), after _execute_extensions() returns:
if ctx.extension_results:
    successful_exts = {k: v for k, v in ctx.extension_results.items() if v.get("status") == "success"}
    if successful_exts:
        ext_lines = ["Extension results:"]
        for name, result in successful_exts.items():
            ext_lines.append(f"- {name}: {result.get('output', '')}")
        ctx.memory_context.append(
            Message(role=MessageRole.SYSTEM, content="\n".join(ext_lines))
        )
```

This append must happen BEFORE the `generate()` / `stream()` call, after `_execute_extensions()`.
Also remove the dead `ext_lines` block at the end of `_execute_extensions()`.

---

## Backend Bug 3 — CORS Is Hardcoded Wide Open

**Status:** ✅ DONE — `server.py` now reads `settings.api.cors.origins`; wildcard removed
**Priority:** HIGH — any web page can call Sena's API
**File:** `src/api/server.py`

### Symptom
`settings.api.cors.origins` is configured with a specific whitelist in `settings.py` but
is completely ignored. The server accepts requests from any origin.

### Root Cause
```python
# CURRENT (wrong) — ignores settings entirely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # dev shortcut never reverted
    ...
)
```

### Fix
```python
# CORRECT
_cors = settings.api.cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors.origins if _cors.enabled else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Backend Bug 4 — mem0 Blocks the Async Event Loop on Every Health Check

**Status:** ✅ DONE — mem0 removed entirely (Option B from Backend Debt 3); blocking call gone with it
**Priority:** HIGH — freezes all requests for up to 1.5 s on each /health call
**File:** `src/memory/mem0_client.py`

### Symptom
The Electron frontend polls `/health` regularly. Every call causes a 1.5-second stall
across ALL concurrent requests because `_ensure_local_memory()` contains a synchronous
`httpx.get()` that blocks the event loop:

```python
# CURRENT (wrong) — synchronous blocking call inside an async context
httpx.get(f"{self.mem0_ollama_base_url}/api/tags", timeout=1.5)
```

### Fix — Option A (preferred): Replace `httpx.get` with `asyncio.get_event_loop().run_in_executor`
```python
import asyncio, httpx
loop = asyncio.get_event_loop()
await loop.run_in_executor(
    None,
    lambda: httpx.get(f"{self.mem0_ollama_base_url}/api/tags", timeout=1.5)
)
```

### Fix — Option B (better long-term): Rewrite `mem0_client.py` entirely
The file has multiple additional issues beyond this one (see Backend Debt 3 below).
If doing a full rewrite, this blocking call disappears naturally.

---

## Backend Bug 5 — Two Disconnected Memory Systems in sena.py

**Status:** Open — partial: short-term still goes through `self._memory_repo.short_term` directly; full unification pending Memory Debt items
**Priority:** MEDIUM — causes inconsistent memory state between storage and retrieval
**File:** `src/core/sena.py`

### Symptom
Short-term memory reads go through `self._memory_repo.short_term` (direct repository).
Long-term memory reads go through `MemoryManager.get_instance().long_term` (singleton).
Long-term memory writes in `_post_process()` go through `MemoryManager.get_instance()`.
There is no single unified view of memory state.

### Root Cause
`_retrieve_memory()` splits access:
```python
# Short-term — direct repository
short_term = await self._memory_repo.short_term.get_session_buffer(...)

# Long-term — through MemoryManager singleton (different object)
mem_mgr = MemoryManager.get_instance()
long_term = await mem_mgr.long_term.search(...)
```

`_post_process()` also calls `MemoryManager.get_instance()` for storage, but the
`MemoryManager` instance is separate from the `MemoryRepository` used for short-term reads.

### Fix
Route ALL memory operations through `MemoryManager`. Remove the dual-path pattern.
`MemoryManager` should be the single source of truth for all memory access in `sena.py`.
`self._memory_repo` should only be used for conversation persistence (storing the full
turn in the `conversations` table), not for memory retrieval.

---

## ═══════════════════════════════════════════════
## BACKEND DEBT — Implement in order after bugs
## ═══════════════════════════════════════════════

---

## Backend Debt 1 — OllamaProcessManager Does Not Exist

**Status:** ✅ DONE — `src/llm/ollama_manager.py` exists and is wired into `LLMManager.initialize()` and `ModelRegistry.initialize()`
**Priority:** CRITICAL — root cause of all cold-start latency
**Files to create:** `src/llm/ollama_manager.py`
**Files to update:** `src/core/bootstrapper.py`, `src/config/settings.py`

### Context
The instructions (`copilot-instructions.md`) document `OllamaProcessManager` in full detail
as if it already exists. It does not. The file `src/llm/ollama_manager.py` is missing.
`bootstrapper._check_ollama()` still manually pings `GET /api/tags` via httpx with no
process management, no auto-start, and no concurrency verification.

This is the primary reason for cold-start latency: Ollama starts with
`OLLAMA_MAX_LOADED_MODELS=1` (CPU default), meaning the router and fast models evict each
other constantly. Nobody is setting `OLLAMA_MAX_LOADED_MODELS` before Sena starts.

### What to build — `src/llm/ollama_manager.py`

```python
class OllamaProcessManager:
    """Singleton — owns the Ollama process lifecycle."""

    async def ensure_running(self, settings: Settings) -> tuple[bool, str]:
        """
        If Ollama is already running: return (True, "already running").
        If not running and manage=True: find binary, start with env vars, wait for /api/tags.
        Sets OLLAMA_MAX_LOADED_MODELS = number of unique model names configured.
        Sets OLLAMA_NUM_PARALLEL = same value.
        Returns (success, message).
        """

    async def verify_concurrency(self, base_url: str, expected_model_names: list[str]) -> None:
        """
        After model preloading, call GET /api/ps.
        If fewer models are resident than expected, log a WARNING (non-fatal).
        Warning text should tell the user to set OLLAMA_MAX_LOADED_MODELS.
        """

    async def shutdown(self) -> None:
        """
        Stop Ollama only if WE started it (we_started=True flag).
        If Ollama was already running when Sena launched, do NOT kill it.
        """

def get_ollama_manager() -> OllamaProcessManager:
    """Return the singleton instance."""
```

Binary search order on Windows: `PATH` → `%LOCALAPPDATA%\Programs\Ollama\ollama.exe`

### Wire-up required

1. In `src/config/settings.py` — add to `LLMConfig`:
```python
class OllamaProcessConfig(BaseModel):
    manage: bool = True
    startup_timeout: int = 30

# Inside LLMConfig:
ollama_process: OllamaProcessConfig = Field(default_factory=OllamaProcessConfig)
```

2. In `src/core/bootstrapper.py` — replace `_check_ollama()` body:
```python
from src.llm.ollama_manager import get_ollama_manager
manager = get_ollama_manager()
success, message = await manager.ensure_running(self.settings)
# Return CheckResult based on success/message
```

3. In `src/llm/models/model_registry.py` — after `_preload_all_concurrent()`:
```python
from src.llm.ollama_manager import get_ollama_manager
expected = list({info.config.name for info in self._models.values() if info.config.name})
await get_ollama_manager().verify_concurrency(self._settings.llm.base_url, expected)
```

4. In `src/core/sena.py` or `src/main.py` — on shutdown:
```python
from src.llm.ollama_manager import get_ollama_manager
await get_ollama_manager().shutdown()
```

---

## Backend Debt 2 — Dead and Incorrect Config Fields in LLMConfig

**Status:** ✅ DONE — `switch_cooldown` and `allow_runtime_switch` removed; `ollama_keep_alive` typed as `int | str = -1`
**Priority:** MEDIUM — causes confusion, misleads future developers
**File:** `src/config/settings.py`

### Issues

1. `switch_cooldown: int = 5` — `switch_to()` is now a thin alias for `get_client()`.
   Cooldown logic was removed. This field does nothing. **Remove it.**

2. `allow_runtime_switch: bool = True` — no code reads this flag. **Remove it.**

3. `ollama_keep_alive: str = "-1"` — typed as `str` but the intent is an integer (`-1`).
   `OllamaClient._keep_alive_value()` already converts numeric strings to int at runtime,
   but the type annotation is misleading. **Change to `Union[int, str]` with default `-1` (int).**

### Fix
```python
# In LLMConfig — remove these two fields entirely:
# allow_runtime_switch: bool = True   ← DELETE
# switch_cooldown: int = 5            ← DELETE

# Change keep_alive type:
ollama_keep_alive: int | str = -1   # int -1 = keep loaded indefinitely
```

---

## Backend Debt 3 — mem0_client.py Needs Full Rewrite or Removal

**Status:** ✅ DONE — removed entirely; `mem0ai` removed from `requirements.txt`; `MemoryConfig.mem0` removed from `settings.py`; `MemoryManager` no longer references `Mem0Client`; `/health` endpoint cleaned up
**Priority:** MEDIUM — reliability risk, wrong logger, sync/async mixing
**File:** `src/memory/mem0_client.py`

### Issues

1. **Uses `loguru` directly** (`from loguru import logger`) instead of the project logger
   (`from src.utils.logger import logger`). Log messages from mem0 have no structured
   fields and don't appear in the session log context.

2. **`_ensure_local_memory()` is synchronous** and is called from async methods, blocking
   the event loop (see Backend Bug 4 above).

3. **`builtins.input` is monkey-patched** to suppress a mem0 interactive prompt:
   ```python
   builtins.input = lambda *_args, **_kwargs: "n"
   ```
   This is a dangerous global side-effect that affects the entire Python process.

4. **Update not supported in library mode** — `update_memory()` returns an error in the
   only mode that actually works offline.

5. **Tag search not supported in library mode** — `get_memories_by_tag()` returns empty
   in library mode.

### Decision required
Either:
- **Rewrite** `mem0_client.py` as a proper async class using `asyncio.get_event_loop().run_in_executor`
  for the synchronous mem0 library calls, using the project logger, removing the `builtins.input`
  patch (find a proper way to suppress the prompt or patch only locally).
- **Remove** mem0 integration entirely and rely solely on the custom `LongTermMemory` +
  embeddings system, which is already more capable for Sena's use case.

If removing: delete `mem0_client.py`, remove `Mem0Client` from `MemoryManager.__init__()`,
remove `mem0` from `requirements.txt`, remove `MemoryConfig.mem0` from `settings.py`,
and remove the `mem0_connected` check from the `/health` endpoint.

---

## Backend Debt 4 — Wire Up `local_domain.py` and `elevation.py`

**Status:** ✅ DONE — `setup_sena_local()` called in `server.py` lifespan startup; non-fatal on failure; `elevation.py` documented as installer/opt-in only
**Priority:** MEDIUM — these are complete implementations that are never called
**Files:** `src/core/local_domain.py`, `src/core/elevation.py`, `src/api/server.py`

### Context
`local_domain.py` registers `sena.local → 127.0.0.1` in the OS hosts file and flushes
the DNS cache. It is a complete, well-written async implementation. It is never called.

`elevation.py` provides UAC elevation (Windows) and sudo re-launch (Unix). It is complete.
It is never called.

Both files were clearly written with a vision: Sena as a local service accessible at
`http://sena.local` rather than `http://127.0.0.1:8000`. This is the right direction for
"behaving as part of the computer."

### Fix — `src/api/server.py` lifespan handler
Add to the startup section of the `lifespan` context manager:

```python
# Register sena.local in the OS hosts file (non-fatal if it fails)
try:
    from src.core.local_domain import setup_sena_local
    local_ok = await setup_sena_local()
    if local_ok:
        logger.info("sena.local is configured — accessible at http://sena.local")
    else:
        logger.info("sena.local not configured — using http://127.0.0.1:8000")
except Exception as e:
    logger.warning(f"local_domain setup failed (non-fatal): {e}")
```

### Note on elevation.py
`elevation.py`'s `ensure_admin()` is intentionally NOT called automatically at runtime —
requiring admin elevation on every launch is bad UX. It should only be called from an
installer/setup context, or gated behind a user opt-in. Document this clearly in the file.

---

## ═══════════════════════════════════════════════
## ARCHITECTURE — True MAS Refactor (Big Work)
## ═══════════════════════════════════════════════

---

## Architecture 1 — Sena Is Not a MAS: It Is a Request-Response Pipeline

**Status:** Planning
**Priority:** This is the root cause of "MAS isn't working"

### Current reality
The entire system collapses to a single sequential funnel:

```
User message → Sena singleton → LLMManager → classify → generate → done.
```

Nothing runs between messages. There are no background agents. The "MAS" label refers
to routing between model types (ROUTER, FAST, CRITICAL, CODE) — not to actual
autonomous agents with state, goals, and independent lifecycles.

### What real MAS requires for Sena
Persistent `asyncio.Task`s that run continuously, not only during a request:

```
MemoryAgent     — background task: continuously compresses, deduplicates,
                  and re-ranks long-term memories every N minutes.

PersonalityAgent — background task: runs inference on recent conversation
                   snapshots on a timer, not only every N messages in _post_process().

PlannerAgent    — receives a user task, breaks it into subtasks, maintains
                   task state between messages. Responds to follow-ups in context
                   of an ongoing plan.

ExecutorAgent   — carries out individual LLM generation subtasks. Multiple
                   instances can run concurrently for different subtasks.

MonitorAgent    — watches for system events (file changes, clipboard, hotkeys)
                   and pushes them into the agent message bus as stimuli.
```

### Communication pattern to adopt
Agents should communicate via `asyncio.Queue`, not via direct method calls.
Each agent owns an inbox queue. The orchestrator routes messages between agents.
This allows:
- Agents to be independently replaceable
- Multiple executor agents to run concurrently for parallel subtasks
- Non-blocking: a slow agent doesn't block the orchestrator

### Minimum viable first step
Before the full agent architecture, extract background tasks from `_post_process()` into
persistent `asyncio.Task` objects started in `Sena.initialize()`:

```python
# In Sena.initialize():
self._background_tasks = [
    asyncio.create_task(self._memory_compression_loop()),
    asyncio.create_task(self._personality_inference_loop()),
]

async def _memory_compression_loop(self):
    """Runs forever. Compresses long-term memory every 30 minutes."""
    while True:
        await asyncio.sleep(1800)
        try:
            await mem_mgr.extract_and_store_learnings(...)
        except Exception as e:
            logger.warning(f"Background memory compression failed: {e}")

async def _personality_inference_loop(self):
    """Runs forever. Runs personality inference on a timer."""
    while True:
        await asyncio.sleep(600)
        try:
            await pm.infer_from_conversation(...)
        except Exception as e:
            logger.warning(f"Background personality inference failed: {e}")
```

Cancel tasks in `Sena.shutdown()`.

### Full agent architecture (follow-up PR)
Design a `BaseAgent` class with:
- `inbox: asyncio.Queue`
- `async def run()` — the agent's event loop
- `async def handle(message: AgentMessage)` — process one message

Implement `AgentMessage` dataclass with `type`, `payload`, `reply_to`.
Build a lightweight `AgentBus` that routes messages between registered agents.
This is the foundation for true MAS and should live in `src/core/agents/`.

---

## Architecture 2 — "Behaves as Part of the Computer" Requirements

**Status:** Planning

### Vision
Sena should function as a persistent OS-level service, not a web app you open.
The following capabilities define what "part of the computer" means:

| Capability | Status | Notes |
|---|---|---|
| Accessible at `sena.local` | Built, not wired | Wire `local_domain.py` — see Backend Debt 4 |
| Runs as background service | Not started | Electron + PyInstaller packaging partially handles this |
| System tray presence | Not started | Electron provides `Tray` API |
| Global hotkey (e.g. Ctrl+Space) | Not started | Electron `globalShortcut` |
| Clipboard monitoring | Not started | Electron `clipboard` API + polling |
| File system awareness | Not started | `watchdog` (Python) or Electron `fs.watch` |
| OS notifications | Not started | Electron `Notification` API |
| Proactive behavior | Not started | Depends on Agent architecture above |

### Implementation order (suggested)
1. Wire `sena.local` (1 hour — already built)
2. System tray with show/hide + quit (Electron `Tray`)
3. Global hotkey to open/focus Sena
4. Background service: OS startup entry (Windows: registry `HKCU\...\Run`)
5. File system watcher → MonitorAgent → feed into agent message bus

---

## ═══════════════════════════════════════════════
## TESTING — No core tests exist. This is critical.
## ═══════════════════════════════════════════════

---

## Testing Debt 1 — Zero Tests for Core Backend Systems

**Status:** Open
**Priority:** HIGH — no safety net for any refactor

### Current state
Only 4 test files exist, all in `src/extensions/tests/`. No tests exist for:
- `src/llm/` (model registry, router, ollama client)
- `src/core/sena.py` (the entire pipeline)
- `src/memory/` (any memory operation)
- `src/api/routes/` (any HTTP endpoint)
- `src/config/settings.py`

### Minimum test suite to write (in priority order)

1. **`src/tests/test_model_registry.py`**
   - Test `ensure_loaded()` concurrent access does not cause double-load
   - Test `get_client()` raises `LLMModelNotFoundError` for unregistered model
   - Test `_preload_all_concurrent()` skips duplicate model names

2. **`src/tests/test_router.py`**
   - Test `_quick_classify()` returns correct intent for known keywords
   - Test circuit breaker opens after threshold failures
   - Test circuit breaker routes to FAST model while open

3. **`src/tests/test_sena_pipeline.py`**
   - Test `process()` with mocked LLMManager returns a response
   - Test extension results ARE injected into context (regression for Backend Bug 2)
   - Test memory retrieval is cancelled when intent does not need it

4. **`src/tests/test_memory.py`**
   - Test `remember()` stores and `recall()` retrieves
   - Test embedding fallback when embedding model is unavailable

5. **`src/tests/test_settings.py`**
   - Test `from_yaml()` loads correct values
   - Test `to_yaml()` + `reload_settings()` round-trips correctly

Use `pytest-asyncio` for all async tests. Mock Ollama HTTP with `respx` or `pytest-httpx`.

---

---

## Bug 1 — Processing Panel Disappears After Response (Should Collapse, Not Vanish)

**Status:** ✅ DONE — capture moved inside `try` block after `fetchJson` resolves; auto-collapse timeout wired; panel persists on message

### Symptom
After Sena sends a response, the "thought process" dropdown disappears entirely.
It should auto-collapse (closed) but remain openable by the user on the message.

### Root Cause — `src/ui/behind-the-sena/src/tabs/Chat.tsx`

Two problems:

**Problem A — stages are never saved into the message properly.**
`capturedStages = [...liveStagesRef.current]` is read BEFORE `fetchJson` resolves — at the
point the line runs, the ref is already cleared by the `finally` block racing with the capture.
Sequence is: `finally { setLiveStages([]); liveStagesRef.current = []; }` runs, THEN
`capturedStages` is read. Result: always empty.

Fix: move the capture to INSIDE the `try` block immediately after `await fetchJson(...)` resolves,
before `finally` can clear the ref:
```typescript
const data = await fetchJson<...>("/api/v1/chat", { ... });
const capturedStages = [...liveStagesRef.current]; // capture HERE, before finally clears
```

**Problem B — `thinkingOpen` state is ephemeral (not persisted).**
`thinkingOpen` is `useState<Record<string, boolean>>({})` — it resets on every re-render cycle
that unmounts Chat. When the panel re-renders after response, the key is gone so the panel
falls back to `open={thinkingOpen[msg.id] ?? true}` = true momentarily, then the component
re-evaluates `stages.length === 0 && !isLive` with empty stages and returns null.

Fix: after capture, always set `thinkingOpen[msgId] = capturedStages.length > 0`
(true = open initially). The panel must NOT return null when `isLive=false` and stages exist —
confirm `if (stages.length === 0 && !isLive) return null` is the only early-return guard
and that `capturedStages` actually has entries (Problem A fix above resolves this).

### Verification
Send a message. While loading the panel shows "Sena is thinking...". After response arrives:
- Panel collapses (closed) after ~1.2 s
- A "Processing" toggle is still visible on the message bubble
- Clicking it expands the panel showing all stages

---

## Bug 2 — WebSocket Creates Multiple Clients on Chat Open/Close

**Status:** ✅ DONE — Chat now uses `addMessageHandler` + `connectSharedSocket` singleton; raw `openWebSocket` call removed

### Symptom
Every time the Chat tab is opened or the component mounts, a new raw WebSocket connection
is created. Backend logs show multiple `/ws` connections. Closing and reopening Chat
accumulates connections.

### Root Cause — `src/ui/behind-the-sena/src/tabs/Chat.tsx`

The `useEffect` that sets up WebSocket calls `openWebSocket()` (line ~373), which always
creates a brand-new `WebSocket` instance. The singleton (`connectSharedSocket` +
`addMessageHandler`) already exists in `websocket.ts` but Chat never uses it.

```typescript
// CURRENT (wrong) — creates new socket every mount
socket = await openWebSocket("/ws", {
  onOpen: () => sendSubscription(socket!, ["processing"]),
  onMessage: handleMessage,
});

// CORRECT — reuses singleton, registers handler only
useEffect(() => {
  const unsubscribe = addMessageHandler(handleMessage);
  void connectSharedSocket("/ws", ["processing", "memory", "personality"]);
  return unsubscribe; // removes handler on unmount, socket stays alive
}, []);
```

### Fix — `src/ui/behind-the-sena/src/tabs/Chat.tsx`
Replace the entire WS `useEffect` with the singleton pattern above.
Import `connectSharedSocket` and `addMessageHandler` from `websocket.ts`.
Remove the `openWebSocket` and `sendSubscription` imports (no longer needed in Chat).
Remove `closeWebSocket` call from cleanup — singleton manages its own lifecycle.

### Verification
Open Chat tab → close it → open it again 3 times.
Backend terminal should show exactly ONE `/ws` connection total, not 3.

---

## Feature 1 — Rename + Clean Up Processing Panel

**Status:** ✅ DONE — dedup `reduceRight` logic in place in `sendMessage`; panel label cleaned up

### What
The current `ThinkingPanel` component shows pipeline stage events. It is being confused
with actual LLM thinking. Rename and clean it up:

- Rename component: `ThinkingPanel` → `ProcessingPanel`
- Rename toggle label: "Thought process" → "Processing"
- Deduplicate consecutive identical stage names
  (e.g. 3x "Classifying intent" in a row → show only the last one with its detail)
- Show only the last detail string per unique stage key, not every intermediate fire
- Keep collapse/expand behavior from Bug 1 fix

### Files
`src/ui/behind-the-sena/src/tabs/Chat.tsx` only.

### Dedup logic (simple)
```typescript
// After capturing stages, reduce to last-occurrence-per-stage:
const dedupedStages = capturedStages.reduceRight<ThinkingStage[]>((acc, s) => {
  if (!acc.find(x => x.stage === s.stage)) acc.unshift(s);
  return acc;
}, []);
```
Store `dedupedStages` as `thinkingStages` on the message instead of raw `capturedStages`.

---

## Feature 2 — Reasoning Pipeline + Thinking Panel (Main Feature)

**Status:** ✅ COMPLETE — all backend + frontend wiring done; reasoning_model default changed to `""` (no hardcode); configurable via Settings → LLM → Reasoning Pipeline toggle + model dropdown

### Architecture Decision (agreed with user)

```
User input
    ↓
Memory retrieval + Personality block assembled
    ↓
[REASONING model — deepseek-r1:14b]  ← NEW STEP
    Input:  user message + memories + personality + extension results
    Output: <think>...</think> block (raw chain-of-thought)
             + structured brief (2-3 sentences for fast model)
    ↓
[FAST model — gemma2:2b]
    Input:  original user message + reasoning brief
    Output: final response
    ↓
Response shown to user
```

The fast model stops trying to be smart — it articulates what the reasoning model worked out.
The reasoning model connects all the dots across memory and personality.
`gpt-oss:120b` (CRITICAL) stays for edge cases where reasoning+fast is insufficient.

### Installed model
`deepseek-r1:14b` — already pulled. Use this as `ModelType.REASONING`.

---

### Backend changes (one PR)

#### 1. `src/core/constants.py`
Add to `ModelType` enum:
```python
REASONING = "reasoning"
```
Add to `ProcessingStage` enum:
```python
REASONING = "reasoning"
```

#### 2. `src/config/settings.py`
Add inside `LLMConfig` (or equivalent model config section):
```python
reasoning_model: str = "deepseek-r1:14b"
reasoning_enabled: bool = True
```

#### 3. `src/llm/models/model_registry.py`
Register the reasoning model the same way FAST/CRITICAL/CODE are registered.
In `initialize()`, after warming FAST and ROUTER, also warm REASONING:
```python
if ModelType.REASONING in self._models:
    await self._models[ModelType.REASONING].client.load()
```

#### 4. `src/api/websocket/manager.py`
Add to `WSEventType`:
```python
LLM_THINKING = "llm_thinking"
```
Add broadcast method:
```python
async def broadcast_llm_thinking(self, think_content: str, brief: str) -> None:
    msg = WSMessage(
        type=WSEventType.LLM_THINKING,
        data={"think_content": think_content, "brief": brief},
    )
    await self.broadcast(msg, channel="processing")
```

#### 5. `src/llm/prompts/reasoning_prompts.py` (new file)
```python
REASONING_PROMPT = """You are Sena's reasoning engine. Think through the user's request carefully.

You have access to:
- Relevant memories: {memories}
- User personality profile: {personality}
- Extension results (if any): {extensions}

User message: {user_message}

Think step by step inside <think> tags. Then outside the tags write a concise brief
(2-3 sentences max) that the response model will use to form its reply.
The brief should state: what the user needs, any relevant context from memory/personality,
and the recommended tone/approach.
"""

def build_reasoning_prompt(
    user_message: str,
    memories: str,
    personality: str,
    extensions: str = "None",
) -> str:
    return REASONING_PROMPT.format(
        user_message=user_message,
        memories=memories or "None",
        personality=personality or "None",
        extensions=extensions,
    )
```

#### 6. `src/core/sena.py`
Insert a new `REASONING` step between `MEMORY_RETRIEVAL` and `LLM_PROCESSING`:

```python
# After memory retrieval, before LLM processing:
if self._settings.llm.reasoning_enabled:
    ctx.set_stage(ProcessingStage.REASONING)
    reasoning_prompt = build_reasoning_prompt(
        user_message=user_input,
        memories="\n".join(m.content for m in memories),
        personality=personality_block,
        extensions=extension_output or "None",
    )
    raw_reasoning = await self._llm_manager.generate_with_model(
        ModelType.REASONING, reasoning_prompt
    )
    # Parse <think> block out of response
    think_match = re.search(r"<think>(.*?)</think>", raw_reasoning, re.DOTALL)
    think_content = think_match.group(1).strip() if think_match else ""
    # Everything after </think> is the structured brief
    brief = re.sub(r"<think>.*?</think>", "", raw_reasoning, flags=re.DOTALL).strip()

    # Emit to frontend via WebSocket
    await ws_manager.broadcast_llm_thinking(think_content, brief)

    # Append brief to the fast model's context
    extra_context = f"\n\n[Reasoning brief]: {brief}" if brief else ""
else:
    extra_context = ""
    think_content = ""
    brief = ""

# Then pass extra_context into the fast model prompt
```

`generate_with_model(model_type, prompt)` — add this method to `LLMManager` if it does not
exist. It should call the specific model type directly, bypassing the router.

---

### Frontend changes (same PR as backend)

#### `src/ui/behind-the-sena/src/tabs/Chat.tsx`

**New data on ChatMessage type:**
```typescript
type ChatMessage = {
  // ... existing fields ...
  thinkingStages?: ThinkingStage[];   // pipeline stages (ProcessingPanel)
  llmThinking?: {                      // reasoning model output (ThinkingPanel)
    think_content: string;
    brief: string;
  };
};
```

**Capture `llm_thinking` WS event** alongside `processing_update` in the WS handler:
```typescript
if (payload.type === "llm_thinking") {
  const data = payload.data as { think_content: string; brief: string };
  setLiveThinking(data); // new useState<{think_content,brief}|null>(null)
}
```
Also add `liveThinkingRef` mirror (same pattern as `liveStagesRef`) so it is captured
correctly in `sendMessage` without stale closure.

**Capture in sendMessage** (same place as `capturedStages`):
```typescript
const capturedThinking = liveThinkingRef.current;
// store on senaMsg:
llmThinking: capturedThinking ?? undefined,
```

**New `ThinkingPanel` component** (keep old one renamed to `ProcessingPanel`):
```
[ Thinking  ▾ ]                          ← collapsible, open by default
  Raw thoughts:
    <scrollable pre block>
      ... deepseek-r1 <think> content ...
    </pre>
  Response brief:
    <p> brief text </p>
```
Show above `ProcessingPanel`, below nothing (so order top-to-bottom is):
```
ThinkingPanel   (llm reasoning)
ProcessingPanel (pipeline stages)
message bubble
```

**Layout in JSX** — for per-message view:
```tsx
{msg.llmThinking && (
  <ThinkingPanel thinking={msg.llmThinking} open={...} onToggle={...} />
)}
{msg.thinkingStages && msg.thinkingStages.length > 0 && (
  <ProcessingPanel stages={msg.thinkingStages} open={...} onToggle={...} />
)}
```

For live view (during loading):
```tsx
{liveThinking && <ThinkingPanel thinking={liveThinking} isLive />}
<ProcessingPanel stages={liveStages} isLive />
```

---

### Settings UI (same PR)

In `src/ui/behind-the-sena/src/components/forms/LLMModelSettingsForm.tsx`:
- Add a text input for `reasoning_model` (default: `deepseek-r1:14b`)
- Add a toggle for `reasoning_enabled`

These read/write via `GET /api/v1/settings` and `POST /api/v1/settings`.

---

---

## ═══════════════════════════════════════════════
## MEMORY SYSTEM DEBT — Fix after reasoning pipeline
## ═══════════════════════════════════════════════

---

## Memory Debt 1 — `extract_learnings()` Is Heuristic-Only, Not AI-Powered

**Status:** Open
**Priority:** HIGH — the single biggest gap vs mem0; most conversation facts are silently never stored
**File:** `src/memory/retrieval.py`

### Problem
`extract_learnings()` scans conversation lines for hardcoded string patterns
(`"I learned"`, `"User prefers"`, `"Note:"`, etc.). If those exact strings don't appear,
nothing is stored — regardless of how much useful information was in the conversation.
A message like "my name is Alex and I work at Google" stores nothing because it doesn't
match any pattern.

This is the root cause of Sena appearing to forget things immediately.

### Current (wrong) code
```python
learning_patterns = {
    "I learned", "I discovered", "User mentioned",
    "User prefers", "User likes", ...
}
for pattern in learning_patterns:
    if pattern.lower() in line.lower():
        learnings.append(line)
        break
```

### Fix
Replace the heuristic loop with an LLM call. Use `LLMManager.generate_simple()` with a
prompt that asks the model to extract a JSON array of facts worth remembering.

```python
# src/memory/retrieval.py — new extract_learnings()
async def extract_learnings(
    self, conversation: str, llm_manager=None
) -> list[str]:
    """Extract key learnings from conversation using LLM."""
    if not conversation or not conversation.strip():
        return []

    # Lazy import to avoid circular dependency
    if llm_manager is None:
        try:
            from src.llm.manager import LLMManager
            llm_manager = LLMManager.get_instance()
        except Exception:
            return []

    EXTRACTION_PROMPT = """You are an AI memory extraction system.
Read the following conversation and extract ONLY facts that are worth
remembering long-term about the user — preferences, personal details,
stated goals, recurring topics, or anything Sena should recall later.

Output a JSON array of short fact strings. Each fact must be:
- Self-contained (understandable without the conversation)
- Specific (not vague like "user talked about things")
- About the USER, not about Sena

If there are no memorable facts, return an empty array: []

Conversation:
{conversation}

JSON array of facts:"""

    try:
        raw = await llm_manager.generate_simple(
            prompt=EXTRACTION_PROMPT.format(conversation=conversation[-3000:]),
            max_tokens=512,
            temperature=0.1,
        )
        # Parse JSON — strip markdown fences if present
        import json, re
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        facts = json.loads(raw)
        if isinstance(facts, list):
            return [str(f).strip() for f in facts if str(f).strip()]
        return []
    except Exception as e:
        logger.warning(f"LLM extraction failed, falling back to heuristics: {e}")
        # Minimal heuristic fallback
        return [
            line.strip() for line in conversation.splitlines()
            if any(p in line.lower() for p in ("my name is", "i prefer", "i work", "i like", "i hate", "remember that"))
        ]
```

### Wire-up required
`MemoryManager.extract_and_store_learnings()` calls `retrieval_engine.extract_learnings(conversation)`.
Update it to pass the shared `LLMManager` instance:

```python
# src/memory/manager.py — extract_and_store_learnings()
# Add llm_manager param and thread it through to extract_learnings:
from src.llm.manager import LLMManager
llm_mgr = LLMManager.get_instance() if LLMManager._instance else None
learnings = await self.retrieval_engine.extract_learnings(
    conversation=conversation,
    llm_manager=llm_mgr,
)
```

Also add `get_instance()` singleton pattern to `LLMManager` so the shared instance
can be retrieved without re-initializing:

```python
# src/llm/manager.py
_instance: Optional["LLMManager"] = None

@classmethod
def get_instance(cls) -> Optional["LLMManager"]:
    return cls._instance

@classmethod
def set_instance(cls, instance: "LLMManager") -> None:
    cls._instance = instance
```

Call `LLMManager.set_instance(self._llm_manager)` inside `Sena.initialize()` after
the manager is ready.

---

## Memory Debt 2 — EmbeddingsHandler Creates a New Uninitialized LLMManager on Every Call

**Status:** Open
**Priority:** HIGH — wasteful, fragile, creates a new OllamaClient on every single embedding
**File:** `src/memory/embeddings.py`

### Problem
```python
# CURRENT (wrong) — creates a brand-new, uninitialized LLMManager on every call
async def generate_embedding(self, text: str) -> Optional[list[float]]:
    from src.llm.manager import LLMManager
    llm_manager = LLMManager()          # ← fresh instance, never initialized
    embedding = await llm_manager.get_embeddings(text=text, ...)
```

`get_embeddings()` internally creates yet another throwaway `OllamaClient`, calls it,
then discards it. This means every embedding generation opens and closes an HTTP
connection with no connection reuse. Under load (e.g. storing 20 memories) this
hammers Ollama with 20 separate cold-start connections.

### Fix
Inject the shared `LLMManager` instance rather than constructing a new one.
`EmbeddingsHandler` should accept an optional `llm_manager` parameter:

```python
# src/memory/embeddings.py
class EmbeddingsHandler:
    def __init__(
        self,
        model_name: str = "nomic-embed-text:latest",
        llm_manager=None,
    ):
        self.model_name = model_name
        self._llm_manager = llm_manager  # injected; falls back to creating one if None

    async def generate_embedding(self, text: str) -> Optional[list[float]]:
        if not text or not text.strip():
            return None
        try:
            mgr = self._llm_manager
            if mgr is None:
                from src.llm.manager import LLMManager
                mgr = LLMManager.get_instance()
            if mgr is None:
                return None
            return await mgr.get_embeddings(text=text, model_name=self.model_name)
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
```

Update `MemoryManager.__init__()` to pass the LLM manager to `EmbeddingsHandler`:

```python
# src/memory/manager.py — __init__
self.embeddings = EmbeddingsHandler(
    model_name=settings.memory.embeddings.model,
    llm_manager=None,  # set later via set_llm_manager() once LLM is ready
)

def set_llm_manager(self, llm_manager) -> None:
    """Inject the initialized LLM manager so embeddings reuse the connection."""
    self.embeddings._llm_manager = llm_manager
    self.long_term._embeddings_handler = self.embeddings
```

Call `MemoryManager.get_instance().set_llm_manager(self._llm_manager)` inside
`Sena.initialize()` after both LLM and memory are ready.

---

## Memory Debt 3 — Long-Term Memory Has No Deduplication

**Status:** Open
**Priority:** MEDIUM — same fact gets stored dozens of times across sessions; search results polluted with duplicates
**File:** `src/memory/long_term.py`, `src/memory/manager.py`

### Problem
`LongTermMemory.add()` unconditionally inserts a new row every time. There is no check
for whether the same (or very similar) fact already exists. After a few weeks of use
the database will contain hundreds of near-duplicate rows like:
- "User's name is Alex"
- "The user's name is Alex"
- "Alex is the user's name"

These clog search results and degrade retrieval quality.

### Fix
In `MemoryManager.remember()`, before calling `long_term.add()`, search for existing
memories with high cosine similarity (>= 0.92). If one is found, skip the insert:

```python
# src/memory/manager.py — remember()
async def remember(self, content: str, metadata: Optional[dict] = None) -> dict[str, Any]:
    embedding = await self.embeddings.generate_embedding(content)

    # Deduplication: skip if a near-identical memory already exists
    if embedding is not None:
        existing = await self.long_term.search(
            query=content,
            embedding=embedding,
            k=1,
        )
        if existing and existing[0].get("relevance", 0) >= 0.92:
            logger.debug(
                f"Skipping duplicate memory (similarity={existing[0]['relevance']:.3f}): {content[:60]}"
            )
            return {"memory_id": existing[0]["memory_id"], "status": "duplicate_skipped"}

    result = await self.long_term.add(content=content, metadata=metadata, embedding=embedding)
    # ... rest of method unchanged
```

The threshold `0.92` is conservative — only near-verbatim duplicates are skipped.
Lower it to `0.85` if you want more aggressive deduplication (catches paraphrases too).

---

## Memory Debt 4 — ChromaDB Is in Requirements But Never Used

**Status:** Open
**Priority:** LOW — not a bug, but chromadb adds ~300 MB of install weight for zero benefit
**Files:** `src/memory/long_term.py`, `requirements.txt`, `src/config/settings.py`

### Problem
`chromadb>=0.4.22` is listed in `requirements.txt`. `VectorDBConfig` exists in
`settings.py` with `provider: str = "chroma"`. But `LongTermMemory` never imports or
uses ChromaDB — it does its own cosine similarity in SQLite + numpy.

The custom SQLite approach is fine for up to ~10,000 memories (loads all embeddings
into RAM for comparison). Beyond that it becomes slow.

### Decision required — pick one:

**Option A — Remove ChromaDB (recommended for now)**
- Delete `chromadb` from `requirements.txt`
- Remove `VectorDBConfig` from `settings.py`
- Accept the SQLite approach until scale demands otherwise
- When Sena's memory grows to 10k+ entries, revisit

**Option B — Wire ChromaDB as the embedding store**
- Replace SQLite embedding columns with ChromaDB collection
- Keep SQLite only for content + metadata (source of truth)
- ChromaDB handles ANN search; SQLite handles structured queries
- More complex but scales to millions of memories
- Implementation: `LongTermMemory` gets a `chroma_client` field; `add()` calls
  `collection.add()`; `search()` calls `collection.query()` instead of numpy loop

If choosing Option B, `VectorDBConfig.persist_dir` must be resolved via
`resolve_data_path()` (same pattern as the SQLite DB path) so it lands under
`%APPDATA%/Sena/data/memory/chroma` in production.

---

## Verification Checklist

| # | Test | Expected |
|---|------|----------|
| 1 | Send message, response arrives | ProcessingPanel collapses to toggle — does NOT disappear |
| 2 | Click "Processing" toggle on old message | Expands showing deduped pipeline stages |
| 3 | Open/close Chat tab 3 times | Backend shows exactly 1 WS connection |
| 4 | Send message with reasoning enabled | "Thinking" panel appears above message with raw deepseek-r1 thoughts + brief |
| 5 | Send message with reasoning disabled | No Thinking panel; ProcessingPanel only |
| 6 | DevTools > WS | See both `processing_update` and `llm_thinking` event types |
| 7 | Check Settings > LLM | reasoning_model field and toggle present |
| 8 | Tell Sena "my name is Alex and I work at Google", send a second message, check DB | `memory_long_term` table contains a row with "Alex" and "Google" — LLM extraction working |
| 9 | Tell Sena the same fact twice (two separate messages) | Second insert is skipped — `duplicate_skipped` status in logs; DB row count stays the same |
| 10 | Add 5 memories rapidly (e.g. via `/api/v1/memory` POST in a loop) | Backend logs show a single Ollama embedding connection reused, not 5 separate ones |
| 11 | `pip show chromadb` after Memory Debt 4 Option A | Package not installed; no import errors on startup |