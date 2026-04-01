# Scout Report: demo/ Directory Scope

## Exploration Scope
- Target: All source files in `demo/` directory
- Boundaries: `demo/server.py`, `demo/ui/src/` (4 source files), `demo/requirements.txt`
- Excluded: `node_modules/`, `dist/`, `package-lock.json`, `__pycache__/`

---

## File Inventory

### 1. `demo/server.py` — Python Backend Server
- **Lines**: 625
- **Purpose**: FastAPI demo server providing REST API for the Text2SQL chatbot UI. Serves both the chat pipeline endpoint and direct HRM/Banking CRUD endpoints against SQLite mock databases.
- **Key functions/endpoints**:
  - `_db_query()` (L31-38): Generic SQLite read helper
  - `_hrm_query()` (L41-42): HRM DB read shorthand
  - `_banking_query()` (L45-46): Banking DB read shorthand
  - `_hrm_write()` (L449-457): HRM DB write helper (INSERT, returns lastrowid)
  - `_build_assistant_message()` (L74-92): Formats pipeline result into chat message
  - `_detect_leave_registration()` (L132-134): Regex check for leave registration intent
  - `_extract_leave_dates()` (L137-178): NLP-lite date extraction from Vietnamese text
  - `_extract_leave_type()` (L181-188): Keyword-based leave type detection
  - `_extract_reason()` (L191-194): Regex reason extraction
  - `_handle_leave_registration()` (L197-302): Full leave registration flow via chat
  - `_count_working_days()` (L436-446): Business day counter
  - **Endpoints**:
    - `POST /api/chat` (L305-328): Main chat endpoint — routes to pipeline or leave registration
    - `GET /api/meta` (L95-108): Returns model config and domain list
    - `GET /api/hrm/departments` (L331-343)
    - `GET /api/hrm/employees` (L346-367): With query params for filtering
    - `GET /api/hrm/attendance` (L370-385)
    - `GET /api/hrm/current-user` (L390-398)
    - `GET /api/hrm/leave-balance` (L401-412)
    - `GET /api/hrm/leave-requests` (L415-427)
    - `GET /api/hrm/leave-types` (L430-433)
    - `POST /api/hrm/leave-request` (L460-506): Form-based leave creation
    - `GET /api/banking/customers` (L511-522)
    - `GET /api/banking/accounts` (L525-546)
    - `GET /api/banking/transactions` (L549-582)
    - `GET /api/banking/summary` (L585-610)
    - `GET /` (L617-624): Serves frontend `index.html`
    - Static mount `/assets` (L613-614)

### 2. `demo/ui/src/App.tsx` — React Frontend (Single-File App)
- **Lines**: 783
- **Purpose**: Monolithic React component containing the entire frontend: chat interface, HRM dashboard (departments, employees, attendance, leave management).
- **Key sections**:
  - Type definitions (L37-118): `View`, `MetaResponse`, `ResultPayload`, `ChatApiResponse`, `Message`, `Session`, HRM types
  - Session helpers (L120-142): localStorage persistence, `createSession`, `loadSessions`, `saveSessions`, `buildColumns`
  - State declarations (L155-190): ~30 `useState` hooks covering chat, nav, HRM, and leave form state
  - Effects (L192-235): Meta fetch, HRM data fetch, leave data fetch
  - `handleLeaveSubmit()` (L237-253): Leave form submission
  - `handleSubmit()` (L290-311): Chat message submission
  - Debug panel collapse items (L314-403): Domain, Schema, SQL inspection panels
  - HRM table columns (L406-441): Column definitions for department, employee, attendance tables
  - JSX Render (L444-783): Full layout — sidebar, chat view, HRM view with tabs

### 3. `demo/ui/src/main.tsx` — React Entry Point
- **Lines**: 10
- **Purpose**: Standard React 18 entry point, renders `<App />` into DOM.

### 4. `demo/ui/src/styles.css` — CSS Styles
- **Lines**: 349
- **Purpose**: Custom styling for the app shell (3-column layout), chat messages, composer, debug pane, HRM navigation, responsive breakpoints.
- **Key patterns**: Glass-morphism (backdrop-filter blur), IBM Plex Sans font, responsive breakpoints at 1400px, 1100px, 900px.

### 5. `demo/ui/src/shadcnTheme.ts` — Ant Design Theme
- **Lines**: 218
- **Purpose**: Shadcn-inspired theme configuration for Ant Design 5. Provides `useShadcnTheme()` hook returning `ConfigProviderProps`.
- **Dependencies**: `antd`, `antd-style`, `clsx`

### 6. `demo/requirements.txt` — Python Dependencies
- **Lines**: 2
- **Contents**: `fastapi==0.118.0`, `uvicorn==0.37.0`
- **Note**: Does NOT list `pydantic` (comes with FastAPI) or any pipeline dependencies.

### 7. Other UI files (not source, but notable)
- `demo/ui/hrm_database.html` — standalone HTML file (likely legacy/prototype)
- `demo/ui/vite.config.ts` — Vite bundler config
- `demo/ui/package.json` — Dependencies: `antd@^5.28.0`, `antd-style@^3.7.1`, `clsx@^2.1.1`, `react@^18.3.1`

---

## Dependencies: demo/ --> Parent Project

### Direct Python Imports (server.py)

| Import | Source Module | What It Provides |
|--------|--------------|------------------|
| `load_domain_registry` | `pipeline.domain_router.registry_loader` | Domain config for `/api/meta` |
| `run_pipeline` | `pipeline.runner` | Full Text2SQL pipeline orchestration for `/api/chat` |
| `get_generation_config` | `pipeline.sql_generation.llm_sql_generator` | LLM model info for `/api/meta` |

### Transitive Dependencies (via `run_pipeline`)
The `pipeline.runner` module imports from:
- `config.settings` — All configuration constants (MAX_RETRY_ATTEMPTS, QUERY_ROW_LIMIT, etc.)
- `pipeline.domain_router` — Domain selection
- `pipeline.schema_router` — Table selection
- `pipeline.intent_detection` — Intent ranking
- `pipeline.entity_extraction` — NER
- `pipeline.slot_filling` — Entity normalization + template filling
- `pipeline.template_store` — Approved SQL templates
- `pipeline.sql_generation` — LLM-based SQL generation
- `pipeline.validator` — SQL validation
- `pipeline.executor` — SQL execution
- `pipeline.explain` — Natural language explanation

### Data Dependencies (filesystem)
| Path | Used By |
|------|---------|
| `data/domains/hrm/mock/hrm.db` | All `/api/hrm/*` endpoints |
| `data/domains/banking/mock/banking.db` | All `/api/banking/*` endpoints |
| `demo/ui/dist/` | Static file serving |

### Frontend Dependencies (App.tsx)
- No imports from parent project — pure API consumer via `fetch()` calls
- All API calls use relative paths (`/api/chat`, `/api/meta`, `/api/hrm/*`)

---

## Blast Radius

Changes to demo/ affect: **Only the demo application itself** (no other module imports from demo/).

Changes FROM parent project that would break demo/:
1. **`pipeline.runner.run_pipeline()`** — If signature changes (especially `demo_mode`, `user_context`, `explain`, `forced_domain` params)
2. **`pipeline.domain_router.registry_loader.load_domain_registry()`** — If return format changes
3. **`pipeline.sql_generation.llm_sql_generator.get_generation_config()`** — If return format changes
4. **`data/domains/*/mock/*.db`** — If SQLite schema changes (table names, columns)
5. **`config.settings`** — Transitively via pipeline

---

## Architecture Layer Mapping

```
+--------------------------------------------------+
|  demo/ui (React + Ant Design)                     |  <-- Presentation Layer
|  - Single-page app, localStorage sessions         |
|  - Calls /api/* via fetch()                       |
+--------------------------------------------------+
              |  HTTP (REST JSON)
              v
+--------------------------------------------------+
|  demo/server.py (FastAPI)                         |  <-- API Gateway / BFF
|  - Routes chat to pipeline OR leave registration  |
|  - Direct SQLite queries for HRM/Banking views    |
|  - Serves static frontend                         |
+--------------------------------------------------+
      |                        |
      v                        v
+------------------+   +------------------+
| pipeline/        |   | data/domains/    |
| (Text2SQL core)  |   | (SQLite mock DBs)|
+------------------+   +------------------+
      |
      v
+------------------+
| config/settings  |
+------------------+
```

demo/ is a **presentation/demo layer** that sits on top of the core pipeline. It is a consumer only — no other module depends on it.

---

## Recent Git Churn

| Commit | Date Area | Files Changed | Description |
|--------|-----------|---------------|-------------|
| `ab3f321` | server.py | Most recent | Add leave registration via chat |
| `d22166d` | App.tsx | Recent | Fix SQL placeholder + model label in UI |
| `ce95327` | Both | Recent | Add leave management — query + register |
| `5b2a244` | server.py | Older | Add banking mock DB + demo mode |
| `c431cde` | — | Older | Refactor: move pipeline modules |
| `f808a03` | Both | Oldest | Initial restructure into demo/ |

**Most actively changed**: `server.py` (5 commits), `App.tsx` (3 commits). The leave management feature is the most recent addition across both files.

---

## Risk Indicators

### CRITICAL — SQL Injection Vulnerability
- **File**: `demo/server.py`, lines 252-256
- **Issue**: `_handle_leave_registration()` builds an `insert_sql` string using f-string interpolation with user-derived values (`employee_id`, `leave_type`, `start_date`, `end_date`, `reason`). This SQL string is assigned to `insert_sql` variable and returned in the response payload (L289), though the actual DB write on L258-262 correctly uses parameterized queries.
- **Severity**: The f-string SQL at L252-256 is **dead code for execution** (the parameterized version on L258-262 is what actually runs), but it is **returned to the client** in `result.sql` (L289). This leaks the pattern and could be misleading. The `reason` field comes directly from user input via regex extraction — if this SQL were ever executed, it would be a direct injection vector.

### HIGH — Monolithic Frontend (783 lines)
- **File**: `demo/ui/src/App.tsx`
- **Issue**: Entire application in a single component with ~30 useState hooks. No component extraction, no custom hooks, no separation of concerns. Difficult to maintain, test, or extend.

### HIGH — No Authentication / Authorization
- **File**: `demo/server.py`
- **Issue**: Hardcoded `DEMO_CURRENT_USER = "EMP001"` (L58). CORS allows all origins (L50-54). No auth middleware. Any client can create leave requests, query all employee data, and access all banking data.
- **Mitigation**: This is explicitly a demo server (documented in module docstring L1-3), but the write endpoint (`POST /api/hrm/leave-request`) modifies actual SQLite data.

### MEDIUM — No Input Sanitization on Chat
- **File**: `demo/server.py`, L62
- **Issue**: `ChatRequest.message` has `min_length=1` but no `max_length`. A very long message could cause issues in the pipeline (LLM token limits, regex backtracking in date extraction patterns).

### MEDIUM — Silent Error Swallowing (Frontend)
- **File**: `demo/ui/src/App.tsx`, lines 211, 217
- **Issue**: Multiple `.catch(() => {})` calls silently swallow fetch errors. HRM data load failures and current-user fetch failures produce no user feedback.

### MEDIUM — Hardcoded Year 2026
- **File**: `demo/server.py`, L409 (`year = 2026`), L473 (`year = 2026`)
- **Issue**: Leave balance queries hardcode year 2026 instead of using `date.today().year`. The chat-based leave registration at L236 correctly uses `date.today().year`, creating inconsistency.

### LOW — Unused Variable / Dead Code
- **File**: `demo/server.py`, L252-256
- **Issue**: The `insert_sql` f-string variable is constructed but never executed. The actual INSERT uses the parameterized query on L258-262. The `insert_sql` is only used for display in the response (L289).

### LOW — Missing `pydantic` in requirements.txt
- **File**: `demo/requirements.txt`
- **Issue**: Only lists `fastapi` and `uvicorn`. Does not list `pydantic` (implicitly installed with FastAPI) or any pipeline dependencies. This requirements file is incomplete for standalone use.

### LOW — No Type Safety on API Responses (Frontend)
- **File**: `demo/ui/src/App.tsx`
- **Issue**: API responses are cast with `as` (e.g., L208, L304) without runtime validation. Malformed responses would cause runtime errors.

---

## Conventions Observed

### Python (server.py)
- **Naming**: Snake_case for functions and variables. Private functions prefixed with `_`.
- **Docstrings**: Vietnamese comments in module docstring; some functions have English docstrings.
- **SQL style**: Inline SQL strings with triple-quoted strings. Parameterized queries using `?` placeholders (SQLite style).
- **Error handling**: Minimal — relies on FastAPI's default exception handling.

### TypeScript (App.tsx)
- **Naming**: PascalCase for types, camelCase for variables/functions.
- **State management**: All local state via `useState` + `useMemo` + `useEffect`. No external state library.
- **Styling**: Ant Design component library + custom CSS classes. No CSS modules or CSS-in-JS (except shadcnTheme).
- **UI text**: Vietnamese language throughout.

### File Organization
- Backend: Single monolithic `server.py`
- Frontend: Single monolithic `App.tsx` + theme + styles + entry point
- No tests in demo/
- No environment configuration (no `.env`, no config file)

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total source files | 6 (1 Python + 4 TypeScript/CSS + 1 txt) |
| Total source lines | ~1,987 (625 + 783 + 10 + 349 + 218 + 2) |
| API endpoints | 16 (1 POST chat, 1 POST leave, 1 GET meta, 13 GET data) |
| Parent project imports | 3 direct (pipeline.runner, registry_loader, llm_sql_generator) |
| External Python deps | 2 listed (fastapi, uvicorn) |
| External JS deps | 5 (react, react-dom, antd, antd-style, clsx) |
| SQLite databases | 2 (hrm.db, banking.db) |
| Risk items found | 7 (1 critical, 2 high, 3 medium, 1 low grouping) |
