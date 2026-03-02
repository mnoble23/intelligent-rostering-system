from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.base import Base


class WorkplaceDB(Base):
    __tablename__ = "workplace"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    min_staff_per_shift = Column(Integer, nullable=False, default=2, server_default="2")
    min_managers_per_hour = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
