from sqlalchemy import Column, Date, ForeignKey, Integer, Time
from app.db.base import Base


class ShiftDB(Base):
    __tablename__ = "shift"

    id = Column(Integer, primary_key=True, index=True)
    workplace_id = Column(Integer, ForeignKey("workplace.id"), nullable=False, index=True)
    week_start_date = Column(Date, nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
