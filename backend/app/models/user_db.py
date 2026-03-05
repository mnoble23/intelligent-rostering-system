from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from app.db.base import Base


class UserDB(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    role = Column(String, nullable=False, default="staff")
    min_hours = Column(Float, nullable=False, default=0.0)
    max_hours = Column(Float, nullable=False, default=40.0)
    min_shifts_per_week = Column(Integer, nullable=False, default=1)
    max_shifts_per_week = Column(Integer, nullable=False, default=7)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    workplace_id = Column(Integer, ForeignKey("workplace.id"), nullable=False)
