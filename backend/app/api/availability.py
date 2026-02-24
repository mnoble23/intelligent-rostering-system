from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api.auth import get_current_user
from app.db.session import get_db
from app.models.availability_db import AvailabilityDB
from app.models.user_db import UserDB
from app.schemas.availability import AvailabilityBulkCreate, AvailabilityCreate, AvailabilityResponse

router = APIRouter(
    prefix="/availability",
    tags=["Availability"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=AvailabilityResponse)
def create_availability(
    availability: AvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    if current_user.role != "manager" and availability.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only manage your own availability")

    target_user = db.query(UserDB).filter_by(
        id=availability.user_id,
        workplace_id=current_user.workplace_id,
        is_active=True,
    ).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found in your workplace")

    if availability.end_time <= availability.start_time:
        raise HTTPException(
            status_code=400,
            detail="end_time must be after start_time",
        )

    existing = db.query(AvailabilityDB).filter(
        AvailabilityDB.workplace_id == current_user.workplace_id,
        AvailabilityDB.user_id == availability.user_id,
        AvailabilityDB.day_of_week == availability.day_of_week,
        AvailabilityDB.start_time < availability.end_time,
        AvailabilityDB.end_time > availability.start_time,
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Availability overlaps with existing entry on day {availability.day_of_week}",
        )

    db_availability = AvailabilityDB(
        workplace_id=current_user.workplace_id,
        **availability.model_dump(),
    )
    db.add(db_availability)
    db.commit()
    db.refresh(db_availability)

    return db_availability


@router.post("/bulk", response_model=List[AvailabilityResponse])
def create_availabilities_bulk(
    bulk: AvailabilityBulkCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    if not bulk.availabilities:
        raise HTTPException(status_code=400, detail="At least one availability entry is required")

    user_ids = {entry.user_id for entry in bulk.availabilities}
    if current_user.role != "manager" and any(user_id != current_user.id for user_id in user_ids):
        raise HTTPException(status_code=403, detail="You can only manage your own availability")

    workplace_user_ids = {
        user.id
        for user in db.query(UserDB.id).filter(
            UserDB.id.in_(user_ids),
            UserDB.workplace_id == current_user.workplace_id,
            UserDB.is_active.is_(True),
        ).all()
    }
    if workplace_user_ids != user_ids:
        raise HTTPException(status_code=404, detail="One or more users are not in your workplace")

    db.query(AvailabilityDB).filter(
        AvailabilityDB.workplace_id == current_user.workplace_id,
        AvailabilityDB.user_id.in_(user_ids),
    ).delete(synchronize_session=False)
    db.commit()

    created_entries = []

    for availability in bulk.availabilities:
        if availability.end_time <= availability.start_time:
            raise HTTPException(
                status_code=400,
                detail=f"end_time must be after start_time for day {availability.day_of_week}",
            )

        existing = db.query(AvailabilityDB).filter(
            AvailabilityDB.workplace_id == current_user.workplace_id,
            AvailabilityDB.user_id == availability.user_id,
            AvailabilityDB.day_of_week == availability.day_of_week,
            AvailabilityDB.start_time < availability.end_time,
            AvailabilityDB.end_time > availability.start_time,
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Availability overlaps with existing entry on day {availability.day_of_week}",
            )

        db_availability = AvailabilityDB(
            workplace_id=current_user.workplace_id,
            **availability.model_dump(),
        )
        db.add(db_availability)
        db.commit()
        db.refresh(db_availability)

        created_entries.append(db_availability)

    return created_entries


@router.get("/", response_model=list[AvailabilityResponse])
def list_availability(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    query = db.query(AvailabilityDB).filter_by(workplace_id=current_user.workplace_id)
    if current_user.role != "manager":
        query = query.filter_by(user_id=current_user.id)
    return query.all()
