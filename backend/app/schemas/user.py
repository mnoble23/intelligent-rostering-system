from typing import Literal
from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    name: str
    role: Literal["manager", "staff"] = "staff"
    min_hours: float = Field(default=0.0, ge=0)
    max_hours: float = Field(default=40.0, ge=0)
    min_shifts_per_week: int = Field(default=1, ge=0, le=7)
    max_shifts_per_week: int = Field(default=7, ge=0, le=7)
    password: str | None = Field(default=None, min_length=8)

class UserRead(BaseModel):
    id: int
    name: str
    role: Literal["manager", "staff"]
    min_hours: float
    max_hours: float
    min_shifts_per_week: int
    max_shifts_per_week: int
    is_active: bool

    class Config:
        from_attributes = True
