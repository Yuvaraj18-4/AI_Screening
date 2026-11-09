from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CriterionIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    kind: str = Field(..., pattern="^(experience|notice|location|skill|domain)$")
    must_have: bool = False
    weight: int = Field(default=1, ge=1, le=5)
    params: dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class CriterionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scorecard_id: int
    name: str
    kind: str
    must_have: bool
    weight: int
    params: dict[str, Any]
    description: str
    created_at: datetime


class ScorecardCreate(BaseModel):
    criteria: list[CriterionIn] = Field(..., min_length=1)


class ScorecardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requisition_id: int
    version: int
    is_active: bool
    criteria: list[CriterionOut]
    created_at: datetime


class JDExtractResponse(BaseModel):
    title: str
    criteria: list[CriterionIn]
