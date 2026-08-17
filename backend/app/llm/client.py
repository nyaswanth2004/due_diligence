import json
import logging
import re
from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import settings

logger = logging.getLogger(__name__)

_UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


class LLMUnavailableError(RuntimeError):
    """Raised when the configured LLM backend cannot be reached."""


class LLMClient(ABC):
    """Chat-completion client over a local open-source model."""

    @abstractmethod
    def generate(
        self,
        messages: list[dict],
        *,
        format: str | None = None,
        temperature: float = 0.1,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def health(self) -> bool:
        raise NotImplementedError

    def generate_text(self, prompt: str, *, max_tokens: int = 600) -> str:
        return self.generate(
            [{"role": "user", "content": prompt}],
            temperature=settings.LLM_TEMPERATURE,
        )


class OllamaClient(LLMClient):
    """Chat completions served by Ollama at OLLAMA_BASE_URL."""

    def __init__(self, base_url: str = "", model: str = "") -> None:
        import httpx  # noqa: PLC0415

        self._client = httpx.Client(
            base_url=base_url or settings.ollama_base_url, timeout=180
        )
        self._model = model or settings.LLM_MODEL

    def generate(
        self,
        messages: list[dict],
        *,
        format: str | None = None,
        temperature: float = 0.1,
    ) -> str:
        payload: dict = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "keep_alive": settings.OLLAMA_KEEP_ALIVE,
            "options": {
                "temperature": temperature,
                "num_ctx": settings.LLM_NUM_CTX,
                "num_predict": settings.LLM_NUM_PREDICT,
            },
        }
        if format:
            payload["format"] = format
        try:
            response = self._client.post("/api/chat", json=payload)
            response.raise_for_status()
        except Exception as exc:
            raise LLMUnavailableError(
                f"Ollama at {settings.ollama_base_url} is unavailable ({exc}). "
                "Start it with `docker compose up ollama` or `ollama serve`."
            ) from exc
        return response.json()["message"]["content"]

    def health(self) -> bool:
        try:
            response = self._client.get("/api/tags", timeout=3)
            return response.status_code == 200
        except Exception:
            return False


class FakeLLM(LLMClient):
    """Deterministic client for tests and offline development.

    Mimics a grounded model: extracts the chunk ids present in the context and
    returns a JSON answer citing the first two of them.
    """

    def generate(
        self,
        messages: list[dict],
        *,
        format: str | None = None,
        temperature: float = 0.1,
    ) -> str:
        last = messages[-1]["content"] if messages else ""
        chunk_ids = list(dict.fromkeys(_UUID_RE.findall(last)))
        citations = chunk_ids[:2]
        answer = (
            "Based on the provided excerpts, the relevant figures are supported by the cited documents."
            if citations
            else "The provided excerpts do not contain enough information to answer this question."
        )
        return json.dumps({"answer": answer, "citations": citations})

    def health(self) -> bool:
        return True

    def generate_text(self, prompt: str, *, max_tokens: int = 600) -> str:
        return "Deterministic narrative summary (fake backend)."


class GroqClient(LLMClient):
    """Chat completions via the Groq cloud API (OpenAI-compatible)."""

    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self) -> None:
        import httpx  # noqa: PLC0415

        self._client = httpx.Client(timeout=180)
        self._model = settings.GROQ_MODEL
        self._api_key = settings.GROQ_API_KEY

    def generate(
        self,
        messages: list[dict],
        *,
        format: str | None = None,
        temperature: float = 0.1,
    ) -> str:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": settings.LLM_NUM_PREDICT,
        }
        if format == "json":
            payload["response_format"] = {"type": "json_object"}
        try:
            response = self._client.post(self.API_URL, json=payload, headers=headers)
            response.raise_for_status()
        except Exception as exc:
            raise LLMUnavailableError(
                f"Groq API is unavailable ({exc}). Check GROQ_API_KEY."
            ) from exc
        return response.json()["choices"][0]["message"]["content"]

    def health(self) -> bool:
        if not self._api_key:
            return False
        try:
            headers = {"Authorization": f"Bearer {self._api_key}"}
            response = self._client.get(
                "https://api.groq.com/openai/v1/models", headers=headers, timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False


@lru_cache
def get_llm_client() -> LLMClient:
    if settings.LLM_BACKEND == "fake":
        logger.info("LLM backend: fake (deterministic)")
        return FakeLLM()
    if settings.LLM_BACKEND == "groq":
        logger.info("LLM backend: groq (%s)", settings.GROQ_MODEL)
        return GroqClient()
    logger.info("LLM backend: ollama (%s)", settings.LLM_MODEL)
    return OllamaClient()
