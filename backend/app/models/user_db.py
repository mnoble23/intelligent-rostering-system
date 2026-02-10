from sqlalchemy import Column, Integer, String
from app.db.base import Base

class UserDB(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
