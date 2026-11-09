from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserLogin(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: str
    client_id: int | None = None
    created_at: datetime


class HealthOut(BaseModel):
    status: str
    database: str
    scoring_mode: str
    worker_status: str = "running"
