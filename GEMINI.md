# ShortList — Workspace Rules

These rules apply to all work in this repository. Derived from the project's Working Rules (docs/BRIEF_AND_RULES.md).

## Phased Development

- Work in phases. Before each phase, show an implementation plan and wait for approval.
- After each phase, STOP and report: what was built, how to verify it (exact commands/URLs), test results, assumptions made. Wait for "Proceed".

## Commit Discipline

- Commit after each logical step with clear conventional messages: `feat:`, `test:`, `fix:`, `docs:`, `chore:`.
- Commit history is read by reviewers. Never squash.

## Source of Truth

- Use only information from ARCHITECTURE.md and BRIEF_AND_RULES.md.
- Every assumption goes in ASSUMPTIONS.md (id, text, why). Never invent client facts.

## Security and Privacy

- No secrets in the repo. Env var names only in `.env.example`.
- No real personal data: all CVs and people are synthetic, emails use `example.com`.
- Logs never contain personal data (log ids only).

## Code Quality

- No dead buttons. Every screen has loading, empty, and error states.
- Clean code: small modules, type hints, docstrings on non-obvious logic, no giant files.
- Routers never touch the DB directly. Services never import FastAPI.
- `ai/` and `parsing/` are pure and unit-testable with no network.

## Architecture Boundaries

- Technical design lives in `docs/ARCHITECTURE.md` (source of truth).
- If anything conflicts with ARCHITECTURE.md, stop and ask the user.

