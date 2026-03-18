from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from app.models.shift_assignment_db import ShiftAssignmentDB
from app.models.shift_db import ShiftDB
from app.models.user_db import UserDB

WeeklyAvailability = Dict[int, Dict[int, List[Tuple[time, time]]]]
UserHourLimits = Dict[int, Tuple[float, float]]
UserShiftLimits = Dict[int, Tuple[int, int]]
UserRoles = Dict[int, str]

BUSINESS_START = 6
BUSINESS_END = 22
ALLOWED_SHIFT_HOURS = (4, 6, 9)
MIN_STAFF_PER_SHIFT = 2
MIN_MANAGERS_PER_HOUR = 1
MAX_CONSECUTIVE_SHIFTS = 7
MIN_HOURS_BETWEEN_SHIFTS = 11
MANAGER_ROLE = "manager"
SOLVER_TIME_LIMIT_SECONDS = 10.0


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


def _load_cp_model() -> Any | None:
    try:
        from ortools.sat.python import cp_model as ortools_cp_model
    except ImportError:  # pragma: no cover - exercised in environments without OR-Tools.
        return None
    return ortools_cp_model


def _format_hour_label(hour: int) -> str:
    return f"{hour:02d}:00"


def _format_day_label(day_of_week: int) -> str:
    day_labels = (
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    )
    return day_labels[day_of_week]


def calculate_max_feasible_minutes_for_user(
    shifts: List["Shift"],
    week_start_date: date,
    *,
    max_consecutive_shifts: int = MAX_CONSECUTIVE_SHIFTS,
    min_hours_between_shifts: int = MIN_HOURS_BETWEEN_SHIFTS,
) -> int:
    cp_model = _load_cp_model()
    if cp_model is None or not shifts:
        return 0

    ordered_shifts = sorted(
        shifts,
        key=lambda shift: (shift.day_of_week, shift.start_time, shift.end_time),
    )

    def shift_duration_minutes(shift: Shift) -> int:
        return (shift.end_hour - shift.start_hour) * 60

    def shift_datetimes(shift: Shift) -> tuple[datetime, datetime]:
        shift_date = week_start_date + timedelta(days=shift.day_of_week)
        start_dt = datetime.combine(shift_date, shift.start_time)
        if shift.end_hour == 24:
            end_dt = datetime.combine(shift_date + timedelta(days=1), time(0, 0))
        else:
            end_dt = datetime.combine(shift_date, shift.end_time)
        return start_dt, end_dt

    def shifts_have_required_rest(earlier: Shift, later: Shift) -> bool:
        earlier_start, earlier_end = shift_datetimes(earlier)
        later_start, later_end = shift_datetimes(later)
        if later_start < earlier_start:
            earlier_start, later_start = later_start, earlier_start
            earlier_end, later_end = later_end, earlier_end
        if later_start < earlier_end:
            return False
        return later_start - earlier_end >= timedelta(hours=min_hours_between_shifts)

    model = cp_model.CpModel()
    shift_vars = [model.NewBoolVar(f"user_shift_{index}") for index, _ in enumerate(ordered_shifts)]

    for day in range(7):
        day_vars = [
            shift_vars[index]
            for index, shift in enumerate(ordered_shifts)
            if shift.day_of_week == day
        ]
        if day_vars:
            model.Add(sum(day_vars) <= 1)

    if 1 <= max_consecutive_shifts < 7:
        work_day_vars = {}
        for day in range(7):
            work_day_var = model.NewBoolVar(f"works_day_{day}")
            work_day_vars[day] = work_day_var
            day_vars = [
                shift_vars[index]
                for index, shift in enumerate(ordered_shifts)
                if shift.day_of_week == day
            ]
            if day_vars:
                model.Add(sum(day_vars) == work_day_var)
            else:
                model.Add(work_day_var == 0)

        for start_day in range(0, 7 - max_consecutive_shifts):
            model.Add(
                sum(work_day_vars[day] for day in range(start_day, start_day + max_consecutive_shifts + 1))
                <= max_consecutive_shifts
            )

    for left_index, left_shift in enumerate(ordered_shifts):
        for right_index in range(left_index + 1, len(ordered_shifts)):
            right_shift = ordered_shifts[right_index]
            if not shifts_have_required_rest(left_shift, right_shift):
                model.Add(shift_vars[left_index] + shift_vars[right_index] <= 1)

    model.Maximize(
        sum(
            shift_duration_minutes(shift) * shift_vars[index]
            for index, shift in enumerate(ordered_shifts)
        )
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 3.0
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return 0
    return int(solver.ObjectiveValue())


def calculate_max_feasible_shifts_for_user(
    shifts: List["Shift"],
    week_start_date: date,
    *,
    max_consecutive_shifts: int = MAX_CONSECUTIVE_SHIFTS,
    min_hours_between_shifts: int = MIN_HOURS_BETWEEN_SHIFTS,
) -> int:
    cp_model = _load_cp_model()
    if cp_model is None or not shifts:
        return 0

    ordered_shifts = sorted(
        shifts,
        key=lambda shift: (shift.day_of_week, shift.start_time, shift.end_time),
    )

    def shift_datetimes(shift: Shift) -> tuple[datetime, datetime]:
        shift_date = week_start_date + timedelta(days=shift.day_of_week)
        start_dt = datetime.combine(shift_date, shift.start_time)
        if shift.end_hour == 24:
            end_dt = datetime.combine(shift_date + timedelta(days=1), time(0, 0))
        else:
            end_dt = datetime.combine(shift_date, shift.end_time)
        return start_dt, end_dt

    def shifts_have_required_rest(earlier: Shift, later: Shift) -> bool:
        earlier_start, earlier_end = shift_datetimes(earlier)
        later_start, later_end = shift_datetimes(later)
        if later_start < earlier_start:
            earlier_start, later_start = later_start, earlier_start
            earlier_end, later_end = later_end, earlier_end
        if later_start < earlier_end:
            return False
        return later_start - earlier_end >= timedelta(hours=min_hours_between_shifts)

    model = cp_model.CpModel()
    shift_vars = [model.NewBoolVar(f"user_shift_count_{index}") for index, _ in enumerate(ordered_shifts)]

    for day in range(7):
        day_vars = [
            shift_vars[index]
            for index, shift in enumerate(ordered_shifts)
            if shift.day_of_week == day
        ]
        if day_vars:
            model.Add(sum(day_vars) <= 1)

    if 1 <= max_consecutive_shifts < 7:
        work_day_vars = {}
        for day in range(7):
            work_day_var = model.NewBoolVar(f"works_shift_day_{day}")
            work_day_vars[day] = work_day_var
            day_vars = [
                shift_vars[index]
                for index, shift in enumerate(ordered_shifts)
                if shift.day_of_week == day
            ]
            if day_vars:
                model.Add(sum(day_vars) == work_day_var)
            else:
                model.Add(work_day_var == 0)

        for start_day in range(0, 7 - max_consecutive_shifts):
            model.Add(
                sum(work_day_vars[day] for day in range(start_day, start_day + max_consecutive_shifts + 1))
                <= max_consecutive_shifts
            )

    for left_index, left_shift in enumerate(ordered_shifts):
        for right_index in range(left_index + 1, len(ordered_shifts)):
            right_shift = ordered_shifts[right_index]
            if not shifts_have_required_rest(left_shift, right_shift):
                model.Add(shift_vars[left_index] + shift_vars[right_index] <= 1)

    model.Maximize(sum(shift_vars))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 3.0
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return 0
    return int(solver.ObjectiveValue())


@dataclass
class Shift:
    week_start_date: date
    day_of_week: int
    start_time: time
    end_time: time
    start_hour: int
    end_hour: int
    staff: List[int] = field(default_factory=list)


def generate_weekly_shifts(
    week_start_date: date,
    business_start_hour: int = BUSINESS_START,
    business_end_hour: int = BUSINESS_END,
) -> Dict[int, List[Shift]]:
    weekly_shifts: Dict[int, List[Shift]] = {}
    for day in range(7):
        shifts: List[Shift] = []
        for start_hour in range(business_start_hour, business_end_hour):
            for duration_hours in ALLOWED_SHIFT_HOURS:
                end_hour = start_hour + duration_hours
                if end_hour > business_end_hour:
                    continue
                shift_end_time = time(hour=23, minute=59) if end_hour == 24 else time(hour=end_hour)
                shift = Shift(
                    week_start_date=week_start_date,
                    day_of_week=day,
                    start_time=time(hour=start_hour),
                    end_time=shift_end_time,
                    start_hour=start_hour,
                    end_hour=end_hour,
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
    business_start_hour: int = BUSINESS_START,
    business_end_hour: int = BUSINESS_END,
) -> Dict[int, List[Shift]]:
    cp_model = _load_cp_model()
    if cp_model is None:
        raise RosterGenerationError(
            code="solver_unavailable",
            message="Roster generation failed: constraint solver dependency is not installed.",
            explanation="The roster engine is configured to use OR-Tools CP-SAT, but the package is unavailable.",
            suggestions=[
                "Install backend dependencies again so OR-Tools is included.",
                "Verify the deployment image includes the ortools package.",
            ],
        )

    user_hour_limits = user_hour_limits or {}
    user_shift_limits = user_shift_limits or {}
    user_roles = user_roles or {}

    all_shifts = [
        shift
        for day in range(7)
        for shift in sorted(
            staffable_shifts.get(day, []),
            key=lambda item: (item.start_time, item.end_time),
        )
    ]
    if not all_shifts:
        raise RosterGenerationError(
            code="no_staffable_shifts",
            message="Roster generation failed: no feasible shifts were available to assign.",
            explanation="No generated shift had enough available staff candidates to be considered.",
            suggestions=[
                "Add or widen staff availability.",
                "Review business hours and generated shift templates.",
            ],
        )

    shift_ids = {id(shift): index for index, shift in enumerate(all_shifts)}
    shifts_by_day: Dict[int, List[Shift]] = {day: [] for day in range(7)}
    for shift in all_shifts:
        shifts_by_day[shift.day_of_week].append(shift)

    users = sorted(
        {
            user_id
            for shift in all_shifts
            for user_id in shift.staff
        }
        | set(user_hour_limits)
        | set(user_shift_limits)
        | set(user_roles)
    )
    user_names: Dict[int, str] = {}
    if users:
        user_names = {
            user.id: user.name
            for user in db.query(UserDB).filter(
                UserDB.workplace_id == workplace_id,
                UserDB.id.in_(users),
            )
        }

    def shift_duration_minutes(shift: Shift) -> int:
        return (shift.end_hour - shift.start_hour) * 60

    def shift_datetimes(shift: Shift) -> tuple[datetime, datetime]:
        shift_date = week_start_date + timedelta(days=shift.day_of_week)
        start_dt = datetime.combine(shift_date, shift.start_time)
        if shift.end_hour == 24:
            end_dt = datetime.combine(shift_date + timedelta(days=1), time(0, 0))
        else:
            end_dt = datetime.combine(shift_date, shift.end_time)
        return start_dt, end_dt

    def shifts_have_required_rest(earlier: Shift, later: Shift) -> bool:
        earlier_start, earlier_end = shift_datetimes(earlier)
        later_start, later_end = shift_datetimes(later)
        if later_start < earlier_start:
            earlier_start, later_start = later_start, earlier_start
            earlier_end, later_end = later_end, earlier_end
        if later_start < earlier_end:
            return False
        return later_start - earlier_end >= timedelta(hours=min_hours_between_shifts)

    def is_manager(user_id: int) -> bool:
        return user_roles.get(user_id, "staff").strip().lower() == MANAGER_ROLE

    def maximize_user_capacity(user_id: int, objective: str) -> int:
        user_shifts = [
            all_shifts[shift_index]
            for (candidate_user_id, shift_index) in assignment_vars
            if candidate_user_id == user_id
        ]
        if objective == "minutes":
            return calculate_max_feasible_minutes_for_user(
                user_shifts,
                week_start_date,
                max_consecutive_shifts=max_consecutive_shifts,
                min_hours_between_shifts=min_hours_between_shifts,
            )
        return calculate_max_feasible_shifts_for_user(
            user_shifts,
            week_start_date,
            max_consecutive_shifts=max_consecutive_shifts,
            min_hours_between_shifts=min_hours_between_shifts,
        )

    model = cp_model.CpModel()
    assignment_vars: Dict[tuple[int, int], Any] = {}

    for shift in all_shifts:
        shift_index = shift_ids[id(shift)]
        for user_id in sorted(set(shift.staff)):
            assignment_vars[(user_id, shift_index)] = model.NewBoolVar(
                f"assign_u{user_id}_s{shift_index}"
            )

    if not assignment_vars:
        raise RosterGenerationError(
            code="no_assignment_candidates",
            message="Roster generation failed: no staff could be assigned to any generated shift.",
            explanation="Availability filtering produced shifts, but no feasible user-shift assignments remained for the solver.",
            suggestions=[
                "Review availability data for time format or overlap issues.",
                "Check that active users exist in the workplace.",
            ],
        )

    users_below_possible_min_shifts = []
    users_below_possible_min_hours = []
    for user_id in users:
        min_shifts, _ = user_shift_limits.get(user_id, (0, 7))
        min_minutes = int(round(user_hour_limits.get(user_id, (0.0, float("inf")))[0] * 60))
        possible_shifts = maximize_user_capacity(user_id, "shifts")
        possible_minutes = maximize_user_capacity(user_id, "minutes")
        if possible_shifts < min_shifts:
            users_below_possible_min_shifts.append(
                {
                    "user_id": user_id,
                    "user_name": user_names.get(user_id, f"User {user_id}"),
                    "required_shifts": min_shifts,
                    "possible_shifts": possible_shifts,
                }
            )
        if possible_minutes < min_minutes:
            users_below_possible_min_hours.append(
                {
                    "user_id": user_id,
                    "user_name": user_names.get(user_id, f"User {user_id}"),
                    "required_hours": round(min_minutes / 60, 2),
                    "possible_hours": round(possible_minutes / 60, 2),
                }
            )

    if users_below_possible_min_shifts:
        users_below_possible_min_shifts.sort(
            key=lambda item: (item["possible_shifts"] - item["required_shifts"], item["user_id"])
        )
        first_user = users_below_possible_min_shifts[0]
        raise RosterGenerationError(
            code="min_shifts_unreachable",
            message="Roster generation failed: one or more users cannot possibly reach their minimum weekly shifts.",
            explanation="Before solving, the scheduler found users whose feasible shift options are fewer than their minimum weekly shift requirement.",
            suggestions=[
                "Increase availability for the affected user.",
                "Add more shift options that fit the user's available windows.",
                "Lower the user's minimum weekly shifts if the requirement is incorrect.",
            ],
            context={
                **first_user,
                "affected_user_ids": ",".join(str(item["user_id"]) for item in users_below_possible_min_shifts[:5]),
            },
        )

    if users_below_possible_min_hours:
        users_below_possible_min_hours.sort(
            key=lambda item: (item["possible_hours"] - item["required_hours"], item["user_id"])
        )
        first_user = users_below_possible_min_hours[0]
        raise RosterGenerationError(
            code="min_hours_unreachable",
            message="Roster generation failed: one or more users cannot possibly reach their minimum weekly hours.",
            explanation="Before solving, the scheduler found users whose individually feasible shift hours are below their minimum weekly hours.",
            suggestions=[
                "Increase availability for the affected user.",
                "Add shift lengths that better fit the user's available windows.",
                "Lower the user's minimum weekly hours if the requirement is incorrect.",
            ],
            context={
                **first_user,
                "affected_user_ids": ",".join(str(item["user_id"]) for item in users_below_possible_min_hours[:5]),
            },
        )

    uncovered_staff_hours = []
    uncovered_manager_hours = []
    for day in range(7):
        for hour in range(business_start_hour, business_end_hour):
            feasible_staff_ids = set()
            feasible_manager_ids = set()
            for shift in shifts_by_day[day]:
                if not (shift.start_hour <= hour < shift.end_hour):
                    continue
                for user_id in shift.staff:
                    feasible_staff_ids.add(user_id)
                    if is_manager(user_id):
                        feasible_manager_ids.add(user_id)

            if len(feasible_staff_ids) < min_staff_per_shift:
                uncovered_staff_hours.append(
                    {
                        "day_of_week": day,
                        "hour": hour,
                        "required_staff": min_staff_per_shift,
                        "available_candidates": len(feasible_staff_ids),
                    }
                )
            if len(feasible_manager_ids) < min_managers_per_hour:
                uncovered_manager_hours.append(
                    {
                        "day_of_week": day,
                        "hour": hour,
                        "required_managers_per_hour": min_managers_per_hour,
                        "available_manager_candidates": len(feasible_manager_ids),
                    }
                )

    if uncovered_manager_hours:
        first_gap = uncovered_manager_hours[0]
        raise RosterGenerationError(
            code="manager_coverage_unreachable",
            message="Roster generation failed: one or more hours do not have enough feasible manager coverage.",
            explanation="Before solving, the scheduler found open hours where the number of available managers is below the required hourly manager target.",
            suggestions=[
                "Increase manager availability during the uncovered hours.",
                "Reduce business hours to periods with manager coverage.",
                "Lower the minimum managers per hour setting if operationally safe.",
            ],
            context={
                **first_gap,
                "day_label": _format_day_label(first_gap["day_of_week"]),
                "hour_label": _format_hour_label(first_gap["hour"]),
                "uncovered_hours": len(uncovered_manager_hours),
            },
        )

    if uncovered_staff_hours:
        first_gap = uncovered_staff_hours[0]
        raise RosterGenerationError(
            code="staff_coverage_unreachable",
            message="Roster generation failed: one or more hours do not have enough feasible staff coverage.",
            explanation="Before solving, the scheduler found open hours where the number of available staff candidates is below the required hourly staffing target.",
            suggestions=[
                "Increase staff availability during the uncovered hours.",
                "Reduce business hours to periods with enough staff.",
                "Lower the minimum staff per shift if service levels allow.",
            ],
            context={
                **first_gap,
                "day_label": _format_day_label(first_gap["day_of_week"]),
                "hour_label": _format_hour_label(first_gap["hour"]),
                "uncovered_hours": len(uncovered_staff_hours),
            },
        )

    for day, day_shifts in shifts_by_day.items():
        for user_id in users:
            user_day_vars = [
                assignment_vars[(user_id, shift_ids[id(shift)])]
                for shift in day_shifts
                if (user_id, shift_ids[id(shift)]) in assignment_vars
            ]
            if user_day_vars:
                model.Add(sum(user_day_vars) <= 1)

    for user_id in users:
        user_vars = [
            var
            for (candidate_user_id, _), var in assignment_vars.items()
            if candidate_user_id == user_id
        ]
        if not user_vars:
            min_shifts, _ = user_shift_limits.get(user_id, (0, 0))
            min_hours, _ = user_hour_limits.get(user_id, (0.0, 0.0))
            if min_shifts > 0 or min_hours > 0:
                raise RosterGenerationError(
                    code="user_has_no_feasible_assignments",
                    message="Roster generation failed: a required user has no feasible assignments.",
                    explanation="At least one user has minimum weekly requirements but no solver-eligible shifts.",
                    suggestions=[
                        "Increase that user's availability.",
                        "Lower their minimum hour or shift requirement.",
                    ],
                    context={"user_id": user_id},
                )
            continue

        min_shifts, max_shifts = user_shift_limits.get(user_id, (0, 7))
        model.Add(sum(user_vars) >= min_shifts)
        model.Add(sum(user_vars) <= max_shifts)

        min_minutes = int(round(user_hour_limits.get(user_id, (0.0, float("inf")))[0] * 60))
        max_hours = user_hour_limits.get(user_id, (0.0, float("inf")))[1]
        max_minutes = sum(
            shift_duration_minutes(all_shifts[shift_index])
            for (candidate_user_id, shift_index), _ in assignment_vars.items()
            if candidate_user_id == user_id
        ) if max_hours == float("inf") else int(round(max_hours * 60))

        user_minutes = sum(
            shift_duration_minutes(all_shifts[shift_index]) * var
            for (candidate_user_id, shift_index), var in assignment_vars.items()
            if candidate_user_id == user_id
        )
        model.Add(user_minutes >= min_minutes)
        model.Add(user_minutes <= max_minutes)

    if 1 <= max_consecutive_shifts < 7:
        work_day_vars: Dict[tuple[int, int], Any] = {}
        for user_id in users:
            for day in range(7):
                day_vars = [
                    assignment_vars[(user_id, shift_ids[id(shift)])]
                    for shift in shifts_by_day[day]
                    if (user_id, shift_ids[id(shift)]) in assignment_vars
                ]
                work_day_var = model.NewBoolVar(f"works_u{user_id}_d{day}")
                work_day_vars[(user_id, day)] = work_day_var
                if day_vars:
                    model.Add(sum(day_vars) == work_day_var)
                else:
                    model.Add(work_day_var == 0)

            for start_day in range(0, 7 - max_consecutive_shifts):
                model.Add(
                    sum(
                        work_day_vars[(user_id, day)]
                        for day in range(start_day, start_day + max_consecutive_shifts + 1)
                    )
                    <= max_consecutive_shifts
                )

    for user_id in users:
        user_shift_indices = sorted(
            shift_index
            for (candidate_user_id, shift_index) in assignment_vars
            if candidate_user_id == user_id
        )
        for left_pos, left_index in enumerate(user_shift_indices):
            left_shift = all_shifts[left_index]
            for right_index in user_shift_indices[left_pos + 1:]:
                right_shift = all_shifts[right_index]
                if not shifts_have_required_rest(left_shift, right_shift):
                    model.Add(
                        assignment_vars[(user_id, left_index)] + assignment_vars[(user_id, right_index)] <= 1
                    )

    for day in range(7):
        for hour in range(business_start_hour, business_end_hour):
            staff_covering_vars = []
            manager_covering_vars = []
            for shift in shifts_by_day[day]:
                if not (shift.start_hour <= hour < shift.end_hour):
                    continue
                shift_index = shift_ids[id(shift)]
                for user_id in shift.staff:
                    var = assignment_vars[(user_id, shift_index)]
                    staff_covering_vars.append(var)
                    if is_manager(user_id):
                        manager_covering_vars.append(var)

            model.Add(sum(staff_covering_vars) >= min_staff_per_shift)
            model.Add(sum(manager_covering_vars) >= min_managers_per_hour)

    total_assigned_minutes = sum(
        shift_duration_minutes(all_shifts[shift_index]) * var
        for (_, shift_index), var in assignment_vars.items()
    )
    total_assignments = sum(assignment_vars.values())
    model.Minimize(total_assigned_minutes * 1000 + total_assignments)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT_SECONDS
    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RosterGenerationError(
            code="constraint_model_infeasible",
            message="Roster generation failed: no assignment satisfies the current constraints.",
            explanation="The constraint solver could not find a feasible roster that meets coverage, rest, and weekly user limits together.",
            suggestions=[
                "Relax minimum staffing or manager coverage requirements.",
                "Reduce minimum hour or shift requirements for some users.",
                "Relax minimum rest-gap or consecutive-shift settings.",
            ],
        )

    assigned_shifts: Dict[int, List[Shift]] = {day: [] for day in range(7)}
    for shift in all_shifts:
        shift_index = shift_ids[id(shift)]
        final_staff = [
            user_id
            for user_id in sorted(set(shift.staff))
            if solver.Value(assignment_vars[(user_id, shift_index)]) == 1
        ]
        if not final_staff:
            continue
        shift.staff = final_staff
        assigned_shifts[shift.day_of_week].append(shift)

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

    for day in range(7):
        for shift in assigned_shifts[day]:
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

            for user_id in shift.staff:
                db.add(
                    ShiftAssignmentDB(
                        shift_id=db_shift.id,
                        user_id=user_id,
                        workplace_id=workplace_id,
                    )
                )
            db.commit()

        assigned_shifts[day].sort(key=lambda item: (item.start_time, item.end_time))

    return assigned_shifts
