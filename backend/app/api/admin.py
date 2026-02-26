import os
import secrets
from datetime import date, time, timedelta

from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth_utils import hash_password
from app.db.session import SessionLocal
from app.models.availability_db import AvailabilityDB
from app.models.shift_assignment_db import ShiftAssignmentDB
from app.models.shift_db import ShiftDB
from app.models.user_db import UserDB
from app.models.workplace_db import WorkplaceDB
from app.services.availability_loader import load_weekly_availability
from app.services.roster_generator import (
    assign_staff_to_shifts,
    generate_weekly_shifts,
    match_availability_to_shifts,
)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


def _week_start_for_today() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _create_demo_user(
    db: Session,
    workplace_id: int,
    name: str,
    role: str,
    password: str,
    min_hours: float,
    max_hours: float,
) -> UserDB:
    user = UserDB(
        name=name,
        role=role,
        min_hours=min_hours,
        max_hours=max_hours,
        password_hash=hash_password(password),
        is_active=True,
        workplace_id=workplace_id,
    )
    db.add(user)
    db.flush()
    return user


def _seed_full_week_availability(db: Session, workplace_id: int, user_ids: list[int]) -> None:
    for user_id in user_ids:
        for day_of_week in range(7):
            db.add(
                AvailabilityDB(
                    workplace_id=workplace_id,
                    user_id=user_id,
                    day_of_week=day_of_week,
                    start_time=time(hour=6),
                    end_time=time(hour=22),
                )
            )


def _reset_and_seed_demo(db: Session) -> dict:
    demo_workplace_name = os.getenv("DEMO_WORKPLACE_NAME", "Demo Company")
    manager_password = os.getenv("DEMO_MANAGER_PASSWORD", "Manager123!")
    staff_password = os.getenv("DEMO_STAFF_PASSWORD", "Staff123!")

    db.query(ShiftAssignmentDB).delete(synchronize_session=False)
    db.query(ShiftDB).delete(synchronize_session=False)
    db.query(AvailabilityDB).delete(synchronize_session=False)
    db.query(UserDB).delete(synchronize_session=False)
    db.query(WorkplaceDB).delete(synchronize_session=False)
    db.commit()

    workplace = WorkplaceDB(name=demo_workplace_name)
    db.add(workplace)
    db.flush()

    manager_primary = _create_demo_user(
        db=db,
        workplace_id=workplace.id,
        name="demo_manager",
        role="manager",
        password=manager_password,
        min_hours=20.0,
        max_hours=60.0,
    )
    manager_secondary = _create_demo_user(
        db=db,
        workplace_id=workplace.id,
        name="demo_manager_2",
        role="manager",
        password=manager_password,
        min_hours=20.0,
        max_hours=60.0,
    )

    staff_users = [
        _create_demo_user(
            db=db,
            workplace_id=workplace.id,
            name=f"demo_staff_{index}",
            role="staff",
            password=staff_password,
            min_hours=10.0,
            max_hours=40.0,
        )
        for index in range(1, 10)
    ]

    all_user_ids = [manager_primary.id, manager_secondary.id, *[user.id for user in staff_users]]
    _seed_full_week_availability(db, workplace.id, all_user_ids)
    db.commit()

    users = db.query(UserDB).filter_by(workplace_id=workplace.id).all()
    weekly_availability = load_weekly_availability(db, workplace.id)
    user_hour_limits = {user.id: (float(user.min_hours), float(user.max_hours)) for user in users}
    user_roles = {user.id: user.role for user in users}
    week_start = _week_start_for_today()
    weekly_shifts = generate_weekly_shifts(week_start)
    staffable = match_availability_to_shifts(weekly_availability, weekly_shifts)
    assign_staff_to_shifts(
        db=db,
        staffable_shifts=staffable,
        week_start_date=week_start,
        workplace_id=workplace.id,
        user_hour_limits=user_hour_limits,
        user_roles=user_roles,
    )

    return {
        "status": "demo reset complete",
        "workplace": demo_workplace_name,
        "week_start_date": week_start.isoformat(),
        "manager_usernames": ["demo_manager", "demo_manager_2"],
        "staff_usernames": [user.name for user in staff_users],
    }


@router.post("/reset-demo")
def reset_demo(x_reset_key: str | None = Header(default=None, alias="X-Reset-Key")):
    app_env = os.getenv("APP_ENV", "").strip().lower()
    if app_env != "demo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo reset is only allowed when APP_ENV=demo",
        )

    configured_key = os.getenv("DEMO_RESET_KEY", "")
    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DEMO_RESET_KEY is not configured",
        )

    if not x_reset_key or not secrets.compare_digest(x_reset_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid reset key",
        )

    db = SessionLocal()
    try:
        return _reset_and_seed_demo(db)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
