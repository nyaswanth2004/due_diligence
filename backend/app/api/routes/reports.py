from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import client_ip, require_roles
from app.db.session import get_db
from app.models import User
from app.services.audit import log_audit
from app.services.reporting import ReportingService

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportRequest(BaseModel):
    document_ids: list[str] = Field(..., min_length=1)


@router.post("/generate")
def generate_report(
    request: Request,
    body: ReportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
) -> dict:
    service = ReportingService(db)
    try:
        payload = service.generate(body.document_ids)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    log_audit(
        action="report.generate",
        user=user,
        resource_type="report",
        details={"document_ids": body.document_ids, "title": payload.get("title", "")},
        ip_address=client_ip(request),
    )
    return payload


@router.get("")
def list_reports(
    limit: int = 20,
    skip: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst", "viewer")),
) -> dict:
    service = ReportingService(db)
    return {"total": len(service.list(limit=limit, skip=skip)), "items": service.list(limit=limit, skip=skip)}


@router.get("/{report_id}")
def get_report(
    report_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst", "viewer")),
) -> dict:
    service = ReportingService(db)
    report = service.get(report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="report not found")
    return report
