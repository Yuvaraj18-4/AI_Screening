from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CriterionResultDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    criterion_id: int
    criterion_name: str
    kind: str
    must_have: bool
    weight: int
    verdict: str  # met, partial, not_found, unclear, unverified
    value: float
    quote: str | None = None
    quote_verified: bool
    confidence: float
    source: str


class ScoreDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scorecard_version: int
    total: float
    confidence: str
    status: str
    scoring_mode: str
    must_have_gaps: list[str] = Field(default_factory=list)
    results: list[CriterionResultDetail] = Field(default_factory=list)


class ApplicationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    requisition_id: int
    candidate_name: str
    candidate_email: str
    candidate_phone: str
    current_role: str
    location: str
    experience_years: float
    notice_days: int
    stage: str
    parse_quality: float
    duplicate_of_id: int | None = None
    has_viewed: bool = False
    score: ScoreDetail | None = None
    created_at: datetime


class ApplicationDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    requisition_id: int
    requisition_title: str
    client_name: str
    candidate_name: str
    candidate_email: str
    candidate_phone: str
    current_role: str
    location: str
    skills: list[str]
    employment: list[dict[str, Any]]
    experience_years: float
    notice_days: int
    current_ctc: str
    expected_ctc: str
    education: list[dict[str, Any]]
    parse_quality: float
    duplicate_of_id: int | None = None
    stage: str
    cv_text: str = ""
    masked_text: str = ""
    has_viewed: bool = True
    score: ScoreDetail | None = None
    created_at: datetime


class StageUpdateRequest(BaseModel):
    stage: str = Field(
        ...,
        pattern="^(sourced|screened|submitted|client_shortlisted|interview|offered|joined|rejected)$",
    )
    note: str | None = None


class DuplicateResolutionRequest(BaseModel):
    action: str = Field(..., pattern="^(merge|keep)$")
