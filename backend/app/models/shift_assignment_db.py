from sqlalchemy import Column, Integer, ForeignKey
from app.db.base import Base

class ShiftAssignmentDB(Base):
    __tablename__ = "shift_assignment"

    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey("shift.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
