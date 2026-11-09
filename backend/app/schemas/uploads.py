from pydantic import BaseModel


class BatchFileProgress(BaseModel):
    id: int
    filename: str
    size: int
    candidate_id: int
    candidate_name: str
    parse_status: str  # ok, needs_review, failed
    parse_error: str | None = None
    is_duplicate: bool = False


class BatchProgressOut(BaseModel):
    batch_id: int
    total: int
    queued: int
    running: int
    done: int
    failed: int
    files: list[BatchFileProgress]


class UploadResponse(BaseModel):
    batch_id: int
    total: int
    message: str
