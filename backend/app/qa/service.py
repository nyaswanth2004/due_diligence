import json
import logging
import re
from datetime import datetime, timezone
from functools import lru_cache

from app.core.config import settings
from app.db.session import SessionLocal
from app.llm import LLMClient, LLMUnavailableError, get_llm_client
from app.models.document import Document
from app.models.qa_cache import QACache, make_qa_cache_key
from app.qa.citation import CitationVerifier, VerificationReport
from app.qa.prompts import build_messages
from app.retrieval import RetrievalService, get_retrieval_service
from app.schemas.qa import EvidenceChunk, QAMessage, QAResponse

logger = logging.getLogger(__name__)

UNANSWERABLE_MESSAGE = (
    "I could not find relevant information in the uploaded documents "
    "to answer this question."
)


class QAService:
    """Grounded question answering with verified citations and answer caching.

    Pipeline: check cache → retrieve evidence → prompt LLM → verify citations
    → save to cache → return answer + evidence.

    Cache is auto-invalidated when documents are reprocessed (updated_at changes).
    """

    def __init__(
        self,
        llm: LLMClient | None = None,
        retrieval: RetrievalService | None = None,
        verifier: CitationVerifier | None = None,
    ) -> None:
        self._llm = llm or get_llm_client()
        self._retrieval = retrieval or get_retrieval_service()
        self._verifier = verifier or CitationVerifier()

    def answer(
        self,
        question: str,
        *,
        top_k: int | None = None,
        document_ids: list[str] | None = None,
        history: list[QAMessage] | None = None,
    ) -> QAResponse:
        doc_ids = sorted(document_ids) if document_ids else []

        cache_key, doc_versions = self._build_cache_key(question, doc_ids)
        cached = self._check_cache(cache_key)
        if cached:
            logger.info("QA cache HIT for question: %s", question[:60])
            return cached

        hits = self._retrieval.search(
            question,
            top_k=top_k,
            document_ids=document_ids,
        )
        context = [self._to_evidence(hit) for hit in hits]
        if not context:
            return QAResponse(
                answer=UNANSWERABLE_MESSAGE,
                context=[],
                citations=[],
                dropped_citations=[],
                unanswerable=True,
            )

        messages = build_messages(context, question, history)
        raw = self._llm.generate(
            messages,
            format="json",
            temperature=settings.LLM_TEMPERATURE,
        )
        parsed = parse_llm_json(raw)

        answer = str(parsed.get("answer", "")).strip() or UNANSWERABLE_MESSAGE
        report = self._verify_citations(parsed.get("citations", []), context)

        citation_map = {chunk.chunk_id: chunk for chunk in context}
        citations = [citation_map[cid] for cid in report.valid if cid in citation_map]
        response = QAResponse(
            answer=answer,
            context=context,
            citations=citations,
            dropped_citations=report.dropped,
            unanswerable=not citations,
        )

        self._save_cache(cache_key, question, doc_ids, doc_versions, response)
        return response

    def _build_cache_key(
        self, question: str, doc_ids: list[str]
    ) -> tuple[str, str]:
        versions = self._get_doc_versions(doc_ids)
        key = make_qa_cache_key(question, doc_ids, versions)
        return key, versions

    def _get_doc_versions(self, doc_ids: list[str]) -> str:
        if not doc_ids:
            return "all"
        db = SessionLocal()
        try:
            docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
            parts = [
                f"{d.id}:{d.updated_at.isoformat()}"
                for d in sorted(docs, key=lambda d: d.id)
            ]
            return "|".join(parts) if parts else "none"
        finally:
            db.close()

    def _check_cache(self, cache_key: str) -> QAResponse | None:
        db = SessionLocal()
        try:
            entry = db.query(QACache).filter(QACache.cache_key == cache_key).first()
            if not entry:
                return None
            entry.hit_count += 1
            entry.last_hit_at = datetime.now(timezone.utc)
            db.commit()
            citations = [
                EvidenceChunk(**c) for c in json.loads(entry.citations_json)
            ]
            context = [
                EvidenceChunk(**c) for c in json.loads(entry.context_json)
            ]
            return QAResponse(
                answer=entry.answer,
                context=context,
                citations=citations,
                dropped_citations=[],
                unanswerable=not citations,
            )
        except Exception:
            db.rollback()
            return None
        finally:
            db.close()

    def _save_cache(
        self,
        cache_key: str,
        question: str,
        doc_ids: list[str],
        doc_versions: str,
        response: QAResponse,
    ) -> None:
        db = SessionLocal()
        try:
            entry = db.query(QACache).filter(QACache.cache_key == cache_key).first()
            if entry:
                entry.answer = response.answer
                entry.citations_json = json.dumps(
                    [c.model_dump() for c in response.citations]
                )
                entry.context_json = json.dumps(
                    [c.model_dump() for c in response.context]
                )
            else:
                entry = QACache(
                    cache_key=cache_key,
                    question=question,
                    document_ids=json.dumps(doc_ids),
                    answer=response.answer,
                    citations_json=json.dumps(
                        [c.model_dump() for c in response.citations]
                    ),
                    context_json=json.dumps(
                        [c.model_dump() for c in response.context]
                    ),
                )
                db.add(entry)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def invalidate_document(self, document_id: str) -> int:
        """Remove all cache entries that reference this document."""
        db = SessionLocal()
        try:
            entries = db.query(QACache).all()
            removed = 0
            for entry in entries:
                ids = json.loads(entry.document_ids)
                if not ids or document_id in ids:
                    db.delete(entry)
                    removed += 1
            db.commit()
            return removed
        finally:
            db.close()

    def _verify_citations(
        self, cited_ids: list, context: list[EvidenceChunk]
    ) -> VerificationReport:
        allowed = {chunk.chunk_id for chunk in context}
        return self._verifier.verify(cited_ids, allowed)

    @staticmethod
    def _to_evidence(hit) -> EvidenceChunk:
        return EvidenceChunk(
            chunk_id=hit.chunk_id,
            document_id=hit.document_id,
            filename=hit.filename,
            doc_type=hit.doc_type,
            page_number=hit.page_number,
            section=hit.section,
            content=hit.content,
            score=hit.score,
        )


def parse_llm_json(raw: str) -> dict:
    """Parse a JSON object from an LLM response, tolerating markdown fences."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            logger.warning("LLM returned non-JSON output: %s", text[:200])
            return {}
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            logger.warning("LLM returned unparsable JSON: %s", text[:200])
            return {}
    if not isinstance(data, dict):
        return {}
    return data


@lru_cache
def get_qa_service() -> QAService:
    return QAService()
