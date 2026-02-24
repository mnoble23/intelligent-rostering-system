from sqlalchemy import Column, ForeignKey, Integer, Time
from app.db.base import Base


class AvailabilityDB(Base):
    __tablename__ = "availability"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    workplace_id = Column(Integer, ForeignKey("workplace.id"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
