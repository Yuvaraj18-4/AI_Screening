# ShortList — Build Log

## Housekeeping
- Python: Pinned to 3.11 everywhere (`backend/.venv`, `backend/pyproject.toml`, `Dockerfile`, `docs/ARCHITECTURE.md`).
- Workspace Rules: Retained single rules source `GEMINI.md`. Removed duplicate `.agent/rules/rules.md`. Active rules: `GEMINI.md`.
- Tailwind & CSS: Tailwind v4 with design tokens defined under `@theme` in `frontend/src/index.css`. Prettier pinned (`^3.5.3`).
- Alembic directory: Set at `backend/app/db/migrations/`.
- npm audit: High severity vulnerability in `zod <4.6.6` (GHSA-mrhx-c7xc-m3w5: memory exhaustion during oversized collection validation). Upgrade to zod@4 is breaking for react-hook-form resolvers / current codebase. `npm audit fix --force` avoided per instructions. Risk assessed: client-side Zod validation parses internal forms with bounded input; risk mitigated on backend by Pydantic.
- google-genai version: `google-genai==1.9.0` verified compatible with structured outputs via `GenerateContentConfig(response_mime_type="application/json", response_schema=...)`. Kept pinned at 1.9.0.

## NEEDS USER
- `GEMINI_API_KEY`: Real Gemini API key required for live AI scoring. App defaults to heuristic scoring mode with banner when key is missing or empty. Script `scripts/verify_gemini.py` provided to test live Gemini once key is provided.
- Production hosting & Neon Postgres: Deployment to Render and Neon requires user credentials and accounts. Step-by-step instructions provided in `deployment.md`.

## Phase Log
### Phase 1: Backend Foundation
- Built database models for all 17 entities in `backend/app/db/models/entities.py`.
- Configured Alembic migrations in `backend/app/db/migrations/` and applied initial migration `24521451b96f`.
- Built security layer (Argon2 hashing, PyJWT tokens, login rate limiting, CSRF header checks).
- Built session and dependency management (`get_db`, `get_current_user`, `require_role`, `verify_csrf`).
- Implemented `visible_applications_for(user)` service scoping helper ensuring strict client isolation.
- Implemented `/api/auth` (login, logout, me) and `/api/health`.
- Test count: 5 backend tests passed (`tests/test_auth_and_roles.py`).
- Ruff check: clean (0 warnings, 0 errors).
- Frontend oxlint and build: clean.

### Phase 2: JD Intake and Scorecard
- Built `LLMClient` protocol and implementations (`GeminiClient`, `FakeClient`, `HeuristicClient`).
- Implemented versioned prompts with prompt injection protection in `backend/app/ai/prompts.py`.
- Built `GeminiClient` with dynamic model selection (`settings.GEMINI_MODEL`), schema-enforced JSON, concurrency limiting, and exponential retry/backoff on 429/5xx.
- Built `HeuristicClient` producing verifiable exact substrings of masked text for quote verification when running without API key.
- Implemented Requisitions API (`/api/requisitions`) and Scorecard versioning API (`/api/requisitions/{id}/scorecard`, `/api/requisitions/{id}/jd/extract`).
- Built frontend components: Button, Card, Badge, Dialog, Skeleton, EmptyState, ErrorState, ScoreRing, StageChip, HeuristicBanner, Navbar.
- Built frontend views: LoginPage, RequisitionListPage, RequisitionDetailPage, ScorecardEditor, and wired routing with role guards.
- Test count: 8 backend tests passed (`tests/test_requisitions_and_scorecards.py`, `tests/test_auth_and_roles.py`).
- Ruff check: clean (0 warnings, 0 errors).
- Frontend oxlint and build: clean (0 warnings, 0 errors).

### Phase 3: Bulk Upload and Parsing
- Built text extraction engine in `backend/app/parsing/extract_text.py` for PDF (pdfplumber) and DOCX (python-docx) with scanned PDF detection and file validation (magic bytes, 5MB limit).
- Built experience calculation engine in `backend/app/parsing/experience.py` merging overlapping employment intervals, tolerant of unusual date formats, with fallback to explicit experience statements.
- Built notice period normalisation in `backend/app/parsing/notice.py` converting diverse expressions (months, days, immediate, serving notice) into standard days.
- Built deduplication engine in `backend/app/parsing/dedup.py` with exact SHA-256 matching and near-duplicate token Jaccard similarity (threshold >= 0.85).
- Built personal data masking engine in `backend/app/ai/masking.py` redacting names, email, phone, honorifics, gendered pronouns, age/DOB, and family details.
- Built DB-backed asyncio Job Queue with atomic claiming, exponential backoff retries, and startup restart recovery resetting stale running jobs.
- Implemented `/api/requisitions/{id}/uploads` and `/api/uploads/{batch_id}/progress`.
- Built frontend Dropzone and Batch Progress UI in `frontend/src/features/uploads/UploadPage.tsx` with 2-second polling.
- Test count: 14 backend tests passed (`tests/test_parsing_and_uploads.py`, `tests/test_requisitions_and_scorecards.py`, `tests/test_auth_and_roles.py`).
- Ruff check: clean (0 warnings, 0 errors).
- Frontend oxlint and build: clean (0 warnings, 0 errors).

### Phase 4: Scoring Engine & Prompt Defense
- Built quote verifier in `backend/app/ai/verifier.py` with case/whitespace/punctuation normalisation ensuring evidence quotes exist in the masked CV text.
- Built hybrid scoring engine in `backend/app/ai/scoring.py` combining deterministic evaluation (experience, notice, location evaluated via code, source="code") and semantic evaluation (skills, domain evaluated via LLM/Heuristic, source="llm").
- Implemented weighted score formula `sum(weight * value) / sum(weight) * 100` with must-have gap flagging.
- Implemented confidence scoring: low if parse quality is degraded, any quote is unverified, or >=30% criteria unclear; medium for single anomaly; else high.
- Implemented SHA-256 cache key determinism over `(masked_text, scorecard_version, prompt_version, model)`.
- Implemented `ai_failed` resilient error state when LLM fails all retries, avoiding silent zero scores.
- Implemented prompt-injection defense with untrusted resume tags and strict schema parsing.
- Test count: 19 backend tests passed (`tests/test_scoring_and_defense.py`, `tests/test_parsing_and_uploads.py`, etc.).
- Ruff check: clean (0 warnings, 0 errors).
- Frontend oxlint and build: clean (0 warnings, 0 errors).


### Phase 5: Recruiter UI & Workflow
- Built candidate application service layer in `backend/app/services/applications.py` with sorting (by weighted score, stage, name), filtering, and status transitions.
- Built submission service in `backend/app/services/submissions.py` strictly enforcing server-side `ViewLog` verification before client submission (HTTP 409 Conflict if not viewed by recruiter).
- Built candidate duplicate resolution and GDPR/DPDP-compliant deletion in `backend/app/services/candidates.py` creating hash-only audit log entries with zero PII retention.
- Implemented `/api/requisitions/{id}/applications`, `/api/applications/{id}`, `/api/applications/{id}/submit`, `/api/applications/{id}/rescore`, `/api/candidates/{id}/resolve-duplicate`, and `DELETE /api/candidates/{id}`.
- Built frontend components and views:
  - `CandidateRankedList.tsx` with score rings, must-have gap chips, duplicate warning badges, search/filter controls, and sort toggles.
  - `CandidateDetailDrawer.tsx` side panel with tabbed navigation (Scorecard Breakdown, Verified Evidence, Parsed Profile, Activity History).
  - `EvidenceItem.tsx` with criterion match verdict, verification indicator, quote citation, and code/LLM source tags.
- Test count: 22 backend tests passed (`tests/test_recruiter_workflow.py`, `tests/test_scoring_and_defense.py`, `tests/test_parsing_and_uploads.py`, etc.).
- Ruff check: clean (0 warnings, 0 errors).
- Frontend oxlint and build: clean (0 warnings, 0 errors).

### Phase 6: Client Portal & Pipeline
- Built client portal service layer in `backend/app/services/portal.py` with multi-tenant client organization isolation and contact privacy masking.
- Implemented contact unmasking rules: email and phone masked as `[MASKED_UNTIL_SHORTLIST]` until client records a Shortlist or Interview decision, unlocking contact info for scheduling.
- Enforced mandatory rejection reason validation on client rejection actions (HTTP 422 if empty).
- Built interview slot scheduling capturing proposed timestamps and advancing stage to `interview`.
- Implemented Candidate Consent API (`POST /api/candidates/{id}/consent` and `DELETE /api/candidates/{id}/consent`) supporting GDPR/DPDP consent lifecycle.
- Built interactive frontend:
  - `PortalRequisitionsPage.tsx`: mobile-first portal home with client requisition tabs and candidate review cards.
  - `PortalSubmissionDetailPage.tsx`: mobile-friendly candidate evaluation screen with contact masking indicators, verified evidence list, and sticky bottom decision bar.
  - `PipelineBoard.tsx`: recruiter Kanban pipeline board with columns (`sourced`, `screened`, `submitted`, `client_shortlisted`, `interview`, `offered`, `joined`, `rejected`), stage transitions, and linked detail drawer.
- Test count: 25 backend tests passed (`tests/test_client_portal_and_pipeline.py`, `tests/test_recruiter_workflow.py`, etc.).
- Ruff check: clean (0 warnings, 0 errors).
- Frontend oxlint and build: clean (0 warnings, 0 errors).

### Phase 7: Quality Pass, Sample Data & Verification
- Built sample data generation engine in `scripts/generate_samples.py` generating 30 synthetic PDF and DOCX CVs conforming to all BRIEF specifications:
  - Ritika Bansal (`CND-91022_Ritika_Bansal.pdf`): Senior Java Developer, 6.5 yrs, Noida, 60d notice, strong match.
  - Arjun Rawat (`CND-91047_Arjun_Rawat.docx`): KYC Analyst, 3.0 yrs, Mumbai, 30d notice.
  - Pooja Nair (`CND-91088_Pooja_Nair.pdf`): Java Developer, 4.0 yrs, 90d notice (must-have notice period gap).
  - Exact duplicate CV (`CND-91022_Ritika_Bansal_copy.pdf`).
  - Two-column layout PDF (`CND-91101_Amit_Patel.pdf`).
  - Table-layout DOCX (`CND-91102_Kavita_Deshmukh.docx`).
  - Image-only scanned PDF (`CND-91103_Scanned_Resume.pdf`, 0 extractable text, triggers scan detection).
  - No-email CV (`CND-91104_Vijay_Sharma.pdf`).
  - Prompt injection CV (`CND-91105_Security_Test.pdf`).
  - Unusual date formats (`CND-91106_Deepak_Gupta.docx`).
  - 20 additional realistic synthetic CVs.
- Built database seeder in `scripts/seed.py`:
  - Seeds 2 recruiters (`recruiter@example.com`, `recruiter2@example.com`), 2 clients (Apex Financial Technologies, Zenith Retail Solutions), and 2 client users (`client1@example.com`, `client2@example.com`).
  - Seeds 2 active requisitions with versioned scorecards and evaluates all 30 CVs.
- Built comprehensive HTTP smoke test in `scripts/smoke_test.py`:
  - Exercises complete 16-step recruiter intake, upload, ranking, viewing, submission, client portal review, contact unmasking, mandatory rejection reason, and cross-client isolation.
  - 16 / 16 steps PASSED: verified Ritika Bansal (100.0) ranks above Pooja Nair (41.7) and Pooja displays notice period gap.
- Built `scripts/verify_gemini.py` for testing live Gemini API key with quote verification and temperature 0 determinism.
- Built automated screenshot generator in `scripts/capture_screenshots.py` using Chrome DevTools Protocol (CDP):
  - Captured desktop and mobile (375px) screenshots for all screens under `docs/screenshots/`.
- Frontend smoke test: `frontend/src/test/smoke.test.js` verified via Node test runner.
- Docker availability check: Docker is not installed in the local environment (documented in BUILD_LOG).
- Test count: 25 backend tests passed (`pytest --cov=app` achieves 61% statement coverage).
- Ruff check: clean (0 warnings, 0 errors).
- Frontend oxlint and build: clean (0 warnings, 0 errors).

### Phase 8: Deploy & Docs (Local Part)
- Created `deployment.md`: comprehensive step-by-step instructions for local running on Windows PowerShell, running HTTP smoke tests, verifying Gemini API keys via `scripts/verify_gemini.py`, cloud deployment steps for Render + Neon PostgreSQL, demo logins, and cold start notes.
- Created `TDD.md`: Technical Design Document covering system architecture, 17-entity data model, main recruiter and client flows, AI pipeline with prompt injection defense, honest evaluation of fairness and contact masking limits, Google Gemini free tier terms disclosure (training data policy necessitates paid tier in production; synthetic data used now), UI decisions, trade-offs, and logged assumptions.
- Updated `ASSUMPTIONS.md`: documented assumptions A1 through A7 detailing database engine, verification criteria, contact reveal rules, heuristic quote extraction, PDF generation methods, and rate limits.
- Updated `README.md`: complete root README with architecture overview, tech stack, one-command run, test commands, demo credentials, and phase completion tracker.
- Verification status: Local backend and frontend verification clean. Live cloud deployment and real Gemini API execution are marked as NOT verified due to external credential requirements.

## Fix Pass & Comprehensive Audit
- **Fixed MissingGreenlet Bug**: `services/portal.py` lazy-loaded `cr.criterion` during candidate submission listing. Resolved by configuring `selectinload(Score.criterion_results).selectinload(CriterionResult.criterion)` and setting `lazy="joined"` on `CriterionResult.criterion` in `entities.py`.
- **Eager Loading Audit Across Codebase**: Audited all services (`applications.py`, `submissions.py`, `portal.py`). Added eager loading on `Score.criterion_results` and `CriterionResult.criterion`.
- **Test Session Isolation**: Modified `conftest.py` `test_client` fixture to create a fresh `AsyncSession` per HTTP request, matching production behaviour and ensuring un-eager loaded relationship queries trigger `MissingGreenlet` in tests.
- **Cross-Client Access Protection**: Updated `_check_client_access` in `portal.py` to return HTTP 404 Not Found (instead of 403) when accessing other clients' submissions or applications, eliminating information leakage.
- **Unknown API & Well-Known Fallback**: Updated `main.py` SPA handler to return JSON 404 for unknown `/api/*` and `/.well-known/*` paths instead of falling back to HTML.
- **Zod Dependency Security Fix**: Upgraded and pinned `zod@4.6.7` and `@hookform/resolvers@5.0.1` in `frontend/package.json`. Clean npm audit (0 vulnerabilities), clean oxlint, and clean TypeScript production build.
- **Added Audit Tests**:
  - `test_masking_personal_data`: name, email, phone, pronouns, DOB, marital status, relation name.
  - `test_score_math_formula_and_weights`: weighted sum formula, met/partial/not_found weights, must-have gap flagging.
  - `test_parser_empty_file`: 0-byte file handling.
  - `test_parser_garbled_file`: corrupted binary data handling.
  - `test_parser_scanned_pdf`: image-only scan detection.
  - `test_experience_overlapping_and_unusual_dates`: merging overlapping spans and parsing unusual date formats.
  - `test_route_sweep_get_endpoints_no_500`: exercises every GET endpoint across recruiter and client roles with zero 500 errors.
- **Enhanced End-to-End HTTP Smoke Test**: Extended `scripts/smoke_test.py` to 19 steps including unsupported `.exe` upload rejection (422), eager loaded portal listing (200), reject without reason blocked (422), and multi-tenant 404 isolation.
- **Screenshots & Automated 375px Overflow Assertion**: Generated screenshots for all 8 screens at desktop (1280px) and mobile (375px) in `docs/screenshots/` with automated JavaScript `scrollWidth <= clientWidth` assertions passing across all screens.

## Final Hardening and Production Handoff Pass
- **google-genai Update & Pinning**: Investigated latest releases on PyPI. Pinned `google-genai==1.75.0` (newest stable 1.x release, May 2026, > 14 days old). Documented 2.x dependency requirement (`pydantic>=2.12.5`) blocked by host Windows AppLocker policy. Verified structured output `types.GenerateContentConfig(temperature=0.0, response_mime_type="application/json")`.
- **DATABASE_URL Normalizer**: Created `backend/app/db/url.py` (`normalize_database_url`) supporting Neon and Render URLs, converting `sslmode=require` to `ssl=require`, removing unsupported `channel_binding` asyncpg parameter, and anchoring SQLite relative paths to repo root. Tested in `backend/tests/test_database_url.py` (4 tests passed).
- **Upload Validation & Batch Resilience**: Magic bytes `MZ` in `.pdf` rejected, invalid `.docx` (non-zip) rejected, file > 5MB rejected, batch > 500 files rejected with `ValidationError`. Individual rejected files do not crash the batch. Tested in `backend/tests/test_upload_validation.py` (3 tests passed).
- **Strict Lazy Loading Enforcement**: Enforced `lazy="raise_on_sql"` across all relationships in `backend/app/db/models/entities.py`.
- **Full Route Sweep**: Built comprehensive test in `backend/tests/test_route_sweep_complete.py` exercising every GET, POST, PUT, PATCH, and DELETE endpoint across recruiter, client1, and client2. 0 5xx responses.
- **Extended End-to-End Smoke Test**: Expanded `scripts/smoke_test.py` to 25 automated steps with `--base-url` support, covering rescore, stage changes, scorecard version 2, consent record & revoke, duplicate resolution, and candidate deletion with hash-only audit entry. All 25/25 steps passed.
- **Production Readiness**: Added production validator in `backend/app/core/config.py` enforcing minimum 32-character non-default `JWT_SECRET`, secure cookies, same-origin CORS default; auto-migrations and idempotent demo seeding in `main.py` lifespan; global unhandled exception handler suppressing stack traces in production.
- **Containerization & Deployment**: Updated `Dockerfile` with multi-stage build, `$PORT` support, non-root user `appuser`, and `/api/health` HEALTHCHECK. Created `render.yaml` blueprint with all required secrets and configuration keys.
- **Automated Browser CDP Verification**: Built `scripts/verify_browser_cdp.py` verifying recruiter evidence drawer quote substring match, client shortlist and reject with reason via UI, 0 console errors, 0 dead buttons, and 0 horizontal overflow at 375px.
- **Sample PDF Verification**: Built `scripts/verify_pdfs.py` validating page counts and text extraction across all 17 sample PDFs via `pdfplumber` (17/17 passed).
- **Handoff Deliverables**:
  - `HANDOFF.md`: complete step-by-step setup, GitHub commands, Neon, Render, PowerShell secret generation, troubleshooting table.
  - `TDD.docx`: generated from `TDD.md` via `scripts/make_tdd_docx.py` with `GitHub: <PASTE URL HERE>` placeholder.
  - `handoff/ShortList_handoff.zip`: generated via `scripts/make_handoff_zip.py` with automated secret scan across files and git history (223 files, 1.59 MB, 0 secrets detected).




