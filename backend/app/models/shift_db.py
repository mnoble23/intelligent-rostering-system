from sqlalchemy import Column, Date, Integer, Time
from app.db.base import Base

class ShiftDB(Base):
    __tablename__ = "shift"

    id = Column(Integer, primary_key=True, index=True)
    week_start_date = Column(Date, nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False) 
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

