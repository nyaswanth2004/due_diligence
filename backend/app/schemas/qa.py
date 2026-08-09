from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class QAMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class EvidenceChunk(BaseModel):
    """A retrieved chunk (the evidence shown to the LLM and the user)."""

    model_config = ConfigDict(from_attributes=True)

    chunk_id: str
    document_id: str
    filename: str
    doc_type: str
    page_number: int
    section: str
    content: str
    score: float


class QARequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=8, ge=1, le=50)
    document_ids: list[str] | None = None
    history: list[QAMessage] = []


class QAResponse(BaseModel):
    answer: str
    context: list[EvidenceChunk]
    citations: list[EvidenceChunk]
    dropped_citations: list[str]
    unanswerable: bool
