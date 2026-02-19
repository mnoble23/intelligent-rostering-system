from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    name: str
    min_hours: float = Field(default=0.0, ge=0)
    max_hours: float = Field(default=40.0, ge=0)

class UserRead(BaseModel):
    id: int
    name: str
    min_hours: float
    max_hours: float

    class Config:
        from_attributes = True
