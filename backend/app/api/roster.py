from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.availability_loader import load_weekly_availability
from app.services.roster_generator import generate_weekly_shifts, match_availability_to_shifts, assign_staff_to_shifts

router = APIRouter(
    prefix="/roster",
    tags=["Roster"]
)

@router.get("/")
def get_roster():
    return [
        {
            "user_id": 1,
            "week": "2026-02-03",
            "shifts": [
                {"day": "Monday", "hours": ["09:00-12:00", "14:00-18:00"]}
            ]
        }
    ]

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

    assigned_shifts = assign_staff_to_shifts(staffable_shifts)
    
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
    assign_staff_to_shifts(db, staffable_shifts)

    return {"status": "roster generated"}