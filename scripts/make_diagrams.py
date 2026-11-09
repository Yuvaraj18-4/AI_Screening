"""Generate architecture.png and ai_pipeline.png diagrams using Pillow."""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DIAGRAMS_DIR = Path(__file__).resolve().parent.parent / "docs" / "diagrams"
DIAGRAMS_DIR.mkdir(parents=True, exist_ok=True)


def get_font(size: int, bold: bool = False):
    font_path = "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf"
    if os.path.exists(font_path):
        return ImageFont.truetype(font_path, size)
    return ImageFont.load_default()


def draw_arrow(draw, start, end, color="#475569", width=2):
    draw.line([start, end], fill=color, width=width)
    x1, y1 = start
    x2, y2 = end
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    arrow_len = 10
    arrow_angle = math.pi / 6
    p1 = (x2 - arrow_len * math.cos(angle - arrow_angle), y2 - arrow_len * math.sin(angle - arrow_angle))
    p2 = (x2 - arrow_len * math.cos(angle + arrow_angle), y2 - arrow_len * math.sin(angle + arrow_angle))
    draw.polygon([end, p1, p2], fill=color)


def create_architecture_diagram():
    width, height = 1300, 800
    img = Image.new("RGB", (width, height), color="#F8FAFC")
    draw = ImageDraw.Draw(img)

    title_font = get_font(24, bold=True)
    header_font = get_font(18, bold=True)
    body_font = get_font(13, bold=False)
    small_font = get_font(11, bold=False)

    # Title Banner
    draw.rectangle([(40, 30), (1260, 80)], fill="#0F172A", outline="#1E293B", width=2)
    draw.text((60, 42), "ShortList - System Architecture & Component Interaction", fill="#F8FAFC", font=title_font)

    # Container 1: Client Layer (SPA)
    draw.rounded_rectangle([(60, 110), (380, 740)], radius=10, fill="#FFFFFF", outline="#CBD5E1", width=2)
    draw.rectangle([(60, 110), (380, 155)], fill="#EEF2F6")
    draw.text((80, 122), "Client Layer (Frontend)", fill="#1E293B", font=header_font)

    spa_boxes = [
        ("React 19 SPA (Vite + Tailwind v4)", ["Single Page Application (served by FastAPI)", "Tailwind v4 responsive design (Desktop & 375px mobile)", "TanStack React Query for async state"]),
        ("Recruiter Workspace", ["Dashboard, Requisition CRUD, Scorecard creator", "Drag & drop CV batch upload with live progress", "Ranked candidates list & interactive Evidence Drawer", "Candidate anonymization toggle & pipeline stages"]),
        ("Client Review Portal", ["Multi-tenant portal scoped by client_id", "Candidate contact masking (Name/Email/Phone masked)", "Shortlist decision (unmasks contacts)", "Reject dialog with mandatory rejection reason"]),
        ("Security Context", ["HttpOnly SameSite cookies (no tokens in JS storage)", "X-Requested-With CSRF header on all mutating requests", "Role-based UI gating (recruiter vs client)"]),
    ]
    y = 170
    for title, bullets in spa_boxes:
        draw.rounded_rectangle([(80, y), (360, y + 120)], radius=6, fill="#F8FAFC", outline="#E2E8F0", width=1)
        draw.text((95, y + 10), title, fill="#0F172A", font=get_font(13, bold=True))
        by = y + 32
        for b in bullets:
            draw.text((105, by), f"• {b}", fill="#475569", font=body_font)
            by += 20
        y += 135

    # Container 2: FastAPI Monolith Service
    draw.rounded_rectangle([(420, 110), (880, 740)], radius=10, fill="#FFFFFF", outline="#3B82F6", width=2)
    draw.rectangle([(420, 110), (880, 155)], fill="#EFF6FF")
    draw.text((440, 122), "Backend Service (Single FastAPI Instance)", fill="#1D4ED8", font=header_font)

    api_boxes = [
        ("API Gateway & Security", 170, 110, [
            "FastAPI 0.115 async routers (/api/*)",
            "JWT verification from HttpOnly cookie",
            "SlowAPI in-memory rate limiting (5/min on /auth/login)",
            "Multi-tenant access control scoping (services/scoping.py)",
        ]),
        ("Document Ingestion & Parsers (Pure)", 295, 110, [
            "Content validation: MZ rejection, zip verification, 5MB limit",
            "Pure unit-testable parsers (pdfplumber, docx2python)",
            "Deterministic experience & notice normalization",
            "Deterministic PII masking engine (app/ai/masking.py)",
        ]),
        ("DB-Backed Async Job Queue", 420, 115, [
            "In-process AsyncWorker pool (WORKER_CONCURRENCY=3)",
            "Database table 'jobs' state machine: queued -> running -> completed",
            "Concurrency-safe claim, retry with backoff, crash recovery",
            "Async background pipeline for parsing, dedup, and scoring",
        ]),
        ("Scoring & Defense Engine", 550, 115, [
            "GeminiClient (google-genai 1.75.0, temp=0, structured JSON)",
            "Quote verifier (exact substring check, 0-tolerance for hallucinations)",
            "Prompt injection defense (XML delimiter framing & detection)",
            "Deterministic Heuristic fallback engine when API key omitted",
        ]),
        ("SPA Static Mount", 680, 45, [
            "Serves frontend/dist/ at root (/) with 404 JSON protection on /api/*",
        ]),
    ]
    for title, by_start, b_height, bullets in api_boxes:
        draw.rounded_rectangle([(440, by_start), (860, by_start + b_height)], radius=6, fill="#F8FAFC", outline="#BFDBFE", width=1)
        draw.text((455, by_start + 8), title, fill="#1E3A8A", font=get_font(13, bold=True))
        cur_y = by_start + 28
        for b in bullets:
            draw.text((465, cur_y), f"• {b}", fill="#334155", font=body_font)
            cur_y += 18

    # Container 3: Persistence & AI Provider
    draw.rounded_rectangle([(920, 110), (1240, 410)], radius=10, fill="#FFFFFF", outline="#10B981", width=2)
    draw.rectangle([(920, 110), (1240, 155)], fill="#ECFDF5")
    draw.text((940, 122), "Data Persistence Layer", fill="#047857", font=header_font)

    db_bullets = [
        ("Dual-Mode SQLAlchemy 2.0 Async", [
            "Development: SQLite + aiosqlite",
            "Production: PostgreSQL + asyncpg (Neon/Render)",
            "Auto-Normalizer: translates sslmode -> ssl=require",
            "Alembic auto-migrations on service lifespan start",
            "17 relational tables with strict foreign keys",
            "lazy='raise_on_sql' prevents async greenlet crashes",
        ]),
    ]
    for title, bullets in db_bullets:
        draw.text((945, 175), title, fill="#065F46", font=get_font(13, bold=True))
        cur_y = 200
        for b in bullets:
            draw.text((955, cur_y), f"• {b}", fill="#334155", font=body_font)
            cur_y += 24

    draw.rounded_rectangle([(920, 440), (1240, 740)], radius=10, fill="#FFFFFF", outline="#8B5CF6", width=2)
    draw.rectangle([(920, 440), (1240, 485)], fill="#F5F3FF")
    draw.text((940, 452), "AI Provider & Fallback", fill="#6D28D9", font=header_font)

    ai_bullets = [
        ("Google Gemini 2.5 Flash", [
            "Structured JSON schema outputs",
            "Zero temperature for reproducible decisions",
            "Extracts JD criteria and evaluates candidate evidence",
            "Rate limit 429 backoff with exponential retry",
        ]),
        ("Deterministic Heuristic Engine", [
            "Executes when GEMINI_API_KEY is omitted",
            "Rule-based keyword, experience & notice scoring",
            "Identical output schema to LLM response",
            "Zero cloud network dependencies in dev/test",
        ]),
    ]
    cur_y = 505
    for title, bullets in ai_bullets:
        draw.text((945, cur_y), title, fill="#5B21B6", font=get_font(13, bold=True))
        cur_y += 22
        for b in bullets:
            draw.text((955, cur_y), f"• {b}", fill="#334155", font=body_font)
            cur_y += 20
        cur_y += 10

    # Draw connection arrows
    draw_arrow(draw, (380, 220), (420, 220), color="#2563EB", width=2)
    draw_arrow(draw, (420, 250), (380, 250), color="#64748B", width=2)

    draw_arrow(draw, (880, 260), (920, 260), color="#059669", width=2)
    draw_arrow(draw, (920, 300), (880, 300), color="#64748B", width=2)

    draw_arrow(draw, (880, 600), (920, 600), color="#7C3AED", width=2)
    draw_arrow(draw, (920, 640), (880, 640), color="#64748B", width=2)

    out_path = DIAGRAMS_DIR / "architecture.png"
    img.save(out_path, format="PNG")
    print(f"Architecture diagram saved: {out_path} ({width}x{height})")


def create_ai_pipeline_diagram():
    width, height = 1300, 850
    img = Image.new("RGB", (width, height), color="#F8FAFC")
    draw = ImageDraw.Draw(img)

    title_font = get_font(24, bold=True)
    step_title_font = get_font(14, bold=True)
    body_font = get_font(12, bold=False)

    # Title Banner
    draw.rectangle([(40, 25), (1260, 75)], fill="#0F172A", outline="#1E293B", width=2)
    draw.text((60, 36), "ShortList - AI Screening Pipeline ('AI Judges, Code Scores')", fill="#F8FAFC", font=title_font)

    steps = [
        ("1. Ingestion & Validation", [
            "PDF/DOCX file upload",
            "Header validation (reject MZ bytes)",
            "Zip integrity check for DOCX",
            "5MB size & 500 batch limit check",
        ], 60, 110, 260, 180, "#3B82F6", "#EFF6FF"),
        ("2. Text Extraction & Dedup", [
            "pdfplumber & docx2python extract text",
            "Empty & garbled file detection",
            "SHA-256 raw content hash deduplication",
            "Fuzzy phone/name match detection",
        ], 360, 110, 260, 180, "#3B82F6", "#EFF6FF"),
        ("3. PII Anonymization / Masking", [
            "Pure regex engine runs before LLM",
            "Candidate name, email, phone masked",
            "Gender pronouns (he/she/him/her) masked",
            "DOB & marital status stripped",
        ], 660, 110, 270, 180, "#E11D48", "#FFF1F2"),
        ("4. Deterministic Code Evaluation", [
            "Experience years calculated by date merging",
            "Overlapping tenures deduplicated",
            "Notice period parsed & converted to days",
            "Location fuzzy match against target city",
        ], 970, 110, 270, 180, "#059669", "#ECFDF5"),

        ("5. LLM Semantic Evaluation", [
            "Gemini 2.5 Flash at temperature 0",
            "Structured JSON schema response",
            "Evaluates skills & domain criteria",
            "Extracts verbatim quotes for evidence",
            "Protected against prompt injection",
        ], 970, 350, 270, 200, "#7C3AED", "#F5F3FF"),
        ("6. Quote Verification ('Trust but Verify')", [
            "Exact substring check against raw CV",
            "Punctuation & whitespace normalized",
            "If quote hallucinated: confidence -> 0,",
            "criterion score -> 0, flagged as UNVERIFIED",
            "Zero hallucinated evidence reaches client",
        ], 660, 350, 270, 200, "#D97706", "#FFFBEB"),
        ("7. Deterministic Scoring Math", [
            "Weighted formula: sum(w_i * s_i) / sum(w_i)",
            "Must-have criteria: score < 3 -> GAP detected",
            "Confidence penalty multiplier applied",
            "Overall score normalized to 0-100 scale",
            "High / Medium / Low confidence tags",
        ], 360, 350, 260, 200, "#059669", "#ECFDF5"),
        ("8. Output Persistence & View Logs", [
            "Score, CriterionResults stored in DB",
            "Cached with SHA-256 (Scorecard + CV)",
            "Recruiter views candidate profile",
            "ViewLog recorded before shortlist submit",
            "Contact info remains masked for client",
        ], 60, 350, 260, 200, "#0F172A", "#F1F5F9"),
    ]

    for title, bullets, x, y, w, h, border_color, fill_color in steps:
        draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=8, fill=fill_color, outline=border_color, width=2)
        draw.text((x + 12, y + 12), title, fill=border_color, font=step_title_font)
        cur_y = y + 38
        for b in bullets:
            draw.text((x + 16, cur_y), f"• {b}", fill="#1E293B", font=body_font)
            cur_y += 24

    # Connect top row left to right
    draw_arrow(draw, (320, 200), (360, 200), color="#3B82F6", width=2)
    draw_arrow(draw, (620, 200), (660, 200), color="#3B82F6", width=2)
    draw_arrow(draw, (930, 200), (970, 200), color="#3B82F6", width=2)

    # Down from 4 to 5
    draw_arrow(draw, (1105, 290), (1105, 350), color="#7C3AED", width=2)

    # Connect bottom row right to left
    draw_arrow(draw, (970, 450), (930, 450), color="#D97706", width=2)
    draw_arrow(draw, (660, 450), (620, 450), color="#059669", width=2)
    draw_arrow(draw, (360, 450), (320, 450), color="#0F172A", width=2)

    # Key Principles Banner at bottom
    draw.rounded_rectangle([(60, 590), (1240, 810)], radius=10, fill="#FFFFFF", outline="#64748B", width=2)
    draw.text((80, 605), "Key Defensive & Governance Principles", fill="#0F172A", font=get_font(16, bold=True))

    principles = [
        ("Deterministic Fallback", "When GEMINI_API_KEY is not configured or fails 3x, the pipeline falls back seamlessly to rule-based heuristic scoring with matching schemas."),
        ("No Auto-Rejection", "The AI never automatically rejects or disqualifies candidates. It surfaces gaps and evidence for human recruiter evaluation and submit decisions."),
        ("Prompt Injection Defense", "Resume text is isolated inside strict XML tags; system instructions dictate instructions inside resume data must never override scoring policy."),
        ("GDPR Erasure & Masking", "Candidate contacts are masked for clients until shortlisted. Candidate deletion replaces PII with an irreversible SHA-256 audit log."),
    ]
    py = 635
    for p_title, p_desc in principles:
        draw.text((95, py), f"{p_title}:", fill="#1E3A8A", font=get_font(13, bold=True))
        draw.text((260, py), p_desc, fill="#334155", font=body_font)
        py += 38

    out_path = DIAGRAMS_DIR / "ai_pipeline.png"
    img.save(out_path, format="PNG")
    print(f"AI pipeline diagram saved: {out_path} ({width}x{height})")


if __name__ == "__main__":
    create_architecture_diagram()
    create_ai_pipeline_diagram()

