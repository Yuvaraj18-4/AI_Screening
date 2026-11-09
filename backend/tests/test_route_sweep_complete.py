import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.models import (
    Application,
    Candidate,
    Client,
    Criterion,
    CriterionResult,
    CVFile,
    Requisition,
    Score,
    Scorecard,
    Submission,
    UploadBatch,
    User,
)


@pytest.mark.asyncio
async def test_complete_route_sweep_all_methods(
    test_client: AsyncClient, db_session: AsyncSession
):
    # Setup organizations & users
    client_org1 = Client(name="Sweep Co 1")
    client_org2 = Client(name="Sweep Co 2")
    db_session.add_all([client_org1, client_org2])
    await db_session.flush()

    recruiter = User(
        email="full_recruiter@example.com",
        password_hash=hash_password("pw123"),
        name="Full Recruiter",
        role="recruiter",
    )
    client_user1 = User(
        email="full_client1@example.com",
        password_hash=hash_password("pw123"),
        name="Full Client 1",
        role="client",
        client_id=client_org1.id,
    )
    client_user2 = User(
        email="full_client2@example.com",
        password_hash=hash_password("pw123"),
        name="Full Client 2",
        role="client",
        client_id=client_org2.id,
    )
    db_session.add_all([recruiter, client_user1, client_user2])
    await db_session.flush()

    # Create Requisition for Client 1
    req1 = Requisition(
        client_id=client_org1.id,
        title="Senior Python Architect",
        jd_text="Python FastAPI PostgreSQL Redis microservices architect with 7+ years experience.",
        status="active",
        owner_id=recruiter.id,
    )
    # Requisition for Client 2
    req2 = Requisition(
        client_id=client_org2.id,
        title="Data Analyst",
        jd_text="Data analysis and SQL reporting.",
        status="active",
        owner_id=recruiter.id,
    )
    db_session.add_all([req1, req2])
    await db_session.flush()

    # Scorecard & criteria for req1
    sc1 = Scorecard(requisition_id=req1.id, version=1, is_active=True)
    db_session.add(sc1)
    await db_session.flush()

    crit1 = Criterion(
        scorecard_id=sc1.id,
        name="Python Experience >= 5 yrs",
        kind="experience",
        must_have=True,
        weight=3,
        params={"min_years": 5.0},
    )
    db_session.add(crit1)
    await db_session.flush()

    # Candidate 1
    cand1 = Candidate(
        name="Rahul Verma",
        email="rahul.verma@example.com",
        phone="+91-9988776655",
        experience_years=6.0,
        notice_days=30,
        location="Bengaluru",
        skills=["Python", "FastAPI", "SQL"],
    )
    # Candidate 2 (duplicate candidate for resolve duplicate test)
    cand2 = Candidate(
        name="Rahul V",
        email="rahul.dup@example.com",
        phone="+91-9988776655",
        experience_years=6.0,
        notice_days=30,
        location="Bengaluru",
        skills=["Python"],
    )
    db_session.add_all([cand1, cand2])
    await db_session.flush()

    # Mark cand2 as duplicate of cand1
    cand2.duplicate_of_id = cand1.id
    await db_session.flush()

    # CV File
    cv_file = CVFile(
        candidate_id=cand1.id,
        filename="rahul_verma.pdf",
        mime="application/pdf",
        size=1024,
        sha256="fake_sha256_rahul",
        content=b"%PDF-1.4 sample content for candidate rahul verma",
        text="Rahul Verma 6 years python fastAPI microservices",
        masked_text="[CANDIDATE] 6 years python fastAPI microservices",
        parse_status="ok",
    )
    db_session.add(cv_file)
    await db_session.flush()

    # Application
    app1 = Application(
        requisition_id=req1.id,
        candidate_id=cand1.id,
        stage="screened",
    )
    db_session.add(app1)
    await db_session.flush()

    # Score
    score1 = Score(
        application_id=app1.id,
        scorecard_version=1,
        total=85.0,
        confidence="high",
        status="scored",
        cache_key="score_cache_key_full_sweep",
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
        quote="6 years python fastAPI microservices",
        quote_verified=True,
        confidence=1.0,
        source="code",
    )
    db_session.add(cr1)
    await db_session.flush()

    # Submission
    sub1 = Submission(
        application_id=app1.id,
        submitted_by=recruiter.id,
        client_decision="pending",
    )
    db_session.add(sub1)

    # Upload Batch
    batch1 = UploadBatch(
        requisition_id=req1.id,
        created_by=recruiter.id,
        total=1,
    )
    db_session.add(batch1)
    await db_session.commit()

    token_recruiter = create_access_token({"sub": str(recruiter.id), "role": "recruiter"})
    token_client1 = create_access_token({"sub": str(client_user1.id), "role": "client"})
    token_client2 = create_access_token({"sub": str(client_user2.id), "role": "client"})

    h_rec = {"access_token": token_recruiter}
    h_c1 = {"access_token": token_client1}
    h_c2 = {"access_token": token_client2}
    csrf_header = {"X-Requested-With": "XMLHttpRequest"}

    # =========================================================================
    # RECRUITER ROUTES SWEEP (GET, POST, PUT, PATCH, DELETE)
    # =========================================================================

    # 1. Health & Auth
    res = await test_client.get("/api/health")
    assert res.status_code == 200 and res.status_code < 500

    res = await test_client.get("/api/auth/me", cookies=h_rec)
    assert res.status_code == 200 and res.status_code < 500

    res = await test_client.post("/api/auth/logout", cookies=h_rec, headers=csrf_header)
    assert res.status_code == 200 and res.status_code < 500

    # 2. Requisitions GET & POST & PATCH
    res = await test_client.get("/api/requisitions", cookies=h_rec)
    assert res.status_code == 200 and res.status_code < 500

    res = await test_client.get(f"/api/requisitions/{req1.id}", cookies=h_rec)
    assert res.status_code == 200 and res.status_code < 500

    res = await test_client.get(f"/api/requisitions/{req1.id}/applications", cookies=h_rec)
    assert res.status_code == 200 and res.status_code < 500

    res = await test_client.post(
        "/api/requisitions",
        cookies=h_rec,
        headers=csrf_header,
        json={"client_id": client_org1.id, "title": "DevOps Engineer", "jd_text": "Docker K8s CI/CD"},
    )
    assert res.status_code == 200 and res.status_code < 500
    new_req_id = res.json()["id"]

    res = await test_client.patch(
        f"/api/requisitions/{new_req_id}",
        cookies=h_rec,
        headers=csrf_header,
        json={"title": "Senior DevOps Engineer", "status": "active"},
    )
    assert res.status_code == 200 and res.status_code < 500

    res = await test_client.post(
        f"/api/requisitions/{req1.id}/jd/extract",
        cookies=h_rec,
        headers=csrf_header,
    )
    assert res.status_code == 200 and res.status_code < 500

    # 3. Scorecards GET, PUT
    res = await test_client.get(f"/api/requisitions/{req1.id}/scorecard", cookies=h_rec)
    assert res.status_code == 200 and res.status_code < 500

    res = await test_client.put(
        f"/api/requisitions/{req1.id}/scorecard",
        cookies=h_rec,
        headers=csrf_header,
        json={
            "criteria": [
                {
                    "name": "Python 5+ yrs",
                    "kind": "experience",
                    "must_have": True,
                    "weight": 3,
                    "params": {"min_years": 5.0},
                    "description": "5+ yrs experience",
                }
            ]
        },
    )
    assert res.status_code == 200 and res.status_code < 500

    # 4. Uploads
    res = await test_client.get(f"/api/uploads/{batch1.id}/progress", cookies=h_rec)
    assert res.status_code == 200 and res.status_code < 500

    res = await test_client.post(
        f"/api/requisitions/{req1.id}/uploads",
        cookies=h_rec,
        headers=csrf_header,
        files=[("files", ("test_cv.pdf", b"%PDF-1.4 fake candidate text", "application/pdf"))],
    )
    assert res.status_code == 200 and res.status_code < 500

    # 5. Applications GET, STAGE, RESCORE, SUBMIT
    res = await test_client.get(f"/api/applications/{app1.id}", cookies=h_rec)
    assert res.status_code == 200 and res.status_code < 500

    res = await test_client.post(
        f"/api/applications/{app1.id}/rescore",
        cookies=h_rec,
        headers=csrf_header,
    )
    assert res.status_code == 200 and res.status_code < 500

    res = await test_client.post(
        f"/api/applications/{app1.id}/stage",
        cookies=h_rec,
        headers=csrf_header,
        json={"stage": "interview", "note": "Moving to interview"},
    )
    assert res.status_code == 200 and res.status_code < 500

    res = await test_client.post(
        f"/api/applications/{app1.id}/submit",
        cookies=h_rec,
        headers=csrf_header,
    )
    assert res.status_code < 500

    # 6. Candidates CONSENT POST/DELETE, DUPLICATE RESOLVE, DELETE
    # Consent record
    res = await test_client.post(
        f"/api/candidates/{cand1.id}/consent",
        cookies=h_rec,
        headers=csrf_header,
        json={"channel": "email", "notes": "Candidate agreed via email"},
    )
    assert res.status_code == 200 and res.status_code < 500

    # Consent revoke
    res = await test_client.delete(
        f"/api/candidates/{cand1.id}/consent",
        cookies=h_rec,
        headers=csrf_header,
    )
    assert res.status_code == 200 and res.status_code < 500

    # Duplicate resolution
    res = await test_client.post(
        f"/api/candidates/{cand2.id}/duplicate-resolution",
        cookies=h_rec,
        headers=csrf_header,
        json={"action": "keep"},
    )
    assert res.status_code == 200 and res.status_code < 500

    # Candidate DELETE
    res = await test_client.delete(
        f"/api/candidates/{cand2.id}",
        cookies=h_rec,
        headers=csrf_header,
    )
    assert res.status_code == 200 and res.status_code < 500

    # =========================================================================
    # CLIENT 1 SWEEP (Authorized client portal GET & POST)
    # =========================================================================
    res = await test_client.get("/api/portal/requisitions", cookies=h_c1)
    assert res.status_code == 200 and res.status_code < 500

    res = await test_client.get(f"/api/portal/requisitions/{req1.id}/submissions", cookies=h_c1)
    assert res.status_code == 200 and res.status_code < 500

    res = await test_client.get(f"/api/portal/submissions/{sub1.id}", cookies=h_c1)
    assert res.status_code == 200 and res.status_code < 500

    res = await test_client.post(
        f"/api/portal/submissions/{sub1.id}/decision",
        cookies=h_c1,
        headers=csrf_header,
        json={"decision": "propose_slot", "proposed_slot": "2026-11-20T10:00:00Z"},
    )
    assert res.status_code == 200 and res.status_code < 500

    res = await test_client.post(
        f"/api/portal/submissions/{sub1.id}/decision",
        cookies=h_c1,
        headers=csrf_header,
        json={"decision": "shortlisted"},
    )
    assert res.status_code == 200 and res.status_code < 500

    # =========================================================================
    # CLIENT 2 SWEEP (Cross-client isolation: 404, never 500)
    # =========================================================================
    res = await test_client.get(f"/api/portal/requisitions/{req1.id}/submissions", cookies=h_c2)
    assert res.status_code == 404 and res.status_code < 500

    res = await test_client.get(f"/api/portal/submissions/{sub1.id}", cookies=h_c2)
    assert res.status_code == 404 and res.status_code < 500

    res = await test_client.post(
        f"/api/portal/submissions/{sub1.id}/decision",
        cookies=h_c2,
        headers=csrf_header,
        json={"decision": "rejected", "reject_reason": "Not a match"},
    )
    assert res.status_code == 404 and res.status_code < 500

    # Client user cannot access recruiter-only routes (403, never 500)
    res = await test_client.get("/api/requisitions", cookies=h_c1)
    assert res.status_code == 403 and res.status_code < 500

    res = await test_client.post(
        "/api/requisitions",
        cookies=h_c1,
        headers=csrf_header,
        json={"client_id": client_org1.id, "title": "Hacker Req", "jd_text": "Bad"},
    )
    assert res.status_code == 403 and res.status_code < 500
