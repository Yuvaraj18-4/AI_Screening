"""Standalone verification script for live Gemini API evaluation.

Run by user after setting GEMINI_API_KEY in the environment.
Evaluates 3 sample CVs against the Senior Java Developer scorecard, validates
quotes, calculates unverified rates, confirms cache determinism, and temperature=0 determinism.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.ai.gemini_client import GeminiClient
from app.ai.verifier import verify_quote
from app.parsing.extract_text import extract_cv_text
from app.ai.masking import mask_personal_data
from app.ai.scoring import compute_cache_key


SCORECARD_CRITERIA = [
    {
        "id": 1,
        "name": "Experience >= 5 years",
        "kind": "experience",
        "must_have": True,
        "weight": 3,
        "params": {"min_years": 5.0},
        "description": "Minimum 5 years of software engineering experience",
    },
    {
        "id": 2,
        "name": "Notice Period <= 60 days",
        "kind": "notice",
        "must_have": True,
        "weight": 2,
        "params": {"max_days": 60},
        "description": "Available to join within 60 calendar days",
    },
    {
        "id": 3,
        "name": "Location in Delhi/NCR/Noida",
        "kind": "location",
        "must_have": True,
        "weight": 2,
        "params": {"target": "delhi/ncr"},
        "description": "Candidate based in Delhi, Noida, or Gurgaon",
    },
    {
        "id": 4,
        "name": "Spring Boot & Microservices",
        "kind": "skill",
        "must_have": True,
        "weight": 3,
        "params": {"skill": "Spring Boot"},
        "description": "Production experience with Spring Boot microservices",
    },
    {
        "id": 5,
        "name": "Kafka & Event Streaming",
        "kind": "skill",
        "must_have": False,
        "weight": 2,
        "params": {"skill": "Kafka"},
        "description": "Hands-on experience with Apache Kafka messaging",
    },
]

SAMPLE_FILES = [
    "CND-91022_Ritika_Bansal.pdf",
    "CND-91088_Pooja_Nair.pdf",
    "CND-91047_Arjun_Rawat.docx",
]


async def run_verification():
    print("=" * 70)
    print("ShortList Gemini API Live Verification Script")
    print("=" * 70)

    api_key = os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    model = os.environ.get("GEMINI_MODEL") or settings.GEMINI_MODEL

    if not api_key:
        print("[FAIL] GEMINI_API_KEY is not set in environment or .env file.")
        print("Please export GEMINI_API_KEY='your-key-here' and re-run.")
        sys.exit(1)

    print(f"Using Model: {model}")
    print(f"API Key: {api_key[:6]}...{api_key[-4:]}")

    gemini = GeminiClient()
    sample_dir = Path("data/sample_cvs")
    if not sample_dir.exists():
        from scripts.generate_samples import generate_all
        generate_all()

    total_semantic_criteria = 0
    total_unverified = 0

    semantic_criteria = [c for c in SCORECARD_CRITERIA if c["kind"] in ("skill", "domain")]

    results_run_1 = {}
    masked_texts = {}

    for fname in SAMPLE_FILES:
        fpath = sample_dir / fname
        if not fpath.exists():
            print(f"[FAIL] Sample file {fpath} not found.")
            sys.exit(1)

        with open(fpath, "rb") as f:
            content = f.read()

        extracted = extract_cv_text(fname, content)
        masked = mask_personal_data(extracted.text)
        masked_texts[fname] = masked

        print(f"\nEvaluating candidate: {fname}...")
        judge_res = await gemini.judge(masked_text=masked, criteria=semantic_criteria)
        results_run_1[fname] = judge_res

        for item in judge_res:
            crit_id = item["criterion_id"]
            crit_name = next(c["name"] for c in semantic_criteria if c["id"] == crit_id)
            verdict = item.get("verdict", "unclear")
            quote = item.get("quote")

            is_verified = False
            if quote:
                is_verified = verify_quote(quote, masked)
            elif verdict in ("not_found", "unclear"):
                is_verified = True

            total_semantic_criteria += 1
            if not is_verified:
                total_unverified += 1

            status_str = "\033[92mVERIFIED\033[0m" if is_verified else "\033[91mUNVERIFIED\033[0m"
            print(f"  • Criterion: {crit_name:30} | Verdict: {verdict:10} | [{status_str}]")
            if quote:
                print(f"    Quote: \"{quote[:80]}...\"" if len(quote) > 80 else f"    Quote: \"{quote}\"")

    unverified_rate = (total_unverified / total_semantic_criteria) if total_semantic_criteria else 0.0
    print(f"\nOverall Unverified Evidence Rate: {unverified_rate:.1%}")

    # Test Cache Determinism
    print("\nTesting Cache Determinism...")
    for fname in SAMPLE_FILES:
        masked = masked_texts[fname]
        key1 = compute_cache_key(masked, 1, "v1", model)
        key2 = compute_cache_key(masked, 1, "v1", model)
        assert key1 == key2, "Cache key calculation must be deterministic"
    print("  [PASS] Cache key computation is 100% deterministic")

    # Repeat call twice without cache to confirm temperature 0 determinism
    print("\nTesting Temperature=0 Determinism (Evaluating Ritika Bansal twice)...")
    ritika_masked = masked_texts[SAMPLE_FILES[0]]
    call_1 = await gemini.judge(masked_text=ritika_masked, criteria=semantic_criteria)
    call_2 = await gemini.judge(masked_text=ritika_masked, criteria=semantic_criteria)

    v1 = [c["verdict"] for c in call_1]
    v2 = [c["verdict"] for c in call_2]
    if v1 != v2:
        print(f"[FAIL] Temperature 0 produced varying verdicts: {v1} != {v2}")
        sys.exit(1)
    print("  [PASS] Temperature 0 produced identical verdicts across repeated calls")

    print("\n" + "=" * 70)
    print("\033[92mGEMINI VERIFICATION COMPLETE - ALL CHECKS PASSED\033[0m")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_verification())
