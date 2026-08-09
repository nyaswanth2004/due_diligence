from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import client_ip, require_roles
from app.llm import LLMUnavailableError
from app.models import User
from app.qa import get_qa_service
from app.schemas.qa import QAResponse, QARequest
from app.services.audit import log_audit

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("", response_model=QAResponse)
def ask(
    request: Request,
    body: QARequest,
    user: User = Depends(require_roles("admin", "analyst", "viewer")),
) -> QAResponse:
    service = get_qa_service()
    try:
        response = service.answer(
            body.question,
            top_k=body.top_k,
            document_ids=body.document_ids,
            history=body.history or None,
        )
    except LLMUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    log_audit(
        action="qa.ask",
        user=user,
        resource_type="qa",
        details={
            "question": body.question,
            "top_k": body.top_k,
            "document_ids": body.document_ids,
            "unanswerable": response.unanswerable,
        },
        ip_address=client_ip(request),
    )
    return response
