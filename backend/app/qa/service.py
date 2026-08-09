import json
import logging
import re
from functools import lru_cache

from app.core.config import settings
from app.llm import LLMClient, LLMUnavailableError, get_llm_client
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
    """Grounded question answering with verified citations.

    Pipeline: retrieve evidence → prompt the LLM to answer strictly from that
    evidence → parse the structured response → verify every citation against
    the provided context → return answer + evidence + verification report.
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
        return QAResponse(
            answer=answer,
            context=context,
            citations=citations,
            dropped_citations=report.dropped,
            unanswerable=not citations,
        )

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
