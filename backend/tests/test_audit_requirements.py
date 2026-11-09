import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.masking import mask_personal_data
from app.ai.scoring import calculate_weighted_score
from app.core.security import create_access_token, hash_password
from app.db.models.entities import (
    Application,
    Candidate,
    Client,
    Criterion,
    CriterionResult,
    Requisition,
    Score,
    Scorecard,
    Submission,
    User,
)
from app.parsing.experience import (
    calculate_experience_from_intervals,
    compute_experience_years,
    merge_date_intervals,
    parse_date_token,
)
from app.parsing.extract_text import extract_cv_text


# ======================================================================
# 1. Masking Tests
# ======================================================================
def test_masking_personal_data():
    raw_cv = """
    Curriculum Vitae
    Name: Ritika Bansal
    Email: ritika.bansal@example.com
    Phone: +91 98765 43210
    Father's Name: Ramesh Bansal
    Date of Birth: 15/08/1992
    Age: 32 years
    Marital Status: Married

    Professional Summary:
    She is a senior Java developer with 6 years experience.
    Her core expertise includes building Spring Boot microservices.
    He worked with him on large-scale distributed databases.
    """

    masked = mask_personal_data(
        raw_cv,
        candidate_name="Ritika Bansal",
        candidate_email="ritika.bansal@example.com",
        candidate_phone="+91 98765 43210",
    )

    # Identifiers must be redacted
    assert "Ritika" not in masked
    assert "Bansal" not in masked
    assert "ritika.bansal@example.com" not in masked
    assert "+91 98765 43210" not in masked
    assert "15/08/1992" not in masked
    assert "Married" not in masked
    assert "Ramesh" not in masked

    # Pronouns should be gender-neutral
    assert "She is" not in masked
    assert "they" in masked.lower()
    assert "them" in masked.lower()

    # Domain skills & experience must remain intact
    assert "Java developer" in masked
    assert "Spring Boot microservices" in masked


# ======================================================================
# 2. Score Math Tests
# ======================================================================
def test_score_math_formula_and_weights():
    # 3 criteria:
    # 1. Experience: weight 3, met (1.0), must_have=True
    # 2. Frameworks: weight 2, partial (0.5), must_have=False
    # 3. Cloud: weight 1, not_found (0.0), must_have=False
    criteria = [
        {"name": "Java Experience", "weight": 3, "must_have": True},
        {"name": "Spring Framework", "weight": 2, "must_have": False},
        {"name": "AWS Cloud", "weight": 1, "must_have": False},
    ]
    results = [
        {"value": 1.0, "verdict": "met"},
        {"value": 0.5, "verdict": "partial"},
        {"value": 0.0, "verdict": "not_found"},
    ]

    total, gaps = calculate_weighted_score(criteria, results)
    # Expected weighted score: (3*1.0 + 2*0.5 + 1*0.0) / (3 + 2 + 1) * 100
    # = (3.0 + 1.0 + 0.0) / 6.0 * 100 = 4.0 / 6.0 * 100 = 66.7
    assert 66.6 <= total <= 66.8
    assert len(gaps) == 0  # must-have was met (1.0)

    # Now test with must-have gap:
    results_with_gap = [
        {"value": 0.5, "verdict": "partial"},  # must-have criterion partially met
        {"value": 1.0, "verdict": "met"},
        {"value": 1.0, "verdict": "met"},
    ]
    total2, gaps2 = calculate_weighted_score(criteria, results_with_gap)
    # Total: (3*0.5 + 2*1.0 + 1*1.0) / 6 * 100 = 4.5 / 6 * 100 = 75.0
    assert 74.9 <= total2 <= 75.1
    assert "Java Experience" in gaps2


# ======================================================================
# 3. Parser Tests (Empty, Garbled, Scanned)
# ======================================================================
def test_parser_empty_file():
    empty_bytes = b""
    res = extract_cv_text("empty.pdf", empty_bytes)
    assert res.parse_status == "failed"
    assert res.text == ""
    assert res.parse_error is not None


def test_parser_garbled_file():
    garbled_bytes = b"\x00\xff\xfe\x01\x02\x03CORRUPTED_BINARY_DATA\x00\x00"
    res = extract_cv_text("corrupt.pdf", garbled_bytes)
    # Should safely return failed or empty status without raising unhandled crash
    assert res.parse_status in ("failed", "empty", "scanned")
    assert isinstance(res.text, str)


def test_parser_scanned_pdf():
    # PDF with image stream but zero text characters
    pdf_no_text = (
        b"%PDF-1.4\n"
        b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
        b"2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
        b"3 0 obj <</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources <</XObject <</Im1 4 0 R>>>> /Contents 5 0 R>> endobj\n"
        b"4 0 obj <</Type /XObject /Subtype /Image /Width 100 /Height 100 "
        b"/ColorSpace /DeviceGray /BitsPerComponent 8 /Length 10>>\n"
        b"stream\n0123456789\nendstream\nendobj\n"
        b"5 0 obj <</Length 18>>\nstream\nq /Im1 Do Q\nendstream\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"0000000009 00000 n \n0000000058 00000 n \n"
        b"0000000115 00000 n \n0000000244 00000 n \n"
        b"0000000405 00000 n \n"
        b"trailer <</Size 6 /Root 1 0 R>>\n"
        b"startxref\n473\n%%EOF\n"
    )
    res = extract_cv_text("scan.pdf", pdf_no_text)
    assert res.is_scan is True or res.parse_status == "scanned" or res.parse_quality <= 0.5


# ======================================================================
# 4. Experience Merge (Overlapping & Unusual Dates)
# ======================================================================
def test_experience_overlapping_and_unusual_dates():
    # Overlapping ranges:
    # Job A: Jan 2018 - Dec 2020 (3 years)
    # Job B: Jun 2020 - Dec 2022 (2.5 years)
    # Merged span: Jan 2018 - Dec 2022 (5 years, not 5.5 years)
    start1 = parse_date_token("Jan 2018")
    end1 = parse_date_token("Dec 2020", is_end_date=True)
    start2 = parse_date_token("Jun 2020")
    end2 = parse_date_token("Dec 2022", is_end_date=True)

    intervals = [(start1, end1), (start2, end2)]
    merged = merge_date_intervals(intervals)
    assert len(merged) == 1
    total_years = calculate_experience_from_intervals(intervals)
    assert 4.9 <= total_years <= 5.1

    # Unusual date formats:
    d_slash_start = parse_date_token("03/2016")
    d_slash_end = parse_date_token("08/2019", is_end_date=True)
    assert d_slash_start is not None and d_slash_start.year == 2016 and d_slash_start.month == 3
    assert d_slash_end is not None and d_slash_end.year == 2019 and d_slash_end.month == 8

    d_apostrophe = parse_date_token("June '19")
    assert d_apostrophe is not None and d_apostrophe.year == 2019

    d_present = parse_date_token("Present", is_end_date=True)
    assert d_present is not None

    # Compute experience from employment entries with unusual formats
    entries = [
        {"start": "03/2016", "end": "08/2019"},
        {"start": "June '19", "end": "Present"},
    ]
    exp, quality = compute_experience_years(entries, "raw resume text")
    assert exp >= 8.0  # From 2016 to present is > 8 years
    assert quality == 1.0


# ======================================================================
# 5. Route-Sweep Test & Regression (No 500s across ALL GET endpoints)
# ======================================================================
@pytest.mark.asyncio
async def test_route_sweep_get_endpoints_no_500(
    test_client: AsyncClient, db_session: AsyncSession
):
    # Setup test entities
    client_org1 = Client(name="Sweep Client 1")
    client_org2 = Client(name="Sweep Client 2")
    db_session.add_all([client_org1, client_org2])
    await db_session.flush()

    recruiter = User(
        email="sweep_recruiter@example.com",
        password_hash=hash_password("password123"),
        name="Sweep Recruiter",
        role="recruiter",
    )
    client_user1 = User(
        email="sweep_client1@example.com",
        password_hash=hash_password("password123"),
        name="Sweep Client 1 User",
        role="client",
        client_id=client_org1.id,
    )
    client_user2 = User(
        email="sweep_client2@example.com",
        password_hash=hash_password("password123"),
        name="Sweep Client 2 User",
        role="client",
        client_id=client_org2.id,
    )
    db_session.add_all([recruiter, client_user1, client_user2])
    await db_session.flush()

    req = Requisition(
        client_id=client_org1.id,
        title="Full Stack Java Engineer",
        jd_text="Java Spring Boot Microservices",
        status="active",
        owner_id=recruiter.id,
    )
    db_session.add(req)
    await db_session.flush()

    scorecard = Scorecard(requisition_id=req.id, version=1, is_active=True)
    db_session.add(scorecard)
    await db_session.flush()

    crit1 = Criterion(
        scorecard_id=scorecard.id,
        name="Java Core",
        kind="skill",
        must_have=True,
        weight=2,
    )
    db_session.add(crit1)
    await db_session.flush()

    candidate = Candidate(
        name="Pooja Sharma",
        email="pooja.sharma@example.com",
        phone="+91-9811223344",
        experience_years=5.0,
        notice_days=30,
        location="Delhi",
    )
    db_session.add(candidate)
    await db_session.flush()

    app = Application(
        requisition_id=req.id,
        candidate_id=candidate.id,
        stage="submitted",
    )
    db_session.add(app)
    await db_session.flush()

    score = Score(
        application_id=app.id,
        scorecard_version=1,
        total=90.0,
        confidence="high",
        status="scored",
        cache_key="sweep_score_cache_key",
        model="heuristic",
        prompt_version="v1",
        scoring_mode="heuristic",
    )
    db_session.add(score)
    await db_session.flush()

    cr = CriterionResult(
        score_id=score.id,
        criterion_id=crit1.id,
        verdict="met",
        value=1.0,
        quote="5 years building Java microservices",
        quote_verified=True,
        confidence=1.0,
        source="code",
    )
    db_session.add(cr)

    sub = Submission(
        application_id=app.id,
        submitted_by=recruiter.id,
        client_decision="pending",
    )
    db_session.add(sub)
    await db_session.commit()

    token_recruiter = create_access_token(
        {"sub": str(recruiter.id), "role": "recruiter"}
    )
    token_client1 = create_access_token(
        {"sub": str(client_user1.id), "role": "client"}
    )
    token_client2 = create_access_token(
        {"sub": str(client_user2.id), "role": "client"}
    )

    # 1. Recruiter GET routes sweep
    recruiter_routes = [
        "/api/health",
        "/api/auth/me",
        "/api/requisitions",
        f"/api/requisitions/{req.id}",
        f"/api/requisitions/{req.id}/scorecard",
        f"/api/requisitions/{req.id}/applications",
        f"/api/applications/{app.id}",
        "/api/portal/requisitions",
    ]
    for route in recruiter_routes:
        res = await test_client.get(
            route, cookies={"access_token": token_recruiter}
        )
        assert (
            res.status_code < 500
        ), f"Route {route} failed with HTTP {res.status_code}"
        assert res.status_code == 200

    # 2. Client 1 GET routes sweep (must not 500; must mask contacts)
    portal_submissions_res = await test_client.get(
        f"/api/portal/requisitions/{req.id}/submissions",
        cookies={"access_token": token_client1},
    )
    assert portal_submissions_res.status_code == 200
    sub_items = portal_submissions_res.json()
    assert len(sub_items) == 1
    assert sub_items[0]["candidate_email"] == "[MASKED_UNTIL_SHORTLIST]"
    assert sub_items[0]["candidate_phone"] == "[MASKED_UNTIL_SHORTLIST]"

    portal_detail_res = await test_client.get(
        f"/api/portal/submissions/{sub.id}",
        cookies={"access_token": token_client1},
    )
    assert portal_detail_res.status_code == 200
    sub_detail = portal_detail_res.json()
    assert sub_detail["candidate_email"] == "[MASKED_UNTIL_SHORTLIST]"
    assert sub_detail["candidate_phone"] == "[MASKED_UNTIL_SHORTLIST]"
    assert len(sub_detail["criteria_results"]) == 1

    # 3. Client 2 cross-client isolation (must return 404, not 403 or 500)
    c2_list_res = await test_client.get(
        f"/api/portal/requisitions/{req.id}/submissions",
        cookies={"access_token": token_client2},
    )
    assert c2_list_res.status_code == 404

    c2_detail_res = await test_client.get(
        f"/api/portal/submissions/{sub.id}",
        cookies={"access_token": token_client2},
    )
    assert c2_detail_res.status_code == 404

    # 4. Unknown /api/* path must return JSON 404
    unknown_api_res = await test_client.get(
        "/api/nonexistent_route_test",
        cookies={"access_token": token_recruiter},
    )
    assert unknown_api_res.status_code == 404
    assert unknown_api_res.headers.get("content-type", "").startswith(
        "application/json"
    )

    # 5. .well-known path must return 404 JSON, not 200 index.html
    well_known_res = await test_client.get("/.well-known/security.txt")
    assert well_known_res.status_code == 404
