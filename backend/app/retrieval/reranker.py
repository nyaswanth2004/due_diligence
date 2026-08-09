import logging
import threading
from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import settings

logger = logging.getLogger(__name__)


class Reranker(ABC):
    """Cross-encoder reranker that scores (query, chunk) pairs."""

    @abstractmethod
    def rerank(self, query: str, candidates: list[tuple[str, str]]) -> list[tuple[str, float]]:
        """Return candidates re-ordered as (chunk_id, score), best first."""
        raise NotImplementedError


class CrossEncoderReranker(Reranker):
    """Local cross-encoder (HF hub download on first use)."""

    def __init__(self) -> None:
        self._model = None
        self._model_name = settings.RERANKER_MODEL
        self._lock = threading.Lock()

    def _get_model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import CrossEncoder  # noqa: PLC0415

                    logger.info("loading reranker model %s", self._model_name)
                    self._model = CrossEncoder(self._model_name)
        return self._model

    def rerank(self, query: str, candidates: list[tuple[str, str]]) -> list[tuple[str, float]]:
        if not candidates:
            return []
        model = self._get_model()
        scores = model.predict([(query, content) for _, content in candidates])
        ranked = sorted(zip([c[0] for c in candidates], scores), key=lambda pair: -pair[1])
        return [(chunk_id, float(score)) for chunk_id, score in ranked]


class NoopReranker(Reranker):
    """Passthrough used when RERANKER_ENABLED=false (tests/offline)."""

    def rerank(self, query: str, candidates: list[tuple[str, str]]) -> list[tuple[str, float]]:
        total = len(candidates)
        return [(chunk_id, 1.0 - index / max(total, 1)) for index, (chunk_id, _) in enumerate(candidates)]


@lru_cache
def get_reranker() -> Reranker:
    if settings.RERANKER_ENABLED:
        return CrossEncoderReranker()
    return NoopReranker()
