from datetime import datetime

from pydantic import BaseModel


class ConsentRecordIn(BaseModel):
    channel: str = "email"
    notes: str | None = None


class ConsentOut(BaseModel):
    candidate_id: str
    consent_status: str
    consented_at: datetime | None = None
    revoked_at: datetime | None = None
