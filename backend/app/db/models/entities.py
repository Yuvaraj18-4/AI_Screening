from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # "recruiter" | "client"
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )

    client: Mapped["Client | None"] = relationship(back_populates="users", lazy="raise_on_sql")


class Client(Base):
    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="client", lazy="raise_on_sql")
    requisitions: Mapped[list["Requisition"]] = relationship(back_populates="client", lazy="raise_on_sql")


class Requisition(Base):
    __tablename__ = "requisitions"

    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    jd_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft"
    )  # draft, active, closed
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    client: Mapped["Client"] = relationship(back_populates="requisitions", lazy="raise_on_sql")
    owner: Mapped["User"] = relationship(lazy="raise_on_sql")
    scorecards: Mapped[list["Scorecard"]] = relationship(
        back_populates="requisition", cascade="all, delete-orphan", lazy="raise_on_sql"
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="requisition", cascade="all, delete-orphan", lazy="raise_on_sql"
    )


class Scorecard(Base):
    __tablename__ = "scorecards"

    requisition_id: Mapped[int] = mapped_column(
        ForeignKey("requisitions.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    requisition: Mapped["Requisition"] = relationship(back_populates="scorecards", lazy="raise_on_sql")
    criteria: Mapped[list["Criterion"]] = relationship(
        back_populates="scorecard", cascade="all, delete-orphan", lazy="raise_on_sql"
    )

    __table_args__ = (
        UniqueConstraint("requisition_id", "version", name="uq_scorecard_req_version"),
    )


class Criterion(Base):
    __tablename__ = "criteria"

    scorecard_id: Mapped[int] = mapped_column(
        ForeignKey("scorecards.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # experience, notice, location, skill, domain
    must_have: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    scorecard: Mapped["Scorecard"] = relationship(back_populates="criteria", lazy="raise_on_sql")


class Candidate(Base):
    __tablename__ = "candidates"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(100), index=True, nullable=False, default="")
    location: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    current_role: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    employment: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    experience_years: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    notice_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_ctc: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    expected_ctc: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    education: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    parse_quality: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active"
    )  # active, deleted
    duplicate_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True
    )

    cv_files: Mapped[list["CVFile"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", lazy="raise_on_sql"
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", lazy="raise_on_sql"
    )
    consents: Mapped[list["Consent"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", lazy="raise_on_sql"
    )


class CVFile(Base):
    __tablename__ = "cv_files"

    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    masked_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    parse_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ok"
    )  # ok, needs_review, failed
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("upload_batches.id", ondelete="SET NULL"), nullable=True
    )

    candidate: Mapped["Candidate"] = relationship(back_populates="cv_files", lazy="raise_on_sql")


class Consent(Base):
    __tablename__ = "consents"

    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    given_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    candidate: Mapped["Candidate"] = relationship(back_populates="consents", lazy="raise_on_sql")


class Application(Base):
    __tablename__ = "applications"

    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    requisition_id: Mapped[int] = mapped_column(
        ForeignKey("requisitions.id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="sourced",
    )  # sourced, screened, submitted, client_shortlisted, interview, offered, joined, rejected

    candidate: Mapped["Candidate"] = relationship(back_populates="applications", lazy="raise_on_sql")
    requisition: Mapped["Requisition"] = relationship(back_populates="applications", lazy="raise_on_sql")
    scores: Mapped[list["Score"]] = relationship(
        back_populates="application", cascade="all, delete-orphan", lazy="raise_on_sql"
    )
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="application", cascade="all, delete-orphan", lazy="raise_on_sql"
    )
    events: Mapped[list["PipelineEvent"]] = relationship(
        back_populates="application", cascade="all, delete-orphan", lazy="raise_on_sql"
    )

    __table_args__ = (
        UniqueConstraint("candidate_id", "requisition_id", name="uq_app_candidate_requisition"),
        Index("ix_app_req_stage", "requisition_id", "stage"),
    )


class Score(Base):
    __tablename__ = "scores"

    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scorecard_version: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[str] = mapped_column(
        String(50), nullable=False, default="high"
    )  # high, medium, low
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )  # scored, ai_failed, pending
    cache_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    scoring_mode: Mapped[str] = mapped_column(
        String(50), nullable=False, default="heuristic"
    )  # llm, heuristic

    application: Mapped["Application"] = relationship(back_populates="scores", lazy="raise_on_sql")
    criterion_results: Mapped[list["CriterionResult"]] = relationship(
        back_populates="score", cascade="all, delete-orphan", lazy="raise_on_sql"
    )


class CriterionResult(Base):
    __tablename__ = "criterion_results"

    score_id: Mapped[int] = mapped_column(
        ForeignKey("scores.id", ondelete="CASCADE"), nullable=False
    )
    criterion_id: Mapped[int] = mapped_column(
        ForeignKey("criteria.id", ondelete="CASCADE"), nullable=False
    )
    verdict: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # met, partial, not_found, unclear, unverified
    value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    quote_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # code, llm

    score: Mapped["Score"] = relationship(back_populates="criterion_results", lazy="raise_on_sql")
    criterion: Mapped["Criterion"] = relationship(lazy="joined")


class Submission(Base):
    __tablename__ = "submissions"

    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    submitted_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    client_decision: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )  # pending, shortlisted, rejected
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    proposed_slot: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    application: Mapped["Application"] = relationship(back_populates="submissions", lazy="raise_on_sql")


class PipelineEvent(Base):
    __tablename__ = "pipeline_events"

    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    from_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    to_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    application: Mapped["Application"] = relationship(back_populates="events", lazy="raise_on_sql")


class ViewLog(Base):
    __tablename__ = "view_logs"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    application_id: Mapped[int | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), nullable=True
    )
    context: Mapped[str] = mapped_column(
        String(100), nullable=False, default="detail"
    )  # detail, portal, resume


class UploadBatch(Base):
    __tablename__ = "upload_batches"

    requisition_id: Mapped[int] = mapped_column(
        ForeignKey("requisitions.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Job(Base):
    __tablename__ = "jobs"

    type: Mapped[str] = mapped_column(String(50), nullable=False)  # parse_cv, score_cv, extract_jd
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="queued"
    )  # queued, running, done, failed
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("upload_batches.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (Index("ix_job_status_next_run", "status", "next_run_at"),)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # never stores personal data, only hashes
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
