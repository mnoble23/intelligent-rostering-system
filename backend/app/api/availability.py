from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.availability import Availability
from app.models.availability_db import AvailabilityDB
from app.db.session import get_db

router = APIRouter(
    prefix="/availability",
    tags=["Availability"]
)


@router.post("/")
def create_availability(
    availability: Availability,
    db: Session = Depends(get_db)
):
    db_availability = AvailabilityDB(
        user_id=availability.user_id,
        day_of_week=availability.day_of_week,
        start_time=availability.start_time,
        end_time=availability.end_time,
    )

    db.add(db_availability)
    db.commit()
    db.refresh(db_availability)

    return {
        "message": "Availability saved",
        "availability": db_availability
    }

@router.get("/")
def list_availability(db: Session = Depends(get_db)):
    availability = db.query(AvailabilityDB).all()
    return availability
