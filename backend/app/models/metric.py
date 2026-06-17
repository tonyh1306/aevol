import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Float, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    experiment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, server_default="{}")
    computed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    task: Mapped["Task"] = relationship(  # type: ignore[name-defined]
        "Task", back_populates="metrics", foreign_keys=[task_id], lazy="noload"
    )
