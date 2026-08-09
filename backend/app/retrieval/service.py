import logging
from functools import lru_cache
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Document, DocumentChunk
from app.retrieval.embeddings import get_embedding_service
from app.retrieval.hybrid import reciprocal_rank_fusion
from app.retrieval.keyword_index import BM25KeywordIndex, KeywordIndex
from app.retrieval.reranker import NoopReranker, Reranker, get_reranker
from app.retrieval.vector_index import VectorIndex, get_vector_index
from app.schemas.search import RetrievalHit

logger = logging.getLogger(__name__)


class RetrievalService:
    """Facade coordinating embeddings, vector + keyword indexes, fusion, reranking.

    `index_chunks` is idempotent per document, so reprocessing a document
    replaces its previous index entries.
    """

    def __init__(self) -> None:
        self._embeddings = get_embedding_service()
        self._vector: VectorIndex = get_vector_index()
        self._keyword: KeywordIndex | None = BM25KeywordIndex() if settings.KEYWORD_ENABLED else None
        self._reranker: Reranker = get_reranker()

    # ---- indexing --------------------------------------------------------

    def index_chunks(self, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            return
        document_id = chunks[0].document_id
        self.remove_document(document_id)

        vectors = self._embeddings.embed([chunk.content for chunk in chunks])
        self._vector.add(document_id, [(chunk.id, vector) for chunk, vector in zip(chunks, vectors)])
        if self._keyword is not None:
            self._keyword.add(
                document_id, [(chunk.id, chunk.content) for chunk in chunks]
            )

    def remove_document(self, document_id: str) -> None:
        self._vector.remove(document_id)
        if self._keyword is not None:
            self._keyword.remove(document_id)

    def count_chunks(self, document_id: str) -> int:
        """Number of chunks currently indexed for a document (0 if absent)."""
        return self._vector.count_chunks(document_id)

    def count_keyword_chunks(self, document_id: str) -> int:
        """Number of chunks in the BM25 keyword index for a document (0 if absent)."""
        if self._keyword is None:
            return 0
        return self._keyword.count_chunks(document_id)

    def reindex_keyword(self, document_id: str, chunks: list[DocumentChunk]) -> None:
        """Rebuild only the BM25 keyword leg for a document (no re-embedding).

        The keyword index is in-memory and is rebuilt on startup via
        `reconcile_index`; this keeps it consistent without touching the
        persisted vector embeddings.
        """
        if self._keyword is None or not chunks:
            return
        self._keyword.add(
            document_id, [(chunk.id, chunk.content) for chunk in chunks]
        )

    # ---- search ----------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int | None = None,
        document_ids: Iterable[str] | None = None,
        db: Session | None = None,
    ) -> list[RetrievalHit]:
        top_k = top_k or settings.RETRIEVAL_TOP_K

        query_vector = self._embeddings.embed_one(query)
        vector_hits = self._vector.search(query_vector, top_k, document_ids=document_ids)

        rankings: list[list[str]] = [[chunk_id for chunk_id, _ in vector_hits]]
        if self._keyword is not None:
            keyword_hits = self._keyword.search(query, top_k, document_ids=document_ids)
            rankings.append([chunk_id for chunk_id, _ in keyword_hits])

        fused = reciprocal_rank_fusion(rankings, k=settings.RETRIEVAL_FUSION_K)
        ordered = [chunk_id for chunk_id, _ in sorted(fused.items(), key=lambda pair: -pair[1])]
        if not ordered:
            return []

        candidates = ordered[: max(top_k * 2, 16)]
        loaded = self._load_candidates(candidates, db)

        if isinstance(self._reranker, NoopReranker):
            final = candidates[:top_k]
            scores = fused
        else:
            pairs = [
                (chunk_id, item.chunk.content)
                for chunk_id, item in loaded.items()
                if chunk_id in loaded
            ]
            reranked = self._reranker.rerank(query, pairs)
            final = [chunk_id for chunk_id, _ in reranked][:top_k]
            scores = {chunk_id: score for chunk_id, score in reranked}

        hits: list[RetrievalHit] = []
        for chunk_id in final:
            item = loaded.get(chunk_id)
            if item is None:
                continue
            hits.append(self._to_hit(item, scores.get(chunk_id, 0.0)))
        return hits

    def statistics(self) -> dict:
        stats = {
            "backend": settings.VECTOR_STORE_BACKEND,
            "embeddings": settings.EMBEDDING_BACKEND,
        }
        stats.update(self._vector.statistics())
        if self._keyword is not None:
            stats["keyword"] = self._keyword.statistics()
        return stats

    # ---- internals -------------------------------------------------------

    @classmethod
    def _load_candidates(
        cls, chunk_ids: list[str], db: Session | None
    ) -> dict[str, "_Candidate"]:
        if db is None:
            from app.db.session import get_db_session  # noqa: PLC0415

            session = get_db_session()
            try:
                return cls._query_candidates(chunk_ids, session)
            finally:
                session.close()
        return cls._query_candidates(chunk_ids, db)

    @staticmethod
    def _query_candidates(chunk_ids: list[str], session: Session) -> dict[str, "_Candidate"]:
        rows = session.execute(
            select(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.id.in_(chunk_ids))
        ).all()
        return {chunk.id: _Candidate(chunk=chunk, document=document) for chunk, document in rows}

    @staticmethod
    def _to_hit(item: "_Candidate", score: float) -> RetrievalHit:
        chunk = item.chunk
        return RetrievalHit(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            filename=item.document.filename if item.document else "",
            doc_type=item.document.doc_type if item.document else "",
            page_number=chunk.page_number,
            section=chunk.section,
            content=chunk.content,
            score=score,
        )


class _Candidate:
    __slots__ = ("chunk", "document")

    def __init__(self, chunk: DocumentChunk, document: Document | None) -> None:
        self.chunk = chunk
        self.document = document


@lru_cache
def get_retrieval_service() -> RetrievalService:
    return RetrievalService()
