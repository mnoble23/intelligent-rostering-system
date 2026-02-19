from dataclasses import dataclass, field
from datetime import time
from typing import Dict, List, Tuple
from app.models.shift_db import ShiftDB
from app.models.shift_assignment_db import ShiftAssignmentDB
from sqlalchemy.orm import Session

WeeklyAvailability = Dict[int, Dict[int, List[Tuple[time, time]]]]
UserHourLimits = Dict[int, Tuple[float, float]]

BUSINESS_START = 6
BUSINESS_END = 22
ALLOWED_SHIFT_HOURS = (4, 6, 9)
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
        for start_hour in range(BUSINESS_START, BUSINESS_END):
            for duration_hours in ALLOWED_SHIFT_HOURS:
                end_hour = start_hour + duration_hours
                if end_hour > BUSINESS_END:
                    continue
                shift = Shift(
                    day_of_week=day,
                    start_time=time(hour=start_hour),
                    end_time=time(hour=end_hour),
                )
                shifts.append(shift)
        weekly_shifts[day] = shifts
    return weekly_shifts

def match_availability_to_shifts(
    weekly_availability: WeeklyAvailability,
    weekly_shifts: Dict[int, List[Shift]],
    min_available_staff: int = 1,
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

            if len(available_users) >= min_available_staff:
                shift.staff = available_users
                staffable_shifts[day].append(shift)

    return staffable_shifts

def assign_staff_to_shifts(
    db: Session,
    staffable_shifts: Dict[int, List[Shift]],
    min_staff_per_shift: int = MIN_STAFF_PER_SHIFT,
    user_hour_limits: UserHourLimits | None = None,
) -> Dict[int, List[Shift]]:
    def shift_duration_hours(shift: Shift) -> float:
        return (
            (shift.end_time.hour * 60 + shift.end_time.minute)
            - (shift.start_time.hour * 60 + shift.start_time.minute)
        ) / 60.0

    user_hour_limits = user_hour_limits or {}
    user_assigned_hours: Dict[int, float] = {}
    for shifts in staffable_shifts.values():
        for shift in shifts:
            for user_id in shift.staff:
                user_assigned_hours.setdefault(user_id, 0.0)
    for user_id in user_hour_limits:
        user_assigned_hours.setdefault(user_id, 0.0)

    db.query(ShiftAssignmentDB).delete()  
    db.query(ShiftDB).delete()            
    db.commit()
    assigned_shifts: Dict[int, List[Shift]] = {}
    user_daily_assignments: Dict[int, Dict[int, List[Shift]]] = {}

    for day, shifts in staffable_shifts.items():
        assigned_shifts[day] = []
        ordered_shifts = sorted(
            shifts,
            key=lambda shift: (
                -shift_duration_hours(shift),
                shift.start_time,
                shift.end_time,
            ),
        )
        available_candidates_by_shift = {
            id(shift): list(shift.staff) for shift in ordered_shifts
        }
        assigned_staff_by_shift: Dict[int, List[int]] = {id(shift): [] for shift in ordered_shifts}
        hourly_assigned_staff = {
            hour: 0 for hour in range(BUSINESS_START, BUSINESS_END)
        }

        while True:
            best_assignment: Tuple[Shift, int, float, int] | None = None
            # (shift, user_id, duration_hours, coverage_gain)

            for shift in ordered_shifts:
                duration_hours = shift_duration_hours(shift)
                sorted_candidates = sorted(
                    available_candidates_by_shift[id(shift)],
                    key=lambda user_id: (
                        -(
                            user_hour_limits.get(user_id, (0.0, float("inf")))[1]
                            - user_assigned_hours.get(user_id, 0.0)
                        ),
                        user_assigned_hours.get(user_id, 0.0),
                        user_id,
                    ),
                )

                for user_id in sorted_candidates:
                    user_daily_assignments.setdefault(user_id, {}).setdefault(day, [])
                    already_assigned_today = len(user_daily_assignments[user_id][day]) > 0
                    _, max_hours = user_hour_limits.get(user_id, (0.0, float("inf")))
                    exceeds_max_hours = user_assigned_hours.get(user_id, 0.0) + duration_hours > max_hours

                    if already_assigned_today or exceeds_max_hours:
                        continue

                    coverage_gain = sum(
                        1
                        for hour in range(shift.start_time.hour, shift.end_time.hour)
                        if hourly_assigned_staff[hour] < min_staff_per_shift
                    )
                    if coverage_gain <= 0:
                        continue

                    if (
                        best_assignment is None
                        or coverage_gain > best_assignment[3]
                        or (
                            coverage_gain == best_assignment[3]
                            and duration_hours > best_assignment[2]
                        )
                        or (
                            coverage_gain == best_assignment[3]
                            and duration_hours == best_assignment[2]
                            and user_assigned_hours.get(user_id, 0.0)
                            < user_assigned_hours.get(best_assignment[1], 0.0)
                        )
                    ):
                        best_assignment = (shift, user_id, duration_hours, coverage_gain)

            if best_assignment is None:
                break

            shift, user_id, duration_hours, _ = best_assignment
            assigned_staff_by_shift[id(shift)].append(user_id)
            user_daily_assignments[user_id][day].append(shift)
            user_assigned_hours[user_id] = user_assigned_hours.get(user_id, 0.0) + duration_hours
            for hour in range(shift.start_time.hour, shift.end_time.hour):
                hourly_assigned_staff[hour] += 1

        for shift in ordered_shifts:
            final_staff = assigned_staff_by_shift[id(shift)]
            if final_staff:
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

        assigned_shifts[day].sort(key=lambda shift: (shift.start_time, shift.end_time))

    return assigned_shifts
