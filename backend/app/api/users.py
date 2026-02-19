from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user_db import UserDB
from app.schemas.user import UserCreate, UserRead

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.get("/")
def get_users(db: Session = Depends(get_db)):
    users = db.query(UserDB).all()
    return [
        {
            "id": user.id,
            "name": user.name,
            "min_hours": user.min_hours,
            "max_hours": user.max_hours,
        }
        for user in users
    ]

@router.post("/", response_model=UserRead)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    normalized_name = user.name.strip()
    if not normalized_name:
        raise HTTPException(status_code=400, detail="Name is required")
    if user.max_hours < user.min_hours:
        raise HTTPException(status_code=400, detail="max_hours must be greater than or equal to min_hours")

    existing_user = (
        db.query(UserDB)
        .filter(func.lower(UserDB.name) == normalized_name.lower())
        .first()
    )
    if existing_user:
        existing_user.min_hours = user.min_hours
        existing_user.max_hours = user.max_hours
        db.commit()
        db.refresh(existing_user)
        return existing_user

    db_user = UserDB(
        name=normalized_name,
        min_hours=user.min_hours,
        max_hours=user.max_hours,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
