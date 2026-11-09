from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    submitted_by: int
    submitted_at: datetime
    client_decision: str  # pending, shortlisted, rejected
    reject_reason: str | None = None
    decided_by: int | None = None
    decided_at: datetime | None = None
    proposed_slot: datetime | None = None
    candidate_name: str | None = None
    requisition_title: str | None = None


class SubmissionDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(shortlisted|rejected|propose_slot)$")
    reject_reason: str | None = None
    proposed_slot: datetime | None = None
