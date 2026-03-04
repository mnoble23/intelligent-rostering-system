from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
import os

from app.api.auth import get_current_user, require_manager
from app.auth_utils import hash_password
from app.db.session import get_db
from app.models.availability_db import AvailabilityDB
from app.models.shift_assignment_db import ShiftAssignmentDB
from app.models.user_db import UserDB
from app.schemas.user import UserCreate, UserRead

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/")
def get_users(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    if current_user.role != "manager":
        return [
            {
                "id": current_user.id,
                "name": current_user.name,
                "role": current_user.role,
                "min_hours": current_user.min_hours,
                "max_hours": current_user.max_hours,
                "min_shifts_per_week": current_user.min_shifts_per_week,
                "max_shifts_per_week": current_user.max_shifts_per_week,
                "is_active": current_user.is_active,
            }
        ]

    users = db.query(UserDB).filter_by(workplace_id=current_user.workplace_id).all()
    return [
        {
            "id": user.id,
            "name": user.name,
            "role": user.role,
            "min_hours": user.min_hours,
            "max_hours": user.max_hours,
            "min_shifts_per_week": user.min_shifts_per_week,
            "max_shifts_per_week": user.max_shifts_per_week,
            "is_active": user.is_active,
        }
        for user in users
    ]


@router.post("/", response_model=UserRead)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(require_manager),
):
    normalized_name = user.name.strip()
    normalized_role = user.role.strip().lower()
    raw_password = (user.password or "").strip()
    default_password = os.getenv("DEFAULT_USER_PASSWORD", "ChangeMe123!")

    if not normalized_name:
        raise HTTPException(status_code=400, detail="Name is required")
    if normalized_role not in {"manager", "staff"}:
        raise HTTPException(status_code=400, detail="role must be 'manager' or 'staff'")
    if user.max_hours < user.min_hours:
        raise HTTPException(status_code=400, detail="max_hours must be greater than or equal to min_hours")
    if user.max_shifts_per_week < user.min_shifts_per_week:
        raise HTTPException(
            status_code=400,
            detail="max_shifts_per_week must be greater than or equal to min_shifts_per_week",
        )
    if raw_password and len(raw_password) < 8:
        raise HTTPException(status_code=400, detail="password must be at least 8 characters")

    existing_user = (
        db.query(UserDB)
        .filter(
            func.lower(UserDB.name) == normalized_name.lower(),
            UserDB.workplace_id == current_user.workplace_id,
        )
        .first()
    )
    if existing_user:
        existing_user.role = normalized_role
        existing_user.min_hours = user.min_hours
        existing_user.max_hours = user.max_hours
        existing_user.min_shifts_per_week = user.min_shifts_per_week
        existing_user.max_shifts_per_week = user.max_shifts_per_week
        existing_user.is_active = True
        if raw_password:
            existing_user.password_hash = hash_password(raw_password)
        db.commit()
        db.refresh(existing_user)
        return existing_user

    password_to_store = raw_password or default_password
    db_user = UserDB(
        name=normalized_name,
        role=normalized_role,
        min_hours=user.min_hours,
        max_hours=user.max_hours,
        min_shifts_per_week=user.min_shifts_per_week,
        max_shifts_per_week=user.max_shifts_per_week,
        password_hash=hash_password(password_to_store),
        is_active=True,
        workplace_id=current_user.workplace_id,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(require_manager),
):
    user = db.query(UserDB).filter_by(id=user_id, workplace_id=current_user.workplace_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    deleted_availability = (
        db.query(AvailabilityDB)
        .filter_by(user_id=user_id, workplace_id=current_user.workplace_id)
        .delete(synchronize_session=False)
    )
    deleted_assignments = (
        db.query(ShiftAssignmentDB)
        .filter_by(user_id=user_id, workplace_id=current_user.workplace_id)
        .delete(synchronize_session=False)
    )
    db.delete(user)
    db.commit()

    return {
        "status": "user deleted",
        "deleted_user_id": user_id,
        "deleted_assignments": deleted_assignments,
        "deleted_availability": deleted_availability,
    }
