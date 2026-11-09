# ShortList — Deployment & Reviewer Guide

Live: {{LIVE_URL}}

ShortList is an AI resume screening tool and multi-tenant client portal built for staffing firms. It scores resumes against job description criteria using a defensive "AI judges, code scores" architecture, provides recruiter evaluation workflows, and delivers isolated, masked candidate reviews for hiring managers.

---

## 1. Prerequisites & Environment

Verify your local environment has the required runtimes installed:

| Tool | Required Version | Tested Version | Verification Command |
|---|---|---|---|
| **Python** | 3.11.x | 3.11.9 | `python --version` |
| **Node.js** | >= 20.x | v24.16.0 | `node --version` |
| **npm** | >= 10.x | 11.13.0 | `npm --version` |
| **Git** | >= 2.x | 2.44.0+ | `git --version` |

---

## 2. Local Setup & Execution

### Option A: Windows PowerShell

```powershell
# 1. Clone repository
git clone https://github.com/Yuvaraj18-4/AI_Screening.git ShortList
cd ShortList

# 2. Setup Python 3.11 virtual environment
py -3.11 -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt

# 3. Configure environment file (.env)
Copy-Item .env.example .env
# Edit .env: JWT_SECRET and DATABASE_URL defaults work immediately out-of-the-box.
# Leave GEMINI_API_KEY empty to run in deterministic offline heuristic mode.

# 4. Install frontend dependencies & compile production bundle
cd frontend
npm ci
npm run build
cd ..

# 5. Initialize database & seed demo accounts
backend\.venv\Scripts\python scripts\seed.py

# 6. Start the unified service (serves API and compiled React SPA)
backend\.venv\Scripts\uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

### Option B: macOS & Linux Bash

```bash
# 1. Clone repository
git clone https://github.com/Yuvaraj18-4/AI_Screening.git ShortList
cd ShortList

# 2. Setup Python 3.11 virtual environment
python3.11 -m venv backend/.venv
source backend/.venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

# 3. Configure environment file (.env)
cp .env.example .env
# Default SQLite configuration works out-of-the-box.

# 4. Install frontend dependencies & compile production bundle
cd frontend
npm ci
npm run build
cd ..

# 5. Initialize database & seed demo accounts
python scripts/seed.py

# 6. Start the unified service
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open your browser to: **`http://localhost:8000`**

### Scoring Mode & Gemini Configuration
- **Heuristic Mode (Default)**: If `GEMINI_API_KEY` is not set or empty, ShortList operates in deterministic offline heuristic mode. The app displays an informational blue banner in the UI: `Scoring mode: heuristic`. All features (intake, ranked candidate lists, quote verification, evidence drawers, client decisions) function normally without network access.
- **Live Gemini Mode**: To enable live AI evaluation via Google Gemini 2.5 Flash, open `.env` and set:
  ```ini
  GEMINI_API_KEY=your_gemini_api_key_here
  GEMINI_MODEL=gemini-2.5-flash
  ```
  Restart the service. The health check (`/api/health`) reports `"scoring_mode": "llm"`.

---

## 3. Demo Accounts & Role Permissions

The seed script (`scripts/seed.py`) configures 5 demo accounts:

| Email | Password | Role | Organization | Permissions & Scoping |
|---|---|---|---|---|
| `recruiter@example.com` | `recruiter123` | Recruiter | Staffing Agency | Full access: all requisitions, scorecards, batch uploads, candidate rankings, evidence drawers, and submissions. |
| `recruiter2@example.com` | `recruiter123` | Recruiter | Staffing Agency | Teammate account: demonstrates multi-recruiter concurrent pipeline access. |
| `client1@example.com` | `client123` | Client | Apex Financial Technologies | Client portal: view candidates submitted for Apex requisitions only. Contact info masked until shortlisted. |
| `client2@example.com` | `client123` | Client | Zenith Retail Solutions | Client portal: view Zenith submissions only. Attempting to view Apex candidates returns HTTP 404 (anti-enumeration). |
| `client3@example.com` | `client123` | Client | CloudScale Systems | Client portal: view CloudScale submissions only (Full Stack Python/React Engineer). |

---

## 4. Testing & Verification Commands

All test and verification commands can be executed from the repository root:

### 1. Backend Test Suite (Pytest)
```powershell
backend\.venv\Scripts\pytest -v
```
*Expected Output*: `40 passed in <10s`.

### 2. Backend Code Linting (Ruff)
```powershell
backend\.venv\Scripts\ruff check backend/
```
*Expected Output*: `All checks passed!`

### 3. Frontend Typecheck, Lint & Security Audit
```powershell
cd frontend
npx tsc --noEmit
npx oxlint
npm audit
cd ..
```
*Expected Output*: 0 errors, 0 warnings, `found 0 vulnerabilities`.

### 4. End-to-End HTTP Smoke Test (25 Steps)
Runs against an in-process ASGI test instance with a fresh SQLite database:
```powershell
backend\.venv\Scripts\python scripts\smoke_test.py
```
*Expected Output*:
```
[PASS] Step 1: Recruiter authentication - HTTP 200
...
[PASS] Step 25: Candidate Erasure & Hash-Only Audit Log - HTTP 200
ALL 25 SMOKE TEST STEPS PASSED SUCCESSFULLY!
```

To run against a deployed live server:
```powershell
backend\.venv\Scripts\python scripts\smoke_test.py --base-url https://your-app.onrender.com
```

### 5. Automated Browser Verification (CDP Headless Chrome)
Verifies quote substring match in evidence drawer, asserts 0 dead buttons, and confirms 0 horizontal overflow at 375px mobile viewport:
```powershell
backend\.venv\Scripts\python scripts\verify_browser_cdp.py
```
*Expected Output*: `AUTOMATED BROWSER CDP VERIFICATION PASSED SUCCESSFULLY (0 ERRORS)`.

### 6. Live Gemini API Verification (Requires API Key)
When you have configured `GEMINI_API_KEY` in `.env`:
```powershell
backend\.venv\Scripts\python scripts\verify_gemini.py
```
*Expected Output*: Evaluates sample CVs against the Java Developer scorecard, validates verbatim quotes, confirms cache determinism, and logs token usage.

---

## 5. Environment Variables Reference

Environment variables are loaded from `.env` via Pydantic Settings. Empty string entries automatically fall back to secure default values.

| Variable Name | Purpose | Required? | Safe Default / Example Value |
|---|---|---|---|
| `ENV` | Environment mode (`development` or `production`) | Optional | `development` |
| `DATABASE_URL` | SQLAlchemy async connection URI | Optional | `sqlite+aiosqlite:///./shortlist.db` |
| `JWT_SECRET` | Secret key used to sign HS256 auth tokens | Required in prod (min 32 chars) | `dev-insecure-secret-key-change-in-production-min32bytes` |
| `GEMINI_API_KEY` | Google Gemini API key | Optional (offline heuristic fallback) | `AIzaSy...` (do not commit real key) |
| `GEMINI_MODEL` | Gemini model name | Optional | `gemini-2.5-flash` |
| `CORS_ORIGINS` | Allowed origins (comma-separated) | Optional (defaults to same-origin in prod) | `http://localhost:5173,http://localhost:8000` |
| `COOKIE_SECURE` | Enforces HTTPS-only cookies | Optional (auto-enabled in prod) | `false` |
| `MAX_UPLOAD_MB` | Maximum single CV file size | Optional | `5` |
| `WORKER_CONCURRENCY` | Number of background processing workers | Optional | `3` |
| `SEED_DEMO_DATA` | Automatically seed demo accounts on startup | Optional | `false` |

---

## 6. Production Deployment (Render + Neon)

ShortList includes a pre-configured `render.yaml` blueprint and a multi-stage `Dockerfile`.

### Step 1: Provision Serverless PostgreSQL on Neon
1. Create a free PostgreSQL project at [neon.tech](https://neon.tech).
2. Copy the database connection URI:
   ```
   postgresql://[user]:[password]@[endpoint].neon.tech/neondb?sslmode=require
   ```
3. ShortList's built-in normalizer (`backend/app/db/url.py`) automatically translates this connection string to `postgresql+asyncpg` with `ssl=require`.

### Step 2: Deploy on Render
1. Push your repository to GitHub.
2. In Render, select **New > Blueprint** and link your repository (or create a **Web Service** using Docker runtime).
3. Set the environment variables in the Render dashboard:
   - `ENV`: `production`
   - `DATABASE_URL`: Your Neon connection URI.
   - `JWT_SECRET`: Generate a secure 32+ character secret using PowerShell:
     ```powershell
     -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 48 | ForEach-Object {[char]$_})
     ```
   - `GEMINI_API_KEY`: Your Google Gemini API key.
   - `SEED_DEMO_DATA`: `true` (seeds demo accounts on initial startup if database is empty).
4. Render builds the multi-stage Docker container:
   - Stage 1: Compiles React frontend via Node 20.
   - Stage 2: Installs Python 3.11 dependencies into non-root user image.
   - Stage 3: Starts Uvicorn honoring Render's dynamic `$PORT` environment variable.
5. On service startup, Alembic migrations run automatically.

*Note on Free Tier*: Render free web services spin down after 15 minutes of inactivity. The initial cold start may take 45–60 seconds.

---

## 7. Troubleshooting Guide

| Issue / Symptom | Root Cause | Solution |
|---|---|---|
| `ArgumentError: Could not parse SQLAlchemy URL ... sslmode=require` | `asyncpg` driver expects `ssl=require`, not `sslmode=require`. | Use `backend/app/db/url.py` `normalize_database_url()`. The app handles this automatically. |
| `ValueError: Production security error: JWT_SECRET must be set ...` | `ENV=production` is set, but `JWT_SECRET` is missing, shorter than 32 characters, or contains default dev strings. | Generate a secure random string of at least 32 characters and set `JWT_SECRET` in environment. |
| `OSError: [WinError 10048] address already in use` | Another process is already running on port 8000. | Run on another port: `--port 8001`, or kill the occupying process via `Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process`. |
| Cookies not persisting over HTTP | `COOKIE_SECURE=true` was specified in a non-HTTPS local environment. | Keep `COOKIE_SECURE=false` for local HTTP testing. Set to true only in HTTPS production environments. |
| Blue "Scoring mode: heuristic" banner visible | `GEMINI_API_KEY` is empty or unset in `.env`. | Provide a valid Google Gemini API key in `.env` and restart the service to activate live AI scoring. |
| `MissingGreenlet` in SQLAlchemy async operations | Relationship accessed in async context without eager loading. | All relationships enforce `lazy="raise_on_sql"`. Use `.options(selectinload(...))` or `lazy="joined"` on relational queries. |
