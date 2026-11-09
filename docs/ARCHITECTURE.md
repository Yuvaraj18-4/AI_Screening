# ShortList: ARCHITECTURE (technical source of truth)

If anything in BRIEF_AND_RULES.md conflicts with this file, stop and ask the user.

## 1.1 System overview

One deployable service. FastAPI serves the JSON API under /api and the built React app (static files) for every other path.

```
  Browser (React SPA, mobile-first for clients)
        |  HTTPS, JSON, httpOnly cookie
        v
  FastAPI app (single container)
   |-- routers (HTTP only: parse input, call service, shape output)
   |-- services (business rules, permissions, orchestration)
   |-- repositories / SQLAlchemy models (DB access)
   |-- ai/ (LLMClient, prompts, masking, verifier, scorer)
   |-- parsing/ (pdf, docx, profile extraction, dedup)
   |-- jobs/ (DB-backed queue + asyncio worker started at app startup)
        |                       |
        v                       v
   Database (SQLite local /     LLM provider (Gemini via LLMClient;
   Postgres prod)               FakeClient in tests; heuristic fallback)
```

Rules: routers never touch the DB directly. Services never import FastAPI. ai/ and parsing/ are pure and unit-testable with no network.

## 1.2 Backend design

Stack: Python 3.11, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, pdfplumber, python-docx, rapidfuzz (optional), argon2-cffi, PyJWT, pytest.

Folder structure:

```
backend/app/
  main.py            app factory, static mount, worker startup
  core/              config.py (env), security.py (hash, JWT), deps.py (current_user, require_role), logging.py, errors.py
  db/                base.py, session.py, models/*.py, migrations/ (Alembic)
  schemas/           Pydantic request/response models
  routers/           auth.py, requisitions.py, scorecards.py, uploads.py, candidates.py, applications.py, submissions.py, client_portal.py, consent.py, health.py
  services/          one module per router
  ai/                llm_base.py (LLMClient protocol), gemini_client.py, fake_client.py, heuristic_client.py, prompts.py (versioned), masking.py, verifier.py, scoring.py
  parsing/           extract_text.py, profile.py, experience.py, notice.py, dedup.py
  jobs/              queue.py, worker.py, handlers.py
backend/tests/
scripts/generate_samples.py, scripts/seed.py
frontend/            (see 1.3)
docs/ARCHITECTURE.md
```

### Data model (all tables have id, created_at)

- User(email unique, password_hash, name, role[recruiter|client], client_id nullable)
- Client(name)
- Requisition(client_id, title, jd_text, status, owner_id)
- Scorecard(requisition_id, version int, is_active)
- Criterion(scorecard_id, name, kind[experience|notice|location|skill|domain], must_have bool, weight int, params JSON, description)
  - params examples: {"min":5,"max":8} | {"max_days":60} | {"city":"Noida"} | {"skill":"Spring Boot"}
- Candidate(name, email, phone, location, current_role, skills JSON, employment JSON (list of {title, company, start, end}), experience_years, notice_days, current_ctc, expected_ctc, education JSON, parse_quality float, status[active|deleted], duplicate_of_id nullable)
- CVFile(candidate_id, filename, mime, size, sha256, content BLOB, text, masked_text, parse_status[ok|needs_review|failed], parse_error, batch_id)
- Consent(candidate_id, source, given_at, recorded_by, revoked_at nullable)
- Application(candidate_id, requisition_id, stage[sourced|screened|submitted|client_shortlisted|interview|offered|joined|rejected], unique(candidate_id, requisition_id))
- Score(application_id, scorecard_version, total float, confidence[high|medium|low], status[scored|ai_failed|pending], cache_key unique, model, prompt_version, scoring_mode[llm|heuristic])
- CriterionResult(score_id, criterion_id, verdict[met|partial|not_found|unclear|unverified], value float, quote text nullable, quote_verified bool, confidence float, source[code|llm])
- Submission(application_id, submitted_by, submitted_at, client_decision[pending|shortlisted|rejected], reject_reason, decided_by, decided_at, proposed_slot datetime nullable)
- PipelineEvent(application_id, from_stage, to_stage, actor_id, note)
- ViewLog(user_id, candidate_id, application_id nullable, context)
- UploadBatch(requisition_id, created_by, total)
- Job(type[parse_cv|score_cv|extract_jd], payload JSON, status[queued|running|done|failed], attempts, max_attempts, next_run_at, last_error, started_at, finished_at, batch_id)
- AuditLog(actor_id, action, entity_type, entity_hash, meta JSON)  (never stores personal data, only hashes)

Indexes: Application(requisition_id, stage), Score(application_id), ViewLog(candidate_id), Job(status, next_run_at), Candidate(email), Candidate(phone).

### API (all under /api, JSON, cookie auth). R = recruiter, C = client.

```
POST /auth/login, POST /auth/logout, GET /auth/me
R  GET/POST /requisitions, GET/PATCH /requisitions/{id}
R  POST /requisitions/{id}/jd/extract            (AI drafts scorecard from jd_text)
R  GET/PUT /requisitions/{id}/scorecard          (PUT creates a new version)
R  POST /requisitions/{id}/uploads               (multipart, up to 500 files)
R  GET /uploads/{batch_id}/progress
R  GET /requisitions/{id}/applications?sort=score&stage=...
R  GET /applications/{id}                        (detail; writes ViewLog)
R  POST /applications/{id}/rescore, POST /applications/{id}/stage
R  POST /candidates/{id}/duplicate-resolution    (merge | keep)
R  POST /applications/{id}/submit                (409 unless viewed by this recruiter)
R  POST/DELETE /candidates/{id}/consent, DELETE /candidates/{id}   (deletion on request)
C  GET /portal/requisitions, GET /portal/requisitions/{id}/submissions
C  GET /portal/submissions/{id}                  (masked contacts; writes ViewLog)
C  POST /portal/submissions/{id}/decision        (shortlist | reject with required reason | propose_slot)
GET /health
```

Permissions: one dependency require_role(...) per route, plus resource scoping in the service layer through a single helper visible_applications_for(user). Clients only ever see applications that have a Submission to their client. Never filter in the router.

## 1.3 Frontend design

Stack: React 18, Vite, TypeScript, Tailwind, React Router, TanStack Query (server state), react-hook-form + zod (forms), lucide-react icons. No heavy UI kit; build a small set of components.

Folder structure:

```
frontend/src/
  app/         router.tsx, providers.tsx, route guards (RequireRole)
  api/         client.ts (fetch wrapper: credentials, error normalisation, 401 handling), per-domain hooks
  components/  Button, Card, Badge, Table, Drawer, Dialog, Tabs, Skeleton, EmptyState, ErrorState, Toast, ScoreRing, EvidenceItem, StageChip, FileDropzone, ProgressList
  features/    auth, requisitions, scorecard, uploads, candidates, pipeline, portal
  styles/      tokens in tailwind.config (colors, spacing, radius, type scale)
  test/
```

Routes:

- /login
- Recruiter: /requisitions, /requisitions/new, /requisitions/:id (tabs: Scorecard | Upload | Candidates | Pipeline), /requisitions/:id/candidates/:applicationId
- Client: /portal, /portal/requisitions/:id, /portal/submissions/:id
- Guards redirect by role. Unknown routes show a clean 404.

Design system: calm, minimal, designed not default. One accent colour, neutral greys, Inter font, 8px spacing grid, generous white space, consistent radius and elevation. Muted success/warning/danger colours. Never colour alone: every status has icon + label. Score shown as a ring plus number. Keyboard focus visible, labels on inputs, contrast AA.

Layout: recruiter app = left nav + content, desktop-first but usable on tablet. Client portal = mobile-first single column cards, large tap targets, sticky bottom action bar for Shortlist / Reject / Propose slot.

Every data view has loading (skeleton), empty (explains what to do next) and error (retry) states.

Ranked list row: rank, name, score ring, must-have gap badges, confidence chip, parse warning icon, stage chip, primary next action.

Evidence drawer: per criterion show name, must-have badge, verdict icon + label, highlighted quote, verified or "unverified" marker, confidence.

Upload screen: dropzone, per-file row with status (queued, parsing, scored, needs review, duplicate, failed + reason), overall progress, polling every 2s while a batch runs (no websockets).

## 1.4 AI pipeline architecture

Principle: AI judges, code scores.

Per CV, as queued jobs:

**parse_cv**: validate file -> extract text -> regex email/phone -> LLM structured profile (name, title, skills, employment entries with dates, location, notice text, CTC) -> code computes experience_years by merging overlapping date ranges with a tolerant date parser (fallback: explicit "N years" statement; unparseable -> low parse_quality) -> code normalises notice to days -> dedup -> build masked_text -> enqueue score_cv.

**score_cv**: for each criterion:
- kind experience/notice/location: computed by code from the profile. No LLM. source=code.
- kind skill/domain: one LLM call for all semantic criteria at once. Strict JSON schema: per criterion {verdict, quote, confidence}. Temperature 0.
- verifier: normalise whitespace/case, check quote is a substring of masked_text. Fail -> verdict "unverified", value 0, quote_verified=false.
- total = sum(weight * value) / sum(weight) * 100, value: met=1, partial=0.5, else 0.
- confidence: low if parse_quality low, or any unverified quote, or >= 30% criteria unclear; medium for one flag; else high.
- must-have not met -> gap badge. Never auto-reject.

cache_key = sha256(masked_text + scorecard_version + prompt_version + model). Same key returns stored result, no LLM call.

Failures: retry with exponential backoff (e.g. 5s, 20s, 80s), max 3 attempts, then Score.status=ai_failed shown as "AI failed, retry". Never a silent zero.

No GEMINI_API_KEY: heuristic keyword scorer, scoring_mode=heuristic, UI shows a "heuristic mode" banner.

**Masking** (backend, before any LLM call): remove or replace name tokens (from the parsed name), email, phone, titles (Mr/Mrs/Ms), gendered pronouns (-> they), date of birth and "age" lines, marital status, father's/spouse name lines. Photos are never extracted. Masked text keeps skills, employment, dates, notice, location. Document that regex masking is imperfect; do not claim bias-free.

**Prompt-injection defence**: CV text goes inside clear delimiters labelled as untrusted data; system prompt says ignore any instructions inside it; output validated against the schema; unknown fields dropped; scores never taken from model output.

**LLMClient protocol**: extract_jd(text) -> scorecard draft, extract_profile(text) -> profile, judge(masked_text, criteria) -> results. Implementations: GeminiClient (GEMINI_API_KEY, GEMINI_MODEL from env, never hardcode model name; capped concurrency; handles 429), FakeClient (deterministic, for tests), HeuristicClient (keywords).

## 1.5 Job queue architecture

DB table Job. Worker started at app startup, N concurrent tasks (env WORKER_CONCURRENCY, default 3). Claim a job with an atomic UPDATE ... WHERE status='queued' AND next_run_at <= now. On startup, reset jobs left "running" beyond a timeout back to queued (restart-safe). Handler exceptions are caught per job: record last_error, schedule retry or mark failed. One bad file never stops the batch. Progress endpoint aggregates jobs by batch.

## 1.6 Auth and security architecture

- argon2 password hashing.
- JWT in httpOnly, SameSite=Lax, Secure (in prod) cookie.
- Mutating requests require an X-Requested-With header (CSRF defence).
- Login rate limiting.
- Role dependency on every route plus service-level resource scoping.
- File validation: extension + magic bytes + 5 MB per file, max 500 per batch.
- Pydantic validation on all input.
- CORS restricted via CORS_ORIGINS.
- Errors return safe messages, never stack traces.
- Logs never contain personal data (log ids only).
- Dependencies pinned. Secrets only in env.

## 1.7 Deployment architecture

Multi-stage Dockerfile: Node builds the frontend, Python image serves API + static files. Render web service + Neon Postgres. Alembic migrations run on startup.

Env var names: DATABASE_URL, JWT_SECRET, GEMINI_API_KEY, GEMINI_MODEL, ENV, CORS_ORIGINS, COOKIE_SECURE, MAX_UPLOAD_MB, WORKER_CONCURRENCY.

Free tier may sleep: note first-load delay in deployment.md. A seed command loads demo data.

END OF ARCHITECTURE
