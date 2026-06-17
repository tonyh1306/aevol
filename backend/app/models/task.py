import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Integer, Numeric, String, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dataset_row_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="PENDING")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")
    worker_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    enqueued_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    claimed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    output_data: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    error_type: Mapped[str | None] = mapped_column(String(255))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    config_override: Mapped[dict | None] = mapped_column(JSONB)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, server_default="{}")

    experiment: Mapped["Experiment"] = relationship(  # type: ignore[name-defined]
        "Experiment", back_populates="tasks", foreign_keys=[experiment_id], lazy="noload"
    )
    metrics: Mapped[list["Metric"]] = relationship(  # type: ignore[name-defined]
        "Metric", back_populates="task", lazy="noload"
    )
    traces: Mapped[list["AgentTrace"]] = relationship(  # type: ignore[name-defined]
        "AgentTrace", back_populates="task", lazy="noload"
    )
