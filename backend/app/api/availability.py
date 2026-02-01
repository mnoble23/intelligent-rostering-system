from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.availability import AvailabilityCreate, AvailabilityResponse
from app.models.availability_db import AvailabilityDB
from app.db.session import get_db

router = APIRouter(
    prefix="/availability",
    tags=["Availability"]
)


@router.post("/", response_model=AvailabilityResponse)
def create_availability(
    availability: AvailabilityCreate,
    db: Session = Depends(get_db)
):
    existing = db.query(AvailabilityDB).filter(
        AvailabilityDB.user_id == availability.user_id,
        AvailabilityDB.day_of_week == availability.day_of_week,
        AvailabilityDB.start_time < availability.end_time,
        AvailabilityDB.end_time > availability.start_time
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Availability overlaps with existing entry")

    db_availability = AvailabilityDB(**availability.dict())
    db.add(db_availability)
    db.commit()
    db.refresh(db_availability)

    return db_availability 

@router.get("/", response_model=list[AvailabilityResponse])
def list_availability(db: Session = Depends(get_db)):
    return db.query(AvailabilityDB).all()
