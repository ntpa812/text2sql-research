# Improvement Plan: demo/ Code Review

## Priority Matrix

| ID  | Issue                                      | Severity | Category       | Effort | Dependency Order |
|-----|--------------------------------------------|----------|----------------|--------|------------------|
| H1  | Dead f-string SQL with unsanitized input   | HIGH     | Security       | S      | 1                |
| H2  | CORS wildcard with write endpoints         | HIGH     | Security       | S      | 2                |
| H3  | No authentication/authorization            | HIGH     | Security       | L      | 3 (after H2)     |
| M1  | No max_length on ChatRequest.message       | MEDIUM   | Security       | S      | 4                |
| M2  | No CSRF protection on POST endpoints       | MEDIUM   | Security       | M      | 5 (after H2)     |
| M3  | PII data exposure, no pagination           | MEDIUM   | Security       | M      | 6 (after H3)     |
| M4  | Error detail leakage to client             | MEDIUM   | Security       | S      | 4                |
| M5  | Debug data returned in all API responses   | MEDIUM   | Security       | S      | 4                |
| M6  | SQLite connection-per-request, write risk  | MEDIUM   | Performance    | M      | 7                |
| M7  | Hardcoded year 2026 inconsistency          | MEDIUM   | Correctness    | S      | 8                |
| M8  | Incorrect error message for zero work days | MEDIUM   | Correctness    | S      | 8                |
| M9  | Date parsing no validation                 | MEDIUM   | Correctness    | S      | 8                |
| M10 | Duplicated leave creation logic            | MEDIUM   | Architecture   | M      | 9 (after M8, M9) |
| M11 | Unbounded localStorage session growth      | MEDIUM   | Performance    | S      | 10               |
| M12 | No HTTP status check on frontend fetch     | MEDIUM   | Correctness    | S      | 10               |
| L1  | Silent error swallowing .catch(() => {})   | LOW      | Correctness    | S      | 10               |
| L2  | Monolithic App.tsx (783 lines)             | LOW      | Architecture   | L      | 11 (last)        |
| L3  | Column definitions recreated every render  | LOW      | Performance    | S      | 10               |
| L4  | debugCollapseItems not memoized            | LOW      | Performance    | S      | 10               |
| L5  | Double loadSessions() on mount             | LOW      | Performance    | S      | 10               |
| L6  | Dead forced_domain/use_embedding from UI   | LOW      | Code Quality   | S      | 10               |
| L7  | Hardcoded attendance default dates         | LOW      | Correctness    | S      | 8                |
| L8  | Date query params no format validation     | LOW      | Correctness    | S      | 8                |
| L9  | reason field no max_length, deps, types    | LOW      | Code Quality   | S      | 4                |

---

## Critical Issues (MUST fix before deploy)

### H1: Dead f-string SQL with unsanitized user input returned in API response

- **Description**: `_handle_leave_registration()` constructs a SQL string via f-string interpolation at L252-256 with user-derived values (`reason` is fully unsanitized). Although the actual DB write uses parameterized queries (L258-262), this f-string SQL is returned in the API response at L289 via `result.sql`, exposing unsanitized user input to the client and rendering it in the frontend debug panel.
- **File:Lines**: `demo/server.py` L252-256 (f-string construction), L289 (returned in response)
- **Root Cause**: The f-string SQL was likely written first for debugging, then the actual insert was parameterized, but the debug version was kept and wired into the response payload.
- **Fix Recommendation**:
  1. Delete lines 252-256 entirely (the `insert_sql` f-string variable).
  2. Replace the value assigned to `result.sql` at L289 with the parameterized template string (e.g., `"INSERT INTO leave_request (...) VALUES (?, ?, ?, ?, ?, ?, ?)"`) so debug output shows the safe template, not interpolated user data.
  3. Verify no other code path references the `insert_sql` variable.
- **Effort Estimate**: S (<30 min)
- **Risk of NOT Fixing**: Unsanitized user input is reflected in API responses. An attacker could craft a `reason` field containing malicious payloads (XSS via debug panel rendering, or social engineering via visible SQL). If the f-string SQL is ever accidentally wired to execute, it becomes a direct SQL injection vector.

---

### H2: CORS wildcard `allow_origins=["*"]` with write endpoints

- **Description**: The CORS middleware permits all origins, all methods, and all headers. Combined with the `POST /api/hrm/leave-request` and `POST /api/chat` write endpoints, any website can issue cross-origin requests that modify data.
- **File:Lines**: `demo/server.py` L49-54
- **Root Cause**: Default permissive CORS configuration was never tightened after initial scaffolding.
- **Fix Recommendation**:
  1. Replace `allow_origins=["*"]` with an explicit list:
     ```python
     ALLOWED_ORIGINS = [
         "http://localhost:5173",   # Vite dev server
         "http://127.0.0.1:8001",  # Local production
     ]
     ```
  2. Read from environment variable for deployment flexibility:
     ```python
     import os
     ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
     ```
  3. Keep `allow_methods=["*"]` and `allow_headers=["*"]` since the origin restriction is the primary control.
- **Effort Estimate**: S (<30 min)
- **Risk of NOT Fixing**: Any malicious website a user visits can silently create leave requests, query employee/banking data, and interact with the chat endpoint on behalf of the user. This is a prerequisite for CSRF protection (M2).

---

### H3: No authentication/authorization, hardcoded user, IDOR on employee_id

- **Description**: All endpoints are unauthenticated. `DEMO_CURRENT_USER = "EMP001"` is hardcoded. Any caller can pass arbitrary `employee_id` query params to access other employees' data. The `POST /api/hrm/leave-request` writes to the database with the hardcoded user identity.
- **File:Lines**: `demo/server.py` L58 (hardcoded user), all endpoints (no auth checks)
- **Root Cause**: Built as a demo with no auth layer planned.
- **Fix Recommendation** (demo-appropriate, not production-grade):
  1. Add a simple token-based demo auth middleware:
     ```python
     DEMO_TOKENS = {"demo-token-001": "EMP001", "demo-token-002": "EMP002"}

     async def get_current_user(authorization: str = Header(None)) -> str:
         token = (authorization or "").removeprefix("Bearer ")
         user = DEMO_TOKENS.get(token)
         if not user:
             raise HTTPException(401, "Invalid demo token")
         return user
     ```
  2. Inject `current_user: str = Depends(get_current_user)` into each endpoint.
  3. Replace all references to `DEMO_CURRENT_USER` with the injected `current_user`.
  4. Filter queries by `current_user` where appropriate (leave requests, attendance).
  5. Update the frontend to send `Authorization: Bearer demo-token-001` header.
- **Effort Estimate**: L (4+ hours) -- touches every endpoint + frontend
- **Risk of NOT Fixing**: Complete data exposure and unauthorized write access. Any network-adjacent attacker can create leave requests for any employee and read all HR/banking data.

---

## Warnings (SHOULD fix)

### M1: No max_length on ChatRequest.message + ReDoS risk

- **Description**: `ChatRequest.message` has `min_length=1` but no `max_length`. Extremely long messages could exhaust LLM token budgets, cause excessive regex backtracking in `_extract_leave_dates()` patterns, or consume server memory.
- **File:Lines**: `demo/server.py` L62 (model definition), L137-178 (regex patterns)
- **Root Cause**: Input validation was minimal from the start.
- **Fix Recommendation**:
  1. Add `max_length=2000` to the message field:
     ```python
     message: str = Field(..., min_length=1, max_length=2000)
     ```
  2. Add `re.DOTALL` flags and use possessive/atomic grouping or timeouts on the date extraction regexes to prevent backtracking. Alternatively, wrap regex calls with a timeout:
     ```python
     import signal
     # or use regex module with timeout parameter
     ```
- **Effort Estimate**: S (<30 min)
- **Risk of NOT Fixing**: Denial-of-service via oversized messages or crafted regex input. A single request could hang the server.

---

### M2: No CSRF protection on POST endpoints

- **Description**: POST endpoints (`/api/chat`, `/api/hrm/leave-request`) have no CSRF tokens. Combined with the CORS wildcard (H2), cross-site request forgery is trivially exploitable.
- **File:Lines**: `demo/server.py` L305-328 (chat endpoint), L460-506 (leave endpoint)
- **Root Cause**: No CSRF middleware was added.
- **Fix Recommendation**:
  1. Fix H2 first (restrict CORS origins). Origin-based CORS restriction is the primary CSRF defense for JSON API endpoints.
  2. Optionally add a custom header check (`X-Requested-With: XMLHttpRequest`) as defense-in-depth:
     ```python
     @app.middleware("http")
     async def csrf_check(request, call_next):
         if request.method == "POST":
             if not request.headers.get("X-Requested-With"):
                 return JSONResponse(status_code=403, content={"detail": "Missing CSRF header"})
         return await call_next(request)
     ```
  3. Update frontend fetch calls to include `"X-Requested-With": "XMLHttpRequest"` header.
- **Effort Estimate**: M (1-2 hours)
- **Risk of NOT Fixing**: Cross-site request forgery allows attackers to create leave requests or trigger chat queries via a victim's browser session.

---

### M3: PII data exposure -- unfiltered employee/customer data, no pagination

- **Description**: Endpoints like `/api/hrm/employees` and `/api/banking/customers` return all records with all columns, including potentially sensitive fields. No pagination means large datasets are returned in full.
- **File:Lines**: `demo/server.py` L346-367 (employees), L511-522 (customers), L525-546 (accounts)
- **Root Cause**: Demo endpoints return raw SELECT * results without field filtering or pagination.
- **Fix Recommendation**:
  1. Add `limit` and `offset` query parameters to list endpoints:
     ```python
     @app.get("/api/hrm/employees")
     async def get_employees(..., limit: int = Query(default=50, le=200), offset: int = Query(default=0, ge=0)):
     ```
  2. Append `LIMIT ? OFFSET ?` to SQL queries.
  3. Return a wrapper with total count: `{"data": [...], "total": count, "limit": limit, "offset": offset}`.
  4. Exclude sensitive columns from responses (e.g., personal phone numbers, addresses) or define explicit column lists instead of `SELECT *`.
- **Effort Estimate**: M (1-2 hours)
- **Risk of NOT Fixing**: Full PII exposure for all employees and customers. No protection against data scraping.

---

### M4: Error detail leakage -- raw pipeline errors returned to client

- **Description**: When `run_pipeline()` or other operations fail, the raw error message is returned to the client, potentially exposing internal paths, database schema details, or stack traces.
- **File:Lines**: `demo/server.py` L79 (error formatting in `_build_assistant_message`)
- **Root Cause**: No error sanitization layer; exceptions are passed directly into API response.
- **Fix Recommendation**:
  1. Wrap pipeline calls in try/except and return generic error messages:
     ```python
     except Exception as e:
         logger.error(f"Pipeline error: {e}", exc_info=True)
         return {"error": "An internal error occurred. Please try again."}
     ```
  2. Add structured logging so errors are captured server-side but not exposed to clients.
  3. In development mode, optionally allow verbose errors behind a flag.
- **Effort Estimate**: S (<30 min)
- **Risk of NOT Fixing**: Information disclosure of internal architecture, file paths, database schema, and stack traces to attackers.

---

### M5: Debug data (SQL, routing, entities, timing) returned in all API responses

- **Description**: Every chat API response includes `sql`, `domain`, `schema`, `entities`, and timing data. This is useful for development but exposes internal implementation details in production.
- **File:Lines**: `demo/server.py` L74-92 (`_build_assistant_message` constructs full debug payload)
- **Root Cause**: Debug information was built into the response format with no toggle.
- **Fix Recommendation**:
  1. Add an environment variable or query parameter to control debug output:
     ```python
     SHOW_DEBUG = os.getenv("DEMO_DEBUG", "true").lower() == "true"
     ```
  2. Conditionally include debug fields:
     ```python
     if SHOW_DEBUG:
         msg["debug"] = {"sql": ..., "domain": ..., "schema": ..., ...}
     ```
  3. Strip debug data when `SHOW_DEBUG` is false.
- **Effort Estimate**: S (<30 min)
- **Risk of NOT Fixing**: Exposes SQL queries, table schemas, routing logic, entity extraction details, and timing information. Aids reconnaissance for targeted attacks.

---

### M6: SQLite connection-per-request, concurrent write risk

- **Description**: Both `_db_query()` and `_hrm_write()` open a new SQLite connection per call. Under concurrent requests, this causes connection churn and potential `database is locked` errors on writes since SQLite has limited write concurrency.
- **File:Lines**: `demo/server.py` L31-38 (`_db_query`), L449-457 (`_hrm_write`)
- **Root Cause**: Simple connection pattern without pooling or serialization.
- **Fix Recommendation**:
  1. Use a module-level connection with WAL mode for better concurrent reads:
     ```python
     _hrm_conn = sqlite3.connect(HRM_DB_PATH, check_same_thread=False)
     _hrm_conn.execute("PRAGMA journal_mode=WAL")
     _hrm_conn.row_factory = sqlite3.Row
     ```
  2. Protect write operations with a threading lock:
     ```python
     import threading
     _write_lock = threading.Lock()

     def _hrm_write(sql, params):
         with _write_lock:
             _hrm_conn.execute(sql, params)
             _hrm_conn.commit()
     ```
  3. Register a shutdown handler to close connections:
     ```python
     @app.on_event("shutdown")
     def close_dbs():
         _hrm_conn.close()
         _banking_conn.close()
     ```
- **Effort Estimate**: M (1-2 hours)
- **Risk of NOT Fixing**: `database is locked` errors under concurrent requests. Connection churn wastes resources. Potential data corruption on concurrent writes.

---

### M7: Hardcoded year 2026 inconsistency

- **Description**: Leave balance and form-based leave request endpoints hardcode `year = 2026`, while the chat-based leave registration correctly uses `date.today().year`. Creates inconsistent behavior when the year changes.
- **File:Lines**: `demo/server.py` L409 (leave-balance), L473 (leave-request form)
- **Root Cause**: Year was hardcoded during initial development and not updated to dynamic.
- **Fix Recommendation**:
  1. Replace `year = 2026` with `year = date.today().year` at both locations.
  2. Search for any other hardcoded `2026` references and update them.
- **Effort Estimate**: S (<30 min)
- **Risk of NOT Fixing**: Leave balance queries return wrong data after year boundary. Inconsistent behavior between chat and form flows.

---

### M8: Incorrect error message for zero working days

- **Description**: When a leave request spans zero working days (e.g., weekend-only range), the error message is incorrect or misleading.
- **File:Lines**: `demo/server.py` L466-467
- **Root Cause**: Edge case not handled in `_count_working_days` result validation.
- **Fix Recommendation**:
  1. Add an explicit check after computing working days:
     ```python
     working_days = _count_working_days(start_dt, end_dt)
     if working_days == 0:
         raise HTTPException(400, detail="Selected date range contains no working days.")
     ```
  2. Ensure the error message clearly states the issue.
- **Effort Estimate**: S (<30 min)
- **Risk of NOT Fixing**: Users can submit leave requests for zero working days, or receive a confusing error message.

---

### M9: Date parsing no validation in _extract_leave_dates

- **Description**: `_extract_leave_dates()` extracts dates via regex but does not validate them (e.g., "31/02/2026" would be parsed without error until it hits `datetime` and raises an unhandled exception).
- **File:Lines**: `demo/server.py` L137-178
- **Root Cause**: Regex extraction assumes well-formed dates without validation.
- **Fix Recommendation**:
  1. Wrap date construction in try/except:
     ```python
     try:
         parsed_date = date(year, month, day)
     except ValueError:
         return None  # or raise a user-friendly error
     ```
  2. Validate that start_date <= end_date.
  3. Validate dates are not in the distant past or future.
- **Effort Estimate**: S (<30 min)
- **Risk of NOT Fixing**: Invalid dates cause unhandled exceptions, which then leak error details to the client (see M4).

---

### M10: Duplicated leave creation logic (chat vs form)

- **Description**: Leave creation logic exists in two places: the chat-based flow (`_handle_leave_registration`, L197-302) and the form-based endpoint (`POST /api/hrm/leave-request`, L460-506). Both perform date validation, working day calculation, balance checking, and INSERT operations independently.
- **File:Lines**: `demo/server.py` L197-302 (chat flow), L460-506 (form flow)
- **Root Cause**: Features were added incrementally without refactoring shared logic.
- **Fix Recommendation**:
  1. Extract a shared function:
     ```python
     def _create_leave_request(employee_id, leave_type_id, start_date, end_date, reason, year=None):
         """Shared leave creation logic: validate, check balance, insert."""
         ...
     ```
  2. Have both the chat handler and form endpoint call this shared function.
  3. This also consolidates the hardcoded year fix (M7) and date validation fix (M9) to a single location.
- **Effort Estimate**: M (1-2 hours)
- **Risk of NOT Fixing**: Bug fixes must be applied twice. Divergent behavior between chat and form flows. Higher maintenance burden.

---

### M11: Unbounded localStorage session growth

- **Description**: Chat sessions are stored in localStorage with no limit. Over time, this grows unbounded, eventually hitting the ~5MB localStorage limit and causing silent data loss or errors.
- **File:Lines**: `demo/ui/src/App.tsx` L135 (saveSessions), L193 (loadSessions)
- **Root Cause**: No session eviction or size management was implemented.
- **Fix Recommendation**:
  1. Limit stored sessions to a maximum (e.g., 50):
     ```typescript
     const MAX_SESSIONS = 50;
     const saveSessions = (s: Session[]) => {
       const trimmed = s.slice(0, MAX_SESSIONS);
       localStorage.setItem("sessions", JSON.stringify(trimmed));
     };
     ```
  2. Optionally add a "clear old sessions" button in the UI.
- **Effort Estimate**: S (<30 min)
- **Risk of NOT Fixing**: localStorage fills up, causing data loss and broken session persistence. User has no indication of the problem.

---

### M12: No HTTP status check on frontend fetch responses

- **Description**: Frontend fetch calls do not check `response.ok` or `response.status` before parsing JSON. Non-200 responses (4xx, 5xx) are silently treated as success or cause cryptic JSON parse errors.
- **File:Lines**: `demo/ui/src/App.tsx` L302-310 (chat submit), L241 (leave submit)
- **Root Cause**: Minimal error handling on fetch calls.
- **Fix Recommendation**:
  1. Add status checks after every fetch:
     ```typescript
     const res = await fetch(url);
     if (!res.ok) {
       const err = await res.json().catch(() => ({ detail: "Request failed" }));
       throw new Error(err.detail || `HTTP ${res.status}`);
     }
     ```
  2. Display error feedback to the user (toast notification or inline error).
- **Effort Estimate**: S (<30 min)
- **Risk of NOT Fixing**: Users see no feedback on server errors. Failed requests appear to succeed. Debugging is difficult.

---

## Suggestions (COULD improve)

### L1: Silent error swallowing .catch(() => {}) x3

- **Description**: Three `.catch(() => {})` calls silently swallow errors from HRM data, current-user, and leave data fetches.
- **File:Lines**: `demo/ui/src/App.tsx` L211, L217, L230
- **Root Cause**: Quick error suppression during development.
- **Fix Recommendation**: Replace with `console.error` at minimum, or show a notification:
  ```typescript
  .catch((err) => console.error("Failed to load HRM data:", err))
  ```
- **Effort Estimate**: S (<30 min)
- **Risk of NOT Fixing**: Failures are invisible. Data may silently not load with no user feedback.

---

### L2: Monolithic App.tsx (783 lines, ~22 useState hooks)

- **Description**: The entire frontend is a single component. No custom hooks, no component extraction, no separation of concerns.
- **File:Lines**: `demo/ui/src/App.tsx` (entire file)
- **Root Cause**: Rapid prototyping without refactoring.
- **Fix Recommendation**:
  1. Extract custom hooks: `useSessions()`, `useHrmData()`, `useLeaveForm()`, `useChatSubmit()`.
  2. Extract components: `ChatView`, `HrmDashboard`, `LeaveForm`, `Sidebar`, `DebugPanel`.
  3. Each component in its own file under `demo/ui/src/components/`.
- **Effort Estimate**: L (4+ hours)
- **Risk of NOT Fixing**: Difficult to maintain, test, or onboard new developers. Any change risks unintended side effects across unrelated functionality.

---

### L3: Column definitions recreated every render

- **Description**: HRM table column definitions are plain objects recreated on every render cycle.
- **File:Lines**: `demo/ui/src/App.tsx` L406-441
- **Root Cause**: Column defs defined inside the component body without memoization.
- **Fix Recommendation**: Move column definitions outside the component or wrap in `useMemo`:
  ```typescript
  const deptColumns = useMemo(() => [...], []);
  ```
- **Effort Estimate**: S (<30 min)
- **Risk of NOT Fixing**: Minor unnecessary re-renders. No functional impact.

---

### L4: debugCollapseItems not memoized

- **Description**: Debug panel collapse items are rebuilt on every render.
- **File:Lines**: `demo/ui/src/App.tsx` L314-403
- **Root Cause**: No memoization applied.
- **Fix Recommendation**: Wrap in `useMemo` with appropriate dependencies.
- **Effort Estimate**: S (<30 min)
- **Risk of NOT Fixing**: Minor performance overhead. No functional impact.

---

### L5: Double loadSessions() on mount

- **Description**: `loadSessions()` parses localStorage JSON twice on component mount -- once for the sessions list and once for the active session ID.
- **File:Lines**: `demo/ui/src/App.tsx` L160-161
- **Root Cause**: State initializers independently call the same parse function.
- **Fix Recommendation**: Parse once and derive both values:
  ```typescript
  const [initialSessions] = useState(() => loadSessions());
  const [sessions, setSessions] = useState(initialSessions);
  const [activeSessionId, setActiveSessionId] = useState(initialSessions[0]?.id ?? "");
  ```
- **Effort Estimate**: S (<30 min)
- **Risk of NOT Fixing**: Double JSON parse on mount. Negligible performance impact.

---

### L6: Dead forced_domain/use_embedding from UI

- **Description**: The `ChatRequest` model supports `forced_domain` and `use_embedding` fields, but the frontend never sends them. These backend parameters are effectively dead code from the UI perspective.
- **File:Lines**: `demo/ui/src/App.tsx` L303 (only sends `message`), `demo/server.py` L63-64
- **Root Cause**: Backend supports features the UI does not expose.
- **Fix Recommendation**: Either add a domain selector dropdown to the UI, or document that these are API-only parameters for programmatic use.
- **Effort Estimate**: S (<30 min)
- **Risk of NOT Fixing**: Confusing API surface. Developers may assume the UI uses these features.

---

### L7: Hardcoded attendance default dates

- **Description**: Attendance endpoint defaults to `2026-03-01` / `2026-03-24` and the frontend displays matching hardcoded text.
- **File:Lines**: `demo/server.py` L372-373, `demo/ui/src/App.tsx` L683
- **Root Cause**: Static demo defaults not made dynamic.
- **Fix Recommendation**: Use dynamic defaults based on current month:
  ```python
  today = date.today()
  default_from = today.replace(day=1).isoformat()
  default_to = today.isoformat()
  ```
- **Effort Estimate**: S (<30 min)
- **Risk of NOT Fixing**: Stale default dates after the demo period.

---

### L8: Date query params no format validation

- **Description**: Date parameters on endpoints like `/api/hrm/attendance` accept any string without format validation. Invalid dates cause unhandled errors.
- **File:Lines**: `demo/server.py` L370-384
- **Root Cause**: Query params are typed as `str` with no pattern validation.
- **Fix Recommendation**: Add regex pattern validation or parse with try/except:
  ```python
  date_from: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
  ```
- **Effort Estimate**: S (<30 min)
- **Risk of NOT Fixing**: Invalid date strings cause 500 errors with stack trace leakage.

---

### L9: reason field no max_length, incomplete requirements.txt, no type safety

- **Description**: Three minor quality issues: (a) `LeaveRequestBody.reason` has no `max_length`, (b) `requirements.txt` is incomplete (missing pipeline deps), (c) frontend API responses use `as` casts without runtime validation.
- **File:Lines**: `demo/server.py` L71 (reason field), `demo/requirements.txt`, `demo/ui/src/App.tsx` L208/L304
- **Root Cause**: Incomplete polish across multiple files.
- **Fix Recommendation**:
  1. Add `max_length=500` to the reason field.
  2. Add missing dependencies to requirements.txt or add a comment explaining they come from the parent project.
  3. Optionally add runtime type checking (zod or manual checks) on frontend API responses.
- **Effort Estimate**: S (<30 min)
- **Risk of NOT Fixing**: Unbounded reason could store very long strings. Incomplete deps cause confusion. Type cast failures cause cryptic runtime errors.

---

## Implementation Order

The following sequence respects dependencies -- each step builds on the previous:

| Step | IDs         | Description                                          | Rationale                                             |
|------|-------------|------------------------------------------------------|-------------------------------------------------------|
| 1    | H1          | Remove dead f-string SQL, return parameterized template | Quick win, removes immediate reflected-input risk    |
| 2    | H2          | Restrict CORS to known origins                       | Prerequisite for CSRF (M2) and auth (H3)              |
| 3    | H3          | Add demo auth middleware                             | Prerequisite for PII filtering (M3) and IDOR fixes    |
| 4    | M1, M4, M5, L9 | Input validation + error sanitization + debug toggle | Independent security hardening, can be done in parallel |
| 5    | M2          | Add CSRF protection                                  | Depends on H2 (CORS restriction)                      |
| 6    | M3          | Add pagination and PII field filtering               | Depends on H3 (auth, to filter by user)               |
| 7    | M6          | Refactor SQLite connection management                | Independent infrastructure change                     |
| 8    | M7, M8, M9, L7, L8 | Fix date handling, hardcoded years, validation  | Group all date/time correctness fixes                  |
| 9    | M10         | Consolidate duplicated leave creation logic          | Depends on M7-M9 fixes being done first               |
| 10   | M11, M12, L1, L3, L4, L5, L6 | Frontend fixes: error handling, memoization, cleanup | Independent frontend improvements, batch together |
| 11   | L2          | Refactor monolithic App.tsx into components          | Do last -- largest effort, benefits from all prior fixes being stable |

---

## Effort Summary

| Severity | Count | S (<30m) | M (1-2h) | L (4h+) | Total Effort Estimate |
|----------|-------|----------|-----------|---------|----------------------|
| HIGH     | 3     | 2        | 0         | 1       | ~5 hours             |
| MEDIUM   | 12    | 7        | 5         | 0       | ~13.5 hours          |
| LOW      | 9     | 8        | 0         | 1       | ~8 hours             |
| **Total**| **24**| **17**   | **5**     | **2**   | **~26.5 hours**      |

### Time Breakdown by Step

| Step | Effort  | Cumulative |
|------|---------|------------|
| 1    | 30 min  | 0.5h       |
| 2    | 30 min  | 1h         |
| 3    | 4 hours | 5h         |
| 4    | 2 hours | 7h         |
| 5    | 1.5h    | 8.5h       |
| 6    | 1.5h    | 10h        |
| 7    | 1.5h    | 11.5h      |
| 8    | 2.5h    | 14h        |
| 9    | 1.5h    | 15.5h      |
| 10   | 3.5h    | 19h        |
| 11   | 4+ hours| ~23-27h    |

**Recommendation**: Steps 1-4 (all HIGH + critical MEDIUM fixes) can be completed in one working day (~7 hours) and should be the minimum bar before any demo deployment.
