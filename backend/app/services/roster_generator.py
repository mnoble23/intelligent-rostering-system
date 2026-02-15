from dataclasses import dataclass, field
from datetime import time
from typing import Dict, List, Tuple
from app.models.shift_db import ShiftDB
from app.models.shift_assignment_db import ShiftAssignmentDB
from sqlalchemy.orm import Session

WeeklyAvailability = Dict[int, Dict[int, List[Tuple[time, time]]]]

BUSINESS_START = 6
BUSINESS_END = 22
MIN_SHIFT_HOURS = 4
MIN_STAFF_PER_SHIFT = 2

@dataclass
class Shift:
    day_of_week: int
    start_time: time
    end_time: time
    staff: List[int] = field(default_factory=list)

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

def match_availability_to_shifts(
    weekly_availability: WeeklyAvailability,
    weekly_shifts: Dict[int, List[Shift]],
    min_staff_per_shift: int = MIN_STAFF_PER_SHIFT
) -> Dict[int, List[Shift]]:
    staffable_shifts: Dict[int, List[Shift]] = {}

    for day, shifts in weekly_shifts.items():
        staffable_shifts[day] = []

        for shift in shifts:
            available_users = []

            for user_id, ranges in weekly_availability.get(day, {}).items():
                for start, end in ranges:
                    if start <= shift.start_time and end >= shift.end_time:
                        available_users.append(user_id)
                        break

            if len(available_users) >= min_staff_per_shift:
                shift.staff = available_users
                staffable_shifts[day].append(shift)

    return staffable_shifts

def assign_staff_to_shifts(
    db: Session,
    staffable_shifts: Dict[int, List[Shift]],
    min_staff_per_shift: int = MIN_STAFF_PER_SHIFT,
) -> Dict[int, List[Shift]]:
    
    db.query(ShiftAssignmentDB).delete()  
    db.query(ShiftDB).delete()            
    db.commit()
    assigned_shifts: Dict[int, List[Shift]] = {}
    user_daily_assignments: Dict[int, Dict[int, List[Shift]]] = {}

    for day, shifts in staffable_shifts.items():
        assigned_shifts[day] = []

        for shift in shifts:
            final_staff: List[int] = []

            for user_id in shift.staff:
                user_daily_assignments.setdefault(user_id, {}).setdefault(day, [])

                overlap = any(
                    not (shift.end_time <= assigned.start_time or shift.start_time >= assigned.end_time)
                    for assigned in user_daily_assignments[user_id][day]
                )

                if not overlap:
                    final_staff.append(user_id)
                    user_daily_assignments[user_id][day].append(shift)

                if len(final_staff) >= min_staff_per_shift:
                    break

            if len(final_staff) >= min_staff_per_shift:
                shift.staff = final_staff
                assigned_shifts[day].append(shift)

                db_shift = (
                    db.query(ShiftDB)
                    .filter_by(
                        day_of_week=shift.day_of_week,
                        start_time=shift.start_time,
                        end_time=shift.end_time,
                    )
                    .first()
                )
                if not db_shift:
                    db_shift = ShiftDB(
                        day_of_week=shift.day_of_week,
                        start_time=shift.start_time,
                        end_time=shift.end_time,
                    )
                    db.add(db_shift)
                    db.commit()
                    db.refresh(db_shift)

                for uid in shift.staff:
                    exists = (
                        db.query(ShiftAssignmentDB)
                        .filter_by(shift_id=db_shift.id, user_id=uid)
                        .first()
                    )
                    if not exists:
                        db_assignment = ShiftAssignmentDB(
                            shift_id=db_shift.id, user_id=uid
                        )
                        db.add(db_assignment)
                db.commit()

    return assigned_shifts