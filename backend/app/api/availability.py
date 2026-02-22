from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.schemas.availability import AvailabilityCreate, AvailabilityResponse, AvailabilityBulkCreate
from app.models.availability_db import AvailabilityDB
from app.api.auth import get_current_user
from app.db.session import get_db

router = APIRouter(
    prefix="/availability",
    tags=["Availability"],
    dependencies=[Depends(get_current_user)],
)

@router.post("/", response_model=AvailabilityResponse)
def create_availability(
    availability: AvailabilityCreate,
    db: Session = Depends(get_db)
):
    if availability.end_time <= availability.start_time:
        raise HTTPException(
            status_code=400,
            detail="end_time must be after start_time"
        )

    existing = db.query(AvailabilityDB).filter(
        AvailabilityDB.user_id == availability.user_id,
        AvailabilityDB.day_of_week == availability.day_of_week,
        AvailabilityDB.start_time < availability.end_time,
        AvailabilityDB.end_time > availability.start_time
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Availability overlaps with existing entry on day {availability.day_of_week}"
        )

    db_availability = AvailabilityDB(**availability.model_dump())
    db.add(db_availability)
    db.commit()
    db.refresh(db_availability)

    return db_availability

@router.post("/bulk", response_model=List[AvailabilityResponse])
def create_availabilities_bulk(
    bulk: AvailabilityBulkCreate,
    db: Session = Depends(get_db)
):
    if not bulk.availabilities:
        raise HTTPException(status_code=400, detail="At least one availability entry is required")

    user_ids = {entry.user_id for entry in bulk.availabilities}
    db.query(AvailabilityDB).filter(AvailabilityDB.user_id.in_(user_ids)).delete(synchronize_session=False)
    db.commit()

    created_entries = []

    for availability in bulk.availabilities:
        if availability.end_time <= availability.start_time:
            raise HTTPException(
                status_code=400,
                detail=f"end_time must be after start_time for day {availability.day_of_week}"
            )

        existing = db.query(AvailabilityDB).filter(
            AvailabilityDB.user_id == availability.user_id,
            AvailabilityDB.day_of_week == availability.day_of_week,
            AvailabilityDB.start_time < availability.end_time,
            AvailabilityDB.end_time > availability.start_time
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Availability overlaps with existing entry on day {availability.day_of_week}"
            )

        db_availability = AvailabilityDB(**availability.model_dump())
        db.add(db_availability)
        db.commit()
        db.refresh(db_availability)

        created_entries.append(db_availability)

    return created_entries

@router.get("/", response_model=list[AvailabilityResponse])
def list_availability(db: Session = Depends(get_db)):
    return db.query(AvailabilityDB).all()
