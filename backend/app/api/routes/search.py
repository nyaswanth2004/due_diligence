from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import client_ip, require_roles
from app.db.session import get_db
from app.models import User
from app.retrieval import get_retrieval_service
from app.schemas.search import RetrievalHit, SearchStats
from app.services.audit import log_audit

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[RetrievalHit])
def search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500),
    top_k: int = Query(default=8, ge=1, le=50),
    document_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst", "viewer")),
) -> list[RetrievalHit]:
    service = get_retrieval_service()
    document_ids = {document_id} if document_id else None
    hits = service.search(q, top_k=top_k, document_ids=document_ids, db=db)
    log_audit(
        action="document.search",
        user=user,
        resource_type="search",
        details={"query": q, "top_k": top_k, "document_id": document_id},
        ip_address=client_ip(request),
    )
    return hits


@router.get("/stats", response_model=SearchStats)
def search_stats(
    user: User = Depends(require_roles("admin", "analyst", "viewer")),
) -> SearchStats:
    stats = get_retrieval_service().statistics()
    keyword = stats.pop("keyword", None)
    return SearchStats(
        backend=stats["backend"],
        embeddings=stats["embeddings"],
        documents=stats["documents"],
        chunks=stats["chunks"],
        keyword_documents=keyword["documents"] if keyword else None,
        keyword_chunks=keyword["chunks"] if keyword else None,
    )
