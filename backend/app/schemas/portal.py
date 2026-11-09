from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.candidates import CriterionResultDetail


class PortalRequisitionOut(BaseModel):
    id: int
    title: str
    department: str | None = None
    location: str | None = None
    status: str
    submission_count: int = 0


class PortalSubmissionListItem(BaseModel):
    submission_id: int
    application_id: int
    candidate_id: int
    candidate_name: str
    candidate_email: str
    candidate_phone: str
    stage: str
    client_decision: str
    submitted_at: datetime
    weighted_score: float | None = None
    must_have_gaps: list[str] = Field(default_factory=list)
    confidence_score: str | None = None
    notes: str | None = None


class PortalSubmissionDetailOut(BaseModel):
    submission_id: int
    application_id: int
    candidate_id: int
    candidate_name: str
    candidate_email: str
    candidate_phone: str
    stage: str
    client_decision: str
    submitted_at: datetime
    weighted_score: float | None = None
    must_have_gaps: list[str] = Field(default_factory=list)
    confidence_score: str | None = None
    notes: str | None = None
    proposed_slot: datetime | None = None
    reject_reason: str | None = None
    masked: bool = True
    criteria_results: list[CriterionResultDetail] = Field(default_factory=list)


class PortalDecisionIn(BaseModel):
    decision: Literal["shortlisted", "rejected", "propose_slot"]
    reject_reason: str | None = None
    proposed_slot: datetime | None = None
    notes: str | None = None
