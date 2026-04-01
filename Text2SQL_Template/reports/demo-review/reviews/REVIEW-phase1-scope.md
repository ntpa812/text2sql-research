# Phase 1 Review: Scope & Context (Devil's Advocate)

**Scout Report Under Review**: `SCOUT-demo-scope.md`
**Reviewer Role**: Devil's Advocate — verify completeness, challenge assumptions
**Status**: CONDITIONAL PASS (with mandatory additions before Phase 2)

---

## Verdict on Each Scout Finding

### 1. CRITICAL — SQL Injection Vulnerability (L252-256)

**Status**: CONFIRMED — but severity DOWNGRADED to MEDIUM

**Evidence**: Lines 252-256 in `server.py` do construct an f-string SQL with user-derived values. Lines 258-262 use parameterized queries for actual execution. The scout correctly identified this.

**However**, the scout's characterization is slightly misleading. The scout says `reason` "comes directly from user input via regex extraction" — this is true, but the scout fails to note that `employee_id` is hardcoded to `DEMO_CURRENT_USER = "EMP001"` (L58, L315), `leave_type` comes from a keyword dict with a fixed set of values (L118-124), and `start_date`/`end_date` are regex-extracted date strings. The only truly unsanitized user input in the f-string is `reason` (via `_extract_reason`, L191-194). This is dead code for execution, so the real risk is information leakage (the raw SQL with user values is returned in the API response at L289), not injection. Severity should be MEDIUM, not CRITICAL.

---

### 2. HIGH — Monolithic Frontend (783 lines)

**Status**: CONFIRMED

**Evidence**: Verified. 783 lines, approximately 30 `useState` hooks (counted 22 explicit `useState` declarations at L159-190), single component, no extraction. The scout's characterization is accurate. This is a real maintainability problem.

---

### 3. HIGH — No Authentication / Authorization

**Status**: CONFIRMED

**Evidence**: `DEMO_CURRENT_USER` hardcoded at L58. CORS `allow_origins=["*"]` at L51. No auth middleware. The `POST /api/hrm/leave-request` endpoint (L460-506) and the chat-based leave registration (L197-302) both write to the actual SQLite database. Confirmed.

**Note**: The scout correctly flags the mitigation (this is a demo), but the write operations are real. This finding stands as-is.

---

### 4. MEDIUM — No Input Sanitization on Chat

**Status**: CONFIRMED

**Evidence**: `ChatRequest` at L61-64 has `min_length=1` but no `max_length`. This is passed to `run_pipeline()` which feeds it to LLM calls and multiple regex operations. The regex patterns in `_extract_leave_dates` (L137-178) have multiple alternation branches that could cause backtracking on adversarial input.

---

### 5. MEDIUM — Silent Error Swallowing (Frontend)

**Status**: CONFIRMED

**Evidence**: App.tsx L211: `.catch(() => {})` on HRM data fetch. L217: `.catch(() => {})` on current-user fetch. L230: `.catch(() => {})` on leave data fetch. The scout identified L211 and L217 but **missed L230** — the leave data fetch also silently swallows errors.

---

### 6. MEDIUM — Hardcoded Year 2026

**Status**: CONFIRMED

**Evidence**: L409 has `year = 2026` in the leave-balance endpoint. L472-473 has `year = 2026` in the form-based leave-request endpoint. L236 uses `date.today().year` in the chat-based leave registration. The inconsistency is real and verified.

---

### 7. LOW — Unused Variable / Dead Code (insert_sql)

**Status**: CONFIRMED

**Evidence**: L252-256 builds `insert_sql` via f-string. L258-262 executes a parameterized query. `insert_sql` is only referenced again at L289 where it is returned in the response payload. This is dead code for execution purposes.

---

### 8. LOW — Missing pydantic in requirements.txt

**Status**: CONFIRMED

**Evidence**: `requirements.txt` contains only `fastapi==0.118.0` and `uvicorn==0.37.0`. Pydantic is an implicit dependency of FastAPI. However, the pipeline dependencies (`pipeline.runner`, `pipeline.domain_router`, etc.) are entirely absent. This file is insufficient for standalone deployment.

---

### 9. LOW — No Type Safety on API Responses (Frontend)

**Status**: CONFIRMED

**Evidence**: L208 uses type assertion on the destructured fetch results. L304 casts `await res.json()` as `ChatApiResponse`. No runtime validation (no zod, no io-ts, no manual checks).

---

## Additional Findings the Scout MISSED

### MISSED-1: HIGH — `@ant-design/icons` Not Listed in package.json

**File**: `demo/ui/package.json` + `demo/ui/src/App.tsx` L24-31

**Evidence**: App.tsx imports `ApartmentOutlined`, `CalendarOutlined`, `MenuFoldOutlined`, `MenuUnfoldOutlined`, `MessageOutlined`, `TeamOutlined`, `UserOutlined` from `@ant-design/icons`. This package is NOT listed in `package.json` dependencies or devDependencies. It likely works because `antd` pulls it as a transitive dependency, but this is fragile — a version bump to antd could break it, and `npm install` in a clean environment may not resolve it. The scout listed "5 (react, react-dom, antd, antd-style, clsx)" as external JS deps but missed this phantom dependency.

### MISSED-2: MEDIUM — Vite Proxy Configuration Not in Scope

**File**: `demo/ui/vite.config.ts`

**Evidence**: The vite config proxies `/api` requests to `http://127.0.0.1:8001`. This means during development, the frontend expects the FastAPI server on port 8001. The scout listed this file as "Other UI files (not source, but notable)" but did not analyze its content or note the port coupling. If the server port changes, development breaks silently (requests go to wrong backend). This is an operational coupling that should be documented.

### MISSED-3: MEDIUM — No `server.py` Startup Port Configuration

**File**: `demo/server.py`

**Evidence**: The server file has no `if __name__ == "__main__"` block and no uvicorn configuration. It is unclear how the server is started or on what port. The vite proxy assumes port 8001, but nothing in the codebase enforces this. There is no startup script, no Makefile, no docker-compose. This is a gap in the operational scope.

### MISSED-4: LOW — `loadSessions()` Called Twice on Mount

**File**: `demo/ui/src/App.tsx` L160-161

**Evidence**: `loadSessions()` is called as the initializer for both `sessions` (L160) and `activeSessionId` (L161). This parses `localStorage` JSON twice on every component mount. Minor performance issue but indicates the initialization logic was not thought through.

### MISSED-5: LOW — Frontend `handleSubmit` Does Not Send `forced_domain` or `use_embedding`

**File**: `demo/ui/src/App.tsx` L303

**Evidence**: The chat POST body is `JSON.stringify({ message })` — it does not include `forced_domain` or `use_embedding` fields even though `ChatRequest` (server.py L61-64) supports them and the meta endpoint returns domain information. The domain selector in the UI does not exist. This means the `forced_domain` and `use_embedding` parameters on the backend are effectively dead code from the UI's perspective.

### MISSED-6: LOW — Attendance Endpoint Default Dates Hardcoded

**File**: `demo/server.py` L372-373

**Evidence**: `date_from: str = Query(default="2026-03-01")` and `date_to: str = Query(default="2026-03-24")`. Same class of issue as the hardcoded year 2026 but applied to the attendance endpoint defaults. The frontend also hardcodes the display text "01/03 - 24/03/2026" at App.tsx L683. The scout only flagged L409 and L473 for the leave-balance/leave-request endpoints.

### MISSED-7: MEDIUM — `_db_query` Opens a New Connection Per Request (Connection Management)

**File**: `demo/server.py` L31-38, L449-457

**Evidence**: Both `_db_query` and `_hrm_write` open a new `sqlite3.connect()` call on every invocation and close it in `finally`. Under concurrent requests (FastAPI is async-capable, uvicorn serves with multiple workers), this creates connection churn. More critically, SQLite has limited write concurrency — concurrent leave registration requests could cause `database is locked` errors. The scout mentioned "connection leak" in the git history (commit f8a8d55) but did not assess whether the current code still has concurrency risks.

---

## Gaps in Scope That Must Be Addressed Before Phase 2

### GAP-1: Pipeline Interface Contract Not Verified

The scout lists the `run_pipeline` signature and its transitive dependencies but did not verify the actual signature matches. I verified it: the signature at `pipeline/runner.py:210-216` is `run_pipeline(question, use_embedding, explain, forced_domain, demo_mode, user_context)` which matches the call at `server.py:317-324`. This gap is now closed.

### GAP-2: SQLite Database Schema Not Inventoried

The scout notes the databases at `data/domains/hrm/mock/hrm.db` and `data/domains/banking/mock/banking.db` as data dependencies, but the actual table schemas are not documented. The server writes to `leave_request` and reads from `leave_balance`, `leave_type`, `employee`, `department`, `attendance`, `customer`, `customer_account`, `transaction`. If any of these schemas change, the inline SQL breaks. **Before Phase 2, the reviewer should have the DB schemas available** to verify SQL correctness.

### GAP-3: `demo/ui/hrm_database.html` Not Assessed

The scout mentions this as "likely legacy/prototype" but did not open or verify it. If it contains hardcoded credentials, API endpoints, or outdated logic that could confuse developers, it should be flagged.

### GAP-4: No Assessment of `demo/ui/index.html`

This is the HTML entry point for the Vite-built SPA. The scout did not list or assess it. It was found in the glob results. It likely just loads the JS bundle, but should be confirmed.

---

## Summary

| Category | Scout Found | Reviewer Verified | Reviewer Added |
|----------|-------------|-------------------|----------------|
| CRITICAL | 1 | 0 (downgraded to MEDIUM) | 0 |
| HIGH | 2 | 2 confirmed | 1 (phantom dependency) |
| MEDIUM | 3 | 3 confirmed (1 incomplete) | 3 (vite proxy, no startup config, connection concurrency) |
| LOW | 3 | 3 confirmed | 3 (double loadSessions, dead forced_domain, attendance dates) |
| **Total** | **9** | **8 confirmed, 1 regraded** | **7 new findings** |

**Final Verdict**: CONDITIONAL PASS. The scout report is substantially correct in its findings and architecture mapping. The blast radius analysis is accurate. However:

1. The SQL injection severity should be downgraded from CRITICAL to MEDIUM (dead code, only one truly unsanitized field, information leakage not execution risk).
2. Seven additional findings were missed, including one HIGH (phantom `@ant-design/icons` dependency).
3. Four scope gaps need resolution before Phase 2 begins (pipeline contract verified, DB schema needed, two unassessed HTML files).

**Recommendation**: Proceed to Phase 2 with the expanded finding list and the four gap items addressed.
