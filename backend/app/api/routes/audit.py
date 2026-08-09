import json

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import AuditLog, User

router = APIRouter(prefix="/audit", tags=["audit"])


def _serialize(row: AuditLog) -> dict:
    details = {}
    if row.details:
        try:
            details = json.loads(row.details)
        except json.JSONDecodeError:
            details = {"raw": row.details}
    return {
        "id": row.id,
        "user_id": row.user_id,
        "username": row.username,
        "action": row.action,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "details": details,
        "ip_address": row.ip_address,
        "created_at": row.created_at.isoformat(),
    }


@router.get("")
def list_audit_logs(
    action: str | None = None,
    username: str | None = None,
    limit: int = 100,
    skip: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
) -> dict:
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    if username:
        query = query.where(AuditLog.username == username)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    rows = db.execute(
        query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    ).scalars().all()
    return {
        "total": total,
        "items": [_serialize(row) for row in rows],
    }
