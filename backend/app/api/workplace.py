from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import require_manager
from app.db.session import get_db
from app.models.user_db import UserDB
from app.models.workplace_db import WorkplaceDB

router = APIRouter(
    prefix="/workplace",
    tags=["Workplace"],
)


class WorkplaceConstraintsResponse(BaseModel):
    workplace_id: int
    min_staff_per_shift: int = Field(ge=1, le=20)
    min_managers_per_hour: int = Field(ge=0, le=10)
    max_consecutive_shifts: int = Field(ge=1, le=7)
    min_hours_between_shifts: int = Field(ge=0, le=24)
    business_start_hour: int = Field(ge=0, le=23)
    business_end_hour: int = Field(ge=1, le=24)


class UpdateWorkplaceConstraintsRequest(BaseModel):
    min_staff_per_shift: int = Field(ge=1, le=20)
    min_managers_per_hour: int = Field(ge=0, le=10)
    max_consecutive_shifts: int = Field(ge=1, le=7)
    min_hours_between_shifts: int = Field(ge=0, le=24)
    business_start_hour: int = Field(ge=0, le=23)
    business_end_hour: int = Field(ge=1, le=24)


@router.get("/constraints", response_model=WorkplaceConstraintsResponse)
def get_workplace_constraints(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(require_manager),
):
    workplace = db.query(WorkplaceDB).filter_by(id=current_user.workplace_id).first()
    if not workplace:
        raise HTTPException(status_code=404, detail="Workplace not found")

    return {
        "workplace_id": workplace.id,
        "min_staff_per_shift": workplace.min_staff_per_shift,
        "min_managers_per_hour": workplace.min_managers_per_hour,
        "max_consecutive_shifts": workplace.max_consecutive_shifts,
        "min_hours_between_shifts": workplace.min_hours_between_shifts,
        "business_start_hour": workplace.business_start_hour,
        "business_end_hour": workplace.business_end_hour,
    }


@router.put("/constraints", response_model=WorkplaceConstraintsResponse)
def update_workplace_constraints(
    payload: UpdateWorkplaceConstraintsRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(require_manager),
):
    if payload.min_managers_per_hour > payload.min_staff_per_shift:
        raise HTTPException(
            status_code=400,
            detail="min_managers_per_hour cannot exceed min_staff_per_shift",
        )
    if payload.business_end_hour <= payload.business_start_hour:
        raise HTTPException(
            status_code=400,
            detail="business_end_hour must be later than business_start_hour",
        )

    workplace = db.query(WorkplaceDB).filter_by(id=current_user.workplace_id).first()
    if not workplace:
        raise HTTPException(status_code=404, detail="Workplace not found")

    workplace.min_staff_per_shift = payload.min_staff_per_shift
    workplace.min_managers_per_hour = payload.min_managers_per_hour
    workplace.max_consecutive_shifts = payload.max_consecutive_shifts
    workplace.min_hours_between_shifts = payload.min_hours_between_shifts
    workplace.business_start_hour = payload.business_start_hour
    workplace.business_end_hour = payload.business_end_hour
    db.commit()
    db.refresh(workplace)

    return {
        "workplace_id": workplace.id,
        "min_staff_per_shift": workplace.min_staff_per_shift,
        "min_managers_per_hour": workplace.min_managers_per_hour,
        "max_consecutive_shifts": workplace.max_consecutive_shifts,
        "min_hours_between_shifts": workplace.min_hours_between_shifts,
        "business_start_hour": workplace.business_start_hour,
        "business_end_hour": workplace.business_end_hour,
    }
