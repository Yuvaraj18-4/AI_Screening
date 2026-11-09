import io
from datetime import UTC, datetime, timedelta

import docx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job, Requisition, User
from app.jobs.queue import (
    claim_next_job,
    fail_or_retry_job,
    reset_stale_running_jobs,
)
from app.parsing.dedup import compute_jaccard_similarity, tokenize_text
from app.parsing.experience import (
    calculate_experience_from_intervals,
    compute_experience_years,
    merge_date_intervals,
    parse_date_token,
)
from app.parsing.extract_text import (
    extract_cv_text,
    extract_text_from_docx,
    extract_text_from_pdf,
)
from app.parsing.notice import normalise_notice_period
from tests.conftest import auth_cookie_for

CSRF_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


def make_dummy_docx(text: str) -> bytes:
    doc = docx.Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_experience_date_merging_and_parsing():
    # Overlapping dates: Jan 2018 - Jun 2020 and Jan 2020 - Dec 2021 (should be Jan 2018 - Dec 2021 = 4 years)
    d1_start = parse_date_token("Jan 2018")
    d1_end = parse_date_token("Jun 2020", is_end_date=True)
    d2_start = parse_date_token("Jan 2020")
    d2_end = parse_date_token("Dec 2021", is_end_date=True)

    intervals = [(d1_start, d1_end), (d2_start, d2_end)]
    merged = merge_date_intervals(intervals)
    assert len(merged) == 1
    assert merged[0][0] == d1_start
    assert merged[0][1] == d2_end

    years = calculate_experience_from_intervals(intervals)
    assert 3.9 <= years <= 4.1

    # Fallback to explicit statement
    exp, quality = compute_experience_years([], "Candidate with 6.5 years of experience in Java.")
    assert exp == 6.5
    assert quality == 0.85

    # Unparseable
    exp0, q0 = compute_experience_years([], "No dates or experience listed.")
    assert exp0 == 0.0
    assert q0 == 0.5


def test_notice_period_normalisation():
    assert normalise_notice_period("30 days") == 30
    assert normalise_notice_period("60 days") == 60
    assert normalise_notice_period("90 days") == 90
    assert normalise_notice_period("1 month") == 30
    assert normalise_notice_period("2 months") == 60
    assert normalise_notice_period("immediate") == 0
    assert normalise_notice_period("serving notice") == 15
    assert (
        normalise_notice_period("", full_text="Candidate is serving notice period of 15 days") == 15
    )


def test_dedup_similarity():
    text1 = "Senior Java Developer with Spring Boot, Microservices, REST APIs, and Docker experience in Noida."
    text2 = "Senior Java Developer with Spring Boot, Microservices, REST APIs, and Docker experience in Noida India."
    text3 = "Junior KYC Analyst specializing in AML fraud monitoring and Excel reports."

    set1 = tokenize_text(text1)
    set2 = tokenize_text(text2)
    set3 = tokenize_text(text3)

    sim_high = compute_jaccard_similarity(set1, set2)
    assert sim_high >= 0.85

    sim_low = compute_jaccard_similarity(set1, set3)
    assert sim_low < 0.2


def test_docx_and_scan_extraction():
    # Empty file
    res_empty = extract_cv_text("empty.pdf", b"")
    assert res_empty.parse_status == "failed"

    # Invalid PDF bytes
    res_inv = extract_text_from_pdf(b"not a real pdf")
    assert res_inv.parse_status == "failed"

    # Valid DOCX
    docx_bytes = make_dummy_docx(
        "Ritika Bansal\nSenior Java Developer with Spring Boot experience."
    )
    res_docx = extract_text_from_docx(docx_bytes)
    assert res_docx.parse_status == "ok"
    assert "Ritika Bansal" in res_docx.text


@pytest.mark.asyncio
async def test_job_queue_retry_and_restart_recovery(db_session: AsyncSession):
    # 1. Test claim and retry
    now = datetime.now(UTC)
    job = Job(
        type="parse_cv",
        payload={"test": 123},
        status="queued",
        next_run_at=now,
        attempts=0,
        max_attempts=3,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Claim next job
    claimed = await claim_next_job(db_session)
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == "running"
    assert claimed.attempts == 1

    # Simulate failure on attempt 1 -> should re-queue with backoff
    await fail_or_retry_job(db_session, job.id, "Network timeout")
    await db_session.refresh(job)
    assert job.status == "queued"
    assert job.last_error == "Network timeout"
    assert job.next_run_at.replace(tzinfo=UTC) >= now

    # Simulate reaching max attempts
    job.attempts = 3
    await fail_or_retry_job(db_session, job.id, "Permanent error")
    await db_session.refresh(job)
    assert job.status == "failed"
    assert job.finished_at is not None

    # 2. Test restart recovery: job stuck running for > 300s reset to queued
    stuck_job = Job(
        type="parse_cv",
        payload={"test": 456},
        status="running",
        started_at=now - timedelta(seconds=400),
        attempts=1,
    )
    db_session.add(stuck_job)
    await db_session.commit()
    await db_session.refresh(stuck_job)

    reset_count = await reset_stale_running_jobs(db_session, timeout_seconds=300)
    assert reset_count >= 1
    await db_session.refresh(stuck_job)
    assert stuck_job.status == "queued"


@pytest.mark.asyncio
async def test_upload_endpoint_and_progress(
    test_client: AsyncClient,
    db_session: AsyncSession,
    recruiter_user: User,
):
    # Create requisition
    req = Requisition(
        client_id=1,
        title="Java Dev",
        jd_text="Java Spring",
        owner_id=recruiter_user.id,
    )
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)

    cookies = auth_cookie_for(recruiter_user)

    docx_data = make_dummy_docx("Candidate Name\nJava Developer with 5 years experience.")
    files = [
        (
            "files",
            (
                "candidate_one.docx",
                docx_data,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        ),
    ]

    res = await test_client.post(
        f"/api/requisitions/{req.id}/uploads",
        cookies=cookies,
        headers=CSRF_HEADERS,
        files=files,
    )
    assert res.status_code == 200
    upload_data = res.json()
    batch_id = upload_data["batch_id"]
    assert upload_data["total"] == 1

    # Check progress
    res_prog = await test_client.get(
        f"/api/uploads/{batch_id}/progress",
        cookies=cookies,
    )
    assert res_prog.status_code == 200
    prog_data = res_prog.json()
    assert prog_data["batch_id"] == batch_id
    assert prog_data["total"] == 1
    assert len(prog_data["files"]) == 1
    assert prog_data["files"][0]["filename"] == "candidate_one.docx"
