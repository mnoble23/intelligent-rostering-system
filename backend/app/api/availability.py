from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api.auth import get_current_user
from app.db.session import get_db
from app.models.availability_db import AvailabilityDB
from app.models.user_db import UserDB
from app.models.workplace_db import WorkplaceDB
from app.schemas.availability import AvailabilityBulkCreate, AvailabilityCreate, AvailabilityResponse
from app.services.roster_generator import (
    calculate_max_feasible_minutes_for_user,
    generate_weekly_shifts,
    match_availability_to_shifts,
)

router = APIRouter(
    prefix="/availability",
    tags=["Availability"],
    dependencies=[Depends(get_current_user)],
)


def _get_week_start(target_date: date) -> date:
    return target_date - date.resolution * target_date.weekday()


def _validate_minimum_hours_reachability(
    *,
    db: Session,
    workplace_id: int,
    user_id: int,
    user_name: str,
    min_hours: float,
    availabilities: list[AvailabilityCreate],
) -> None:
    if min_hours <= 0:
        return

    workplace = db.query(WorkplaceDB).filter_by(id=workplace_id).first()
    if workplace is None:
        raise HTTPException(status_code=404, detail="Workplace not found")

    weekly_availability = {day: {} for day in range(7)}
    for entry in availabilities:
        weekly_availability.setdefault(entry.day_of_week, {}).setdefault(user_id, []).append(
            (entry.start_time, entry.end_time)
        )
    for day in weekly_availability:
        if user_id in weekly_availability[day]:
            weekly_availability[day][user_id].sort(key=lambda item: item[0])

    week_start = _get_week_start(date.today())
    weekly_shifts = generate_weekly_shifts(
        week_start,
        business_start_hour=workplace.business_start_hour,
        business_end_hour=workplace.business_end_hour,
    )
    staffable_shifts = match_availability_to_shifts(weekly_availability, weekly_shifts)
    user_shifts = [
        shift
        for day in range(7)
        for shift in staffable_shifts.get(day, [])
        if user_id in shift.staff
    ]
    possible_minutes = calculate_max_feasible_minutes_for_user(
        user_shifts,
        week_start,
        max_consecutive_shifts=workplace.max_consecutive_shifts,
        min_hours_between_shifts=workplace.min_hours_between_shifts,
    )
    required_minutes = int(round(min_hours * 60))
    if possible_minutes < required_minutes:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "min_hours_unreachable_on_submission",
                "message": "Availability submission failed: the user cannot reach their minimum weekly hours with the submitted availability.",
                "explanation": "The submitted weekly availability does not contain enough solver-feasible hours to satisfy the user's minimum weekly hours.",
                "suggestions": [
                    "Add more availability blocks for this user.",
                    "Use longer or less fragmented availability windows.",
                    "Lower the user's minimum weekly hours if the requirement is incorrect.",
                ],
                "context": {
                    "user_id": user_id,
                    "user_name": user_name,
                    "required_hours": round(required_minutes / 60, 2),
                    "possible_hours": round(possible_minutes / 60, 2),
                },
            },
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

    availability_by_user: dict[int, list[AvailabilityCreate]] = {user_id: [] for user_id in user_ids}
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

        availability_by_user.setdefault(availability.user_id, []).append(availability)

    target_users = {
        user.id: user
        for user in db.query(UserDB).filter(
            UserDB.id.in_(user_ids),
            UserDB.workplace_id == current_user.workplace_id,
            UserDB.is_active.is_(True),
        )
    }
    for user_id, user_availability in availability_by_user.items():
        target_user = target_users.get(user_id)
        if target_user is None:
            continue
        _validate_minimum_hours_reachability(
            db=db,
            workplace_id=current_user.workplace_id,
            user_id=user_id,
            user_name=target_user.name,
            min_hours=float(target_user.min_hours),
            availabilities=user_availability,
        )

    for availability in bulk.availabilities:
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
