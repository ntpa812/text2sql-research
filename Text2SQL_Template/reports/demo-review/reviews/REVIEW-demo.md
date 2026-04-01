# Code Review: demo/

## Verdict: CHANGES REQUIRED

## Executive Summary

The demo/ application (FastAPI backend + React frontend, ~1,987 lines across 6 source files) provides a functional Text2SQL chatbot with HRM and banking data endpoints. However, 3 HIGH-severity security issues -- dead f-string SQL returning unsanitized user input, CORS wildcard on write endpoints, and absent authentication -- make it unsuitable for any deployment beyond isolated local development. An estimated 7 hours of focused work on the top-priority fixes (Steps 1-4) would bring the application to an acceptable baseline; the full remediation plan totals approximately 26.5 hours.

## Scope

| Attribute | Detail |
|-----------|--------|
| Files reviewed | `demo/server.py` (625 lines), `demo/ui/src/App.tsx` (783 lines), `demo/ui/src/main.tsx` (10 lines), `demo/ui/src/styles.css` (349 lines), `demo/ui/src/shadcnTheme.ts` (218 lines), `demo/requirements.txt` (2 lines) |
| Total source lines | ~1,987 |
| API endpoints | 16 (2 POST, 14 GET) |
| Databases | 2 SQLite (hrm.db, banking.db) |
| Parent project imports | 3 (`pipeline.runner`, `registry_loader`, `llm_sql_generator`) |
| Review dimensions | Correctness, Security, Performance, Architecture, Code Quality |

## Risk Assessment

| Risk | Severity | Likelihood | Business Impact | Mitigation |
|------|----------|------------|-----------------|------------|
| Unsanitized user input reflected in API responses (H1) | HIGH | High | XSS via debug panel; social engineering via visible SQL; latent injection vector | Remove f-string SQL, return parameterized template only |
| Cross-origin data modification via CORS wildcard (H2) | HIGH | High | Any website can create leave requests and query all HR/banking data | Restrict `allow_origins` to known hosts; use env var for deployment |
| No authentication; hardcoded user; IDOR on all endpoints (H3) | HIGH | High | Complete unauthorized data access and write capability | Add demo token-based auth middleware; inject current user per-request |
| No CSRF protection on POST endpoints (M2) | MEDIUM | Medium | Cross-site request forgery on leave creation and chat | Fix CORS first, then add custom header check |
| PII data exposure without pagination (M3) | MEDIUM | Medium | Full employee/customer data scraping | Add pagination, column filtering, auth-scoped queries |
| Error/debug detail leakage to client (M4, M5) | MEDIUM | Medium | Reconnaissance aid for targeted attacks | Sanitize errors; toggle debug output via env var |
| SQLite connection churn and write contention (M6) | MEDIUM | Low | `database is locked` errors under concurrency | Use shared connection with WAL mode and write lock |
| Monolithic frontend (L2) | LOW | N/A | Maintenance burden; difficult to test or extend | Extract components and custom hooks |

## Critical Issues (3) -- MUST fix

| # | Category | File:Line | Description | Fix | Effort |
|---|----------|-----------|-------------|-----|--------|
| H1 | Security | `demo/server.py` L252-256, L289 | f-string SQL with unsanitized user input (`reason` field) returned in API response and rendered in frontend debug panel | Delete f-string SQL (L252-256); replace `result.sql` at L289 with parameterized template string | S (<30 min) |
| H2 | Security | `demo/server.py` L49-54 | CORS `allow_origins=["*"]` permits any website to call write endpoints (`POST /api/chat`, `POST /api/hrm/leave-request`) | Replace with explicit origin list; read from `CORS_ORIGINS` env var | S (<30 min) |
| H3 | Security | `demo/server.py` L58, all endpoints | No authentication; `DEMO_CURRENT_USER = "EMP001"` hardcoded; any caller can pass arbitrary `employee_id` for IDOR | Add demo token-based auth middleware with `Depends(get_current_user)`; filter queries by authenticated user | L (4+ hours) |

## Warnings (12) -- SHOULD fix

| # | Category | File:Line | Description | Fix | Effort |
|---|----------|-----------|-------------|-----|--------|
| M1 | Security | `demo/server.py` L62, L137-178 | No `max_length` on `ChatRequest.message`; ReDoS risk in date extraction regexes | Add `max_length=2000`; add regex timeouts or possessive grouping | S |
| M2 | Security | `demo/server.py` L305-328, L460-506 | No CSRF protection on POST endpoints | Fix H2 first; add `X-Requested-With` header check middleware | M |
| M3 | Security | `demo/server.py` L346-367, L511-546 | PII data exposed via `SELECT *` with no pagination | Add `limit`/`offset` params; exclude sensitive columns | M |
| M4 | Security | `demo/server.py` L79 | Raw pipeline errors returned to client, leaking internal paths and schema | Return generic error messages; log details server-side | S |
| M5 | Security | `demo/server.py` L74-92 | Debug data (SQL, domain, schema, timing) in all API responses | Add `DEMO_DEBUG` env toggle; conditionally include debug fields | S |
| M6 | Performance | `demo/server.py` L31-38, L449-457 | New SQLite connection per request; concurrent write risk | Use module-level connection with WAL mode and threading lock | M |
| M7 | Correctness | `demo/server.py` L409, L473 | Hardcoded `year = 2026` inconsistent with chat flow using `date.today().year` | Replace with `date.today().year` | S |
| M8 | Correctness | `demo/server.py` L466-467 | Incorrect/misleading error for zero working days in date range | Add explicit check: `if working_days == 0: raise HTTPException(400, ...)` | S |
| M9 | Correctness | `demo/server.py` L137-178 | Date parsing via regex with no validation (e.g., "31/02/2026" unhandled) | Wrap date construction in try/except; validate start <= end | S |
| M10 | Architecture | `demo/server.py` L197-302, L460-506 | Duplicated leave creation logic between chat and form flows | Extract shared `_create_leave_request()` function | M |
| M11 | Performance | `demo/ui/src/App.tsx` L135, L193 | Unbounded localStorage session growth; will hit ~5MB limit | Cap stored sessions at 50; trim on save | S |
| M12 | Correctness | `demo/ui/src/App.tsx` L302-310, L241 | No HTTP status check on frontend fetch; errors silently treated as success | Check `response.ok` before parsing; display error feedback | S |

## Suggestions (9) -- COULD improve

| # | Category | File:Line | Description | Fix | Effort |
|---|----------|-----------|-------------|-----|--------|
| L1 | Correctness | `demo/ui/src/App.tsx` L211, L217, L230 | Silent error swallowing via `.catch(() => {})` on 3 fetch calls | Replace with `console.error` or user notification | S |
| L2 | Architecture | `demo/ui/src/App.tsx` (entire file) | Monolithic 783-line single component with ~22 useState hooks | Extract custom hooks and sub-components into `components/` directory | L |
| L3 | Performance | `demo/ui/src/App.tsx` L406-441 | Column definitions recreated every render cycle | Move outside component or wrap in `useMemo` | S |
| L4 | Performance | `demo/ui/src/App.tsx` L314-403 | Debug collapse items rebuilt on every render | Wrap in `useMemo` with appropriate dependencies | S |
| L5 | Performance | `demo/ui/src/App.tsx` L160-161 | Double `loadSessions()` parse on mount | Parse once, derive both sessions list and active ID | S |
| L6 | Code Quality | `demo/server.py` L63-64, `App.tsx` L303 | `forced_domain`/`use_embedding` params unused by frontend | Add UI controls or document as API-only params | S |
| L7 | Correctness | `demo/server.py` L372-373, `App.tsx` L683 | Hardcoded attendance default dates (2026-03-01/2026-03-24) | Use dynamic defaults based on current month | S |
| L8 | Correctness | `demo/server.py` L370-384 | Date query params accept any string without format validation | Add regex pattern validation or parse with try/except | S |
| L9 | Code Quality | `demo/server.py` L71, `requirements.txt`, `App.tsx` L208/L304 | `reason` field no `max_length`; incomplete requirements.txt; no runtime type validation on frontend | Add `max_length=500`; update deps; optionally add zod/manual checks | S |

## Security Summary

**OWASP Top 10 Assessment:**

| OWASP Category | Status | Key Issues |
|----------------|--------|------------|
| A01: Broken Access Control | FAIL | No authentication, no authorization, IDOR on employee_id (H3) |
| A03: Injection | FAIL | Unsanitized user input reflected in API response (H1); dead f-string SQL vector |
| A05: Security Misconfiguration | FAIL | CORS wildcard on write endpoints (H2); debug data in all responses (M5) |
| A07: Identification & Auth Failures | FAIL | Hardcoded user identity; no auth mechanism (H3) |
| A09: Security Logging & Monitoring | FAIL | Silent error swallowing; no structured logging |
| A04: Insecure Design | WARN | No CSRF protection (M2); no input length limits (M1) |
| A08: Software & Data Integrity | WARN | No HTTP status validation on frontend (M12) |
| A02: Cryptographic Failures | PASS | No cryptographic operations in scope |
| A06: Vulnerable Components | PASS | Dependencies are current versions |
| A10: SSRF | PASS | No server-side request construction from user input |

**Vulnerability count by severity:** 3 HIGH, 5 MEDIUM security-specific findings.

## Performance Summary

| Bottleneck | Impact | Location |
|------------|--------|----------|
| SQLite connection-per-request | Connection churn; `database is locked` under concurrency | `server.py` L31-38, L449-457 |
| No pagination on list endpoints | Full table scans returned to client; memory pressure on large datasets | `server.py` L346-367, L511-546 |
| Unbounded localStorage growth | Browser storage limit hit after extended use | `App.tsx` L135 |
| Column defs + debug items rebuilt every render | Unnecessary React reconciliation work | `App.tsx` L314-441 |
| Double localStorage parse on mount | Minor redundant deserialization | `App.tsx` L160-161 |

Overall performance impact is moderate for a demo application. The SQLite connection management (M6) and missing pagination (M3) are the most impactful under any realistic load.

## Architecture Assessment

**Layer separation:** The demo follows a clean 2-tier architecture (React SPA over FastAPI BFF) with clear HTTP boundaries. The frontend is a pure API consumer with no direct parent project imports.

**Blast radius:** Changes to demo/ affect only the demo application. No other module depends on it. Parent project changes to `run_pipeline()` signature, domain registry format, or SQLite schemas would break demo/.

**Separation of concerns -- Backend:** The single `server.py` file mixes API routing, business logic (leave registration, date extraction, working day calculation), and data access. Leave creation logic is duplicated across chat and form flows (M10).

**Separation of concerns -- Frontend:** The entire UI lives in a single 783-line `App.tsx` with ~22 useState hooks and no component extraction. This is the single largest maintainability concern.

**Testability:** Zero test files exist in demo/. The monolithic structure of both backend and frontend makes unit testing difficult without refactoring.

## Positive Findings

- **Parameterized queries for actual execution:** Despite the f-string SQL issue (H1), the actual database writes at L258-262 correctly use parameterized queries with `?` placeholders. The team understands SQL injection prevention.
- **Clean pipeline integration:** The 3 imports from the parent project (`run_pipeline`, `load_domain_registry`, `get_generation_config`) are well-isolated, making the demo easy to update when the pipeline evolves.
- **Functional feature completeness:** The demo covers chat-based Text2SQL, leave management (both chat and form flows), HRM dashboard, and banking data views -- a comprehensive showcase.
- **Responsive UI design:** Glass-morphism styling with responsive breakpoints at 1400px, 1100px, and 900px. Professional visual presentation.
- **Correct working day calculation:** `_count_working_days()` properly excludes weekends using weekday arithmetic.
- **Vietnamese NLP date extraction:** `_extract_leave_dates()` handles multiple Vietnamese date formats with reasonable regex coverage.
- **Modern stack choices:** FastAPI with Pydantic models, React 18 with Ant Design 5, Vite bundler -- all current and well-supported.

## Recommended Actions

1. **Remove dead f-string SQL and sanitize response payload (H1)** -- Owner: Backend Engineer -- Priority: P0
2. **Restrict CORS origins to known hosts (H2)** -- Owner: Backend Engineer -- Priority: P0
3. **Add demo authentication middleware (H3)** -- Owner: Backend Engineer -- Priority: P0
4. **Add input validation limits and error sanitization (M1, M4, M5, L9)** -- Owner: Backend Engineer -- Priority: P1
5. **Add CSRF protection on POST endpoints (M2)** -- Owner: Backend Engineer -- Priority: P1
6. **Add pagination and PII field filtering (M3)** -- Owner: Backend Engineer -- Priority: P1
7. **Refactor SQLite connection management with WAL mode (M6)** -- Owner: Backend Engineer -- Priority: P1
8. **Fix all date handling: hardcoded year, validation, error messages (M7, M8, M9, L7, L8)** -- Owner: Backend Engineer -- Priority: P1
9. **Consolidate duplicated leave creation logic (M10)** -- Owner: Backend Engineer -- Priority: P2
10. **Frontend fixes: HTTP status checks, error handling, memoization, session limits (M11, M12, L1, L3, L4, L5, L6)** -- Owner: Frontend Engineer -- Priority: P2
11. **Refactor monolithic App.tsx into components and custom hooks (L2)** -- Owner: Frontend Engineer -- Priority: P2

**Minimum deployment bar:** Complete actions 1-4 (~7 hours) before any non-local demo deployment.

## Review Metadata

- **Review type:** Golden Triangle (3-agent adversarial)
- **Phases completed:** 4 (Scope Mapping, Deep Review, Improvement Planning, Summary)
- **Total findings:** 24 (3 HIGH, 12 MEDIUM, 9 LOW)
- **Debate rounds:** 3 consensus decisions across 11 exchanges; 1 severity arbitration (SQL injection: CRIT disputed to HIGH, resolved by evidence-based ruling -- dead code for execution but actively returned with unsanitized input)
- **Review date:** 2026-04-01
- **Agents involved:** scouter (scope), reviewer/executor (deep review), security-engineer (security lens), planner (improvement plan), reporter (final synthesis)
- **Estimated remediation effort:** ~26.5 hours total (17 small, 5 medium, 2 large tasks)
