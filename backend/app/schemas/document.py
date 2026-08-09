from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    doc_type: str
    mime_type: str
    page_count: int
    status: str
    error_message: str | None
    created_at: datetime
    chunk_count: int = 0


class DocumentListOut(BaseModel):
    total: int
    items: list[DocumentOut]


class ChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    chunk_index: int
    page_number: int
    section: str
    content: str
    token_count: int
