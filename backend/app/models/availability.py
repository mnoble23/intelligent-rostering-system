from pydantic import BaseModel
from datetime import time
from typing import Optional


class Availability(BaseModel):
    user_id: int
    day_of_week: int  # 0 = Monday, 6 = Sunday
    start_time: time
    end_time: time
    id: Optional[int] = None
