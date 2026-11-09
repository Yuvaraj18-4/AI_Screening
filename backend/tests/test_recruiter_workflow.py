import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Application,
    AuditLog,
    Candidate,
    Client,
    Criterion,
    CVFile,
    Requisition,
    Scorecard,
    User,
)
from tests.conftest import auth_cookie_for

CSRF_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


@pytest.mark.asyncio
async def test_submit_requires_view_enforcement(
    test_client: AsyncClient,
    db_session: AsyncSession,
    recruiter_user: User,
    sample_client_org: Client,
):
    cookies = auth_cookie_for(recruiter_user)

    # Setup requisition & application
    req = Requisition(
        client_id=sample_client_org.id, title="Senior Java Dev", owner_id=recruiter_user.id
    )
    db_session.add(req)
    await db_session.flush()

    cand = Candidate(
        name="Ritika Bansal", experience_years=6.5, notice_days=60, email="ritika@example.com"
    )
    db_session.add(cand)
    await db_session.flush()

    app_obj = Application(candidate_id=cand.id, requisition_id=req.id, stage="screened")
    db_session.add(app_obj)
    await db_session.commit()

    # 1. Submit without viewing -> Expect 409 Conflict
    res = await test_client.post(
        f"/api/applications/{app_obj.id}/submit",
        cookies=cookies,
        headers=CSRF_HEADERS,
    )
    assert res.status_code == 409
    assert "view-before-submit" in res.json()["detail"].lower()

    # 2. View application detail -> Expect 200 (records ViewLog)
    res_view = await test_client.get(
        f"/api/applications/{app_obj.id}",
        cookies=cookies,
    )
    assert res_view.status_code == 200
    assert res_view.json()["candidate_name"] == "Ritika Bansal"

    # 3. Submit after viewing -> Expect 200
    res_sub = await test_client.post(
        f"/api/applications/{app_obj.id}/submit",
        cookies=cookies,
        headers=CSRF_HEADERS,
    )
    assert res_sub.status_code == 200
    sub_data = res_sub.json()
    assert sub_data["client_decision"] == "pending"
    assert sub_data["application_id"] == app_obj.id

    # 4. Duplicate submit -> Expect 409
    res_dup = await test_client.post(
        f"/api/applications/{app_obj.id}/submit",
        cookies=cookies,
        headers=CSRF_HEADERS,
    )
    assert res_dup.status_code == 409


@pytest.mark.asyncio
async def test_ranked_list_sorting(
    test_client: AsyncClient,
    db_session: AsyncSession,
    recruiter_user: User,
    sample_client_org: Client,
):
    cookies = auth_cookie_for(recruiter_user)

    req = Requisition(
        client_id=sample_client_org.id, title="Senior Java Developer", owner_id=recruiter_user.id
    )
    db_session.add(req)
    await db_session.flush()

    sc = Scorecard(requisition_id=req.id, version=1, is_active=True)
    db_session.add(sc)
    await db_session.flush()

    c1 = Criterion(
        scorecard_id=sc.id,
        name="Experience",
        kind="experience",
        must_have=True,
        weight=5,
        params={"min": 5, "max": 8},
    )
    c2 = Criterion(
        scorecard_id=sc.id,
        name="Notice",
        kind="notice",
        must_have=True,
        weight=4,
        params={"max_days": 60},
    )
    db_session.add_all([c1, c2])
    await db_session.flush()

    # Ritika: 6.5 yrs, 60d notice (Score 100)
    cand_ritika = Candidate(name="Ritika Bansal", experience_years=6.5, notice_days=60)
    cand_pooja = Candidate(name="Pooja Nair", experience_years=4.0, notice_days=90)
    db_session.add_all([cand_ritika, cand_pooja])
    await db_session.flush()

    cv_ritika = CVFile(
        candidate_id=cand_ritika.id,
        filename="ritika.pdf",
        mime="application/pdf",
        size=1024,
        sha256="sha_ritika_unique",
        content=b"%PDF-ritika",
        text="Ritika Bansal Senior Java Developer with Spring Boot",
        masked_text="Senior Java Developer with Spring Boot",
    )
    cv_pooja = CVFile(
        candidate_id=cand_pooja.id,
        filename="pooja.pdf",
        mime="application/pdf",
        size=1024,
        sha256="sha_pooja_unique",
        content=b"%PDF-pooja",
        text="Pooja Nair Java Developer notice 90 days",
        masked_text="Java Developer notice 90 days",
    )
    db_session.add_all([cv_ritika, cv_pooja])
    await db_session.flush()

    app_ritika = Application(candidate_id=cand_ritika.id, requisition_id=req.id)
    app_pooja = Application(candidate_id=cand_pooja.id, requisition_id=req.id)
    db_session.add_all([app_ritika, app_pooja])
    await db_session.commit()

    # Score both applications
    from app.ai.scoring import evaluate_and_score_application

    await evaluate_and_score_application(db_session, app_ritika.id)
    await evaluate_and_score_application(db_session, app_pooja.id)

    # Fetch ranked list
    res = await test_client.get(
        f"/api/requisitions/{req.id}/applications?sort=score",
        cookies=cookies,
    )
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    # Ritika ranks first
    assert items[0]["candidate_name"] == "Ritika Bansal"
    assert items[1]["candidate_name"] == "Pooja Nair"
    assert items[0]["score"]["total"] > items[1]["score"]["total"]
    # Pooja shows notice period gap
    assert "Notice" in items[1]["score"]["must_have_gaps"]


@pytest.mark.asyncio
async def test_duplicate_resolution_and_deletion(
    test_client: AsyncClient,
    db_session: AsyncSession,
    recruiter_user: User,
):
    cookies = auth_cookie_for(recruiter_user)

    cand_orig = Candidate(name="Original Cand", email="orig@example.com")
    db_session.add(cand_orig)
    await db_session.flush()

    cand_dup = Candidate(
        name="Duplicate Cand", email="dup@example.com", duplicate_of_id=cand_orig.id
    )
    db_session.add(cand_dup)
    await db_session.commit()

    # Resolve duplicate: keep
    res = await test_client.post(
        f"/api/candidates/{cand_dup.id}/duplicate-resolution",
        cookies=cookies,
        headers=CSRF_HEADERS,
        json={"action": "keep"},
    )
    assert res.status_code == 200
    assert res.json()["duplicate_of_id"] is None

    # Deletion on request
    res_del = await test_client.delete(
        f"/api/candidates/{cand_orig.id}",
        cookies=cookies,
        headers=CSRF_HEADERS,
    )
    assert res_del.status_code == 200

    # Verify candidate is redacted
    await db_session.refresh(cand_orig)
    assert cand_orig.name == "[DELETED_CANDIDATE]"
    assert cand_orig.status == "deleted"

    # Verify audit log exists with hash-only
    audit_res = await db_session.execute(
        select(AuditLog).where(AuditLog.entity_type == "candidate")
    )
    audit = audit_res.scalars().first()
    assert audit is not None
    assert len(audit.entity_hash) == 64
    assert audit.action == "delete_candidate_personal_data"
