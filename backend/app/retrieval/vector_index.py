import json
import threading
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import numpy as np

from app.core.config import settings


class VectorIndex(ABC):
    """Stores chunk embeddings and returns nearest neighbours.

    `add`/`remove` are idempotent per document so reprocessing is safe.
    """

    @abstractmethod
    def add(self, document_id: str, items: list[tuple[str, list[float]]]) -> None:
        raise NotImplementedError

    @abstractmethod
    def remove(self, document_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query_vector: list[float],
        top_k: int,
        document_ids: Iterable[str] | None = None,
    ) -> list[tuple[str, float]]:
        raise NotImplementedError

    @abstractmethod
    def count_chunks(self, document_id: str) -> int:
        """Number of chunks currently indexed for a document (0 if absent)."""
        raise NotImplementedError

    @abstractmethod
    def statistics(self) -> dict:
        raise NotImplementedError


def _normalize(vectors: np.ndarray) -> np.ndarray:
    vectors = vectors.astype(np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


class LocalVectorIndex(VectorIndex):
    """Brute-force cosine index persisted to disk as npy+json.

    Suitable for development and moderate corpora; swap to PgVectorIndex for
    production scale. All state is guarded by a re-entrant lock.
    """

    def __init__(self, path: str = "") -> None:
        self._path = Path(path or settings.VECTOR_INDEX_PATH)
        self._path.mkdir(parents=True, exist_ok=True)
        self._vectors: np.ndarray | None = None
        self._chunk_ids: list[str] = []
        self._doc_of: dict[str, str] = {}
        self._chunks_of: dict[str, list[str]] = {}
        self._lock = threading.RLock()
        self._load()

    # ---- persistence -----------------------------------------------------

    def _load(self) -> None:
        vectors_path = self._path / "vectors.npy"
        meta_path = self._path / "meta.json"
        if not (vectors_path.exists() and meta_path.exists()):
            return
        try:
            self._vectors = np.load(vectors_path)
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self._chunk_ids = list(meta["chunk_ids"])
            self._doc_of = dict(meta["doc_of"])
            self._chunks_of = {k: list(v) for k, v in meta["chunks_of"].items()}
        except Exception:
            self._vectors = None
            self._chunk_ids = []
            self._doc_of = {}
            self._chunks_of = {}

    def _save(self) -> None:
        tmp_vectors = self._path / "vectors.tmp.npy"
        np.save(tmp_vectors, self._vectors if self._vectors is not None else np.zeros((0, 0), dtype=np.float32))
        tmp_vectors.replace(self._path / "vectors.npy")

        meta = {
            "chunk_ids": self._chunk_ids,
            "doc_of": self._doc_of,
            "chunks_of": self._chunks_of,
        }
        tmp_meta = self._path / "meta.tmp.json"
        tmp_meta.write_text(json.dumps(meta), encoding="utf-8")
        tmp_meta.replace(self._path / "meta.json")

    # ---- interface -------------------------------------------------------

    def add(self, document_id: str, items: list[tuple[str, list[float]]]) -> None:
        if not items:
            return
        with self._lock:
            ids = [item[0] for item in items]
            incoming = _normalize(np.asarray([item[1] for item in items], dtype=np.float32))
            if self._vectors is None or self._vectors.shape[0] == 0:
                self._vectors = incoming
            else:
                if self._vectors.shape[1] != incoming.shape[1]:
                    raise ValueError(
                        f"embedding dimension mismatch: index={self._vectors.shape[1]} "
                        f"incoming={incoming.shape[1]}"
                    )
                self._vectors = np.concatenate([self._vectors, incoming], axis=0)
            self._chunk_ids.extend(ids)
            self._chunks_of.setdefault(document_id, []).extend(ids)
            for chunk_id in ids:
                self._doc_of[chunk_id] = document_id
            self._save()

    def remove(self, document_id: str) -> None:
        with self._lock:
            ids = set(self._chunks_of.pop(document_id, []))
            if not ids:
                return
            keep = [i for i, chunk_id in enumerate(self._chunk_ids) if chunk_id not in ids]
            self._chunk_ids = [self._chunk_ids[i] for i in keep]
            self._vectors = self._vectors[keep] if keep else None
            for chunk_id in ids:
                self._doc_of.pop(chunk_id, None)
            self._save()

    def search(
        self,
        query_vector: list[float],
        top_k: int,
        document_ids: Iterable[str] | None = None,
    ) -> list[tuple[str, float]]:
        query = np.asarray(query_vector, dtype=np.float32)
        query_norm = float(np.linalg.norm(query))
        if query_norm == 0:
            return []
        query = query / query_norm

        with self._lock:
            if self._vectors is None or len(self._vectors) == 0:
                return []
            if document_ids:
                allowed = set(document_ids)
                keep = [
                    i for i, chunk_id in enumerate(self._chunk_ids)
                    if self._doc_of.get(chunk_id) in allowed
                ]
                if not keep:
                    return []
                scores = self._vectors[keep] @ query
                order = np.argsort(-scores)
                results = [(self._chunk_ids[keep[i]], float(scores[i])) for i in order]
            else:
                scores = self._vectors @ query
                order = np.argsort(-scores)
                results = [(self._chunk_ids[i], float(scores[i])) for i in order]
            return results[:top_k]

    def statistics(self) -> dict:
        with self._lock:
            return {"documents": len(self._chunks_of), "chunks": len(self._chunk_ids)}

    def count_chunks(self, document_id: str) -> int:
        with self._lock:
            return len(self._chunks_of.get(document_id, []))


class PgVectorIndex(VectorIndex):
    """pgvector-backed index for production Postgres.

    Schema is created idempotently with raw DDL so it works alongside
    SQLAlchemy without coupling metadata to a non-default extension.
    """

    def __init__(self, dim: int | None = None) -> None:
        from sqlalchemy import text as sql_text  # noqa: PLC0415

        self._dim = dim or settings.VECTOR_DIM
        self._text = sql_text
        self._lock = threading.RLock()
        self._ensure_schema()

    def _engine(self):
        from app.db.session import engine  # noqa: PLC0415

        return engine

    def _ensure_schema(self) -> None:
        from sqlalchemy import text as sql_text  # noqa: PLC0415

        with self._engine().begin() as conn:
            conn.execute(sql_text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(
                sql_text(
                    "CREATE TABLE IF NOT EXISTS chunk_embeddings ("
                    " chunk_id VARCHAR(36) PRIMARY KEY,"
                    " document_id VARCHAR(36) NOT NULL,"
                    f" embedding vector({self._dim}))"
                )
            )
            conn.execute(
                sql_text(
                    "CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_doc"
                    " ON chunk_embeddings(document_id)"
                )
            )

    @staticmethod
    def _literal(vector: list[float]) -> str:
        return "[" + ",".join(repr(float(v)) for v in vector) + "]"

    def add(self, document_id: str, items: list[tuple[str, list[float]]]) -> None:
        if not items:
            return
        with self._lock:
            with self._engine().begin() as conn:
                conn.execute(
                    self._text("DELETE FROM chunk_embeddings WHERE document_id = :d"),
                    {"d": document_id},
                )
                conn.execute(
                    self._text(
                        "INSERT INTO chunk_embeddings (chunk_id, document_id, embedding)"
                        " VALUES (:c, :d, :e::vector)"
                    ),
                    [
                        {"c": chunk_id, "d": document_id, "e": self._literal(vector)}
                        for chunk_id, vector in items
                    ],
                )

    def remove(self, document_id: str) -> None:
        with self._lock:
            with self._engine().begin() as conn:
                conn.execute(
                    self._text("DELETE FROM chunk_embeddings WHERE document_id = :d"),
                    {"d": document_id},
                )

    def search(
        self,
        query_vector: list[float],
        top_k: int,
        document_ids: Iterable[str] | None = None,
    ) -> list[tuple[str, float]]:
        params: dict = {"q": self._literal(query_vector), "limit": top_k}
        where = ""
        if document_ids:
            allowed = list(document_ids)
            placeholders = ",".join(f":d{i}" for i in range(len(allowed)))
            where = f" AND document_id IN ({placeholders})"
            params.update({f"d{i}": d for i, d in enumerate(allowed)})

        statement = self._text(
            "SELECT chunk_id, 1 - (embedding <=> :q::vector) AS score"
            " FROM chunk_embeddings WHERE 1=1"
            f"{where}"
            " ORDER BY embedding <=> :q::vector"
            " LIMIT :limit"
        )
        with self._engine().connect() as conn:
            rows = conn.execute(statement, params).fetchall()
            return [(row[0], float(row[1])) for row in rows]

    def statistics(self) -> dict:
        from sqlalchemy import text as sql_text  # noqa: PLC0415

        with self._engine().connect() as conn:
            chunks = conn.execute(
                sql_text("SELECT count(*) FROM chunk_embeddings")
            ).scalar_one()
            documents = conn.execute(
                sql_text("SELECT count(DISTINCT document_id) FROM chunk_embeddings")
            ).scalar_one()
            return {"documents": documents, "chunks": chunks}

    def count_chunks(self, document_id: str) -> int:
        from sqlalchemy import text as sql_text  # noqa: PLC0415

        with self._engine().connect() as conn:
            return conn.execute(
                sql_text(
                    "SELECT count(*) FROM chunk_embeddings WHERE document_id = :d"
                ),
                {"d": document_id},
            ).scalar_one()


@lru_cache
def get_vector_index() -> VectorIndex:
    if settings.VECTOR_STORE_BACKEND == "pgvector":
        return PgVectorIndex()
    return LocalVectorIndex()
