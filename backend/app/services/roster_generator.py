from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from app.models.shift_assignment_db import ShiftAssignmentDB
from app.models.shift_db import ShiftDB

WeeklyAvailability = Dict[int, Dict[int, List[Tuple[time, time]]]]
UserHourLimits = Dict[int, Tuple[float, float]]
UserShiftLimits = Dict[int, Tuple[int, int]]
UserRoles = Dict[int, str]

BUSINESS_START = 6
BUSINESS_END = 22
ALLOWED_SHIFT_HOURS = (4, 6, 9)
MIN_STAFF_PER_SHIFT = 2
MIN_MANAGERS_PER_HOUR = 1
MAX_CONSECUTIVE_SHIFTS = 5
MIN_HOURS_BETWEEN_SHIFTS = 11
MANAGER_ROLE = "manager"


class RosterGenerationError(ValueError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        explanation: str,
        suggestions: List[str] | None = None,
        context: Dict[str, int | float | str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.explanation = explanation
        self.suggestions = suggestions or []
        self.context = context or {}


@dataclass
class Shift:
    week_start_date: date
    day_of_week: int
    start_time: time
    end_time: time
    staff: List[int] = field(default_factory=list)


def generate_weekly_shifts(week_start_date: date) -> Dict[int, List[Shift]]:
    weekly_shifts: Dict[int, List[Shift]] = {}
    for day in range(7):
        shifts: List[Shift] = []
        for start_hour in range(BUSINESS_START, BUSINESS_END):
            for duration_hours in ALLOWED_SHIFT_HOURS:
                end_hour = start_hour + duration_hours
                if end_hour > BUSINESS_END:
                    continue
                shift = Shift(
                    week_start_date=week_start_date,
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
    week_start_date: date,
    workplace_id: int,
    min_staff_per_shift: int = MIN_STAFF_PER_SHIFT,
    user_hour_limits: UserHourLimits | None = None,
    user_shift_limits: UserShiftLimits | None = None,
    user_roles: UserRoles | None = None,
    min_managers_per_hour: int = MIN_MANAGERS_PER_HOUR,
    max_consecutive_shifts: int = MAX_CONSECUTIVE_SHIFTS,
    min_hours_between_shifts: int = MIN_HOURS_BETWEEN_SHIFTS,
) -> Dict[int, List[Shift]]:
    def shift_duration_hours(shift: Shift) -> float:
        return (
            (shift.end_time.hour * 60 + shift.end_time.minute)
            - (shift.start_time.hour * 60 + shift.start_time.minute)
        ) / 60.0

    user_hour_limits = user_hour_limits or {}
    user_shift_limits = user_shift_limits or {}
    user_roles = user_roles or {}
    user_assigned_hours: Dict[int, float] = {}
    user_assigned_shift_counts: Dict[int, int] = {}
    for shifts in staffable_shifts.values():
        for shift in shifts:
            for user_id in shift.staff:
                user_assigned_hours.setdefault(user_id, 0.0)
                user_assigned_shift_counts.setdefault(user_id, 0)
    for user_id in user_hour_limits:
        user_assigned_hours.setdefault(user_id, 0.0)
        user_assigned_shift_counts.setdefault(user_id, 0)
    for user_id in user_shift_limits:
        user_assigned_shift_counts.setdefault(user_id, 0)

    assigned_shifts: Dict[int, List[Shift]] = {day: [] for day in range(7)}
    user_daily_assignments: Dict[int, Dict[int, List[Shift]]] = {}
    ordered_shifts_by_day: Dict[int, List[Shift]] = {}
    available_candidates_by_shift: Dict[int, List[int]] = {}
    assigned_staff_by_shift: Dict[int, List[int]] = {}
    hourly_assigned_staff_by_day: Dict[int, Dict[int, int]] = {}
    hourly_assigned_managers_by_day: Dict[int, Dict[int, int]] = {}
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
        hourly_assigned_managers_by_day[day] = {
            hour: 0 for hour in range(BUSINESS_START, BUSINESS_END)
        }
        for shift in ordered_shifts:
            shift_id = id(shift)
            shift_lookup_by_id[shift_id] = shift
            shift_day_by_id[shift_id] = day
            available_candidates_by_shift[shift_id] = list(shift.staff)
            assigned_staff_by_shift[shift_id] = []

    def shift_datetimes(shift: Shift) -> tuple[datetime, datetime]:
        shift_date = week_start_date + timedelta(days=shift.day_of_week)
        start_dt = datetime.combine(shift_date, shift.start_time)
        end_dt = datetime.combine(shift_date, shift.end_time)
        return start_dt, end_dt

    def would_exceed_max_consecutive_shifts(user_id: int, candidate_day: int) -> bool:
        assigned_days = set(user_daily_assignments.get(user_id, {}).keys())
        assigned_days.add(candidate_day)
        return projected_consecutive_run(user_id, candidate_day) > max_consecutive_shifts

    def _max_consecutive_run(assigned_days: set[int]) -> int:
        max_run = 0
        current_run = 0
        for day in range(7):
            if day in assigned_days:
                current_run += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 0
        return max_run

    def projected_consecutive_run(user_id: int, candidate_day: int) -> int:
        assigned_days = set(user_daily_assignments.get(user_id, {}).keys())
        assigned_days.add(candidate_day)
        return _max_consecutive_run(assigned_days)

    def has_minimum_rest_gap(user_id: int, candidate_shift: Shift) -> bool:
        candidate_start, candidate_end = shift_datetimes(candidate_shift)
        required_gap = timedelta(hours=min_hours_between_shifts)
        for assigned_shifts_by_day in user_daily_assignments.get(user_id, {}).values():
            for assigned_shift in assigned_shifts_by_day:
                assigned_start, assigned_end = shift_datetimes(assigned_shift)
                if candidate_start >= assigned_end:
                    gap = candidate_start - assigned_end
                elif assigned_start >= candidate_end:
                    gap = assigned_start - candidate_end
                else:
                    return False
                if gap < required_gap:
                    return False
        return True

    def can_assign_user_to_shift(user_id: int, shift_id: int) -> bool:
        shift = shift_lookup_by_id[shift_id]
        day = shift_day_by_id[shift_id]
        duration_hours = shift_duration_hours(shift)
        user_daily_assignments.setdefault(user_id, {}).setdefault(day, [])
        already_assigned_today = len(user_daily_assignments[user_id][day]) > 0
        if already_assigned_today:
            return False

        if would_exceed_max_consecutive_shifts(user_id, day):
            return False

        if not has_minimum_rest_gap(user_id, shift):
            return False

        _, max_shifts = user_shift_limits.get(user_id, (0, 7))
        exceeds_max_shifts = user_assigned_shift_counts.get(user_id, 0) + 1 > max_shifts
        if exceeds_max_shifts:
            return False

        _, max_hours = user_hour_limits.get(user_id, (0.0, float("inf")))
        exceeds_max_hours = user_assigned_hours.get(user_id, 0.0) + duration_hours > max_hours
        if exceeds_max_hours:
            return False

        if user_id in assigned_staff_by_shift[shift_id]:
            return False

        return True

    def is_manager(user_id: int) -> bool:
        return user_roles.get(user_id, "staff").strip().lower() == MANAGER_ROLE

    def apply_assignment(user_id: int, shift_id: int) -> None:
        shift = shift_lookup_by_id[shift_id]
        day = shift_day_by_id[shift_id]
        duration_hours = shift_duration_hours(shift)
        assigned_staff_by_shift[shift_id].append(user_id)
        user_daily_assignments.setdefault(user_id, {}).setdefault(day, []).append(shift)
        user_assigned_hours[user_id] = user_assigned_hours.get(user_id, 0.0) + duration_hours
        user_assigned_shift_counts[user_id] = user_assigned_shift_counts.get(user_id, 0) + 1
        for hour in range(shift.start_time.hour, shift.end_time.hour):
            hourly_assigned_staff_by_day[day][hour] += 1
            if is_manager(user_id):
                hourly_assigned_managers_by_day[day][hour] += 1

    while True:
        best_manager_assignment: Tuple[int, int, float, int, int] | None = None

        for day, ordered_shifts in ordered_shifts_by_day.items():
            hourly_assigned_managers = hourly_assigned_managers_by_day[day]
            for shift in ordered_shifts:
                shift_id = id(shift)
                duration_hours = shift_duration_hours(shift)
                manager_candidates = [
                    user_id
                    for user_id in available_candidates_by_shift[shift_id]
                    if is_manager(user_id)
                ]
                sorted_manager_candidates = sorted(
                    manager_candidates,
                    key=lambda user_id: (
                        projected_consecutive_run(user_id, day),
                        user_assigned_shift_counts.get(user_id, 0),
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

                for user_id in sorted_manager_candidates:
                    if not can_assign_user_to_shift(user_id, shift_id):
                        continue

                    manager_coverage_gain = sum(
                        1
                        for hour in range(shift.start_time.hour, shift.end_time.hour)
                        if hourly_assigned_managers[hour] < min_managers_per_hour
                    )
                    if manager_coverage_gain <= 0:
                        continue

                    if (
                        best_manager_assignment is None
                        or manager_coverage_gain > best_manager_assignment[3]
                        or (
                            manager_coverage_gain == best_manager_assignment[3]
                            and duration_hours > best_manager_assignment[2]
                        )
                        or (
                            manager_coverage_gain == best_manager_assignment[3]
                            and duration_hours == best_manager_assignment[2]
                            and projected_consecutive_run(user_id, day)
                            < projected_consecutive_run(
                                best_manager_assignment[1],
                                best_manager_assignment[4],
                            )
                        )
                        or (
                            manager_coverage_gain == best_manager_assignment[3]
                            and duration_hours == best_manager_assignment[2]
                            and projected_consecutive_run(user_id, day)
                            == projected_consecutive_run(
                                best_manager_assignment[1],
                                best_manager_assignment[4],
                            )
                            and user_assigned_shift_counts.get(user_id, 0)
                            < user_assigned_shift_counts.get(best_manager_assignment[1], 0)
                        )
                        or (
                            manager_coverage_gain == best_manager_assignment[3]
                            and duration_hours == best_manager_assignment[2]
                            and user_assigned_hours.get(user_id, 0.0)
                            < user_assigned_hours.get(best_manager_assignment[1], 0.0)
                        )
                    ):
                        best_manager_assignment = (
                            shift_id,
                            user_id,
                            duration_hours,
                            manager_coverage_gain,
                            day,
                        )

        if best_manager_assignment is None:
            break

        shift_id, user_id, _, _, _ = best_manager_assignment
        apply_assignment(user_id, shift_id)

    while True:
        best_assignment: Tuple[int, int, float, int, int] | None = None

        for day, ordered_shifts in ordered_shifts_by_day.items():
            hourly_assigned_staff = hourly_assigned_staff_by_day[day]
            for shift in ordered_shifts:
                shift_id = id(shift)
                duration_hours = shift_duration_hours(shift)
                sorted_candidates = sorted(
                    available_candidates_by_shift[shift_id],
                    key=lambda user_id: (
                        projected_consecutive_run(user_id, day),
                        user_assigned_shift_counts.get(user_id, 0),
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
                            and projected_consecutive_run(user_id, day)
                            < projected_consecutive_run(best_assignment[1], best_assignment[4])
                        )
                        or (
                            coverage_gain == best_assignment[3]
                            and duration_hours == best_assignment[2]
                            and projected_consecutive_run(user_id, day)
                            == projected_consecutive_run(best_assignment[1], best_assignment[4])
                            and user_assigned_shift_counts.get(user_id, 0)
                            < user_assigned_shift_counts.get(best_assignment[1], 0)
                        )
                        or (
                            coverage_gain == best_assignment[3]
                            and duration_hours == best_assignment[2]
                            and user_assigned_hours.get(user_id, 0.0)
                            < user_assigned_hours.get(best_assignment[1], 0.0)
                        )
                    ):
                        best_assignment = (shift_id, user_id, duration_hours, coverage_gain, day)

        if best_assignment is None:
            break

        shift_id, user_id, _, _, _ = best_assignment
        apply_assignment(user_id, shift_id)

    while True:
        users_below_min_shifts = [
            user_id
            for user_id, (min_shifts, _) in user_shift_limits.items()
            if user_assigned_shift_counts.get(user_id, 0) < min_shifts
        ]
        if not users_below_min_shifts:
            break

        progress = False
        users_below_min_shifts.sort(
            key=lambda user_id: (
                -(user_shift_limits[user_id][0] - user_assigned_shift_counts.get(user_id, 0)),
                user_assigned_shift_counts.get(user_id, 0),
                user_id,
            )
        )

        for user_id in users_below_min_shifts:
            min_shifts, _ = user_shift_limits[user_id]
            remaining_shifts = min_shifts - user_assigned_shift_counts.get(user_id, 0)
            if remaining_shifts <= 0:
                continue

            best_shift_id: int | None = None
            best_score: Tuple[int, float, int] | None = None

            for day, ordered_shifts in ordered_shifts_by_day.items():
                for shift in ordered_shifts:
                    shift_id = id(shift)
                    if user_id not in available_candidates_by_shift[shift_id]:
                        continue
                    if not can_assign_user_to_shift(user_id, shift_id):
                        continue

                    duration_hours = shift_duration_hours(shift)
                    coverage_gain = sum(
                        1
                        for hour in range(shift.start_time.hour, shift.end_time.hour)
                        if hourly_assigned_staff_by_day[day][hour] < min_staff_per_shift
                    )
                    score = (
                        -coverage_gain,
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

    uncovered_manager_hours: List[Tuple[int, int]] = []
    for day in range(7):
        for hour in range(BUSINESS_START, BUSINESS_END):
            if hourly_assigned_managers_by_day[day][hour] < min_managers_per_hour:
                uncovered_manager_hours.append((day, hour))
    if uncovered_manager_hours:
        first_uncovered_day, first_uncovered_hour = uncovered_manager_hours[0]
        raise RosterGenerationError(
            code="manager_coverage_unmet",
            message="Roster generation failed: manager coverage target could not be met.",
            explanation=(
                "At least one open hour has fewer managers assigned than required."
            ),
            suggestions=[
                "Increase manager availability for the uncovered period.",
                "Lower the minimum managers per hour setting if operationally safe.",
                "Relax rest-gap or consecutive-shift rules if they are too restrictive.",
            ],
            context={
                "day_of_week": first_uncovered_day,
                "hour": first_uncovered_hour,
                "required_managers_per_hour": min_managers_per_hour,
            },
        )

    uncovered_staff_hours: List[Tuple[int, int]] = []
    for day in range(7):
        for hour in range(BUSINESS_START, BUSINESS_END):
            if hourly_assigned_staff_by_day[day][hour] < min_staff_per_shift:
                uncovered_staff_hours.append((day, hour))
    if uncovered_staff_hours:
        first_uncovered_day, first_uncovered_hour = uncovered_staff_hours[0]
        assigned_count = hourly_assigned_staff_by_day[first_uncovered_day][first_uncovered_hour]
        raise RosterGenerationError(
            code="staff_coverage_unmet",
            message="Roster generation failed: minimum staff coverage could not be met.",
            explanation=(
                "At least one open hour has fewer assigned team members than required."
            ),
            suggestions=[
                "Collect more availability for the uncovered period.",
                "Reduce minimum staff per shift if service levels allow.",
                "Review max-hours and max-shifts limits for key users.",
            ],
            context={
                "day_of_week": first_uncovered_day,
                "hour": first_uncovered_hour,
                "assigned_staff": assigned_count,
                "required_staff": min_staff_per_shift,
            },
        )

    users_below_min_shifts = [
        (
            user_id,
            user_assigned_shift_counts.get(user_id, 0),
            min_shifts,
        )
        for user_id, (min_shifts, _) in user_shift_limits.items()
        if user_assigned_shift_counts.get(user_id, 0) < min_shifts
    ]
    if users_below_min_shifts:
        user_id, assigned_shifts, required_shifts = users_below_min_shifts[0]
        raise RosterGenerationError(
            code="min_shifts_unmet",
            message="Roster generation failed: one or more users did not reach minimum weekly shifts.",
            explanation=(
                "The scheduler could not satisfy minimum weekly shift targets while respecting all constraints."
            ),
            suggestions=[
                "Lower minimum shifts for affected users.",
                "Increase those users' availability windows.",
                "Relax constraints such as rest gaps or consecutive-shift limits.",
            ],
            context={
                "user_id": user_id,
                "assigned_shifts": assigned_shifts,
                "required_shifts": required_shifts,
            },
        )

    existing_shift_ids = [
        shift_id
        for (shift_id,) in db.query(ShiftDB.id)
        .filter_by(week_start_date=week_start_date, workplace_id=workplace_id)
        .all()
    ]
    if existing_shift_ids:
        db.query(ShiftAssignmentDB).filter(
            ShiftAssignmentDB.shift_id.in_(existing_shift_ids),
            ShiftAssignmentDB.workplace_id == workplace_id,
        ).delete(synchronize_session=False)
    db.query(ShiftDB).filter_by(
        week_start_date=week_start_date,
        workplace_id=workplace_id,
    ).delete(synchronize_session=False)
    db.commit()

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
                    workplace_id=workplace_id,
                    week_start_date=week_start_date,
                    day_of_week=shift.day_of_week,
                    start_time=shift.start_time,
                    end_time=shift.end_time,
                )
                .first()
            )
            if not db_shift:
                db_shift = ShiftDB(
                    workplace_id=workplace_id,
                    week_start_date=week_start_date,
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
                    .filter_by(shift_id=db_shift.id, user_id=uid, workplace_id=workplace_id)
                    .first()
                )
                if not exists:
                    db_assignment = ShiftAssignmentDB(
                        shift_id=db_shift.id,
                        user_id=uid,
                        workplace_id=workplace_id,
                    )
                    db.add(db_assignment)
            db.commit()

        assigned_shifts[day].sort(key=lambda shift: (shift.start_time, shift.end_time))

    return assigned_shifts
