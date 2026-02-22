from datetime import date, datetime, time, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Dict, List, Set
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.api.auth import get_current_user, require_manager
from app.services.availability_loader import load_weekly_availability
from app.services.roster_generator import (
    BUSINESS_END,
    BUSINESS_START,
    MIN_STAFF_PER_SHIFT,
    assign_staff_to_shifts,
    generate_weekly_shifts,
    match_availability_to_shifts,
)
from app.models.shift_db import ShiftDB
from app.models.shift_assignment_db import ShiftAssignmentDB
from app.models.user_db import UserDB

router = APIRouter(
    prefix="/roster",
    tags=["Roster"],
    dependencies=[Depends(get_current_user)],
)


class ManualAssignmentUpdate(BaseModel):
    shift_id: int
    user_id: int


class ShiftUpsertRequest(BaseModel):
    week_start_date: date | None = None
    day_of_week: int
    start_time: str
    end_time: str


class GenerateRosterRequest(BaseModel):
    weeks: int = Field(default=1, ge=1, le=52)
    start_date: date | None = None


def parse_hhmm(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Time must be in HH:MM format") from exc


def get_week_start(target_date: date) -> date:
    return target_date - timedelta(days=target_date.weekday())


def get_latest_week_start(db: Session) -> date | None:
    return db.query(func.max(ShiftDB.week_start_date)).scalar()


def resolve_week_start(db: Session, requested_week_start: date | None) -> date | None:
    if requested_week_start is not None:
        return get_week_start(requested_week_start)
    latest = get_latest_week_start(db)
    if latest is not None:
        return latest
    return None


@router.get("/debug/availability")
def debug_availability(
    db: Session = Depends(get_db),
    _current_user: UserDB = Depends(require_manager),
):
    """
    For debugging, will remove later.
    """
    return load_weekly_availability(db)


@router.get("/debug/shifts")
def debug_shifts(_current_user: UserDB = Depends(require_manager)):
    """
    For debugging, will remove later.
    """
    weekly = generate_weekly_shifts(get_week_start(date.today()))
    return {day: [f"{s.start_time}-{s.end_time}" for s in shifts] for day, shifts in weekly.items()}


@router.get("/debug/staffable-shifts")
def debug_staffable_shifts(
    db: Session = Depends(get_db),
    _current_user: UserDB = Depends(require_manager),
):
    """
    For debugging, will remove later.
    """
    availability_map = load_weekly_availability(db)
    weekly_shifts = generate_weekly_shifts(get_week_start(date.today()))
    staffable = match_availability_to_shifts(availability_map, weekly_shifts)

    return {
        day: [
            {
                "start": s.start_time.strftime("%H:%M"),
                "end": s.end_time.strftime("%H:%M"),
                "staff": s.staff
            }
            for s in shifts
        ]
        for day, shifts in staffable.items()
    }


@router.get("/debug/assigned-shifts")
def debug_assigned_shifts(
    db: Session = Depends(get_db),
    _current_user: UserDB = Depends(require_manager),
):
    """
    For debugging, will remove later.
    """
    availability_map = load_weekly_availability(db)

    week_start = get_week_start(date.today())
    weekly_shifts = generate_weekly_shifts(week_start)

    staffable_shifts = match_availability_to_shifts(availability_map, weekly_shifts)

    users = db.query(UserDB).all()
    user_hour_limits = {
        user.id: (float(user.min_hours), float(user.max_hours))
        for user in users
    }
    user_roles = {
        user.id: user.role
        for user in users
    }
    assigned_shifts = assign_staff_to_shifts(
        db,
        staffable_shifts,
        week_start_date=week_start,
        user_hour_limits=user_hour_limits,
        user_roles=user_roles,
    )

    return {
        day: [
            {
                "start": s.start_time.strftime("%H:%M"),
                "end": s.end_time.strftime("%H:%M"),
                "staff": s.staff
            }
            for s in shifts
        ]
        for day, shifts in assigned_shifts.items()
    }


@router.post("/generate")
def generate_roster(
    payload: GenerateRosterRequest = GenerateRosterRequest(),
    db: Session = Depends(get_db),
    _current_user: UserDB = Depends(require_manager),
):
    weekly_availability = load_weekly_availability(db)
    users = db.query(UserDB).all()
    user_hour_limits = {
        user.id: (float(user.min_hours), float(user.max_hours))
        for user in users
    }
    user_roles = {
        user.id: user.role
        for user in users
    }
    start_week = get_week_start(payload.start_date or date.today())
    end_week = start_week + timedelta(days=(payload.weeks - 1) * 7)
    try:
        for offset in range(payload.weeks):
            week_start = start_week + timedelta(days=offset * 7)
            weekly_shifts = generate_weekly_shifts(week_start)
            staffable_shifts = match_availability_to_shifts(
                weekly_availability,
                weekly_shifts,
            )
            assign_staff_to_shifts(
                db,
                staffable_shifts,
                week_start_date=week_start,
                user_hour_limits=user_hour_limits,
                user_roles=user_roles,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "roster generated",
        "weeks_generated": payload.weeks,
        "start_week": start_week.isoformat(),
        "end_week": end_week.isoformat(),
    }


@router.get("/")
def get_roster(
    week_start_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> List[Dict]:
    resolved_week_start = resolve_week_start(db, week_start_date)
    if resolved_week_start is None:
        return []

    shifts = (
        db.query(ShiftDB)
        .filter_by(week_start_date=resolved_week_start)
        .order_by(ShiftDB.day_of_week, ShiftDB.start_time)
        .all()
    )
    roster = []

    for shift in shifts:
        assignments = db.query(ShiftAssignmentDB).filter_by(shift_id=shift.id).all()

        staff = []
        for a in assignments:
            if current_user.role != "manager" and a.user_id != current_user.id:
                continue
            user = db.query(UserDB).get(a.user_id)
            if user:
                staff.append({"id": user.id, "name": user.name})

        if current_user.role != "manager" and not staff:
            continue

        roster.append({
            "id": shift.id,
            "week_start_date": shift.week_start_date.isoformat(),
            "day_of_week": shift.day_of_week,
            "start_time": str(shift.start_time),
            "end_time": str(shift.end_time),
            "staff": staff
        })

    return roster


@router.get("/weeks")
def get_available_roster_weeks(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> List[str]:
    if current_user.role == "manager":
        weeks = (
            db.query(ShiftDB.week_start_date)
            .distinct()
            .order_by(ShiftDB.week_start_date.desc())
            .all()
        )
        return [week_start.isoformat() for (week_start,) in weeks]

    weeks = (
        db.query(ShiftDB.week_start_date)
        .join(ShiftAssignmentDB, ShiftAssignmentDB.shift_id == ShiftDB.id)
        .filter(ShiftAssignmentDB.user_id == current_user.id)
        .distinct()
        .order_by(ShiftDB.week_start_date.desc())
        .all()
    )
    return [week_start.isoformat() for (week_start,) in weeks]


@router.delete("/week/{week_start_date}")
def delete_roster_week(
    week_start_date: date,
    db: Session = Depends(get_db),
    _current_user: UserDB = Depends(require_manager),
):
    resolved_week_start = get_week_start(week_start_date)

    shifts = db.query(ShiftDB).filter_by(week_start_date=resolved_week_start).all()
    if not shifts:
        raise HTTPException(status_code=404, detail="Roster week not found")

    shift_ids = [shift.id for shift in shifts]
    deleted_assignments = (
        db.query(ShiftAssignmentDB)
        .filter(ShiftAssignmentDB.shift_id.in_(shift_ids))
        .delete(synchronize_session=False)
    )
    deleted_shifts = (
        db.query(ShiftDB)
        .filter_by(week_start_date=resolved_week_start)
        .delete(synchronize_session=False)
    )
    db.commit()

    return {
        "status": "roster week deleted",
        "week_start_date": resolved_week_start.isoformat(),
        "deleted_shifts": deleted_shifts,
        "deleted_assignments": deleted_assignments,
    }


@router.get("/coverage")
def get_shift_coverage(
    week_start_date: date | None = None,
    db: Session = Depends(get_db),
    _current_user: UserDB = Depends(require_manager),
):
    resolved_week_start = resolve_week_start(db, week_start_date)
    if resolved_week_start is None:
        return {
            "week_start_date": None,
            "business_hours": {
                "start": f"{BUSINESS_START:02d}:00",
                "end": f"{BUSINESS_END:02d}:00",
            },
            "minimum_staff_per_shift": MIN_STAFF_PER_SHIFT,
            "summary": {
                "fully_staffed_hours": 0,
                "understaffed_hours": 0,
                "closed_hours": 0,
            },
            "coverage": [],
        }

    shifts = db.query(ShiftDB).filter_by(week_start_date=resolved_week_start).all()
    assignments = db.query(ShiftAssignmentDB).all()

    staff_by_shift: Dict[int, Set[int]] = {}
    for assignment in assignments:
        staff_by_shift.setdefault(assignment.shift_id, set()).add(assignment.user_id)

    coverage = []
    fully_staffed_hours = 0
    understaffed_hours = 0

    for day in range(7):
        day_slots = []
        day_shifts = [shift for shift in shifts if shift.day_of_week == day]

        for hour in range(BUSINESS_START, BUSINESS_END):
            hour_start = time(hour=hour)
            hour_end = time(hour=hour + 1)

            active_shifts = [
                shift for shift in day_shifts
                if shift.start_time <= hour_start and shift.end_time >= hour_end
            ]

            required_staff = MIN_STAFF_PER_SHIFT
            assigned_staff_ids: Set[int] = set()
            for shift in active_shifts:
                assigned_staff_ids.update(staff_by_shift.get(shift.id, set()))

            assigned_staff = len(assigned_staff_ids)

            if assigned_staff >= required_staff:
                status = "fully_staffed"
                fully_staffed_hours += 1
            else:
                status = "understaffed"
                understaffed_hours += 1

            day_slots.append({
                "hour_start": f"{hour:02d}:00",
                "hour_end": f"{hour + 1:02d}:00",
                "required_staff": required_staff,
                "assigned_staff": assigned_staff,
                "status": status,
            })

        coverage.append({"day_of_week": day, "hours": day_slots})

    return {
        "week_start_date": resolved_week_start.isoformat(),
        "business_hours": {
            "start": f"{BUSINESS_START:02d}:00",
            "end": f"{BUSINESS_END:02d}:00",
        },
        "minimum_staff_per_shift": MIN_STAFF_PER_SHIFT,
        "summary": {
            "fully_staffed_hours": fully_staffed_hours,
            "understaffed_hours": understaffed_hours,
            "closed_hours": 0,
        },
        "coverage": coverage,
    }


@router.post("/assign")
def assign_user_to_shift(
    payload: ManualAssignmentUpdate,
    db: Session = Depends(get_db),
    _current_user: UserDB = Depends(require_manager),
):
    shift = db.query(ShiftDB).filter_by(id=payload.shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    user = db.query(UserDB).filter_by(id=payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_assignment = db.query(ShiftAssignmentDB).filter_by(
        shift_id=payload.shift_id,
        user_id=payload.user_id,
    ).first()
    if existing_assignment:
        raise HTTPException(status_code=400, detail="User already assigned to this shift")

    assignment = ShiftAssignmentDB(shift_id=payload.shift_id, user_id=payload.user_id)
    db.add(assignment)
    db.commit()

    return {"status": "user assigned to shift"}


@router.post("/shifts/upsert")
def upsert_shift(
    payload: ShiftUpsertRequest,
    db: Session = Depends(get_db),
    _current_user: UserDB = Depends(require_manager),
):
    if payload.day_of_week < 0 or payload.day_of_week > 6:
        raise HTTPException(status_code=400, detail="day_of_week must be between 0 and 6")

    resolved_week_start = resolve_week_start(db, payload.week_start_date)
    if resolved_week_start is None:
        resolved_week_start = get_week_start(date.today())

    start_time = parse_hhmm(payload.start_time)
    end_time = parse_hhmm(payload.end_time)

    if end_time <= start_time:
        raise HTTPException(status_code=400, detail="end_time must be later than start_time")

    existing_shift = db.query(ShiftDB).filter_by(
        week_start_date=resolved_week_start,
        day_of_week=payload.day_of_week,
        start_time=start_time,
        end_time=end_time,
    ).first()

    if existing_shift:
        return {
            "id": existing_shift.id,
            "week_start_date": existing_shift.week_start_date.isoformat(),
            "day_of_week": existing_shift.day_of_week,
            "start_time": str(existing_shift.start_time),
            "end_time": str(existing_shift.end_time),
            "created": False,
        }

    new_shift = ShiftDB(
        week_start_date=resolved_week_start,
        day_of_week=payload.day_of_week,
        start_time=start_time,
        end_time=end_time,
    )
    db.add(new_shift)
    db.commit()
    db.refresh(new_shift)

    return {
        "id": new_shift.id,
        "week_start_date": new_shift.week_start_date.isoformat(),
        "day_of_week": new_shift.day_of_week,
        "start_time": str(new_shift.start_time),
        "end_time": str(new_shift.end_time),
        "created": True,
    }


@router.post("/unassign")
def unassign_user_from_shift(
    payload: ManualAssignmentUpdate,
    db: Session = Depends(get_db),
    _current_user: UserDB = Depends(require_manager),
):
    assignment = db.query(ShiftAssignmentDB).filter_by(
        shift_id=payload.shift_id,
        user_id=payload.user_id,
    ).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    db.delete(assignment)
    db.commit()

    return {"status": "user removed from shift"}
