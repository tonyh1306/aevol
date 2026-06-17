import uuid
from datetime import datetime

from sqlalchemy import Float, Integer, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    pid: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="idle")
    current_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tasks_completed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    tasks_failed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_heartbeat: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    registered_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    cpu_percent: Mapped[float | None] = mapped_column(Float)
    memory_mb: Mapped[int | None] = mapped_column(Integer)
    capabilities: Mapped[list[str]] = mapped_column(ARRAY(String), server_default="{}")
