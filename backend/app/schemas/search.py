from pydantic import BaseModel, ConfigDict


class RetrievalHit(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: str
    document_id: str
    filename: str
    doc_type: str
    page_number: int
    section: str
    content: str
    score: float


class SearchStats(BaseModel):
    backend: str
    embeddings: str
    documents: int
    chunks: int
    keyword_documents: int | None = None
    keyword_chunks: int | None = None
