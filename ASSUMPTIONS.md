# Assumptions

| ID | Assumption | Why |
|----|-----------|-----|
| A1 | Contacts revealed to client only after client shortlists | Brief §Fairness: "assumption: revealed after the client shortlists". Masking stays active in client portal until client makes shortlist decision. |
| A2 | CV files stored as BLOBs in database, not object storage | Architecture §1.2: CVFile has `content BLOB`. Keeps deployment single-container and self-contained at internship scale (~500 files/batch, <=5MB each). |
| A3 | Consent is recruiter-attested at upload time | Brief §Fairness: "Consent recorded at upload (source, date)". Recruiter asserts candidate consent exists; no public candidate-facing portal in core slice. |
| A4 | Each client user belongs to exactly one client organization | Architecture §1.2: User model has single `client_id nullable`. Client users belong to one client; recruiters have `client_id = null`. |
| A5 | Heuristic scoring mode active when GEMINI_API_KEY is empty | Enables 100% offline development, testing, and continuous integration. Heuristic engine generates exact substring quotes so verifier and evidence drawer function normally. |
| A6 | FastAPI serves compiled Vite SPA static bundle from `frontend/dist` | Allows single-command startup and unified container deployment without requiring a separate Node.js server in production. |
| A7 | In-memory sliding window login rate limiting | Protects authentication endpoints against credential stuffing in single-process deployments without introducing external Redis dependency in dev. |
| A8 | Sample PDF verification via pdfplumber on host | Windows Application Control (AppLocker) blocks dynamic binary loading of pypdfium2_raw\pdfium.dll on local host. pdfplumber and pdfminer.six provide 100% pure Python structural and text extraction validation. |
| A9 | google-genai pinned to 1.75.0 (stable 1.x) | PyPI release google-genai 2.x requires pydantic >= 2.12.5 which is blocked by host Windows AppLocker DLL policy. google-genai 1.75.0 provides full structured JSON output and temperature 0 compatibility with installed pydantic 2.10.4. |
| A10 | Canonical repo root SQLite path resolution | normalize_database_url converts relative ./shortlist.db to the absolute repo root path to prevent diverging database states when running commands from root vs backend subdirectories. |
