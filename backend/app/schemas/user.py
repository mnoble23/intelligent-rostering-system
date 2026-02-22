from typing import Literal
from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    name: str
    role: Literal["manager", "staff"] = "staff"
    min_hours: float = Field(default=0.0, ge=0)
    max_hours: float = Field(default=40.0, ge=0)
    password: str | None = Field(default=None, min_length=8)

class UserRead(BaseModel):
    id: int
    name: str
    role: Literal["manager", "staff"]
    min_hours: float
    max_hours: float
    is_active: bool

    class Config:
        from_attributes = True
