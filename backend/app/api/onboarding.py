from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth_utils import create_access_token, hash_password
from app.db.session import get_db
from app.models.user_db import UserDB
from app.models.workplace_db import WorkplaceDB

router = APIRouter(
    prefix="/onboarding",
    tags=["Onboarding"],
)


class OnboardingStatusResponse(BaseModel):
    is_bootstrapped: bool


class CreateWorkplaceRequest(BaseModel):
    workplace_name: str
    manager_name: str
    password: str = Field(min_length=8)


class AuthUserResponse(BaseModel):
    id: int
    name: str
    role: str
    is_active: bool
    workplace_id: int


class CreateWorkplaceResponse(BaseModel):
    access_token: str
    token_type: str
    user: AuthUserResponse


@router.get("/status", response_model=OnboardingStatusResponse)
def onboarding_status(db: Session = Depends(get_db)):
    has_users = db.query(UserDB.id).first() is not None
    return {"is_bootstrapped": has_users}


@router.post("/create-workplace", response_model=CreateWorkplaceResponse)
def create_workplace(payload: CreateWorkplaceRequest, db: Session = Depends(get_db)):
    existing_user = db.query(UserDB.id).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workplace has already been created",
        )

    workplace_name = payload.workplace_name.strip()
    manager_name = payload.manager_name.strip()

    if not workplace_name:
        raise HTTPException(status_code=400, detail="Workplace name is required")
    if not manager_name:
        raise HTTPException(status_code=400, detail="Manager name is required")

    workplace = WorkplaceDB(name=workplace_name)
    db.add(workplace)
    db.flush()

    manager = UserDB(
        name=manager_name,
        role="manager",
        min_hours=0.0,
        max_hours=40.0,
        password_hash=hash_password(payload.password),
        is_active=True,
        workplace_id=workplace.id,
    )
    db.add(manager)
    db.commit()
    db.refresh(manager)

    access_token = create_access_token(
        user_id=manager.id,
        role=manager.role,
        workplace_id=workplace.id,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": manager.id,
            "name": manager.name,
            "role": manager.role,
            "is_active": manager.is_active,
            "workplace_id": workplace.id,
        },
    }
