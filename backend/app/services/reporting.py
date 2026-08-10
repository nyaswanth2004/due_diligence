"""Due diligence report generation and persistence."""

from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis import DueDiligenceOrchestrator
from app.llm import get_llm_client
from app.models import Document, DocumentChunk, DueDiligenceReport

logger = logging.getLogger(__name__)


class ReportingService:
    """Runs the multi-agent workflow and persists the resulting report."""

    def __init__(self, db: Session, orchestrator: DueDiligenceOrchestrator | None = None):
        self._db = db
        self._orchestrator = orchestrator or DueDiligenceOrchestrator(llm=get_llm_client())

    def generate(self, document_ids: list[str], created_by: str | None = None) -> dict:
        documents = self._load_documents(document_ids)
        if not documents:
            raise ValueError("No documents found for the requested report.")

        chunks = self._load_chunks(document_ids)
        result = self._orchestrator.run(documents, chunks)
        report = result.report_data
        if report is None:
            raise RuntimeError("Report agent produced no output.")

        payload = {
            "title": report.title,
            "generated_on": report.generated_on,
            "document_count": report.document_count,
            "summary": report.summary,
            "executive_summary": report.executive_summary,
            "sections": report.sections,
            "source_chunk_ids": report.source_chunk_ids,
            "financial_metrics": self._financial_summary(result),
        }
        self._persist(document_ids, payload, created_by=created_by)
        return payload

    def delete(self, report_id: str) -> bool:
        """Delete a report by id; returns False when it does not exist."""
        row = self._db.get(DueDiligenceReport, report_id)
        if row is None:
            return False
        self._db.delete(row)
        self._db.commit()
        return True

    def list(self, limit: int = 20, skip: int = 0) -> list[dict]:
        rows = self._db.execute(
            select(DueDiligenceReport)
            .order_by(DueDiligenceReport.created_at.desc())
            .offset(skip)
            .limit(limit)
        ).scalars().all()
        return [self._serialize(row) for row in rows]

    def get(self, report_id: str) -> dict | None:
        row = self._db.get(DueDiligenceReport, report_id)
        return self._serialize(row) if row else None

    def _load_documents(self, document_ids: list[str]) -> list[Document]:
        if not document_ids:
            return []
        return list(self._db.execute(
            select(Document).where(Document.id.in_(document_ids))
        ).scalars().all())

    def _load_chunks(self, document_ids: list[str]) -> list[DocumentChunk]:
        if not document_ids:
            return []
        return list(self._db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id.in_(document_ids))
            .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
        ).scalars().all())

    def _persist(
        self, document_ids: list[str], payload: dict, created_by: str | None = None
    ) -> DueDiligenceReport:
        row = DueDiligenceReport(
            document_ids=json.dumps(document_ids),
            title=payload["title"],
            summary=payload["summary"],
            executive_summary=payload["executive_summary"],
            data=json.dumps(payload),
            created_by=created_by,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    @staticmethod
    def _financial_summary(result) -> dict:
        metrics: dict[str, dict] = {}
        for metric, entries in result.financials.items.items():
            item = entries[0]
            metrics[metric] = {
                "label": item.label,
                "value": item.value,
                "prior_value": item.prior_value,
                "document_id": item.document_id,
                "filename": item.filename,
                "page": item.page,
                "chunk_id": item.chunk_id,
            }
        return metrics

    @staticmethod
    def _serialize(row: DueDiligenceReport) -> dict:
        return {
            "id": row.id,
            "document_ids": json.loads(row.document_ids),
            "title": row.title,
            "summary": row.summary,
            "executive_summary": row.executive_summary,
            "data": json.loads(row.data),
            "created_by": row.created_by,
            "created_at": row.created_at.isoformat(),
        }
