from pydantic import BaseModel
from datetime import time
from typing import List

class AvailabilityBase(BaseModel):
    user_id: int
    day_of_week: int  # 0 = Monday, 6 = Sunday
    start_time: time
    end_time: time

class AvailabilityCreate(AvailabilityBase):
    pass


class AvailabilityBulkCreate(BaseModel):
    availabilities: List[AvailabilityCreate]

class AvailabilityResponse(AvailabilityBase):
    id: int

    class Config:
        from_attributes = True
