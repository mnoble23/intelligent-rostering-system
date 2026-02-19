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

    assigned_shifts: Dict[int, List[Shift]] = {day: [] for day in range(7)}
    user_daily_assignments: Dict[int, Dict[int, List[Shift]]] = {}
    ordered_shifts_by_day: Dict[int, List[Shift]] = {}
    available_candidates_by_shift: Dict[int, List[int]] = {}
    assigned_staff_by_shift: Dict[int, List[int]] = {}
    hourly_assigned_staff_by_day: Dict[int, Dict[int, int]] = {}
    shift_lookup_by_id: Dict[int, Shift] = {}
    shift_day_by_id: Dict[int, int] = {}

    for day, shifts in staffable_shifts.items():
        ordered_shifts = sorted(
            shifts,
            key=lambda shift: (
                -shift_duration_hours(shift),
                shift.start_time,
                shift.end_time,
            ),
        )
        ordered_shifts_by_day[day] = ordered_shifts
        hourly_assigned_staff_by_day[day] = {
            hour: 0 for hour in range(BUSINESS_START, BUSINESS_END)
        }
        for shift in ordered_shifts:
            shift_id = id(shift)
            shift_lookup_by_id[shift_id] = shift
            shift_day_by_id[shift_id] = day
            available_candidates_by_shift[shift_id] = list(shift.staff)
            assigned_staff_by_shift[shift_id] = []

    def can_assign_user_to_shift(user_id: int, shift_id: int) -> bool:
        shift = shift_lookup_by_id[shift_id]
        day = shift_day_by_id[shift_id]
        duration_hours = shift_duration_hours(shift)
        user_daily_assignments.setdefault(user_id, {}).setdefault(day, [])
        already_assigned_today = len(user_daily_assignments[user_id][day]) > 0
        if already_assigned_today:
            return False

        _, max_hours = user_hour_limits.get(user_id, (0.0, float("inf")))
        exceeds_max_hours = user_assigned_hours.get(user_id, 0.0) + duration_hours > max_hours
        if exceeds_max_hours:
            return False

        if user_id in assigned_staff_by_shift[shift_id]:
            return False

        return True

    def apply_assignment(user_id: int, shift_id: int) -> None:
        shift = shift_lookup_by_id[shift_id]
        day = shift_day_by_id[shift_id]
        duration_hours = shift_duration_hours(shift)
        assigned_staff_by_shift[shift_id].append(user_id)
        user_daily_assignments.setdefault(user_id, {}).setdefault(day, []).append(shift)
        user_assigned_hours[user_id] = user_assigned_hours.get(user_id, 0.0) + duration_hours
        for hour in range(shift.start_time.hour, shift.end_time.hour):
            hourly_assigned_staff_by_day[day][hour] += 1

    # Phase 1: prioritize minimum coverage across business hours.
    while True:
        best_assignment: Tuple[int, int, float, int] | None = None
        # (shift_id, user_id, duration_hours, coverage_gain)

        for day, ordered_shifts in ordered_shifts_by_day.items():
            hourly_assigned_staff = hourly_assigned_staff_by_day[day]
            for shift in ordered_shifts:
                shift_id = id(shift)
                duration_hours = shift_duration_hours(shift)
                sorted_candidates = sorted(
                    available_candidates_by_shift[shift_id],
                    key=lambda user_id: (
                        -max(
                            0.0,
                            user_hour_limits.get(user_id, (0.0, float("inf")))[0]
                            - user_assigned_hours.get(user_id, 0.0),
                        ),
                        -(
                            user_hour_limits.get(user_id, (0.0, float("inf")))[1]
                            - user_assigned_hours.get(user_id, 0.0)
                        ),
                        user_assigned_hours.get(user_id, 0.0),
                        user_id,
                    ),
                )

                for user_id in sorted_candidates:
                    if not can_assign_user_to_shift(user_id, shift_id):
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
                        best_assignment = (shift_id, user_id, duration_hours, coverage_gain)

        if best_assignment is None:
            break

        shift_id, user_id, _, _ = best_assignment
        apply_assignment(user_id, shift_id)

    # Phase 2: top up users who are still below minimum weekly hours.
    while True:
        users_below_min = [
            user_id
            for user_id, (min_hours, _) in user_hour_limits.items()
            if user_assigned_hours.get(user_id, 0.0) < min_hours
        ]
        if not users_below_min:
            break

        progress = False
        users_below_min.sort(
            key=lambda user_id: (
                -(
                    user_hour_limits[user_id][0]
                    - user_assigned_hours.get(user_id, 0.0)
                ),
                user_assigned_hours.get(user_id, 0.0),
                user_id,
            )
        )

        for user_id in users_below_min:
            min_hours, _ = user_hour_limits[user_id]
            remaining_hours = min_hours - user_assigned_hours.get(user_id, 0.0)
            if remaining_hours <= 0:
                continue

            best_shift_id: int | None = None
            best_score: Tuple[float, float, int] | None = None

            for day, ordered_shifts in ordered_shifts_by_day.items():
                for shift in ordered_shifts:
                    shift_id = id(shift)
                    if user_id not in available_candidates_by_shift[shift_id]:
                        continue
                    if not can_assign_user_to_shift(user_id, shift_id):
                        continue

                    duration_hours = shift_duration_hours(shift)
                    overshoot = max(0.0, duration_hours - remaining_hours)
                    score = (
                        overshoot,
                        -duration_hours,
                        day,
                    )
                    if best_score is None or score < best_score:
                        best_score = score
                        best_shift_id = shift_id

            if best_shift_id is not None:
                apply_assignment(user_id, best_shift_id)
                progress = True

        if not progress:
            break

    for day, ordered_shifts in ordered_shifts_by_day.items():
        for shift in ordered_shifts:
            final_staff = assigned_staff_by_shift[id(shift)]
            if not final_staff:
                continue

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
