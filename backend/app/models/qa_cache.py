import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def make_qa_cache_key(question: str, document_ids: list[str], doc_versions: str) -> str:
    raw = f"{question.strip().lower()}|{sorted(document_ids)}|{doc_versions}"
    return hashlib.sha256(raw.encode()).hexdigest()


class QACache(Base):
    __tablename__ = "qa_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cache_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    question: Mapped[str] = mapped_column(Text)
    document_ids: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    citations_json: Mapped[str] = mapped_column(Text, default="[]")
    context_json: Mapped[str] = mapped_column(Text, default="[]")
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_hit_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
