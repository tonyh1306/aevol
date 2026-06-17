import uuid
from datetime import datetime

from sqlalchemy import Integer, String, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    model_name: Mapped[str | None] = mapped_column(String(255))
    prompt_template: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), server_default="{}")
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="draft")
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    total_tasks: Mapped[int] = mapped_column(Integer, server_default="0")
    completed_tasks: Mapped[int] = mapped_column(Integer, server_default="0")
    failed_tasks: Mapped[int] = mapped_column(Integer, server_default="0")

    dataset: Mapped["Dataset"] = relationship(  # type: ignore[name-defined]
        "Dataset", back_populates="experiments", foreign_keys=[dataset_id], lazy="noload"
    )
    tasks: Mapped[list["Task"]] = relationship(  # type: ignore[name-defined]
        "Task", back_populates="experiment", lazy="noload"
    )
    clusters: Mapped[list["FailureCluster"]] = relationship(  # type: ignore[name-defined]
        "FailureCluster", back_populates="experiment", lazy="noload"
    )
