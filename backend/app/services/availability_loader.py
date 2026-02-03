from sqlalchemy.orm import Session
from app.models.availability_db import AvailabilityDB
from datetime import time
from typing import Dict, List, Tuple


TimeRange = Tuple[time, time]
WeeklyAvailability = Dict[int, Dict[int, List[TimeRange]]]


def load_weekly_availability(db: Session) -> WeeklyAvailability:
    weekly_availability: WeeklyAvailability = {day: {} for day in range(7)}

    availabilities = db.query(AvailabilityDB).all()

    for availability in availabilities:
        day = availability.day_of_week
        user_id = availability.user_id

        if user_id not in weekly_availability[day]:
            weekly_availability[day][user_id] = []

        weekly_availability[day][user_id].append(
            (availability.start_time, availability.end_time)
        )

    for day in weekly_availability:
        for user_id in weekly_availability[day]:
            weekly_availability[day][user_id].sort(key=lambda x: x[0])

    return weekly_availability
