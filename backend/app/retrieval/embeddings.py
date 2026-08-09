import hashlib
import logging
import threading
from abc import ABC, abstractmethod
from functools import lru_cache

import numpy as np

from app.core.config import settings
from app.retrieval.tokens import tokenize

logger = logging.getLogger(__name__)


class EmbeddingService(ABC):
    """Encodes text into dense vectors.

    Backends never import their heavy model at module load time; models load
    lazily on first embed so tests and lightweight deployments stay fast.
    """

    @property
    @abstractmethod
    def dim(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


class OllamaEmbeddingService(EmbeddingService):
    """Local embeddings served by Ollama at OLLAMA_BASE_URL."""

    def __init__(self) -> None:
        import httpx  # noqa: PLC0415

        self._client = httpx.Client(base_url=settings.OLLAMA_BASE_URL, timeout=120)
        self._model = settings.EMBEDDING_MODEL

    @property
    def dim(self) -> int:
        return settings.VECTOR_DIM

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.post("/api/embed", json={"model": self._model, "input": texts})
        response.raise_for_status()
        data = response.json()
        return [list(map(float, emb)) for emb in data["embeddings"]]


class SentenceTransformerService(EmbeddingService):
    """Local PyTorch embeddings via sentence-transformers (HF hub download on first use)."""

    def __init__(self) -> None:
        self._model = None
        self._model_name = settings.EMBEDDING_MODEL
        self._lock = threading.Lock()

    def _get_model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import SentenceTransformer  # noqa: PLC0415

                    logger.info("loading embedding model %s", self._model_name)
                    self._model = SentenceTransformer(self._model_name)
        return self._model

    @property
    def dim(self) -> int:
        return int(self._get_model().get_sentence_embedding_dimension())

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [v.tolist() for v in vectors]


class HashEmbeddingService(EmbeddingService):
    """Deterministic, network-free embedder for tests and offline development.

    NOT for production ranking quality; it only exercises retrieval plumbing.
    """

    @property
    def dim(self) -> int:
        return settings.VECTOR_DIM

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            vector = np.zeros(settings.VECTOR_DIM, dtype=np.float32)
            for token in tokenize(text):
                digest = hashlib.md5(token.encode("utf-8")).digest()
                index = int.from_bytes(digest[:4], "big") % settings.VECTOR_DIM
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vector[index] += sign
            norm = float(np.linalg.norm(vector))
            if norm > 0:
                vector = vector / norm
            out.append(vector.tolist())
        return out


@lru_cache
def get_embedding_service() -> EmbeddingService:
    backend = settings.EMBEDDING_BACKEND
    if backend == "ollama":
        logger.info("embedding backend: ollama (%s)", settings.EMBEDDING_MODEL)
        return OllamaEmbeddingService()
    if backend == "hash":
        logger.info("embedding backend: hash (dim=%d)", settings.VECTOR_DIM)
        return HashEmbeddingService()
    logger.info("embedding backend: sentence_transformers (%s)", settings.EMBEDDING_MODEL)
    return SentenceTransformerService()
