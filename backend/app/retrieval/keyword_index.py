import threading
from abc import ABC, abstractmethod
from typing import Iterable

from rank_bm25 import BM25Okapi

from app.retrieval.tokens import tokenize


class KeywordIndex(ABC):
    """Lexical index (BM25) used as the keyword leg of hybrid retrieval."""

    @abstractmethod
    def add(self, document_id: str, items: list[tuple[str, str]]) -> None:
        raise NotImplementedError

    @abstractmethod
    def remove(self, document_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int,
        document_ids: Iterable[str] | None = None,
    ) -> list[tuple[str, float]]:
        raise NotImplementedError

    @abstractmethod
    def statistics(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def count_chunks(self, document_id: str) -> int:
        """Number of chunks currently keyword-indexed for a document (0 if absent)."""
        raise NotImplementedError


class BM25KeywordIndex(KeywordIndex):
    """BM25Okapi over tokenized chunk content.

    The index rebuilds after each mutation, which is cheap at moderate scale
    and keeps results consistent with the stored chunks at all times.
    """

    def __init__(self) -> None:
        self._chunk_ids: list[str] = []
        self._corpus: list[list[str]] = []
        self._doc_of: dict[str, str] = {}
        self._chunks_of: dict[str, list[str]] = {}
        self._bm25: BM25Okapi | None = None
        self._lock = threading.RLock()

    def _rebuild(self) -> None:
        self._bm25 = BM25Okapi(self._corpus) if self._corpus else None

    def add(self, document_id: str, items: list[tuple[str, str]]) -> None:
        if not items:
            return
        with self._lock:
            self._remove_locked(document_id)
            for chunk_id, content in items:
                self._chunk_ids.append(chunk_id)
                self._corpus.append(tokenize(content))
                self._doc_of[chunk_id] = document_id
                self._chunks_of.setdefault(document_id, []).append(chunk_id)
            self._rebuild()

    def remove(self, document_id: str) -> None:
        with self._lock:
            self._remove_locked(document_id)
            self._rebuild()

    def _remove_locked(self, document_id: str) -> None:
        ids = set(self._chunks_of.pop(document_id, []))
        if not ids:
            return
        keep = [i for i, chunk_id in enumerate(self._chunk_ids) if chunk_id not in ids]
        self._chunk_ids = [self._chunk_ids[i] for i in keep]
        self._corpus = [self._corpus[i] for i in keep]
        for chunk_id in ids:
            self._doc_of.pop(chunk_id, None)

    def search(
        self,
        query: str,
        top_k: int,
        document_ids: Iterable[str] | None = None,
    ) -> list[tuple[str, float]]:
        tokens = tokenize(query)
        if not tokens or self._bm25 is None or not self._chunk_ids:
            return []

        with self._lock:
            scores = self._bm25.get_scores(tokens)
            if document_ids:
                allowed = set(document_ids)
                order = [
                    i for i in range(len(self._chunk_ids))
                    if self._doc_of.get(self._chunk_ids[i]) in allowed
                ]
                order.sort(key=lambda i: -scores[i])
            else:
                order = sorted(range(len(scores)), key=lambda i: -scores[i])

            results: list[tuple[str, float]] = []
            for index in order:
                if scores[index] <= 0:
                    continue
                results.append((self._chunk_ids[index], float(scores[index])))
                if len(results) >= top_k:
                    break
            return results

    def statistics(self) -> dict:
        with self._lock:
            return {"documents": len(self._chunks_of), "chunks": len(self._chunk_ids)}

    def count_chunks(self, document_id: str) -> int:
        with self._lock:
            return len(self._chunks_of.get(document_id, []))
