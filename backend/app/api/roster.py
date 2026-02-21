from datetime import datetime, time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Set
from pydantic import BaseModel

from app.db.session import get_db
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
    tags=["Roster"]
)


class ManualAssignmentUpdate(BaseModel):
    shift_id: int
    user_id: int


class ShiftUpsertRequest(BaseModel):
    day_of_week: int
    start_time: str
    end_time: str


def parse_hhmm(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Time must be in HH:MM format") from exc

@router.get("/debug/availability")
def debug_availability(db: Session = Depends(get_db)):
    """
    For debugging, will remove later.
    """
    return load_weekly_availability(db)

@router.get("/debug/shifts")
def debug_shifts():
    """
    For debugging, will remove later.
    """
    weekly = generate_weekly_shifts()
    return {day: [f"{s.start_time}-{s.end_time}" for s in shifts] for day, shifts in weekly.items()}

@router.get("/debug/staffable-shifts")
def debug_staffable_shifts(db: Session = Depends(get_db)):
    """
    For debugging, will remove later.
    """
    availability_map = load_weekly_availability(db)
    weekly_shifts = generate_weekly_shifts()
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
def debug_assigned_shifts(db: Session = Depends(get_db)):
    """
    For debugging, will remove later.
    """
    availability_map = load_weekly_availability(db)

    weekly_shifts = generate_weekly_shifts()

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
def generate_roster(db: Session = Depends(get_db)):
    weekly_availability = load_weekly_availability(db)

    weekly_shifts = generate_weekly_shifts()
    staffable_shifts = match_availability_to_shifts(
        weekly_availability,
        weekly_shifts,
    )
    users = db.query(UserDB).all()
    user_hour_limits = {
        user.id: (float(user.min_hours), float(user.max_hours))
        for user in users
    }
    user_roles = {
        user.id: user.role
        for user in users
    }
    try:
        assign_staff_to_shifts(
            db,
            staffable_shifts,
            user_hour_limits=user_hour_limits,
            user_roles=user_roles,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "roster generated"}

@router.get("/")
def get_roster(db: Session = Depends(get_db)) -> List[Dict]:
    shifts = db.query(ShiftDB).all()
    roster = []

    for shift in shifts:
        assignments = db.query(ShiftAssignmentDB).filter_by(shift_id=shift.id).all()

        staff = []
        for a in assignments:
            user = db.query(UserDB).get(a.user_id)
            if user:
                staff.append({"id": user.id, "name": user.name})

        roster.append({
            "id": shift.id,
            "day_of_week": shift.day_of_week,
            "start_time": str(shift.start_time),
            "end_time": str(shift.end_time),
            "staff": staff
        })

    return roster


@router.get("/coverage")
def get_shift_coverage(db: Session = Depends(get_db)):
    shifts = db.query(ShiftDB).all()
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
def assign_user_to_shift(payload: ManualAssignmentUpdate, db: Session = Depends(get_db)):
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
def upsert_shift(payload: ShiftUpsertRequest, db: Session = Depends(get_db)):
    if payload.day_of_week < 0 or payload.day_of_week > 6:
        raise HTTPException(status_code=400, detail="day_of_week must be between 0 and 6")

    start_time = parse_hhmm(payload.start_time)
    end_time = parse_hhmm(payload.end_time)

    if end_time <= start_time:
        raise HTTPException(status_code=400, detail="end_time must be later than start_time")

    existing_shift = db.query(ShiftDB).filter_by(
        day_of_week=payload.day_of_week,
        start_time=start_time,
        end_time=end_time,
    ).first()

    if existing_shift:
        return {
            "id": existing_shift.id,
            "day_of_week": existing_shift.day_of_week,
            "start_time": str(existing_shift.start_time),
            "end_time": str(existing_shift.end_time),
            "created": False,
        }

    new_shift = ShiftDB(
        day_of_week=payload.day_of_week,
        start_time=start_time,
        end_time=end_time,
    )
    db.add(new_shift)
    db.commit()
    db.refresh(new_shift)

    return {
        "id": new_shift.id,
        "day_of_week": new_shift.day_of_week,
        "start_time": str(new_shift.start_time),
        "end_time": str(new_shift.end_time),
        "created": True,
    }


@router.post("/unassign")
def unassign_user_from_shift(payload: ManualAssignmentUpdate, db: Session = Depends(get_db)):
    assignment = db.query(ShiftAssignmentDB).filter_by(
        shift_id=payload.shift_id,
        user_id=payload.user_id,
    ).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    db.delete(assignment)
    db.commit()

    return {"status": "user removed from shift"}
