import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import clear_login_attempts
from app.db.models import Application, Candidate, Requisition, Submission, User
from app.services.scoping import visible_applications_for
from tests.conftest import auth_cookie_for

CSRF_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


@pytest.mark.asyncio
async def test_csrf_header_required_on_mutating_requests(
    test_client: AsyncClient,
    recruiter_user: User,
):
    # Missing CSRF header on POST /api/auth/login
    response = await test_client.post(
        "/api/auth/login",
        json={"email": recruiter_user.email, "password": "recruiter123"},
    )
    assert response.status_code == 403
    assert "X-Requested-With" in response.json()["detail"]

    # With CSRF header -> success
    response = await test_client.post(
        "/api/auth/login",
        json={"email": recruiter_user.email, "password": "recruiter123"},
        headers=CSRF_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["email"] == recruiter_user.email
    assert "access_token" in response.cookies


@pytest.mark.asyncio
async def test_login_invalid_credentials_and_rate_limit(
    test_client: AsyncClient,
    recruiter_user: User,
):
    rate_limit_key = f"unknown:{recruiter_user.email}"
    clear_login_attempts(rate_limit_key)

    for _ in range(4):
        res = await test_client.post(
            "/api/auth/login",
            json={"email": recruiter_user.email, "password": "wrongpassword"},
            headers=CSRF_HEADERS,
        )
        assert res.status_code == 401

    # 5th attempt still 401
    res = await test_client.post(
        "/api/auth/login",
        json={"email": recruiter_user.email, "password": "wrongpassword"},
        headers=CSRF_HEADERS,
    )
    assert res.status_code == 401

    # 6th attempt hits rate limit
    res = await test_client.post(
        "/api/auth/login",
        json={"email": recruiter_user.email, "password": "wrongpassword"},
        headers=CSRF_HEADERS,
    )
    assert res.status_code == 429
    clear_login_attempts(rate_limit_key)


@pytest.mark.asyncio
async def test_auth_me_endpoint(
    test_client: AsyncClient,
    recruiter_user: User,
):
    # Unauthenticated
    res = await test_client.get("/api/auth/me")
    assert res.status_code == 401

    # Authenticated via cookie
    cookies = auth_cookie_for(recruiter_user)
    res = await test_client.get("/api/auth/me", cookies=cookies)
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == recruiter_user.email
    assert data["role"] == "recruiter"


@pytest.mark.asyncio
async def test_health_check(test_client: AsyncClient):
    res = await test_client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert data["scoring_mode"] in ("llm", "heuristic")


@pytest.mark.asyncio
async def test_visible_applications_scoping(
    db_session: AsyncSession,
    recruiter_user: User,
    client_user: User,
    client_user_2: User,
):
    # Setup: 2 requisitions for 2 clients
    req1 = Requisition(
        client_id=client_user.client_id,
        title="Java Dev",
        jd_text="Java",
        owner_id=recruiter_user.id,
    )
    req2 = Requisition(
        client_id=client_user_2.client_id,
        title="Python Dev",
        jd_text="Python",
        owner_id=recruiter_user.id,
    )
    db_session.add_all([req1, req2])
    await db_session.commit()
    await db_session.refresh(req1)
    await db_session.refresh(req2)

    cand1 = Candidate(name="Candidate 1", email="c1@example.com")
    cand2 = Candidate(name="Candidate 2", email="c2@example.com")
    db_session.add_all([cand1, cand2])
    await db_session.commit()
    await db_session.refresh(cand1)
    await db_session.refresh(cand2)

    app1 = Application(candidate_id=cand1.id, requisition_id=req1.id, stage="submitted")
    app2 = Application(candidate_id=cand2.id, requisition_id=req2.id, stage="submitted")
    db_session.add_all([app1, app2])
    await db_session.commit()
    await db_session.refresh(app1)
    await db_session.refresh(app2)

    # Submissions: app1 submitted to client 1, app2 submitted to client 2
    sub1 = Submission(application_id=app1.id, submitted_by=recruiter_user.id)
    sub2 = Submission(application_id=app2.id, submitted_by=recruiter_user.id)
    db_session.add_all([sub1, sub2])
    await db_session.commit()

    # Recruiter sees both
    q_rec = visible_applications_for(recruiter_user)
    rec_apps = (await db_session.execute(q_rec)).scalars().all()
    assert len(rec_apps) == 2

    # Client 1 sees only app1
    q_c1 = visible_applications_for(client_user)
    c1_apps = (await db_session.execute(q_c1)).scalars().all()
    assert len(c1_apps) == 1
    assert c1_apps[0].id == app1.id

    # Client 2 sees only app2
    q_c2 = visible_applications_for(client_user_2)
    c2_apps = (await db_session.execute(q_c2)).scalars().all()
    assert len(c2_apps) == 1
    assert c2_apps[0].id == app2.id
