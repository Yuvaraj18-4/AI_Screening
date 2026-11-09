# ShortList

GitHub: https://github.com/Yuvaraj18-4/AI_Screening  
Live: {{LIVE_URL}}

> **AI resume-screening tool and client shortlist portal for staffing firms.**  
> Upload CVs against a job, see best candidates first with verified evidence citations. Clients review shortlists in a mobile-first portal with privacy-preserving contact masking.

---

## Highlights

- **Evidence Drawer & Quote Verification:** Every criterion score is backed by an exact substring citation from the candidate's masked resume text, checked deterministically to eliminate hallucinations.
- **Hybrid Scoring Engine:** Deterministic criteria (years of experience, notice period, location) are evaluated purely by code; semantic domain criteria are evaluated via LLM. Weighted scores are computed with mandatory must-have gap detection.
- **Prompt Injection Defense:** Resumes are wrapped in boundary XML tags and isolated from scoring instructions; raw text is strictly parsed with zero direct code execution.
- **Privacy-First Contact Masking:** Candidate contact information (email, phone, address) is completely masked from client reviewers until they record a shortlist or interview decision.
- **View-Before-Submit Enforcement:** Server strictly rejects candidate submission to clients unless a recruiter has actively reviewed the candidate in the evidence drawer (`ViewLog` audited).
- **Audit-Compliant GDPR/DPDP Deletion:** Removing candidates replaces PII with hash-only audit records, preserving application metrics without retaining identifiable data.

---

## Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, SQLite (dev) / PostgreSQL (Neon / prod)
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query, Lucide React
- **AI & Scoring:** Google Gemini API (`gemini-2.5-flash`, `google-genai 1.75.0`) with structured JSON schema output; automatic fallback to internal verifiable Heuristic scoring when API key is missing
- **Parsing:** `pdfplumber`, `python-docx`, custom date interval merger, notice period normalizer, exact SHA-256 + fuzzy deduplication

---

## Quick Start (Local Run)

### 1. Prerequisites
- Python 3.11 (`py -3.11`)
- Node.js 20+ (tested on Node v24.16.0, npm 11.13.0)
- Git

### 2. Setup Backend & Seed Data
```powershell
# Navigate to repo
cd C:\dev\AI_screening

# Activate Python 3.11 venv
.\backend\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r backend\requirements.txt

# Seed database with sample recruiters, clients, requisitions, and synthetic CVs
python scripts\seed.py
```

### 3. Build Frontend & Start Server
FastAPI serves the built React SPA directly alongside the API.
```powershell
# Direct uvicorn command
.\backend\.venv\Scripts\uvicorn.exe app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

---

## Demo Credentials

| Role | Email | Password | Organization | Access Scope |
| :--- | :--- | :--- | :--- | :--- |
| **Lead Recruiter** | `recruiter@example.com` | `recruiter123` | Internal Staffing | Full recruiter access, upload, scoring, submission, pipeline |
| **Associate Recruiter**| `recruiter2@example.com` | `recruiter123` | Internal Staffing | Recruiter access across all open requisitions |
| **Client Reviewer 1** | `client1@example.com` | `client123` | Apex Financial Technologies | Client portal for Apex requisitions only (Senior Java Developer, Lead DevOps) |
| **Client Reviewer 2** | `client2@example.com` | `client123` | Zenith Retail Solutions | Client portal for Zenith requisitions only (KYC Analyst) |
| **Client Reviewer 3** | `client3@example.com` | `client123` | CloudScale Systems | Client portal for CloudScale requisitions only (Full Stack Python/React) |

---

## Running Tests & Verification

### 1. Backend Unit & Integration Tests (pytest)
```powershell
.\backend\.venv\Scripts\pytest.exe backend\tests -v
```
*Current test suite: 40 passed in <10s.*

### 2. Code Quality & Linting
```powershell
# Backend ruff check
.\backend\.venv\Scripts\ruff.exe check backend

# Frontend lint & typecheck
cd frontend
npm run lint
npm run build
cd ..
```

### 3. End-to-End HTTP Smoke Test
Starts an in-process test server and validates complete end-to-end recruiter intake, bulk upload, ranking, viewing, submission, client portal review, contact unmasking, and cross-client isolation:
```powershell
.\backend\.venv\Scripts\python.exe scripts\smoke_test.py
```
*All 25 automated steps pass successfully.*

### 4. Automated Browser Verification (CDP Headless Chrome)
```powershell
.\backend\.venv\Scripts\python.exe scripts\verify_browser_cdp.py
```
*0 dead buttons, 0 horizontal overflow at 375px mobile viewport, verified evidence quotes.*

### 5. Live Gemini API Verification
When a real `GEMINI_API_KEY` is provided, run the verification harness:
```powershell
.\backend\.venv\Scripts\python.exe scripts\verify_gemini.py
```

---

## Visual Walkthrough & Screenshots

Automated headless Chrome DevTools Protocol (CDP) screenshots captured across desktop and 375px mobile viewport are located in `docs/screenshots/`:
- `01_login_desktop.png` & `02_login_mobile_375.png`: Authentication view
- `03_requisition_list_desktop.png` & `04_requisition_list_mobile_375.png`: Recruiter intake list with heuristic banner
- `05_scorecard_desktop.png`: Configurable scorecard with must-have weights
- `06_ranked_list_desktop.png` & `07_ranked_list_mobile_375.png`: Candidate ranking with score rings and gap indicators
- `08_evidence_drawer_desktop.png`: Side-drawer with verifiable citation text and code evaluation
- `09_client_portal_desktop.png` & `10_client_portal_mobile_375.png`: Client evaluation portal with sticky action bar

---

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Technical architecture, API contracts, schema, and security specifications.
- [docs/BRIEF_AND_RULES.md](docs/BRIEF_AND_RULES.md) — Product brief, phased delivery requirements, and operating rules.
- [TDD.md](TDD.md) — Complete Technical Design Document covering system design, AI pipeline, prompt injection defense, and fairness limits.
- [deployment.md](deployment.md) — Step-by-step local running instructions and production deployment guide for Render and Neon PostgreSQL.
- [BUILD_LOG.md](BUILD_LOG.md) — Comprehensive build history across all 8 phases.
- [ASSUMPTIONS.md](ASSUMPTIONS.md) — Explicit record of engineering decisions and assumptions.
