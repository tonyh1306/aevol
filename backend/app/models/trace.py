from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Trace(Base):
    __tablename__ = "traces"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    input: Mapped[dict] = mapped_column(JSONB, nullable=False)
    expected: Mapped[dict | None] = mapped_column(JSONB)
    spans: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
