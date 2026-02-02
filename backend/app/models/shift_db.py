from sqlalchemy import Column, Integer, Time
from app.db.base import Base

class ShiftDB(Base):
    __tablename__ = "shift"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0 = Monday, 6 = Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
