"""Authentication and role-based access control dependencies."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import TokenError, decode_access_token
from app.db.session import get_db
from app.models import User

_bearer = HTTPBearer(auto_error=False)

ROLES = ("admin", "analyst", "viewer")
ROLE_LABELS = {"admin": "Administrator", "analyst": "Analyst", "viewer": "Viewer"}


def _credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise _credentials_error()
    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise _credentials_error() from exc
    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise _credentials_error()
    return user


def require_roles(*roles: str):
    allowed = set(roles)
    if not allowed <= set(ROLES):
        raise ValueError(f"unknown role(s): {allowed - set(ROLES)}")

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(sorted(allowed))}",
            )
        return user

    return checker


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""
