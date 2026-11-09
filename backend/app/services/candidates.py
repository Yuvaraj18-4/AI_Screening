import hashlib
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models import AuditLog, Candidate, CVFile


async def resolve_candidate_duplicate(
    db: AsyncSession,
    candidate_id: int,
    action: str,  # "merge" | "keep"
) -> dict[str, Any]:
    cand = await db.get(Candidate, candidate_id)
    if not cand:
        raise NotFoundError("Candidate not found")

    if action == "keep":
        cand.duplicate_of_id = None
    elif action == "merge":
        # Keep duplicate_of_id and mark status as duplicate
        cand.status = "duplicate"

    await db.commit()
    await db.refresh(cand)
    return {
        "id": cand.id,
        "name": cand.name,
        "duplicate_of_id": cand.duplicate_of_id,
        "status": cand.status,
    }


async def delete_candidate_on_request(
    db: AsyncSession,
    candidate_id: int,
    actor_id: int,
) -> dict[str, Any]:
    cand = await db.get(Candidate, candidate_id)
    if not cand:
        raise NotFoundError("Candidate not found")

    # Compute entity hash before redacting
    id_hash = hashlib.sha256(f"cand_{cand.id}_{cand.email}".encode()).hexdigest()

    # Redact personal data from candidate record
    cand.name = "[DELETED_CANDIDATE]"
    cand.email = f"deleted_{cand.id}@example.com"
    cand.phone = "[DELETED]"
    cand.location = "[DELETED]"
    cand.status = "deleted"

    # Redact CV files
    cv_res = await db.execute(select(CVFile).where(CVFile.candidate_id == cand.id))
    for cv in cv_res.scalars().all():
        cv.text = "[DELETED_ON_REQUEST]"
        cv.masked_text = "[DELETED_ON_REQUEST]"
        cv.content = b""

    # Write hash-only AuditLog
    audit = AuditLog(
        actor_id=actor_id,
        action="delete_candidate_personal_data",
        entity_type="candidate",
        entity_hash=id_hash,
        meta={"candidate_id": cand.id, "reason": "data_subject_erasure_request"},
    )
    db.add(audit)

    await db.commit()
    return {"ok": True, "message": "Candidate personal data erased; audit hash recorded"}
