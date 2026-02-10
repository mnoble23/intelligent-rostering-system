from fastapi import APIRouter, Depends, HTTPException
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
            "name": user.name
        }
        for user in users
    ]

@router.post("/", response_model=UserRead)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = UserDB(name=user.name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user