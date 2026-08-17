from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import client_ip, require_roles
from app.core.ratelimit import check_rate_limit, get_rate_limit_headers
from app.llm import LLMUnavailableError
from app.models import User
from app.qa import get_qa_service
from app.schemas.qa import QAResponse, QARequest
from app.services.audit import log_audit

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("", response_model=QAResponse)
def ask(
    request: Request,
    response: Response,
    body: QARequest,
    user: User = Depends(require_roles("admin", "analyst", "viewer")),
) -> QAResponse:
    remaining = check_rate_limit(str(user.id))
    for k, v in get_rate_limit_headers(str(user.id)).items():
        response.headers[k] = v

    service = get_qa_service()
    try:
        resp = service.answer(
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
            "unanswerable": resp.unanswerable,
        },
        ip_address=client_ip(request),
    )
    return resp
