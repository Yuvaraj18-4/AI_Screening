from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RequisitionCreate(BaseModel):
    client_id: int
    title: str = Field(..., min_length=1, max_length=255)
    jd_text: str = ""


class RequisitionUpdate(BaseModel):
    title: str | None = None
    jd_text: str | None = None
    status: str | None = Field(default=None, pattern="^(draft|active|closed)$")


class RequisitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    title: str
    jd_text: str
    status: str
    owner_id: int
    client_name: str | None = None
    applications_count: int = 0
    active_scorecard_version: int | None = None
    created_at: datetime
