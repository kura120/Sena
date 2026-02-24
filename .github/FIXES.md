# Sena — Fix & Feature Instructions (Next Context Window)

Read this file top-to-bottom before touching any file.
Implement items in the order listed. One PR per item unless noted.

---

## Context You Must Load First

| File | Why |
|------|-----|
| `src/ui/behind-the-sena/src/tabs/Chat.tsx` | All UI bugs live here |
| `src/ui/behind-the-sena/src/utils/websocket.ts` | Singleton WS already implemented — just not used by Chat |
| `src/core/sena.py` | Pipeline orchestrator — reasoning step goes here |
| `src/core/constants.py` | ModelType, ProcessingStage enums |
| `src/config/settings.py` | Add reasoning_model config |
| `src/llm/models/model_registry.py` | Register + warm reasoning model |
| `src/api/websocket/manager.py` | Add llm_thinking event type |
| `src/llm/prompts/` | Add reasoning_prompts.py |

---

## Bug 1 — Processing Panel Disappears After Response (Should Collapse, Not Vanish)

**Status:** Open

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

**Status:** Open

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

**Status:** Not started — PR after Bug 1 and Bug 2 are fixed

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

**Status:** Not started — implement after Feature 1

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