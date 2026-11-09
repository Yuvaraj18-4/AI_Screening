from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

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


@pytest.mark.asyncio
async def test_client_portal_isolation_and_masking(test_client: AsyncClient, db_session: AsyncSession):
    # 1. Setup two clients
    client1 = Client(name="FinTech Corp")
    client2 = Client(name="HealthCare Ltd")
    db_session.add_all([client1, client2])
    await db_session.flush()

    recruiter = User(
        email="recruiter_p6@example.com",
        password_hash=hash_password("pw123"),
        name="Recruiter P6",
        role="recruiter",
    )
    user_client1 = User(
        email="client1_p6@example.com",
        password_hash=hash_password("pw123"),
        name="Client User 1",
        role="client",
        client_id=client1.id,
    )
    user_client2 = User(
        email="client2_p6@example.com",
        password_hash=hash_password("pw123"),
        name="Client User 2",
        role="client",
        client_id=client2.id,
    )
    db_session.add_all([recruiter, user_client1, user_client2])
    await db_session.flush()

    # Create requisition for client1
    req1 = Requisition(
        client_id=client1.id,
        title="Senior Python Architect",
        jd_text="Python async architecture",
        status="active",
        owner_id=recruiter.id,
    )
    db_session.add(req1)
    await db_session.flush()

    # Candidate with real contacts
    cand1 = Candidate(
        name="Ananya Sharma",
        email="ananya.sharma@example.com",
        phone="+91-9876543210",
        location="Bangalore",
        current_role="Lead Engineer",
        skills=["Python", "FastAPI"],
        experience_years=7.5,
        notice_days=30,
    )
    db_session.add(cand1)
    await db_session.flush()

    app1 = Application(
        requisition_id=req1.id,
        candidate_id=cand1.id,
        stage="submitted",
    )
    db_session.add(app1)
    await db_session.flush()

    card = Scorecard(requisition_id=req1.id, version=1, is_active=True)
    db_session.add(card)
    await db_session.flush()

    crit1 = Criterion(
        scorecard_id=card.id,
        name="Python Experience",
        kind="experience",
        must_have=True,
        weight=2,
        params={"min_years": 5},
    )
    db_session.add(crit1)
    await db_session.flush()

    score1 = Score(
        application_id=app1.id,
        scorecard_version=1,
        total=85.0,
        confidence="high",
        status="scored",
        cache_key="test_cache_key_1",
        model="heuristic",
        prompt_version="v1",
        scoring_mode="heuristic",
    )
    db_session.add(score1)
    await db_session.flush()

    cr1 = CriterionResult(
        score_id=score1.id,
        criterion_id=crit1.id,
        verdict="met",
        value=1.0,
        quote="7.5 years of Python development",
        quote_verified=True,
        confidence=1.0,
        source="code",
    )
    db_session.add(cr1)

    sub1 = Submission(
        application_id=app1.id,
        submitted_by=recruiter.id,
        client_decision="pending",
    )
    db_session.add(sub1)
    await db_session.commit()

    token_client1 = create_access_token({"sub": str(user_client1.id), "role": "client"})
    token_client2 = create_access_token({"sub": str(user_client2.id), "role": "client"})

    # Client 1 queries submissions for req1
    res1 = await test_client.get(
        f"/api/portal/requisitions/{req1.id}/submissions",
        cookies={"access_token": token_client1},
    )
    assert res1.status_code == 200
    items = res1.json()
    assert len(items) == 1
    assert items[0]["candidate_name"] == "Ananya Sharma"
    # Contact masking check: masked before shortlist
    assert items[0]["candidate_email"] == "[MASKED_UNTIL_SHORTLIST]"
    assert items[0]["candidate_phone"] == "[MASKED_UNTIL_SHORTLIST]"

    # Client 2 queries same requisition submissions -> 404 Not Found
    res2 = await test_client.get(
        f"/api/portal/requisitions/{req1.id}/submissions",
        cookies={"access_token": token_client2},
    )
    assert res2.status_code == 404

    # Client 2 tries to view Client 1's submission detail -> 404 Not Found
    res_detail_c2 = await test_client.get(
        f"/api/portal/submissions/{sub1.id}",
        cookies={"access_token": token_client2},
    )
    assert res_detail_c2.status_code == 404

    # Client 1 views submission detail
    res_detail_c1 = await test_client.get(
        f"/api/portal/submissions/{sub1.id}",
        cookies={"access_token": token_client1},
    )
    assert res_detail_c1.status_code == 200
    detail = res_detail_c1.json()
    assert detail["candidate_name"] == "Ananya Sharma"
    assert detail["candidate_email"] == "[MASKED_UNTIL_SHORTLIST]"
    assert detail["candidate_phone"] == "[MASKED_UNTIL_SHORTLIST]"
    assert detail["masked"] is True

    # Client 1 shortlists candidate
    shortlist_res = await test_client.post(
        f"/api/portal/submissions/{sub1.id}/decision",
        json={"decision": "shortlisted"},
        headers={"X-Requested-With": "XMLHttpRequest"},
        cookies={"access_token": token_client1},
    )
    assert shortlist_res.status_code == 200
    shortlisted_data = shortlist_res.json()
    assert shortlisted_data["stage"] == "client_shortlisted"
    assert shortlisted_data["masked"] is False
    # Contact info UNMASKED after shortlist
    assert shortlisted_data["candidate_email"] == "ananya.sharma@example.com"
    assert shortlisted_data["candidate_phone"] == "+91-9876543210"


@pytest.mark.asyncio
async def test_rejection_requires_reason_and_propose_slot(test_client: AsyncClient, db_session: AsyncSession):
    # Setup client and application
    client_org = Client(name="Retail Tech")
    db_session.add(client_org)
    await db_session.flush()

    recruiter = User(
        email="recruiter_p6_2@example.com",
        password_hash=hash_password("pw123"),
        name="Recruiter",
        role="recruiter",
    )
    client_user = User(
        email="client_p6_2@example.com",
        password_hash=hash_password("pw123"),
        name="Client Approver",
        role="client",
        client_id=client_org.id,
    )
    db_session.add_all([recruiter, client_user])
    await db_session.flush()

    req = Requisition(
        client_id=client_org.id,
        title="Frontend Specialist",
        jd_text="React and TypeScript",
        status="active",
        owner_id=recruiter.id,
    )
    db_session.add(req)
    await db_session.flush()

    cand = Candidate(
        name="Rahul Verma",
        email="rahul.verma@example.com",
        phone="+91-9123456789",
        location="Delhi",
    )
    db_session.add(cand)
    await db_session.flush()

    app = Application(
        requisition_id=req.id,
        candidate_id=cand.id,
        stage="submitted",
    )
    db_session.add(app)
    await db_session.flush()

    sub = Submission(
        application_id=app.id,
        submitted_by=recruiter.id,
        client_decision="pending",
    )
    db_session.add(sub)
    await db_session.commit()

    token = create_access_token({"sub": str(client_user.id), "role": "client"})

    # 1. Try reject without reason -> fails with 422
    rej_fail = await test_client.post(
        f"/api/portal/submissions/{sub.id}/decision",
        json={"decision": "rejected", "reject_reason": ""},
        headers={"X-Requested-With": "XMLHttpRequest"},
        cookies={"access_token": token},
    )
    assert rej_fail.status_code == 422

    # 2. Reject with valid reason -> succeeds
    rej_ok = await test_client.post(
        f"/api/portal/submissions/{sub.id}/decision",
        json={"decision": "rejected", "reject_reason": "Insufficient experience with micro-frontends"},
        headers={"X-Requested-With": "XMLHttpRequest"},
        cookies={"access_token": token},
    )
    assert rej_ok.status_code == 200
    rej_data = rej_ok.json()
    assert rej_data["stage"] == "rejected"
    assert rej_data["reject_reason"] == "Insufficient experience with micro-frontends"

    # 3. Create another submission and propose slot
    cand2 = Candidate(
        name="Sunil Rao",
        email="sunil.rao@example.com",
        phone="+91-9888877777",
        location="Pune",
    )
    db_session.add(cand2)
    await db_session.flush()

    app2 = Application(
        requisition_id=req.id,
        candidate_id=cand2.id,
        stage="submitted",
    )
    db_session.add(app2)
    await db_session.flush()

    sub2 = Submission(
        application_id=app2.id,
        submitted_by=recruiter.id,
        client_decision="pending",
    )
    db_session.add(sub2)
    await db_session.commit()

    slot_time = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    slot_res = await test_client.post(
        f"/api/portal/submissions/{sub2.id}/decision",
        json={"decision": "propose_slot", "proposed_slot": slot_time},
        headers={"X-Requested-With": "XMLHttpRequest"},
        cookies={"access_token": token},
    )
    assert slot_res.status_code == 200
    slot_data = slot_res.json()
    assert slot_data["stage"] == "interview"
    assert slot_data["proposed_slot"] is not None


@pytest.mark.asyncio
async def test_consent_record_and_revoke(test_client: AsyncClient, db_session: AsyncSession):
    recruiter = User(
        email="recruiter_consent@example.com",
        password_hash=hash_password("pw123"),
        name="Consent Recruiter",
        role="recruiter",
    )
    db_session.add(recruiter)
    await db_session.flush()

    cand = Candidate(
        name="Vikas Kumar",
        email="vikas.kumar@example.com",
        phone="+91-9988776655",
    )
    db_session.add(cand)
    await db_session.commit()

    token = create_access_token({"sub": str(recruiter.id), "role": "recruiter"})

    # Record consent
    rec_res = await test_client.post(
        f"/api/candidates/{cand.id}/consent",
        json={"channel": "email", "notes": "Consent received via signed PDF form"},
        headers={"X-Requested-With": "XMLHttpRequest"},
        cookies={"access_token": token},
    )
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["consent_status"] == "granted"
    assert rec_data["consented_at"] is not None

    # Revoke consent
    rev_res = await test_client.delete(
        f"/api/candidates/{cand.id}/consent",
        headers={"X-Requested-With": "XMLHttpRequest"},
        cookies={"access_token": token},
    )
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert rev_data["consent_status"] == "revoked"
    assert rev_data["revoked_at"] is not None
