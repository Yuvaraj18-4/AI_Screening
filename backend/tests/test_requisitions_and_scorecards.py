from unittest.mock import AsyncMock, patch

import pytest
from google.genai import errors as genai_errors
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import set_llm_client_override
from app.ai.fake_client import FakeClient
from app.ai.gemini_client import GeminiAIError, GeminiClient
from app.db.models import Client, Scorecard, User
from tests.conftest import auth_cookie_for

CSRF_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


@pytest.fixture(autouse=True)
def setup_fake_llm():
    fake = FakeClient()
    set_llm_client_override(fake)
    yield fake
    set_llm_client_override(None)


@pytest.mark.asyncio
async def test_requisition_crud_and_scorecard_versioning(
    test_client: AsyncClient,
    db_session: AsyncSession,
    recruiter_user: User,
    sample_client_org: Client,
):
    cookies = auth_cookie_for(recruiter_user)

    # 1. Create requisition
    res = await test_client.post(
        "/api/requisitions",
        cookies=cookies,
        headers=CSRF_HEADERS,
        json={
            "client_id": sample_client_org.id,
            "title": "Senior Java Developer",
            "jd_text": "Need 5-8 years experience in Java, Spring Boot, Noida, notice 60 days.",
        },
    )
    assert res.status_code == 200
    req_data = res.json()
    req_id = req_data["id"]
    assert req_data["title"] == "Senior Java Developer"
    assert req_data["client_name"] == sample_client_org.name

    # 2. Extract JD criteria
    res = await test_client.post(
        f"/api/requisitions/{req_id}/jd/extract",
        cookies=cookies,
        headers=CSRF_HEADERS,
    )
    assert res.status_code == 200
    draft = res.json()
    assert "criteria" in draft
    assert len(draft["criteria"]) >= 3

    # 3. Save scorecard v1
    v1_criteria = [
        {
            "name": "Java Experience",
            "kind": "experience",
            "must_have": True,
            "weight": 5,
            "params": {"min": 5, "max": 8},
            "description": "5-8 yrs Java",
        },
        {
            "name": "Spring Boot",
            "kind": "skill",
            "must_have": True,
            "weight": 4,
            "params": {"skill": "Spring Boot"},
            "description": "Spring Boot",
        },
    ]

    res = await test_client.put(
        f"/api/requisitions/{req_id}/scorecard",
        cookies=cookies,
        headers=CSRF_HEADERS,
        json={"criteria": v1_criteria},
    )
    assert res.status_code == 200
    sc_v1 = res.json()
    assert sc_v1["version"] == 1
    assert sc_v1["is_active"] is True
    assert len(sc_v1["criteria"]) == 2

    # 4. Save scorecard v2 (update)
    v2_criteria = [
        *v1_criteria,
        {
            "name": "Notice Period",
            "kind": "notice",
            "must_have": False,
            "weight": 2,
            "params": {"max_days": 60},
            "description": "60 days",
        },
    ]

    res = await test_client.put(
        f"/api/requisitions/{req_id}/scorecard",
        cookies=cookies,
        headers=CSRF_HEADERS,
        json={"criteria": v2_criteria},
    )
    assert res.status_code == 200
    sc_v2 = res.json()
    assert sc_v2["version"] == 2
    assert sc_v2["is_active"] is True
    assert len(sc_v2["criteria"]) == 3

    # Verify in DB: v1 is now is_active = False, v2 is is_active = True
    v1_db = (
        await db_session.execute(
            select(Scorecard).where(Scorecard.requisition_id == req_id, Scorecard.version == 1)
        )
    ).scalar_one()
    assert v1_db.is_active is False


@pytest.mark.asyncio
async def test_client_user_forbidden_on_requisition_routes(
    test_client: AsyncClient,
    client_user: User,
    sample_client_org: Client,
):
    cookies = auth_cookie_for(client_user)
    res = await test_client.get("/api/requisitions", cookies=cookies)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_gemini_client_mock_sdk():
    client = GeminiClient(api_key="test-fake-key", model_name="gemini-2.5-flash")

    # 1. Valid response test
    mock_response = AsyncMock()
    mock_response.text = '{"title": "Java Dev", "criteria": [{"name": "Java", "kind": "skill", "must_have": true, "weight": 5}]}'

    mock_genai_client = AsyncMock()
    mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    client._client = mock_genai_client

    result = await client.extract_jd("Senior Java Developer job description")
    assert result["title"] == "Java Dev"
    assert len(result["criteria"]) == 1

    # 2. Malformed JSON test -> raises GeminiAIError
    bad_response = AsyncMock()
    bad_response.text = "NOT_JSON"
    mock_genai_client.aio.models.generate_content = AsyncMock(return_value=bad_response)
    with pytest.raises(GeminiAIError, match="Malformed JSON"):
        await client.extract_jd("some jd")

    # 3. 429 retry then success
    api_err = genai_errors.APIError(429, {"message": "Too Many Requests"})
    api_err.code = 429

    mock_genai_client.aio.models.generate_content = AsyncMock(side_effect=[api_err, mock_response])
    with patch("asyncio.sleep", new=AsyncMock()):
        res = await client.extract_jd("test retry")
        assert res["title"] == "Java Dev"

    # 4. Repeated failures -> raises GeminiAIError
    mock_genai_client.aio.models.generate_content = AsyncMock(side_effect=api_err)
    with patch("asyncio.sleep", new=AsyncMock()), pytest.raises(GeminiAIError):
        await client.extract_jd("test failure")
