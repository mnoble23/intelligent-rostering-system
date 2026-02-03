from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.availability_loader import load_weekly_availability
from app.services.roster_generator import generate_weekly_shifts

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