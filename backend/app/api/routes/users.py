from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import client_ip, require_roles
from app.core.security import hash_password
from app.db.session import get_db
from app.models import DueDiligenceReport, User
from app.schemas.user import UserCreate, UserList, UserOut, UserUpdate
from app.services.audit import log_audit

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserList)
def list_users(
    search: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin")),
) -> UserList:
    query = select(User)
    if search:
        term = f"%{search}%"
        query = query.where(or_(User.username.ilike(term), User.email.ilike(term)))
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    rows = db.execute(
        query.order_by(User.created_at.asc()).offset(skip).limit(limit)
    ).scalars().all()
    return UserList(total=total, items=list(rows))


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
) -> UserOut:
    existing = db.execute(
        select(User).where((User.username == body.username) | (User.email == body.email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that username or email already exists",
        )
    new_user = User(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    log_audit(
        action="user.create",
        user=user,
        resource_type="user",
        resource_id=new_user.id,
        details={"username": new_user.username, "role": new_user.role},
        ip_address=client_ip(request),
    )
    return new_user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    body: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
) -> UserOut:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    if user_id == user.id and body.is_active is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate yourself")

    changes: dict = {}
    if body.role is not None and body.role != target.role:
        target.role = body.role
        changes["role"] = target.role
    if body.is_active is not None and body.is_active != target.is_active:
        target.is_active = body.is_active
        changes["is_active"] = target.is_active
    if changes:
        db.commit()
        db.refresh(target)
        log_audit(
            action="user.update",
            user=user,
            resource_type="user",
            resource_id=target.id,
            details={"changes": changes},
            ip_address=client_ip(request),
        )
    return target


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
) -> None:
    if user_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete yourself")
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    deleted_reports = db.execute(
        select(func.count())
        .select_from(DueDiligenceReport)
        .where(DueDiligenceReport.created_by == user_id)
    ).scalar_one()
    db.execute(delete(DueDiligenceReport).where(DueDiligenceReport.created_by == user_id))
    db.delete(target)
    db.commit()
    log_audit(
        action="user.delete",
        user=user,
        resource_type="user",
        resource_id=user_id,
        details={
            "username": target.username,
            "deleted_reports": deleted_reports,
        },
        ip_address=client_ip(request),
    )
