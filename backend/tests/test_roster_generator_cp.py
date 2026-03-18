import pathlib
import sys
from datetime import date, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

pytest.importorskip("ortools")

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.models.user_db import UserDB
from app.models.workplace_db import WorkplaceDB
from app.services.roster_generator import (
    RosterGenerationError,
    Shift,
    generate_weekly_shifts,
    parse_allowed_shift_lengths,
    assign_staff_to_shifts,
    match_availability_to_shifts,
)


def _build_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return SessionLocal()


def test_cp_solver_assigns_manager_and_staff_to_cover_open_hours():
    db = _build_session()
    week_start = date(2026, 1, 5)

    workplace = WorkplaceDB(
        name="Coverage Test Workplace",
        min_staff_per_shift=2,
        min_managers_per_hour=1,
        business_start_hour=9,
        business_end_hour=13,
    )
    db.add(workplace)
    db.commit()
    db.refresh(workplace)

    manager = UserDB(
        name="manager",
        role="manager",
        min_hours=0,
        max_hours=40,
        min_shifts_per_week=0,
        max_shifts_per_week=7,
        password_hash="x",
        is_active=True,
        workplace_id=workplace.id,
    )
    staff = UserDB(
        name="staff",
        role="staff",
        min_hours=0,
        max_hours=40,
        min_shifts_per_week=0,
        max_shifts_per_week=7,
        password_hash="x",
        is_active=True,
        workplace_id=workplace.id,
    )
    db.add_all([manager, staff])
    db.commit()
    db.refresh(manager)
    db.refresh(staff)

    weekly_availability = {
        day: {
            manager.id: [(time(9, 0), time(13, 0))],
            staff.id: [(time(9, 0), time(13, 0))],
        }
        for day in range(7)
    }
    weekly_shifts = generate_weekly_shifts(
        week_start,
        business_start_hour=9,
        business_end_hour=13,
    )
    staffable_shifts = match_availability_to_shifts(weekly_availability, weekly_shifts)

    assigned = assign_staff_to_shifts(
        db,
        staffable_shifts,
        week_start_date=week_start,
        workplace_id=workplace.id,
        min_staff_per_shift=2,
        user_hour_limits={
            manager.id: (0.0, 40.0),
            staff.id: (0.0, 40.0),
        },
        user_shift_limits={
            manager.id: (0, 7),
            staff.id: (0, 7),
        },
        user_roles={
            manager.id: "manager",
            staff.id: "staff",
        },
        min_managers_per_hour=1,
        max_consecutive_shifts=7,
        min_hours_between_shifts=11,
        business_start_hour=9,
        business_end_hour=13,
    )

    for day in range(7):
        assert len(assigned[day]) == 1
        assert assigned[day][0].start_time == time(9, 0)
        assert assigned[day][0].end_time == time(13, 0)
        assert assigned[day][0].staff == [manager.id, staff.id]


def test_cp_solver_reports_unreachable_minimum_shifts_when_rest_gap_blocks_second_shift():
    db = _build_session()
    week_start = date(2026, 1, 5)

    workplace = WorkplaceDB(
        name="Rest Gap Workplace",
        min_staff_per_shift=1,
        min_managers_per_hour=1,
        business_start_hour=6,
        business_end_hour=22,
    )
    db.add(workplace)
    db.commit()
    db.refresh(workplace)

    manager = UserDB(
        name="solo_manager",
        role="manager",
        min_hours=0,
        max_hours=40,
        min_shifts_per_week=2,
        max_shifts_per_week=7,
        password_hash="x",
        is_active=True,
        workplace_id=workplace.id,
    )
    db.add(manager)
    db.commit()
    db.refresh(manager)

    staffable_shifts = {
        0: [
            Shift(
                week_start_date=week_start,
                day_of_week=0,
                start_time=time(18, 0),
                end_time=time(22, 0),
                start_hour=18,
                end_hour=22,
                staff=[manager.id],
            )
        ],
        1: [
            Shift(
                week_start_date=week_start,
                day_of_week=1,
                start_time=time(6, 0),
                end_time=time(10, 0),
                start_hour=6,
                end_hour=10,
                staff=[manager.id],
            )
        ],
        2: [],
        3: [],
        4: [],
        5: [],
        6: [],
    }

    with pytest.raises(RosterGenerationError) as exc_info:
        assign_staff_to_shifts(
            db,
            staffable_shifts,
            week_start_date=week_start,
            workplace_id=workplace.id,
            min_staff_per_shift=1,
            user_hour_limits={manager.id: (0.0, 40.0)},
            user_shift_limits={manager.id: (2, 7)},
            user_roles={manager.id: "manager"},
            min_managers_per_hour=0,
            max_consecutive_shifts=7,
            min_hours_between_shifts=11,
            business_start_hour=6,
            business_end_hour=22,
        )

    assert exc_info.value.code == "min_shifts_unreachable"
    assert exc_info.value.context["user_name"] == "solo_manager"


def test_cp_solver_reports_user_with_unreachable_minimum_hours():
    db = _build_session()
    week_start = date(2026, 1, 5)

    workplace = WorkplaceDB(
        name="User Minimum Hours Workplace",
        min_staff_per_shift=1,
        min_managers_per_hour=1,
        business_start_hour=9,
        business_end_hour=13,
    )
    db.add(workplace)
    db.commit()
    db.refresh(workplace)

    manager = UserDB(
        name="manager_hours",
        role="manager",
        min_hours=0,
        max_hours=40,
        min_shifts_per_week=0,
        max_shifts_per_week=7,
        password_hash="x",
        is_active=True,
        workplace_id=workplace.id,
    )
    staff = UserDB(
        name="staff_hours",
        role="staff",
        min_hours=10,
        max_hours=40,
        min_shifts_per_week=0,
        max_shifts_per_week=7,
        password_hash="x",
        is_active=True,
        workplace_id=workplace.id,
    )
    db.add_all([manager, staff])
    db.commit()
    db.refresh(manager)
    db.refresh(staff)

    staffable_shifts = {
        0: [
            Shift(
                week_start_date=week_start,
                day_of_week=0,
                start_time=time(9, 0),
                end_time=time(13, 0),
                start_hour=9,
                end_hour=13,
                staff=[manager.id, staff.id],
            )
        ],
        1: [],
        2: [],
        3: [],
        4: [],
        5: [],
        6: [],
    }

    with pytest.raises(RosterGenerationError) as exc_info:
        assign_staff_to_shifts(
            db,
            staffable_shifts,
            week_start_date=week_start,
            workplace_id=workplace.id,
            min_staff_per_shift=1,
            user_hour_limits={
                manager.id: (0.0, 40.0),
                staff.id: (10.0, 40.0),
            },
            user_shift_limits={
                manager.id: (0, 7),
                staff.id: (0, 7),
            },
            user_roles={
                manager.id: "manager",
                staff.id: "staff",
            },
            min_managers_per_hour=1,
            max_consecutive_shifts=7,
            min_hours_between_shifts=11,
            business_start_hour=9,
            business_end_hour=13,
        )

    assert exc_info.value.code == "min_hours_unreachable"
    assert exc_info.value.context["user_id"] == staff.id
    assert exc_info.value.context["user_name"] == "staff_hours"
    assert exc_info.value.context["possible_hours"] == 4.0


def test_cp_solver_reports_unreachable_manager_coverage_before_solving():
    db = _build_session()
    week_start = date(2026, 1, 5)

    workplace = WorkplaceDB(
        name="Manager Coverage Workplace",
        min_staff_per_shift=1,
        min_managers_per_hour=1,
        business_start_hour=9,
        business_end_hour=13,
    )
    db.add(workplace)
    db.commit()
    db.refresh(workplace)

    staff = UserDB(
        name="staff_only",
        role="staff",
        min_hours=0,
        max_hours=40,
        min_shifts_per_week=0,
        max_shifts_per_week=7,
        password_hash="x",
        is_active=True,
        workplace_id=workplace.id,
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)

    staffable_shifts = {
        0: [
            Shift(
                week_start_date=week_start,
                day_of_week=0,
                start_time=time(9, 0),
                end_time=time(13, 0),
                start_hour=9,
                end_hour=13,
                staff=[staff.id],
            )
        ],
        1: [],
        2: [],
        3: [],
        4: [],
        5: [],
        6: [],
    }

    with pytest.raises(RosterGenerationError) as exc_info:
        assign_staff_to_shifts(
            db,
            staffable_shifts,
            week_start_date=week_start,
            workplace_id=workplace.id,
            min_staff_per_shift=1,
            user_hour_limits={staff.id: (0.0, 40.0)},
            user_shift_limits={staff.id: (0, 7)},
            user_roles={staff.id: "staff"},
            min_managers_per_hour=1,
            max_consecutive_shifts=7,
            min_hours_between_shifts=11,
            business_start_hour=9,
            business_end_hour=13,
        )

    assert exc_info.value.code == "manager_coverage_unreachable"
    assert exc_info.value.context["day_of_week"] == 0
    assert exc_info.value.context["hour"] == 9


def test_generate_weekly_shifts_uses_configured_shift_lengths():
    weekly_shifts = generate_weekly_shifts(
        date(2026, 1, 5),
        business_start_hour=9,
        business_end_hour=17,
        allowed_shift_hours=parse_allowed_shift_lengths("5,8"),
    )

    monday_lengths = sorted({shift.end_hour - shift.start_hour for shift in weekly_shifts[0]})
    assert monday_lengths == [5, 8]
