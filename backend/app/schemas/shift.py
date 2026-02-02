from pydantic import BaseModel
from datetime import time

class ShiftBase(BaseModel):
    user_id: int
    day_of_week: int
    start_time: time
    end_time: time

class ShiftResponse(ShiftBase):
    id: int

    class Config:
        from_attributes = True
