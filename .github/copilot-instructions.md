# Sena - AI Agent Development Guidelines

This document defines the structure, philosophy, and rules for developing Sena. It is prescriptive and enforced. If anything is unclear or conflicts with your implementation approach, **ask the user directly before proceeding**.

---

## Core Philosophy

### 1. Module-Based, Pipeline-Driven Architecture
Sena is built as **stackable modules**, where each layer reinforces and extends previous ones:

```
Foundation:     LLM Manager (Ollama routing)
    ↓
Layer 1:        Core Orchestrator (Sena class)
    ↓
Layer 2:        Memory System (short-term + long-term + embeddings)
    ↓
Layer 3:        Extensions (dynamic loading, dependency resolution)
    ↓
Layer 4:        API Routes (Chat, Memory, Extensions, Telemetry, Logs, Settings)
    ↓
Layer 5:        Frontend Components (UI tabs, reusable elements)
    ↓
Layer 6:        WebSocket/Real-time Updates (memory events, processing stages)
```

**Rule**: When adding new features, identify which layer they belong to. Do not skip layers. Do not create circular dependencies.

### 2. Build-Ready, Not Half-Baked
Every feature must have:
- Clear structure and hierarchy in the project
- No hard-coded values (everything in config or constants)
- UI control mechanism (user-facing settings)
- Proper error handling and graceful degradation
- Tests or validation approach
- Documentation in this file if it introduces new patterns

**Rule**: If a feature feels incomplete or you're unsure about structure, ask the user before continuing.

### 3. UI-First Configurability
**All user-facing settings must be changeable via the Settings tab (behind-the-sena).**

**Categories**:
- **User Settings** (Settings tab): Model selection, hotkeys, provider choice, etc.
- **System Settings** (config files): Database paths, logging levels, internal timeouts
- **Useless Settings**: Don't add toggles for values that users shouldn't touch

**Rule**: If you add a configurable value, add a UI control for it unless it's system-level.

### 4. Offline-First, Explicit Internet Requirements
Sena should work without internet access unless explicitly marked otherwise.

**Rule**: 
- Non-critical APIs must fail gracefully with clear messages
- Features requiring internet must have a clear `@RequiresInternet` marker or equivalent
- Default behavior assumes offline operation
- Cache external data locally when possible

### 5. Component Reusability (DRY for UI)
Reusable UI components live in `src/ui/behind-the-sena/src/components/` and can be imported/reused across tabs without rewriting code.

**Rule**: If you write a UI component twice, extract it. Shared components = maintainability.

### 6. Questions & Doubts Protocol
**If you are unsure about implementation approach, ask the user DIRECTLY before proceeding.**

Do not:
- Leave comments asking for clarification
- Proceed with half-baked assumptions
- Guess the intended structure

Do:
- Ask explicitly in plain language
- Wait for user response
- Clarify unclear requirements

---

## Architecture Overview

### Two-Tier Deployment Model
Sena uses a **distributed local architecture** optimized for GitHub CI/CD:

```
┌─────────────────────────────────────────┐
│  Frontend: Electron App (Behind-the-Sena)│
│  - Built with: React 18 + TypeScript     │
│  - Styling: Tailwind CSS (dark theme)    │
│  - Execution: npm run build + packaging  │
│  - Uses: System IPC for OS interactions  │
│  - Calls: Python API at localhost:8000   │
└────────────────┬────────────────────────┘
                 │ HTTP to localhost:8000
┌────────────────▼────────────────────────┐
│  Backend: FastAPI Server (Python)        │
│  - Entry: src/main.py or python -m uvicorn
│  - Port: 8000 (localhost only)           │
│  - API: /api/v1/{routes}                 │
│  - WebSocket: /ws                        │
│  - Static Files: Serves built React UI   │
│  - Execution: PyInstaller for .exe       │
└──────────────────────────────────────────┘
   │
   ├─→ Ollama (http://localhost:11434)
   ├─→ SQLite (data/memory/sena.db)
   ├─→ Extensions (src/extensions/)
   └─→ Configuration (settings.yaml)
```

### Module Hierarchy & Communication Rules

**Backend Module Layers** (ordered by abstraction):

1. **Config Layer** (`src/config/settings.py`)
   - Single source of truth for all settings
   - Loaded from `settings.yaml` (user-editable)
   - No other module should hard-code configuration
   - Dependency: None

2. **Database Layer** (`src/database/`)
   - SQLite connection management
   - Repository pattern for data access
   - Async operations only (aiosqlite)
   - Dependency: Config

3. **LLM Layer** (`src/llm/`)
   - Ollama client wrapper
   - Model registry and switching
   - Health checks and timeouts
   - Dependency: Config

4. **Core Services** (`src/core/` + `src/memory/` + `src/extensions/`)
   - Sena orchestrator (main coordinator)
   - Memory manager (short/long-term)
   - Extension manager (dynamic loading)
   - Dependency: Database, LLM, Config

5. **API Routes** (`src/api/routes/`)
   - Expose core services via HTTP
   - Consistent response models
   - WebSocket events for real-time updates
   - Dependency: Core Services

6. **Frontend** (`src/ui/behind-the-sena/src/`)
   - React components
   - Fetch from API routes
   - WebSocket subscriptions
   - Dependency: API Routes (HTTP/WS)

**Communication Rules**:
- ✅ **Allowed**: Layer N calls Layer N-1 (down the stack)
- ✅ **Allowed**: Sibling layers via dependency injection
- ✅ **Allowed**: API routes publish WebSocket events
- ❌ **Forbidden**: Layer N-1 calls Layer N (up the stack)
- ❌ **Forbidden**: Circular dependencies
- ❌ **Forbidden**: Frontend directly accessing backend files

---

## Project Structure Reference

### Backend (`src/`)

```
src/
├── main.py                          # CLI entry point (modes: cli, test, normal)
├── api/
│   ├── server.py                    # FastAPI app, middleware, routes
│   ├── routes/                      # Organized by domain
│   │   ├── chat.py                  # /api/v1/chat
│   │   ├── memory.py                # /api/v1/memory
│   │   ├── extensions.py            # /api/v1/extensions
│   │   ├── telemetry.py             # /api/v1/telemetry
│   │   ├── logs.py                  # /api/v1/logs
│   │   ├── settings.py              # /api/v1/settings (NEW)
│   │   ├── debug.py                 # /api/v1/debug
│   │   └── processing.py            # /api/v1/processing
│   ├── models/
│   │   ├── requests.py              # Request schemas (Pydantic)
│   │   └── responses.py             # Response schemas
│   ├── deps.py                      # Dependency injection
│   └── websocket/
│       └── manager.py               # WebSocket connection management
├── core/
│   ├── sena.py                      # Main orchestrator
│   ├── bootstrapper.py              # System initialization
│   ├── telemetry.py                 # Metrics & event tracking
│   ├── error_handler.py             # Error handling middleware
│   ├── constants.py                 # Enums (ModelType, ProcessingStage, etc.)
│   └── exceptions.py                # Custom exceptions
├── config/
│   └── settings.py                  # Configuration (Pydantic Settings)
├── database/
│   ├── connection.py                # aiosqlite setup
│   ├── models/                      # Data models (SQLAlchemy-like)
│   └── repositories/                # Data access layer
│       ├── conversation_repo.py
│       ├── memory_repo.py
│       ├── telemetry_repo.py
│       └── extension_repo.py
├── llm/
│   ├── manager.py                   # LLM orchestrator
│   ├── router.py                    # Intent-based routing
│   └── models/
│       ├── base.py                  # BaseLLM interface
│       ├── ollama_client.py         # Ollama implementation
│       └── model_registry.py        # Multi-model management
├── memory/
│   ├── manager.py                   # Memory orchestrator
│   ├── short_term.py                # Conversation context
│   ├── long_term.py                 # Persistent learning
│   ├── mem0_client.py               # mem0 integration
│   ├── embeddings.py                # Vector embeddings
│   └── retrieval.py                 # Memory search & ranking
├── extensions/
│   ├── __init__.py                  # ExtensionManager singleton
│   ├── core/                        # Built-in extensions
│   │   ├── web_search.py
│   │   └── file_search.py
│   ├── user/                        # User-created extensions
│   └── generated/                   # AI-generated extensions
└── utils/
    └── logger.py                    # Structured logging
```

### Frontend (`src/ui/behind-the-sena/src/`)

```
src/ui/behind-the-sena/src/
├── App.tsx                          # Router & main component
├── main.tsx                         # React entry point
├── index.css                        # Global styles
├── components/                      # Reusable UI components
│   ├── ChatTab.tsx
│   ├── MemoryTab.tsx
│   ├── SettingsTab.tsx
│   ├── LogsTab.tsx
│   ├── ExtensionsTab.tsx
│   ├── TelemetryTab.tsx
│   ├── MemoryCard.tsx               # Example reusable component
│   └── (other shared components)
├── tabs/                            # Full tab implementations
│   ├── ChatContent.tsx
│   ├── MemoryContent.tsx
│   ├── SettingsContent.tsx
│   └── (other tabs)
├── windows/                         # Larger UI sections
│   ├── LoaderWindow.tsx             # Boot sequence display
│   └── DashboardWindow.tsx          # Main interface
└── utils/                           # Helper functions
    ├── api.ts                       # HTTP client
    └── websocket.ts                 # WebSocket utilities
```

---

## Critical Patterns & Rules

### Pattern 1: API Route Implementation
All routes must follow this structure:

```python
# src/api/routes/[domain].py
from fastapi import APIRouter, HTTPException, Depends
from src.core.sena import Sena

router = APIRouter(prefix="/[domain]", tags=["[Domain]"])

async def get_[service]() -> [Service]:
    """Dependency injection."""
    return [Service].get_instance()

@router.get("/endpoint", response_model=dict)
async def get_endpoint(
    param: str,
    service: [Service] = Depends(get_[service])
) -> dict:
    """Endpoint description."""
    try:
        result = await service.operation(param)
        return {
            "status": "success",
            "data": result,
            "message": "Operation completed"
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Rules**:
- Always use async/await
- Always wrap responses consistently
- Always handle exceptions
- Always use dependency injection for service access

### Pattern 2: UI Components (Reusable)
Extract any component used more than once:

```typescript
// src/ui/behind-the-sena/src/components/ReusableComponent.tsx
import React from "react"
import { Icon } from "lucide-react"

interface Props {
  value: string
  onChange: (value: string) => void
  label?: string
}

export const ReusableComponent: React.FC<Props> = ({
  value,
  onChange,
  label
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded p-3">
      {label && <label className="text-xs text-slate-400">{label}</label>}
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-slate-950 text-slate-50 rounded px-2 py-1"
      />
    </div>
  )
}
```

**Rules**:
- Use TypeScript interfaces for props
- Use lucide-react for icons (not emojis)
- Use dark theme colors (slate-950, purple-500)
- Export as named export
- One component per file
- Keep logic minimal (move to parent or utils)

### Pattern 3: Settings Management
Settings flow from Config → UI → Back to Config:

```
settings.py (default values)
    ↓
settings.yaml (user edits or API writes)
    ↓
/api/v1/settings/* (API endpoints to read/write)
    ↓
SettingsContent.tsx (UI form)
    ↓
Save → POST to /api/v1/settings/* → Update settings.yaml → Reload
```

**Rules**:
- Always persist to `settings.yaml` on change
- Always call `reload_settings()` after updates
- Always fetch fresh settings in UI on mount
- UI should display current values, never assume

### Pattern 4: Memory System Integration
Memory flows: User Input → Short-term → Long-term (+ embeddings) → Retrieval:

```python
# Store memory
await memory_mgr.remember(
    content="The number is 6",
    metadata={"source": "user_input"}
)

# Retrieve memory
results = await memory_mgr.recall(query="What number was stored?", k=5)

# Emit WebSocket event
await ws_manager.broadcast_memory_update(
    action="stored",
    memory_id=memory_id,
    details={"content": content, "metadata": metadata}
)
```

**Rules**:
- All memory operations are async
- Always emit WebSocket events after storage
- Always include metadata for context
- Always handle embedding failures gracefully

### Pattern 5: Extension Architecture
Extensions are dynamically loaded, validated, and executed:

```python
# src/extensions/core/[name].py
VERSION = "1.0.0"
METADATA = {
    "name": "Extension Name",
    "description": "What it does",
    "author": "Your Name",
    "parameters": {"param_name": {"type": "str", "description": "..."}},
    "requires": []  # Dependencies on other extensions
}

def execute(user_input: str, context: dict, **kwargs) -> str:
    """Execute extension logic."""
    return f"Result: {user_input}"

def validate(user_input: str, **kwargs) -> tuple[bool, str]:
    """Validate input. Return (is_valid, error_message)."""
    if not user_input:
        return False, "Input cannot be empty"
    return True, ""
```

**Rules**:
- Every extension must have `VERSION` and `METADATA`
- `execute()` must return a string
- `validate()` must return a tuple
- Extensions auto-load from `src/extensions/core/`
- Declare all dependencies in `METADATA["requires"]`

### Pattern 6: WebSocket Events for Real-Time Updates
Use WebSocket for broadcasting state changes:

```python
# Backend: Broadcast memory stored
await ws_manager.broadcast_memory_update(
    action="stored",
    memory_id=memory_id,
    details={"content": content}
)

# Frontend: Subscribe and refresh
useEffect(() => {
  const socket = new WebSocket("ws://127.0.0.1:8000/ws")
  socket.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data)
    if (payload?.type === "memory_update") {
      // Refresh memory list
      fetchMemories()
    }
  })
}, [])
```

**Rules**:
- Only use WebSocket for real-time state updates (not initial data)
- Always include `type` and `data` in message payload
- Always add timestamps for diagnostics
- Subscribe to specific channels (e.g., "memory", "processing")

### Pattern 7: Error Handling & Logging
Consistent error handling and structured logging:

```python
# Backend
try:
    result = await operation()
    logger.info(f"Operation completed: {result}")
    return {"status": "success", "data": result}
except ValueError as e:
    logger.warning(f"Invalid value: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Internal error")
```

**Rules**:
- Use appropriate log levels (debug, info, warning, error)
- Always include context in log messages
- Include `exc_info=True` for unexpected errors
- Catch specific exceptions first, general last
- Never expose internal error details to users

### Pattern 8: Async/Await for All I/O
All database, network, and file operations must be async:

```python
# ✅ Correct
async def fetch_memories(self, query: str):
    results = await self.db.fetch_all(...)
    embedding = await self.embeddings.generate(query)
    return results

# ❌ Wrong
def fetch_memories(self, query: str):
    results = self.db.query(...)  # Blocks thread
    return results
```

**Rules**:
- Always use `async def` for I/O operations
- Always use `await` for async calls
- Never block the event loop with synchronous I/O
- Use `asyncio.gather()` for parallel operations

---

## Development Workflow

### Adding a New Feature (Step-by-Step)

**Step 1: Identify the Layer**
- Is this LLM-related? → `src/llm/`
- Is this memory-related? → `src/memory/` + API route
- Is this UI-related? → `src/ui/behind-the-sena/src/components/`
- Is this a new domain? → New route file in `src/api/routes/`

**Step 2: Ask for Clarification**
- Is this a breaking change?
- Should users be able to configure this?
- Does this require internet access?
- Should this emit WebSocket events?

**If any answer is unclear, ask the user directly.**

**Step 3: Implement Incrementally**
1. Add config defaults (if applicable)
2. Implement core logic (backend service or frontend component)
3. Add API route or hook
4. Add UI control (if user-facing)
5. Add WebSocket event (if real-time needed)
6. Add tests or validation

**Step 4: Verify**
- Does it follow the architecture patterns?
- Is there any hard-coded configuration?
- Is all I/O async?
- Does it handle errors gracefully?
- Is it documented (if introducing new pattern)?

### Local Development

```bash
# Terminal 1: Start Python API
python -m uvicorn src.api.server:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Build React (one-time or watch)
cd src/ui/behind-the-sena
npm run build
# Or for development with hot reload:
npm run dev

# Then open: http://127.0.0.1:8000
```

### Testing Changes

**Backend**:
```bash
pytest src/ -v  # Run all tests
pytest src/tests/test_memory.py -v  # Test specific module
```

**Frontend**:
```bash
cd src/ui/behind-the-sena
npm run build  # Verify build succeeds
```

**Integration**:
- Open DevTools (F12) → Console/Network tabs
- Watch for errors or failed requests
- Check WebSocket messages (DevTools → Network → WS)

---

## Offline-First & Internet Requirements

### Marking Internet-Required Features

Use explicit markers in code and documentation:

```python
# Backend
@router.get("/weather")
async def get_weather(location: str) -> dict:
    """Get weather data.
    
    @RequiresInternet: OpenWeather API (fallback: cached data)
    @Graceful: Returns cached value if API unavailable
    """
    try:
        data = await fetch_weather_api(location)
        cache_weather(location, data)
        return {"status": "success", "data": data, "cached": False}
    except Exception as e:
        logger.warning(f"Weather API unavailable, using cache: {e}")
        cached = get_cached_weather(location)
        if cached:
            return {"status": "success", "data": cached, "cached": True}
        return {"status": "error", "message": "No cached data available"}
```

```typescript
// Frontend
/**
 * @RequiresInternet: OpenWeather API
 * @Graceful: Falls back to cached data
 */
export async function fetchWeather(location: string) {
  try {
    const response = await fetch(`/api/v1/weather?location=${location}`)
    const data = await response.json()
    return data
  } catch {
    return { status: "error", message: "Weather unavailable offline" }
  }
}
```

**Rules**:
- Use `@RequiresInternet` comment for features needing internet
- Use `@Graceful` comment for features that degrade gracefully
- Always provide fallback (cached data, default values, etc.)
- Always log when fallback is used

---

## Build & Release

### GitHub Actions CI/CD

The CI/CD pipeline (`.github/workflows/release.yml`) automatically:

1. **On every push to main/develop**:
   - Run tests (Python 3.10, 3.11, 3.12)
   - Build React app
   - Lint code

2. **On tag push (e.g., `git tag v1.0.0`)**:
   - Run tests on 3 Python versions
   - Build Electron app (npm run dist)
   - Create GitHub Release with built artifacts
   - Upload binaries (`.exe`, etc.)

### Local Release Testing

```bash
# Update version
echo "1.0.1" > VERSION

# Rebuild
cd src/ui/behind-the-sena
npm run build
cd ../../..

# Test the build
npm run dist  # Creates .exe (if Electron setup is correct)
```

### Distribution

Users download from: **GitHub Releases** → Download → Run executable

---

## Common Mistakes to Avoid

| Mistake | Fix |
|---------|-----|
| Hard-coded URLs/models | Use `settings.py` |
| Synchronous I/O (blocking) | Use `async/await` |
| Inconsistent error responses | Use standard response format |
| Circular module imports | Keep hierarchy one-way |
| Missing settings UI | Add to SettingsContent.tsx |
| Forgetting WebSocket events | Emit after state changes |
| No offline handling | Add fallback behavior |
| Heavy synchronous computation | Use extensions for processing |

---

## Quick Reference: Where to Add Things

| What | Where | Pattern |
|-----|-------|---------|
| New LLM model support | `src/llm/models/` | Inherit `BaseLLM` |
| New memory type | `src/memory/` + route | Add manager method + API |
| New API endpoint | `src/api/routes/[domain].py` | Standard route pattern |
| New setting | `src/config/settings.py` + UI | Add to SettingsContent.tsx |
| New extension | `src/extensions/core/[name].py` | Follow extension interface |
| New reusable component | `src/ui/.../components/` | Named export, props interface |
| New event type | `src/api/websocket/manager.py` | Add to `WSEventType` enum |
| Bug fix | Test first, fix in layer, test again | TDD approach |

---

## When in Doubt

**Ask the user directly:**
- "Should this be configurable via UI?"
- "Which layer should this logic live in?"
- "Does this feature need internet? How should it fail gracefully?"
- "Should this emit a WebSocket event?"
- "Is this a breaking change?"

Do not guess. Do not proceed with assumptions. Do not leave clarifications in comments.

---

**Last Updated**: February 2026
**Current Phase**: Modular architecture established, ready for feature expansion