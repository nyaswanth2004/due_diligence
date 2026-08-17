from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "VeritasIQ Due Diligence Copilot"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    DATABASE_URL: str = "sqlite:///./veritasiq.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    LOCAL_STORAGE_PATH: str = "storage/documents"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_DOCUMENTS: str = "documents"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    # Preferred way to configure the Ollama server URL (e.g. in Docker:
    # OLLAMA_HOST=http://ollama:11434). OLLAMA_BASE_URL remains a
    # backwards-compatible fallback for local development.
    OLLAMA_HOST: str | None = None
    LLM_MODEL: str = "qwen2.5:7b"

    # LLM backend: "ollama" (local), "groq" (cloud, free tier), or "fake" (tests).
    LLM_BACKEND: Literal["ollama", "groq", "fake"] = "ollama"
    LLM_TEMPERATURE: float = 0.1
    QA_MAX_HISTORY: int = 6

    # Groq cloud LLM (free tier: 30 req/min)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Ollama generation bounds: explicit context avoids silent truncation of
    # grounded prompts; num_predict caps answer length; keep_alive keeps the
    # model loaded between requests so users don't pay a reload stall.
    LLM_NUM_CTX: int = 8192
    LLM_NUM_PREDICT: int = 600
    OLLAMA_KEEP_ALIVE: str = "10m"

    # Due diligence report generation
    REPORT_NARRATIVE_ENABLED: bool = True
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"

    # Embeddings: "ollama" (local via Ollama API), "sentence_transformers"
    # (local PyTorch model), or "hash" (deterministic, for tests/offline dev).
    EMBEDDING_BACKEND: Literal["ollama", "sentence_transformers", "hash"] = "sentence_transformers"

    # Vector index: "pgvector" for production Postgres, "local" for dev (no Docker).
    VECTOR_STORE_BACKEND: Literal["pgvector", "local"] = "local"
    VECTOR_DIM: int = 384
    VECTOR_INDEX_PATH: str = "storage/vectors"

    # Retrieval tuning
    RETRIEVAL_TOP_K: int = 8
    RETRIEVAL_FUSION_K: int = 60
    KEYWORD_ENABLED: bool = True
    RERANKER_ENABLED: bool = True
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    CHUNK_SIZE: int = 1024
    CHUNK_OVERLAP: int = 128

    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = ".pdf,.png,.jpg,.jpeg,.xlsx,.xls,.csv"

    # OCR: "auto" prefers Tesseract when the binary is present, else RapidOCR.
    OCR_ENGINE: Literal["auto", "tesseract", "rapidocr"] = "auto"

    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    @property
    def database_sync_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("sqlite"):
            return url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def database_is_sqlite(self) -> bool:
        return self.database_sync_url.startswith("sqlite")

    @property
    def ollama_base_url(self) -> str:
        return self.OLLAMA_HOST or self.OLLAMA_BASE_URL


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
