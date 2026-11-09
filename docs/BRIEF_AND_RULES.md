# ShortList: BRIEF AND RULES

Project: "ShortList", an AI resume-screening tool and client shortlist portal for a staffing firm. 7-day solo internship assignment, scored on quality of work (50%), problem solving (30%), communication (20%). A client could try the result today. Build a small slice really well, not everything badly.

Technical design lives in ARCHITECTURE.md. If anything here conflicts with it, stop and ask the user.

## Working rules (follow always)

- Work in phases. Before each phase show an implementation plan and wait for approval. After each phase STOP and report: what you built, how to verify it (exact commands/URLs), test results, assumptions made. Wait for the user to say "Proceed".
- Commit after each logical step with clear conventional messages (feat:, test:, fix:, docs:, chore:). Commit history is read by reviewers. Never squash.
- Use only information from this brief. Every assumption goes in ASSUMPTIONS.md (id, text, why). Never invent client facts.
- No secrets in the repo. Env var names only in .env.example. No real personal data: all CVs and people are synthetic, emails use example.com.
- No dead buttons. Every screen has loading, empty and error states.
- Clean code: small modules, type hints, docstrings on non-obvious logic, no giant files.

## Product

Client: staffing firm, Noida. 120 staff, 70 recruiters. Contract and permanent hiring for IT services, banking back-office and retail.

Today: recruiters read every CV by hand, email Excel shortlists, track status in personal sheets.

Ask: upload a pile of CVs against a job, see best first with reasons. Clients review shortlists in a portal, not by phone. The firm must be able to show clients candidates are treated fairly.

Users: recruiter, client hiring manager (mostly on phone). Delivery head is out of scope except a stretch report.

## Core slice (must work end to end)

1. JD intake -> editable scorecard
2. Bulk CV upload (PDF/DOCX, up to 500) -> parsed profiles with duplicate detection
3. AI score per CV with verified evidence per criterion, ranked list
4. Client portal: masked contacts, shortlist / reject with required reason / propose interview slot
5. Pipeline per requisition: sourced, screened, submitted, client_shortlisted, interview, offered, joined, rejected

Also: candidate consent record and deletion on request; log of who viewed what.

Out of scope: job board integrations or scraping, video interviews, background verification, OCR, payments.

## Fairness and privacy rules

- Never reject automatically. Low scorers stay visible and searchable.
- A recruiter must open a CV (logged) before submitting it. Enforce server-side.
- Each client sees only candidates submitted to them. Contacts masked for clients (assumption: revealed after the client shortlists).
- Consent recorded at upload (source, date). Deletion on request removes personal data, leaves a hash-only audit entry.
- Free Gemini tier content may be used by Google to improve products: state in the TDD that production needs the paid tier; use only synthetic data now.

## Sample data (scripts/generate_samples.py, committed; seed.py loads it)

About 30 synthetic CVs in PDF and DOCX with varied layouts. Include these brief candidates:

- Ritika Bansal (CND-91022): Senior Java Developer, 6.5 yrs, Java / Spring Boot / microservices, notice 60 days
- Arjun Rawat (CND-91047): KYC Analyst, 3.0 yrs, KYC / AML checks / Excel, notice 30 days
- Pooja Nair (CND-91088): Java Developer, 4.0 yrs, Java / Hibernate / REST APIs, notice 90 days

JDs:

- Senior Java Developer: 5-8 years, Spring Boot, Noida, notice up to 60 days
- KYC Analyst for banking back-office

Also include: a duplicate under a different filename, a two-column PDF, a table-layout DOCX, an image-only scanned PDF, a CV with no email, one with a prompt-injection line, one with unusual date formats.

Seed two recruiters, two client users belonging to different clients, requisitions at different stages, demo logins documented.

## Tests (pytest, FakeClient so no network)

- parser (pdf, docx, empty, garbled, scan)
- experience-years calculation (overlaps, unusual dates)
- notice normalisation
- masking
- evidence verifier including a hallucinated quote
- score math
- dedup
- role access (client cannot see another client's candidates or recruiter routes)
- submit-requires-view
- cache determinism
- job retry and restart recovery
- injection CV
- a minimal frontend smoke test

## Phases

- **Phase 0: Setup.** Create workspace rules from the working rules, repo structure from ARCHITECTURE.md 1.2 and 1.3, docs/ARCHITECTURE.md and docs/BRIEF_AND_RULES.md copied into the repo (source material for the TDD), README skeleton, .gitignore, .env.example, ASSUMPTIONS.md, lint config, Dockerfile skeleton.
- **Phase 1: Backend foundation.** Models, Alembic migrations, auth, roles, resource scoping helper, seed loader, health check, tests for auth and access control.
- **Phase 2: JD intake and scorecard.** LLMClient + Gemini + Fake + heuristic. JD extraction, scorecard CRUD with versioning, editor UI, login and app shell.
- **Phase 3: Upload and parsing.** Job queue and worker, bulk upload, parsing, profile extraction, experience calculation, dedup, progress UI, per-file errors, tests.
- **Phase 4: Scoring.** Masking, deterministic criteria, LLM criteria, quote verification, scoring, confidence, caching, failure handling, injection defence, tests.
- **Phase 5: Recruiter UI.** Ranked list, evidence drawer, candidate view, ViewLog, view-before-submit rule, submission flow.
- **Phase 6: Client portal and pipeline.** Client views, masked contacts, shortlist / reject-with-reason / slot proposal, pipeline events and board, consent record and deletion.
- **Phase 7: Quality pass.** Loading/empty/error states, responsive check, accessibility basics, design consistency, edge cases, full test run, coverage report.
- **Phase 8: Deploy and docs.** Deploy to Render + Neon, deployment.md (local run step by step, deployment steps, env var names only, demo logins), TDD.md draft (GitHub URL at top, architecture and why, data model, main flows, AI pipeline, UI decisions, what was cut and next, labelled assumptions), final README.

END OF BRIEF AND RULES
