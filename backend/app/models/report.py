import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DueDiligenceReport(Base):
    __tablename__ = "dd_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_ids: Mapped[str] = mapped_column(Text)  # JSON array
    title: Mapped[str] = mapped_column(String(512), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    executive_summary: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[str] = mapped_column(Text, default="{}")  # JSON payload
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
