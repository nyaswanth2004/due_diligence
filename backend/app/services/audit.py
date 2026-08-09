"""Cross-cutting audit logging. Uses its own short-lived session so logging
never disturbs the request's transaction, and never fails the request."""

import json
import logging
from typing import Any

from app.db import session as db_session
from app.models import AuditLog, User

logger = logging.getLogger(__name__)


def log_audit(
    *,
    action: str,
    user: User | None,
    resource_type: str = "",
    resource_id: str = "",
    details: dict[str, Any] | None = None,
    ip_address: str = "",
) -> None:
    try:
        with db_session.SessionLocal() as session:
            session.add(
                AuditLog(
                    user_id=user.id if user else None,
                    username=user.username if user else "",
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details=json.dumps(details or {}, default=str),
                    ip_address=ip_address,
                )
            )
            session.commit()
    except Exception:
        logger.exception("Failed to write audit log entry")
