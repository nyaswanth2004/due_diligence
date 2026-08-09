from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import client_ip, require_roles
from app.db.session import get_db
from app.ingestion.pipeline import process_document
from app.models import Document, DocumentChunk, User
from app.retrieval import get_retrieval_service
from app.schemas.document import ChunkOut, DocumentListOut, DocumentOut
from app.services.audit import log_audit
from app.services.queue import get_task_queue
from app.services.storage import build_storage_key, get_storage

router = APIRouter(prefix="/documents", tags=["documents"])

_MAX_SIZE = 50 * 1024 * 1024
_ALLOWED = {".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".xls", ".csv"}


def _document_out(session: Session, document: Document) -> DocumentOut:
    chunk_count = session.execute(
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.document_id == document.id)
    ).scalar_one()
    out = DocumentOut.model_validate(document)
    out.chunk_count = chunk_count
    return out


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
) -> DocumentOut:
    ext = "." + (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in _ALLOWED:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"unsupported file type '{ext}'. Allowed: {sorted(_ALLOWED)}",
        )

    data = file.file.read()
    if len(data) > _MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="file exceeds 50 MB limit",
        )

    document = Document(
        filename=file.filename or "unnamed",
        storage_key="",
        mime_type=file.content_type or "",
        status="pending",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    document.storage_key = build_storage_key(document.filename, document.id)
    get_storage().save(document.storage_key, data)
    db.commit()

    get_task_queue().submit(process_document, document.id)
    log_audit(
        action="document.upload",
        user=user,
        resource_type="document",
        resource_id=document.id,
        details={"filename": document.filename, "size_bytes": len(data)},
        ip_address=client_ip(request),
    )
    return _document_out(db, document)


@router.get("", response_model=DocumentListOut)
def list_documents(
    skip: int = 0,
    limit: int = 50,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst", "viewer")),
) -> DocumentListOut:
    query = select(Document)
    if status_filter:
        query = query.where(Document.status == status_filter)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    docs = db.execute(query.order_by(Document.created_at.desc()).offset(skip).limit(limit)).scalars().all()
    return DocumentListOut(
        total=total,
        items=[_document_out(db, d) for d in docs],
    )


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst", "viewer")),
) -> DocumentOut:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    return _document_out(db, document)


@router.get("/{document_id}/chunks", response_model=list[ChunkOut])
def list_chunks(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst", "viewer")),
) -> list[ChunkOut]:
    if db.get(Document, document_id) is None:
        raise HTTPException(status_code=404, detail="document not found")
    chunks = db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    ).scalars().all()
    return list(chunks)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
) -> None:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    storage_key = document.storage_key
    filename = document.filename
    db.delete(document)
    db.execute(DocumentChunk.__table__.delete().where(DocumentChunk.document_id == document_id))
    db.commit()
    if storage_key:
        get_storage().delete(storage_key)
    get_retrieval_service().remove_document(document_id)
    log_audit(
        action="document.delete",
        user=user,
        resource_type="document",
        resource_id=document_id,
        details={"filename": filename},
        ip_address=client_ip(request),
    )
