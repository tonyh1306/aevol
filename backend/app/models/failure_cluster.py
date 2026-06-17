import uuid
from datetime import datetime

from sqlalchemy import Integer, String, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FailureCluster(Base):
    __tablename__ = "failure_clusters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    cluster_label: Mapped[str] = mapped_column(String(255), nullable=False)
    error_pattern: Mapped[str] = mapped_column(Text, nullable=False)
    sample_errors: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    task_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    suggestion: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    experiment: Mapped["Experiment"] = relationship(  # type: ignore[name-defined]
        "Experiment", back_populates="clusters", foreign_keys=[experiment_id], lazy="noload"
    )
