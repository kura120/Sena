Here’s a **proposed audit + refactor plan** based on your direction (start at core, expand outward, with UI as the main refactor target). I’ll wait for your confirmation before editing.

---

## ✅ Phase 0 — Baseline Inventory (no changes yet)
**Goal:** map current architecture, identify rule violations and dead code.

- **Backend:** scan `src/config`, `src/database`, `src/llm`, `src/core`, `src/memory`, `src/extensions`, `src/api/routes`.
- **Frontend:** map `src/ui/behind-the-sena/src` structure and cross-check with rules.
- **Outcome:** checklist of violations, duplication, dead code, and refactor candidates.

---

## ✅ Phase 1 — Core & Config Compliance
**Goal:** ensure the lower layers follow the rules before touching API/UI.

- Verify **config-only settings** in `src/config/settings.py`.
- Remove any **hard-coded values** in core services.
- Ensure **async I/O only** across core modules.
- Add missing **error handling patterns** and logging consistency.

---

## ✅ Phase 2 — Database & LLM Layer Cleanup
**Goal:** make data + LLM layers clean, async, and rule-compliant.

- Confirm repository pattern + async DB usage.
- Validate LLM routing / model registry flow.
- Flag any sync calls or config leakage.

---

## ✅ Phase 3 — API Routes Standardization
**Goal:** enforce the route pattern across all routes.

- Ensure every route:
  - uses dependency injection
  - consistent response format
  - proper error handling
- Remove dead or unused endpoints.
- Ensure settings routes **persist to `settings.yaml`** and **reload**.

---

## ✅ Phase 4 — Frontend Refactor (primary focus)
**Goal:** make UI fully modular, DRY, and build‑ready.

### **Core UI changes**
- Collapse redundant **`components/*Tab.tsx` wrappers** (e.g., `ChatTab` just returning `ChatContent`).
- Make **each tab a single file** under `src/tabs/`.
- Move **shared UI elements** into reusable components in `src/components/`:
  - `TabLayout`, `TabHeader`
  - `SectionHeader`
  - `StatCard`, `EmptyState`, `LoadingState`
  - `PrimaryButton`, `IconButton`
  - `TextInput`, `SearchInput`, `SelectField`
  - `Card`, `Badge`, `Tooltip`
- Centralize API access under `src/utils/api.ts` (base URL + fetch wrappers).
- Centralize **WebSocket utilities** under `src/utils/websocket.ts`.
- Normalize styling tokens (colors + spacing) across components.

### **Tabs structure after refactor**
- `tabs/Chat.tsx`
- `tabs/Memory.tsx`
- `tabs/Extensions.tsx`
- `tabs/Telemetry.tsx`
- `tabs/Logs.tsx`
- `tabs/Settings.tsx`

Each tab will import **shared components only** and remain thin.

---

## ✅ Phase 5 — Dead Code Removal + Cleanup
- Remove unused components, duplicated helpers, orphan files.
- Remove unused styles / assets.
- Clean unused imports and props.

---

## ✅ Phase 6 — Validation & Build-Ready Check
- Ensure all changes compile.
- Validate UI still works with backend endpoints.
- Provide a **final audit summary** of what changed.