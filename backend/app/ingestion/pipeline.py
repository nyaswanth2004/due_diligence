import logging
from pathlib import Path

from sqlalchemy import delete, select

from app.core.config import settings
from app.db.session import get_db_session
from app.ingestion.chunker import TextChunker
from app.ingestion.classifier import DocumentClassifier
from app.ingestion.extractors import (
    OcrExtractor,
    PdfExtractor,
    SpreadsheetExtractor,
)
from app.ingestion.extractors.base import BaseExtractor
from app.models import Document, DocumentChunk
from app.retrieval import get_retrieval_service
from app.services.storage import get_storage

logger = logging.getLogger(__name__)

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
_SPREADSHEET_EXTENSIONS = {".xlsx", ".xls", ".csv"}

_SCANNED_TEXT_THRESHOLD = 40


class IngestionPipeline:
    def __init__(self) -> None:
        self.storage = get_storage()
        self.classifier = DocumentClassifier()
        self.chunker = TextChunker()
        self._ocr: OcrExtractor | None = None

    @property
    def ocr(self) -> OcrExtractor:
        if self._ocr is None:
            self._ocr = OcrExtractor()
        return self._ocr

    def process(self, document_id: str) -> None:
        session = get_db_session()
        try:
            document = session.get(Document, document_id)
            if document is None:
                logger.warning("document %s not found", document_id)
                return

            document.status = "processing"
            session.commit()

            data = self.storage.load(document.storage_key)
            ext = Path(document.filename).suffix.lower()

            extractor = self._select_extractor(ext)
            result = extractor.extract(data, document.filename)

            if result.metadata.get("scanned") and not _has_text(result):
                logger.info("document %s is scanned; running OCR", document_id)
                result = self.ocr.extract(data, document.filename)

            sample_text = "\n".join(p.text for p in result.pages[:20])
            doc_type, confidence = self.classifier.classify(document.filename, sample_text)

            chunks = self.chunker.chunk_pages(result.pages, document_id)

            session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
            chunk_rows = [DocumentChunk(**chunk) for chunk in chunks]
            session.add_all(chunk_rows)

            document.doc_type = doc_type
            document.page_count = len(result.pages)
            document.status = "processing"
            document.error_message = None
            session.commit()

            try:
                get_retrieval_service().index_chunks(chunk_rows)
            except Exception as exc:
                logger.exception("indexing failed for document %s", document_id)
                document.status = "failed"
                document.error_message = f"indexing failed: {exc}"[:2000]
                session.commit()
                return

            document.status = "ready"
            session.commit()
            logger.info(
                "document %s ready: type=%s pages=%d chunks=%d (classifier=%.2f)",
                document_id, doc_type, len(result.pages), len(chunks), confidence,
            )
            try:
                from app.models.qa_cache import QACache  # noqa: PLC0415
                from app.db.session import SessionLocal  # noqa: PLC0415
                db = SessionLocal()
                try:
                    stale = db.query(QACache).filter(
                        QACache.document_ids.contains(document_id)
                    ).all()
                    for entry in stale:
                        db.delete(entry)
                    if stale:
                        db.commit()
                        logger.info("invalidated %d QA cache entries for document %s", len(stale), document_id)
                finally:
                    db.close()
            except Exception:
                pass
        except Exception as exc:
            session.rollback()
            logger.exception("ingestion failed for document %s", document_id)
            document = session.get(Document, document_id)
            if document is not None:
                document.status = "failed"
                document.error_message = str(exc)[:2000]
                session.commit()
        finally:
            session.close()

    def _select_extractor(self, ext: str) -> BaseExtractor:
        if ext == ".pdf":
            return PdfExtractor()
        if ext in _SPREADSHEET_EXTENSIONS:
            return SpreadsheetExtractor()
        if ext in _IMAGE_EXTENSIONS:
            return self.ocr
        raise ValueError(f"unsupported file extension: {ext}")


def _has_text(result) -> bool:
    return sum(len(p.text) for p in result.pages) >= _SCANNED_TEXT_THRESHOLD


def reconcile_index() -> dict:
    """Repair index state after crashes or interrupts, on startup.

    Two failure modes are repaired idempotently:

    * "ready" documents whose vector/keyword index entries don't match the
      database (an interrupt used to leave a document with chunks stored but
      no search index, so every QA would silently return "unanswerable").
    * "processing" documents orphaned by a killed/hung ingest: recovered (re-
      embedded and marked ready) when chunks exist, else marked failed so the
      document doesn't sit in "processing" forever.
    """
    session = get_db_session()
    repaired = {"documents": 0, "chunks": 0, "keyword": 0, "recovered": 0, "failed": 0}
    try:
        retrieval = get_retrieval_service()
        for status in ("ready", "processing"):
            documents = session.execute(
                select(Document).where(Document.status == status)
            ).scalars().all()
            for document in documents:
                rows = session.execute(
                    select(DocumentChunk).where(DocumentChunk.document_id == document.id)
                ).scalars().all()
                if status == "processing":
                    if not rows:
                        logger.warning(
                            "document %s left in 'processing' without chunks; marking failed",
                            document.id,
                        )
                        document.status = "failed"
                        document.error_message = (
                            "processing was interrupted; re-upload the document"
                        )
                        session.commit()
                        repaired["failed"] += 1
                        continue
                    logger.info(
                        "recovering interrupted document %s (%d chunks)",
                        document.id, len(rows),
                    )
                    retrieval.index_chunks(list(rows))
                    document.status = "ready"
                    document.error_message = None
                    session.commit()
                    repaired["recovered"] += 1
                    repaired["chunks"] += len(rows)
                    continue
                if not rows:
                    continue
                indexed = retrieval.count_chunks(document.id)
                if indexed == len(rows):
                    keyword = retrieval.count_keyword_chunks(document.id)
                    if keyword == len(rows):
                        continue
                    logger.info(
                        "rebuilding keyword index for document %s (keyword=%d db=%d)",
                        document.id, keyword, len(rows),
                    )
                    retrieval.reindex_keyword(document.id, list(rows))
                    repaired["keyword"] += 1
                    continue
                logger.info(
                    "reindexing document %s (index=%d db=%d)",
                    document.id, indexed, len(rows),
                )
                retrieval.index_chunks(list(rows))
                repaired["documents"] += 1
                repaired["chunks"] += len(rows)
        return repaired
    finally:
        session.close()


def process_document(document_id: str) -> None:
    IngestionPipeline().process(document_id)


# Module-level singleton used by the API layer.
pipeline = IngestionPipeline()
