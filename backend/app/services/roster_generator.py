from dataclasses import dataclass
from datetime import time
from typing import Dict, List

BUSINESS_START = 6
BUSINESS_END = 22
MIN_SHIFT_HOURS = 4

@dataclass
class Shift:
    day_of_week: int
    start_time: time
    end_time: time

def generate_weekly_shifts() -> Dict[int, List[Shift]]:
    weekly_shifts: Dict[int, List[Shift]] = {}
    for day in range(7):
        shifts: List[Shift] = []
        start_hour = BUSINESS_START
        while start_hour + MIN_SHIFT_HOURS <= BUSINESS_END:
            shift = Shift(
                day_of_week=day,
                start_time=time(hour=start_hour),
                end_time=time(hour=min(start_hour + MIN_SHIFT_HOURS, BUSINESS_END))
            )
            shifts.append(shift)
            start_hour += MIN_SHIFT_HOURS
        weekly_shifts[day] = shifts
    return weekly_shifts
