# Sena - AI Agent Development Guidelines

This document provides critical context for AI agents (Claude, Copilot, Cursor, etc.) working on the Sena codebase. Focus on understanding architecture, workflows, and project-specific patterns rather than isolated code snippets.

---

## Architecture Overview

### Big Picture
Sena is a **Self-Evolving AI Assistant** with three-tier architecture:

```
┌──────────────────────────────────────────────────┐
│  Frontend Layer: Web UI (React + Tailwind)       │
│  - React 18 + TypeScript + Tailwind CSS          │
│  - 6 tabs: Chat, Memory, Extensions, Telemetry,  │
│    Logs, Processing (boot sequence)              │
│  - Dark theme: slate-950 background, purple      │
│    accents (color-purple-500)                    │
│  - Served from Python backend at localhost:8000  │
└─────────────────┬──────────────────────────────┘
                  │ HTTP
┌─────────────────▼──────────────────────────────┐
│  Backend API Layer: FastAPI Server              │
│  - Port 8000, localhost:8000                    │
│  - Serves React static files at /                │
│  - API routes: /api/v1/{chat,memory,            │
│    extensions,debug,telemetry,logs,processing} │
│  - CORS enabled for local development           │
│  - Health check: GET /health                    │
└─────────────────┬──────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────┐
│  Core Services Layer: Python Backend            │
│  ├─ LLMManager: Ollama-based LLM routing        │
│  ├─ MemoryManager: SQLite + embeddings         │
│  ├─ ExtensionManager: Singleton, auto-load      │
│  ├─ DatabaseManager: aiosqlite async DB        │
│  └─ TelemetryCollector: Metrics tracking        │
└──────────────────────────────────────────────┘
```

### Key Ports & Services
- **FastAPI Backend**: http://127.0.0.1:8000 (production & dev)
- **Vite Dev Server**: http://localhost:5173 (development only, for hot reload)
- **Ollama LLM**: http://127.0.0.1:11434 (external dependency)

---

## Critical Developer Workflows

### Workflow 1: Development (Simple & Fast)
**Files:** `start-dev.bat` or `npm run build` + manual server startup

**Development Flow:**
1. Start Python API server (in one terminal):
   ```bash
   python -m uvicorn src.api.server:app --host 127.0.0.1 --port 8000 --reload
   ```
2. In another terminal, build React for development:
   ```bash
   cd src/ui/behind-the-sena
   npm run build
   cd ../../..
   ```
3. Open browser to http://127.0.0.1:8000
4. React UI is served from Python backend

**Alternative - Automated:**
Run `start-dev.bat` which handles steps 1-3 automatically

**Key Insight:** React builds are **copied** to Python static folder, not served via Vite in production. Vite dev server only used for hot-reload during `npm run dev`.

### Workflow 2: Launcher & Distribution
**Files:** `launcher.js`, `build-installer.bat`, desktop shortcut

**Execution Flow:**
1. Users click desktop shortcut (created by `build-installer.bat`)
2. `launcher.js` (Node.js) runs automatically:
   - Checks if server is already running
   - Starts Python API if needed
   - Opens default browser to http://127.0.0.1:8000
   - Keeps running in background (Ctrl+C to stop)
3. User interacts with React UI in browser

**Key Insight:** **No Electron involved**. Simple Node.js launcher + system browser = simpler, smaller, fewer dependencies.

### Workflow 3: Building for Distribution
**File:** `build-installer.bat`
**Purpose:** Setup and create desktop shortcut

**Execution Flow:**
1. Validates Python 3.10+ and Node.js LTS
2. Creates Python virtual environment
3. Installs Python dependencies from `requirements.txt`
4. Installs Node dependencies via `npm install` (BTS folder)
5. Builds React: `npm run build` (outputs to `dist/`)
6. Creates desktop shortcut that launches `launcher.js`

**Deliverables:**
- Desktop shortcut: "Sena Debug Dashboard.lnk"
- Launcher script: `launcher.js`
- React app: Built to `src/ui/behind-the-sena/dist/` and served by Python

**Key Insight:** Distribution is just sharing `launcher.js` + Python backend. No complex installer needed.

### Workflow 4: API Route Implementation
**Pattern:** All API routes follow FastAPI async pattern with proper error handling

**Standard Structure:**
```python
# src/api/routes/[module].py
from fastapi import APIRouter, HTTPException
from src.api.models.responses import StandardResponse

router = APIRouter(prefix="/api/v1/[module]", tags=["[module]"])

@router.get("/endpoint")
async def get_endpoint(param: str) -> StandardResponse:
    """Endpoint docstring."""
    try:
        result = await async_operation()
        return StandardResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Response Format:** All endpoints return `StandardResponse` (see [src/api/models/responses.py](src/api/models/responses.py))

**Key Insight:** Never return raw data; always wrap in StandardResponse for consistency.

### Workflow 5: UI Component Development
**Pattern:** React TypeScript components with reusable structure

**File Organization:**
- Tabs: `src/ui/behind-the-sena/src/components/[TabName]Tab.tsx`
- Reusable: `src/ui/behind-the-sena/src/components/[ComponentName].tsx`
- Utils: `src/ui/behind-the-sena/src/utils/[util-name].ts`

**Standard Structure:**
```typescript
// Components use dark theme by default
import React from 'react'
import { Icon } from 'lucide-react'  // Use lucide-react, not emojis

interface Props {
  // Prop definitions
}

export function ComponentName({ prop }: Props) {
  return (
    <div className="bg-slate-950 text-slate-50">
      {/* Use purple-500 for accents/highlights */}
      <div className="text-purple-500">Active State</div>
    </div>
  )
}
```

**Styling Conventions:**
- Background: `bg-slate-950` (dark) or `bg-slate-900` (slightly lighter)
- Text: `text-slate-50` (white) or `text-slate-200` (light gray)
- Accents: `text-purple-500` or `bg-purple-500`
- Borders: `border-slate-800`
- Hover: `hover:bg-slate-800` or `hover:text-purple-400`

**Key Insight:** All new components must follow dark theme. Never add light-themed components.

---

## Project-Specific Patterns

### Pattern 1: Server Auto-Start via Launcher
**How It Works:**
1. **Desktop Shortcut** (created by `build-installer.bat`): Runs `launcher.js`
2. **Launcher** (`launcher.js`): Node.js script that:
   - Checks if server is already running (health check)
   - Starts Python API if not running
   - Opens default browser to http://127.0.0.1:8000
   - Runs in background until user closes browser or presses Ctrl+C
3. **React UI** (`App.tsx`): Shows ProcessingTab while waiting for server

**Code Flow:**
```
User clicks desktop shortcut
  ↓
launcher.js runs (Node.js)
  ↓
Check server health (GET /health)
  ↓
If not healthy:
  - Start Python with: python -m uvicorn src.api.server:app
  ↓
Open browser to http://127.0.0.1:8000
  ↓
React UI loads
  ↓
App.tsx checks health every 500ms
  ↓
Once healthy:
  - Hide ProcessingTab
  - Show main dashboard (6 tabs)
```

**Key Insight:** No Electron IPC needed. Simple process spawning + browser = 10x simpler, 100x smaller app size.

### Pattern 2: Memory System Integration
**Architecture:** SQLite persistence + embeddings + retrieval

**Key Components:**
- `MemoryManager`: Main orchestrator (singleton)
- `MemoryRepository`: Database operations (aiosqlite)
- Embeddings: Via Ollama `nomic-embed-text:latest`
- Retrieval: Semantic similarity with threshold 0.6

**Usage Pattern:**
```python
from src.database.repositories.memory_repo import MemoryRepository

repo = MemoryRepository(db_connection)
# Store memory
await repo.add_memory(content, embedding, memory_type)
# Retrieve similar
similar = await repo.search_similar(query_embedding, limit=5)
```

**Key Insight:** Memory operations are **async**. Always use `await` for database calls.

**Reliability Note:** Ensure `MemoryManager.initialize()` runs so the global database connection is attached before fetching recent or long-term memories.

### Pattern 3: Extension Loading & Hot-Reload
**File Organization:**
- Core extensions: `src/extensions/core/[extension_name].py`
- User extensions: `src/extensions/user/[extension_name].py`
- Generated: `src/extensions/generated/[extension_name].py`

**Extension Interface:**
Every extension must define:
```python
VERSION = "1.0.0"
METADATA = {
    "name": "Extension Name",
    "description": "What it does",
    "author": "Author Name",
    "parameters": {"param_name": {"type": "str", "description": "..."}},
    "requires": ["dependency_extension"]  # Or empty list
}

def execute(user_input: str, context: dict, **kwargs) -> str:
    """Main execution function."""
    return "result"

def validate(user_input: str, **kwargs) -> tuple[bool, str]:
    """Optional: Validate before execution."""
    return True, ""
```

**Extension Manager (Singleton):**
```python
from src.extensions import ExtensionManager

manager = ExtensionManager()  # Singleton instance
extensions = manager.get_all_extensions()
result = await manager.execute_extension("extension_name", user_input, context)
```

**Key Insight:** Extensions auto-load from `src/extensions/core/` on startup. New core extensions appear automatically without code changes.

### Pattern 4: Dark Theme Consistency
**Rule:** All UI components must use dark theme colors.

**Color Palette:**
- Primary Background: `bg-slate-950` (#030712)
- Secondary Background: `bg-slate-900` (#0f172a)
- Text Primary: `text-slate-50` (#f8fafc)
- Text Secondary: `text-slate-200` (#e2e8f0)
- Accent: `text-purple-500` (#a855f7)
- Borders: `border-slate-800` (#1e293b)

**Never:**
- Use white (`bg-white`) or light backgrounds
- Use black text (`text-black`) on dark background (use slate-50 instead)
- Add light-themed components

**Key Insight:** The entire UI is intentionally dark for reduced eye strain during debugging.

### Pattern 5: Processing Tab (Boot Sequence Visualization)
**File:** `src/ui/behind-the-sena/src/components/ProcessingTab.tsx`

**Smart Timing Logic:**
- Each startup step displays for **minimum 1 second**
- If actual step duration is **longer than 1 second**, display for actual duration
- Example: 0.5s step → shows 1s; 1.5s step → shows 1.5s

**7 Startup Steps:**
1. "Initializing Python backend"
2. "Loading configuration"
3. "Connecting to database"
4. "Initializing memory system"
5. "Loading extensions"
6. "Starting LLM router"
7. "Connecting to API endpoint"

**Parallel Operations:**
- Steps animate sequentially (one at a time)
- API health check runs **every 500ms** (in parallel)
- Once API is ready (health check passes), boot sequence ends immediately
- ProcessingTab hides, main dashboard shows

**Key Insight:** Users see progress even if server starts quickly (minimum 1s per step), but don't wait unnecessarily if server starts slowly.

### Pattern 6: CORS Configuration
**File:** `src/api/server.py`

**Configuration:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Reason:** Electron's Vite dev server (http://localhost:5173) makes requests to FastAPI (http://127.0.0.1:8000). These are cross-origin and require CORS headers.

**Key Insight:** CORS must allow `localhost:5173` for dev, and production Electron URL for deployed version.

---

## Integration Points

### Integration 1: Frontend → Backend Communication
**Method:** HTTP fetch to http://127.0.0.1:8000/api/v1/[endpoint]

**Example:**
```typescript
// src/ui/behind-the-sena/src/components/ChatTab.tsx
const response = await fetch('http://127.0.0.1:8000/api/v1/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: userInput })
})
const data = await response.json()
```

**Standard Response Format:**
```json
{
  "success": true,
  "data": { /* endpoint-specific data */ },
  "error": null,
  "metadata": { "timestamp": "...", "request_id": "..." }
}
```

### Integration 2: Launcher Process Control
**File:** `launcher.js` (Node.js script)

**Launcher Functions:**
```javascript
// Check if server is healthy
function isServerHealthy(): Promise<boolean>

// Start the Python API server
function startServer(): Promise<boolean>

// Open browser to http://127.0.0.1:8000
function openBrowser()
```

**Execution:**
- Users click desktop shortcut → `launcher.js` executes
- Launcher checks if server is running (`isServerHealthy()`)
- If not, starts Python process: `python -m uvicorn src.api.server:app`
- Opens browser to http://127.0.0.1:8000
- Shows progress in console
- User closes terminal to stop services

**Key Insight:** Launcher is a simple Node.js script—no system service, no background process, just spawn → open → wait.

### Integration 3: API Health Check
**Endpoint:** `GET http://127.0.0.1:8000/health`

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T12:34:56Z",
  "uptime_seconds": 123.45
}
```

**Usage in React:**
```typescript
export async function isServerHealthy(): Promise<boolean> {
  try {
    const response = await fetch('http://127.0.0.1:8000/health', {
      signal: AbortSignal.timeout(5000)
    })
    return response.ok
  } catch {
    return false
  }
}
```

---

## File Structure Reference

### Backend Entry Point
- **[src/main.py](src/main.py)** - CLI entry point (modes: cli, test, normal)

### API Layer
- **[src/api/server.py](src/api/server.py)** - FastAPI app initialization, middleware, CORS
- **[src/api/routes/](src/api/routes/)** - All API endpoints organized by domain

### Core Orchestration
- **[src/core/sena.py](src/core/sena.py)** - Main orchestrator coordinating all subsystems
- **[src/core/bootstrapper.py](src/core/bootstrapper.py)** - System initialization
- **[src/core/error_handler.py](src/core/error_handler.py)** - Error handling middleware

### Database & Persistence
- **[src/database/connection.py](src/database/connection.py)** - aiosqlite setup
- **[src/database/repositories/](src/database/repositories/)** - Data access layer (conversation, memory, telemetry)
- **[src/database/models/](src/database/models/)** - SQLAlchemy models

### Memory System
- **[src/database/repositories/memory_repo.py](src/database/repositories/memory_repo.py)** - Memory storage/retrieval
- **[src/core/sena.py](src/core/sena.py)** - Integration point

### Extensions
- **[src/extensions/core/](src/extensions/core/)** - Core extensions (file_search, web_search)
- **[src/extensions/__init__.py](src/extensions/__init__.py)** - ExtensionManager singleton

### LLM Management
- **[src/llm/manager.py](src/llm/manager.py)** - LLMManager (Ollama client wrapper)
- **[src/llm/router.py](src/llm/router.py)** - Intent-based LLM selection

### Frontend (BTS)
- **[src/ui/behind-the-sena/src/App.tsx](src/ui/behind-the-sena/src/App.tsx)** - Main React app
- **[src/ui/behind-the-sena/src/components/](src/ui/behind-the-sena/src/components/)** - React components (tabs + reusable)
- **[src/ui/behind-the-sena/main.ts](src/ui/behind-the-sena/main.ts)** - Electron main process
- **[src/ui/behind-the-sena/renderer.ts](src/ui/behind-the-sena/renderer.ts)** - Electron preload (IPC bridge)

### Build & Deployment
- **[start-dev.bat](start-dev.bat)** - Single-command dev launcher
- **[build-installer.bat](build-installer.bat)** - Build and create desktop shortcut
- **[launcher.js](launcher.js)** - Node.js launcher for distribution
- **[src/ui/behind-the-sena/package.json](src/ui/behind-the-sena/package.json)** - React + Vite config (no Electron)
- **[src/api/server.py](src/api/server.py)** - FastAPI server that serves React static files

---

## Common Tasks & Solutions

### Task 1: Add New API Endpoint
**Steps:**
1. Create route file in `src/api/routes/`
2. Define FastAPI route with `@router.get/post/etc`
3. Return `StandardResponse` wrapper
4. Import and include router in `src/api/server.py`

**Example:**
```python
# src/api/routes/newmodule.py
from fastapi import APIRouter
from src.api.models.responses import StandardResponse

router = APIRouter(prefix="/api/v1/newmodule")

@router.get("/status")
async def get_status() -> StandardResponse:
    return StandardResponse(success=True, data={"status": "ok"})

# In src/api/server.py:
from src.api.routes.newmodule import router as newmodule_router
app.include_router(newmodule_router)
```

### Task 2: Add New UI Component
**Steps:**
1. Create `.tsx` file in `src/ui/behind-the-sena/src/components/`
2. Use dark theme colors (slate-950, purple-500)
3. Import lucide-react for icons (not emojis)
4. Export as named export

**Example:**
```typescript
// src/ui/behind-the-sena/src/components/MyComponent.tsx
import { Clock } from 'lucide-react'

export function MyComponent() {
  return (
    <div className="bg-slate-900 p-4 rounded border border-slate-800">
      <Clock className="text-purple-500" size={20} />
      <p className="text-slate-50">Content</p>
    </div>
  )
}
```

### Task 3: Add New Core Extension
**Steps:**
1. Create `.py` file in `src/extensions/core/`
2. Define VERSION, METADATA, execute() function
3. Extension auto-loads on next server restart

**Example:**
```python
# src/extensions/core/example_tool.py
VERSION = "1.0.0"
METADATA = {
    "name": "Example Tool",
    "description": "Does something useful",
    "author": "Sena Team",
    "parameters": {"input": {"type": "str", "description": "Input data"}},
    "requires": []
}

def execute(user_input: str, context: dict, **kwargs) -> str:
    # Implementation here
    return f"Processed: {user_input}"

def validate(user_input: str, **kwargs) -> tuple[bool, str]:
    if not user_input:
        return False, "Input cannot be empty"
    return True, ""
```

### Task 4: Fix TypeScript Build Errors
**Common Issues & Solutions:**

| Error | Cause | Solution |
|-------|-------|----------|
| `noDeprecation property conflicts` | @types/node vs electron type mismatch | Add `"skipLibCheck": true` to `tsconfig.main.json` |
| `Cannot find module 'electron'` | Electron not in devDependencies | Move electron from `dependencies` to `devDependencies` |
| `Vite not starting` | Port 5173 already in use | Kill process on port 5173 or change port |
| `API fetch fails in dev` | CORS not configured | Ensure CORS middleware includes `http://localhost:5173` |

### Task 5: Debug Production Installer Issues
**Common Issues & Solutions:**

| Issue | Debug Step | Solution |
|-------|-----------|----------|
| .exe not created | Check `src/ui/behind-the-sena/release/` | Verify icon path, run `npm run dist` with admin elevation |
| Admin elevation loop | Check `%TEMP%\sena_elevation_check.tmp` | Clean temp folder, re-run build-installer.bat |
| Python/Node not found | Run `python --version` and `node --version` | Install Python 3.10+ or Node.js LTS |
| App crashes on startup | Check logs in `src/data/logs/` | Look for database connection or extension load errors |

---

## Development Best Practices

### 1. Always Use Async/Await for I/O
```python
# ✓ CORRECT
async def fetch_data():
    result = await db.query()
    return result

# ✗ WRONG
def fetch_data():
    result = db.query()  # Blocks thread
    return result
```

### 2. Wrap API Responses Consistently
```typescript
// ✓ CORRECT
const response = await fetch('http://127.0.0.1:8000/api/v1/...')
const data = await response.json() // StandardResponse format
if (data.success) { /* use data.data */ }

// ✗ WRONG
const response = await fetch('...')
const data = await response.json()
// data might be raw value, not wrapped
```

### 3. Test Components in Dark Mode
```css
/* ✓ CORRECT: Always specify dark colors */
.component { @apply bg-slate-950 text-slate-50; }

/* ✗ WRONG: Assumes light mode will be default */
.component { color: black; }
```

### 4. Use `launcher.js` for Distribution
```bash
# ✓ CORRECT: Users run launcher to auto-start everything
node launcher.js

# ✗ WRONG: Manually starting separate services
python -m uvicorn src.api.server:app &
npm run dev  # This is for development only, not production
```

### 5. Always Handle Extension Dependencies
```python
# ✓ CORRECT
METADATA = {
    "requires": ["web_search"],  # Declare if depends on other extensions
    ...
}

# ✗ WRONG
METADATA = {
    "requires": [],  # But execute() calls web_search internally
    ...
}
```

---

## Testing & Validation

### Run Tests
```bash
# All tests
pytest src/ -v

# Specific test file
pytest src/tests/test_memory.py -v

# With coverage
pytest src/ --cov=src --cov-report=html
```

### Manual API Testing
```bash
# Health check
curl http://127.0.0.1:8000/health

# Chat endpoint
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

### Dev Workflow Validation
```bash
# Run dev environment
start-dev.bat

# Should see:
# 1. Python server starting
# 2. React building
# 3. Browser opens to http://127.0.0.1:8000
# 4. ProcessingTab shows 7-step startup
# 5. After ~5-10 seconds, main dashboard appears
```

---

## Release & Distribution

### Version Management
- **Single source of truth:** `VERSION` file at project root (e.g., `1.0.0`)
- **Read by:** `src/__init__.py` (auto-loads on import)
- **Updated when:** Making a new release

### GitHub Actions CI/CD Pipeline (`.github/workflows/release.yml`)

**Triggers:**
- Pushes to main/develop → Run tests only
- Tags starting with `v` (e.g., `v1.0.0`) → Run tests + build + create release

**Automated testing:**
- 3 operating systems: Windows, Linux, macOS (parallel)
- 3 Python versions: 3.10, 3.11, 3.12
- Total: 9 test environments

**Automated building (on tag):**
- Install all dependencies
- Build React UI (`npm run build`)
- Use PyInstaller to create standalone `Sena.exe`
- Create GitHub Release with generated notes

### Release Process

**Step 1: Update VERSION**
```bash
echo "1.0.1" > VERSION
```

**Step 2: Update CHANGELOG.md**
Add entry for new version with changes made.

**Step 3: Commit and tag**
```bash
git commit -am "Release v1.0.1"
git tag v1.0.1
git push origin main --tags
```

**Step 4: GitHub Actions takes over**
- Tests run automatically
- Builds Sena.exe automatically
- Creates GitHub Release automatically
- Users can download from: `github.com/USER/Sena/releases`

### Local Building (for testing)
```bash
# Requires: Python 3.10+, Node.js LTS, PyInstaller
build-standalone.bat

# Output: dist/Sena.exe
```

### Distribution Points
1. **Primary:** GitHub Releases (github.com/USER/Sena/releases)
2. **Secondary:** Website (sena-ai.dev/download) - redirects to Releases
3. **Tertiary:** Direct sharing (users can share .exe link)

### User Experience
1. Download `Sena.exe` from GitHub Releases
2. Run executable
3. Python server starts automatically
4. Browser opens to localhost:8000
5. UI loads with full React dashboard
6. No Python/Node.js installation needed

---

## Navigation & References

**Quick Links:**
- `.github/PHASES.md` - Current phase tracker
- `.github/WORKSPACE.md` - Workspace organization guide
- `INSTRUCTIONS.md` - Detailed architecture reference
- `README.md` - User-facing project info
- `CONTRIBUTING.md` - Contribution guidelines

---

1. **Architecture Questions:** Refer to README.md or INSTRUCTIONS.md (main documentation)
2. **API Questions:** Check existing route implementations in `src/api/routes/`
3. **UI Questions:** Reference existing Tab components (ChatTab, MemoryTab, etc.)
4. **Extension Questions:** Review core extensions in `src/extensions/core/`
5. **Styling Questions:** Check App.tsx or any Tab component for color usage
6. **Release Questions:** Follow release process above, or check GitHub Actions logs
7. **Build Questions:** Run `build-standalone.bat` locally to debug

---

**Last Updated:** February 4, 2026
**Current Phase:** Post Phase-1, release infrastructure ready for v1.0.0
