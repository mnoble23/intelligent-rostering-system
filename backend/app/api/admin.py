import os
import secrets
from datetime import time

from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth_utils import hash_password
from app.db.session import SessionLocal
from app.models.availability_db import AvailabilityDB
from app.models.shift_assignment_db import ShiftAssignmentDB
from app.models.shift_db import ShiftDB
from app.models.user_db import UserDB
from app.models.workplace_db import WorkplaceDB

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


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


def _seed_realistic_demo_availability(db: Session, workplace_id: int, users: list[UserDB]) -> None:
    def hm(value: str) -> time:
        hour, minute = value.split(":")
        return time(hour=int(hour), minute=int(minute))

    def add_windows(user_id: int, windows: list[tuple[int, str, str]]) -> None:
        for day_of_week, start, end in windows:
            db.add(
                AvailabilityDB(
                    workplace_id=workplace_id,
                    user_id=user_id,
                    day_of_week=day_of_week,
                    start_time=hm(start),
                    end_time=hm(end),
                )
            )

    users_by_name = {user.name: user for user in users}

    schedule_by_name: dict[str, list[tuple[int, str, str]]] = {
        # Managers: fully available all week for robust manager coverage.
        "demo_manager": [(day, "06:00", "22:00") for day in range(7)],
        "demo_manager_2": [(day, "06:00", "22:00") for day in range(7)],
        "demo_manager_3": [(day, "06:00", "22:00") for day in range(7)],
        # Staff: realistic mixed patterns (early/mid/late + weekdays/weekends + part-time).
        "demo_staff_1": [
            (0, "06:00", "14:00"), (1, "06:00", "14:00"), (2, "06:00", "14:00"),
            (3, "06:00", "14:00"), (4, "06:00", "14:00"),
        ],
        "demo_staff_2": [
            (0, "07:00", "15:00"), (1, "07:00", "15:00"), (2, "07:00", "15:00"),
            (3, "07:00", "15:00"), (4, "07:00", "15:00"),
        ],
        "demo_staff_3": [
            (1, "08:00", "16:00"), (2, "08:00", "16:00"), (3, "08:00", "16:00"),
            (4, "08:00", "16:00"), (5, "08:00", "16:00"),
        ],
        "demo_staff_4": [
            (1, "10:00", "18:00"), (2, "10:00", "18:00"), (3, "10:00", "18:00"),
            (4, "10:00", "18:00"), (5, "10:00", "18:00"),
        ],
        "demo_staff_5": [
            (2, "12:00", "20:00"), (3, "12:00", "20:00"), (4, "12:00", "20:00"),
            (5, "12:00", "20:00"), (6, "12:00", "20:00"),
        ],
        "demo_staff_6": [
            (0, "14:00", "22:00"), (1, "14:00", "22:00"), (2, "14:00", "22:00"),
            (3, "14:00", "22:00"), (4, "14:00", "22:00"),
        ],
        "demo_staff_7": [
            (1, "13:00", "21:00"), (2, "13:00", "21:00"), (3, "13:00", "21:00"),
            (4, "13:00", "21:00"), (5, "13:00", "21:00"),
        ],
        "demo_staff_8": [
            (0, "16:00", "22:00"), (5, "06:00", "14:00"), (6, "06:00", "14:00"),
        ],
        "demo_staff_9": [
            (4, "12:00", "20:00"), (5, "14:00", "22:00"), (6, "14:00", "22:00"),
        ],
        "demo_staff_10": [
            (0, "09:00", "17:00"), (2, "09:00", "17:00"), (4, "09:00", "17:00"),
        ],
        "demo_staff_11": [
            (1, "09:00", "17:00"), (3, "09:00", "17:00"), (5, "09:00", "17:00"),
        ],
        "demo_staff_12": [
            (0, "11:00", "19:00"), (1, "11:00", "19:00"), (2, "11:00", "19:00"),
            (3, "11:00", "19:00"), (4, "11:00", "19:00"), (5, "11:00", "19:00"),
            (6, "11:00", "19:00"),
        ],
        "demo_staff_13": [
            (0, "15:00", "22:00"), (1, "15:00", "22:00"),
            (3, "15:00", "22:00"), (4, "15:00", "22:00"),
        ],
        "demo_staff_14": [
            (2, "06:00", "12:00"), (3, "06:00", "12:00"), (4, "06:00", "12:00"),
            (5, "06:00", "12:00"), (6, "06:00", "12:00"),
        ],
        "demo_staff_15": [
            (0, "08:00", "16:00"), (2, "08:00", "16:00"),
            (4, "08:00", "16:00"), (6, "08:00", "16:00"),
        ],
        "demo_staff_16": [
            (2, "16:00", "22:00"),
        ],
    }

    for name, windows in schedule_by_name.items():
        user = users_by_name.get(name)
        if user:
            add_windows(user.id, windows)


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

    manager_third = _create_demo_user(
        db=db,
        workplace_id=workplace.id,
        name="demo_manager_3",
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
        for index in range(1, 17)
    ]

    all_users = [manager_primary, manager_secondary, manager_third, *staff_users]
    _seed_realistic_demo_availability(db, workplace.id, all_users)
    db.commit()

    return {
        "status": "demo reset complete",
        "workplace": demo_workplace_name,
        "roster_generated": False,
        "manager_usernames": ["demo_manager", "demo_manager_2", "demo_manager_3"],
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
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
