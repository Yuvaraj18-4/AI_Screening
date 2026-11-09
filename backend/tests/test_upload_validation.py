import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationError
from app.db.models import Requisition, User
from app.services.uploads import process_cv_uploads, validate_file_content


def test_validate_file_content_rules():
    max_bytes = 5 * 1024 * 1024

    # 1. MZ header in PDF
    err_mz = validate_file_content("malicious.pdf", b"MZ\x90\x00\x03\x00executable", max_bytes)
    assert err_mz is not None
    assert "MZ header" in err_mz

    # 2. Non-zip DOCX
    err_docx = validate_file_content("corrupt.docx", b"Not a zip file at all", max_bytes)
    assert err_docx is not None
    assert "not a valid zip archive" in err_docx

    # 3. File over 5MB
    large_bytes = b"a" * (5 * 1024 * 1024 + 1)
    err_size = validate_file_content("large.pdf", large_bytes, max_bytes)
    assert err_size is not None
    assert "exceeds" in err_size

    # 4. Valid PDF and Valid DOCX
    valid_pdf_bytes = b"%PDF-1.4 sample content"
    assert validate_file_content("valid.pdf", valid_pdf_bytes, max_bytes) is None


@pytest.mark.asyncio
async def test_batch_upload_over_500_files_rejected(
    db_session: AsyncSession, recruiter_user: User, sample_client_org
):
    req = Requisition(
        title="Test Req",
        client_id=sample_client_org.id,
        owner_id=recruiter_user.id,
        status="open",
    )
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)

    # 501 files
    fake_files = [(f"cv_{i}.pdf", b"%PDF-1.4 sample") for i in range(501)]

    with pytest.raises(ValidationError, match="exceeds maximum limit of 500 files"):
        await process_cv_uploads(
            db=db_session,
            requisition_id=req.id,
            user_id=recruiter_user.id,
            file_tuples=fake_files,
        )


@pytest.mark.asyncio
async def test_batch_upload_with_rejected_files_does_not_crash_batch(
    test_client: AsyncClient,
    db_session: AsyncSession,
    recruiter_user: User,
    sample_client_org,
):
    from tests.conftest import auth_cookie_for

    req = Requisition(
        title="Test Req Mixed",
        client_id=sample_client_org.id,
        owner_id=recruiter_user.id,
        status="open",
    )
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)

    files = [
        ("files", ("valid.pdf", b"%PDF-1.4 candidate text", "application/pdf")),
        ("files", ("bad_mz.pdf", b"MZexecutable_binary", "application/pdf")),
        ("files", ("not_zip.docx", b"plain text fake docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
    ]

    res = await test_client.post(
        f"/api/requisitions/{req.id}/uploads",
        files=files,
        cookies=auth_cookie_for(recruiter_user),
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert res.status_code == 200, res.text
    batch_data = res.json()
    batch_id = batch_data["batch_id"]
    assert batch_data["total"] == 3

    # Check progress
    progress_res = await test_client.get(
        f"/api/uploads/{batch_id}/progress",
        cookies=auth_cookie_for(recruiter_user),
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert progress_res.status_code == 200
    prog = progress_res.json()
    assert prog["total"] == 3
    # Two failed validation files
    assert prog["failed"] >= 2
    statuses = {f["filename"]: f["parse_status"] for f in prog["files"]}
    assert statuses["bad_mz.pdf"] == "failed"
    assert statuses["not_zip.docx"] == "failed"
    assert statuses["valid.pdf"] in ("ok", "queued")
