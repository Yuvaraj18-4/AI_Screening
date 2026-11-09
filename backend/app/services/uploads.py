import io
import zipfile
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import NotFoundError, ValidationError
from app.db.models import (
    Application,
    Candidate,
    Consent,
    CVFile,
    Job,
    Requisition,
    UploadBatch,
)
from app.jobs.queue import enqueue_job
from app.parsing.dedup import compute_sha256


def validate_file_content(fname: str, content: bytes, max_bytes: int) -> str | None:
    """Validates file constraints. Returns error message if invalid, None if valid."""
    if len(content) > max_bytes:
        return f"File {fname} exceeds {settings.MAX_UPLOAD_MB}MB limit"

    lower_name = fname.lower()
    if not (lower_name.endswith(".pdf") or lower_name.endswith(".docx")):
        return f"Unsupported file type: {fname}. Only PDF and DOCX are supported."

    if lower_name.endswith(".pdf"):
        if content.startswith(b"MZ"):
            return f"Invalid PDF: executable binary detected in {fname} (MZ header)"
    elif lower_name.endswith(".docx") and not zipfile.is_zipfile(io.BytesIO(content)):
        return f"Invalid DOCX: file {fname} is not a valid zip archive"

    return None


async def process_cv_uploads(
    db: AsyncSession,
    requisition_id: int,
    user_id: int,
    file_tuples: list[tuple[str, bytes]],  # [(filename, content)]
) -> dict[str, Any]:
    req = await db.get(Requisition, requisition_id)
    if not req:
        raise NotFoundError("Requisition not found")

    if not file_tuples:
        raise ValidationError("No files provided for upload")

    if len(file_tuples) > 500:
        raise ValidationError("Batch upload exceeds maximum limit of 500 files")

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024

    # Create UploadBatch
    batch = UploadBatch(
        requisition_id=requisition_id,
        created_by=user_id,
        total=len(file_tuples),
    )
    db.add(batch)
    await db.flush()

    now = datetime.now(UTC)

    for fname, content in file_tuples:
        val_error = validate_file_content(fname, content, max_bytes)
        sha256_hash = compute_sha256(content)
        mime = (
            "application/pdf"
            if fname.lower().endswith(".pdf")
            else (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                if fname.lower().endswith(".docx")
                else "application/octet-stream"
            )
        )

        candidate_name = fname.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")
        candidate = Candidate(
            name=candidate_name if candidate_name.strip() else "Unknown Candidate",
            email="",
            phone="",
            status="active",
        )
        db.add(candidate)
        await db.flush()

        # Record consent
        consent = Consent(
            candidate_id=candidate.id,
            source="recruiter_bulk_upload",
            given_at=now,
            recorded_by=user_id,
        )
        db.add(consent)

        # Create CVFile
        cv_file = CVFile(
            candidate_id=candidate.id,
            filename=fname,
            mime=mime,
            size=len(content),
            sha256=sha256_hash,
            content=content,
            text="",
            masked_text="",
            parse_status="failed" if val_error else "ok",
            parse_error=val_error,
            batch_id=batch.id,
        )
        db.add(cv_file)
        await db.flush()

        # Create Application
        application = Application(
            candidate_id=candidate.id,
            requisition_id=requisition_id,
            stage="sourced",
        )
        db.add(application)
        await db.flush()

        # Only enqueue parse job if file passed initial format validation
        if not val_error:
            await enqueue_job(
                db=db,
                job_type="parse_cv",
                payload={
                    "cv_file_id": cv_file.id,
                    "candidate_id": candidate.id,
                    "requisition_id": requisition_id,
                    "batch_id": batch.id,
                },
                batch_id=batch.id,
            )

    await db.commit()
    return {
        "batch_id": batch.id,
        "total": len(file_tuples),
        "message": f"Successfully processed batch of {len(file_tuples)} files.",
    }


async def get_batch_progress(db: AsyncSession, batch_id: int) -> dict[str, Any]:
    batch = await db.get(UploadBatch, batch_id)
    if not batch:
        raise NotFoundError("Upload batch not found")

    # Query jobs for this batch
    jobs_res = await db.execute(select(Job).where(Job.batch_id == batch_id))
    jobs = jobs_res.scalars().all()

    queued_count = sum(1 for j in jobs if j.status == "queued")
    running_count = sum(1 for j in jobs if j.status == "running")
    done_count = sum(1 for j in jobs if j.status == "done")
    failed_jobs_count = sum(1 for j in jobs if j.status == "failed")

    # Query files associated with this batch
    cv_res = await db.execute(
        select(CVFile, Candidate)
        .join(Candidate, Candidate.id == CVFile.candidate_id)
        .where(CVFile.batch_id == batch_id)
    )
    files_list = []
    failed_files_count = 0
    for cv_file, candidate in cv_res.all():
        if cv_file.parse_status == "failed":
            failed_files_count += 1
        files_list.append(
            {
                "id": cv_file.id,
                "filename": cv_file.filename,
                "size": cv_file.size,
                "candidate_id": candidate.id,
                "candidate_name": candidate.name,
                "parse_status": cv_file.parse_status,
                "parse_error": cv_file.parse_error,
                "is_duplicate": candidate.duplicate_of_id is not None,
            }
        )

    return {
        "batch_id": batch.id,
        "total": batch.total,
        "queued": queued_count,
        "running": running_count,
        "done": done_count,
        "failed": failed_jobs_count + failed_files_count,
        "files": files_list,
    }
