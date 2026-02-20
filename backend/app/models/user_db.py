from sqlalchemy import Column, Float, Integer, String
from app.db.base import Base

class UserDB(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="staff")
    min_hours = Column(Float, nullable=False, default=0.0)
    max_hours = Column(Float, nullable=False, default=40.0)
