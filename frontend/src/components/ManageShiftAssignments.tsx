import { useCallback, useEffect, useMemo, useState } from "react";
import API, { formatApiError } from "../services/api";
import RosterTable, { type EmployeeRow, type ShiftAssignment } from "./RosterTable";
import "./ManageShiftAssignments.css";

interface User {
  id: number;
  name: string;
}

interface ShiftUpsertResponse {
  id: number;
}

const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function formatDayLabel(dayIndex: number, weekStartDate?: string) {
  if (!weekStartDate) return days[dayIndex];
  const [year, month, day] = weekStartDate.split("-").map(Number);
  const baseDate = new Date(year, month - 1, day);
  baseDate.setDate(baseDate.getDate() + dayIndex);
  const mm = String(baseDate.getMonth() + 1).padStart(2, "0");
  const dd = String(baseDate.getDate()).padStart(2, "0");
  return `${days[dayIndex]} ${dd}/${mm}`;
}

function formatTime(timeStr: string) {
  const [hour, minute] = timeStr.split(":").map(Number);
  const ampm = hour >= 12 ? "PM" : "AM";
  const hour12 = hour % 12 || 12;
  return `${hour12}:${minute.toString().padStart(2, "0")} ${ampm}`;
}

function toHHMM(timeStr: string) {
  const [hour = "00", minute = "00"] = timeStr.split(":");
  return `${hour.padStart(2, "0")}:${minute.padStart(2, "0")}`;
}

function validateShiftRange(start: string, end: string) {
  if (!start || !end) return "Choose both start and end times.";
  if (end <= start) return "End time must be later than start time.";
  return null;
}

interface ManageShiftAssignmentsProps {
  weekStartDate?: string;
}

export default function ManageShiftAssignments({ weekStartDate }: ManageShiftAssignmentsProps) {
  const [users, setUsers] = useState<EmployeeRow[]>([]);
  const [shifts, setShifts] = useState<ShiftAssignment[]>([]);
  const [selectedCell, setSelectedCell] = useState<{ userId: number; dayIndex: number } | null>(null);
  const [currentShiftId, setCurrentShiftId] = useState<number | "">("");
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("17:00");
  const [status, setStatus] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [usersRes, shiftsRes] = await Promise.all([
        API.get("/users/"),
        API.get("/roster", weekStartDate ? { params: { week_start_date: weekStartDate } } : undefined),
      ]);
      setUsers(usersRes.data.map((user: User) => ({ id: user.id, name: user.name })));
      setShifts(shiftsRes.data);
    } catch (err) {
      console.error(err);
      setStatus(formatApiError(err, { fallbackMessage: "Failed to load users and shifts." }));
    }
  }, [weekStartDate]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const sortedShifts = useMemo(
    () =>
      [...shifts].sort((a, b) => {
        if (a.day_of_week !== b.day_of_week) return a.day_of_week - b.day_of_week;
        return a.start_time.localeCompare(b.start_time);
      }),
    [shifts]
  );

  const dayShiftOptions = useMemo(() => {
    if (!selectedCell) return [];
    return sortedShifts.filter(shift => shift.day_of_week === selectedCell.dayIndex);
  }, [selectedCell, sortedShifts]);

  const assignedShiftsForSelection = useMemo(() => {
    if (!selectedCell) return [];
    return dayShiftOptions.filter(shift => shift.staff.some(person => person.id === selectedCell.userId));
  }, [dayShiftOptions, selectedCell]);

  useEffect(() => {
    if (!selectedCell) return;

    const assignedShift = assignedShiftsForSelection[0];
    if (assignedShift) {
      setCurrentShiftId(assignedShift.id);
      setStartTime(toHHMM(assignedShift.start_time));
      setEndTime(toHHMM(assignedShift.end_time));
      return;
    }

    const firstDayShift = dayShiftOptions[0];
    setCurrentShiftId("");
    if (firstDayShift) {
      setStartTime(toHHMM(firstDayShift.start_time));
      setEndTime(toHHMM(firstDayShift.end_time));
    } else {
      setStartTime("09:00");
      setEndTime("17:00");
    }
  }, [selectedCell, assignedShiftsForSelection, dayShiftOptions]);

  const ensureShiftForSelectedDay = async () => {
    if (!selectedCell) return null;

    const response = await API.post<ShiftUpsertResponse>("/roster/shifts/upsert", {
      week_start_date: weekStartDate,
      day_of_week: selectedCell.dayIndex,
      start_time: startTime,
      end_time: endTime,
    });
    return response.data.id;
  };

  const runAssignmentRequest = async (action: "assign" | "unassign", shiftId: number, userId: number) => {
    await API.post(`/roster/${action}`, {
      user_id: userId,
      shift_id: shiftId,
    });
  };

  const handleAdd = async () => {
    if (!selectedCell) {
      setStatus("Select a roster cell first.");
      return;
    }
    const validationError = validateShiftRange(startTime, endTime);
    if (validationError) {
      setStatus(validationError);
      return;
    }
    setIsSubmitting(true);
    setStatus("");
    try {
      const targetShiftId = await ensureShiftForSelectedDay();
      if (!targetShiftId) throw new Error("Missing target shift");

      await runAssignmentRequest("assign", targetShiftId, selectedCell.userId);
      setStatus("Shift added.");
      await loadData();
      setSelectedCell(null);
    } catch (err: unknown) {
      setStatus(formatApiError(err, {
        fallbackMessage: "Failed to add shift.",
        detailMap: {
          "Shift not found": "Selected shift could not be found. Reload and try again.",
          "User not found": "User could not be found in this workplace.",
          "User already assigned to this shift": "This user is already assigned to that shift.",
          "day_of_week must be between 0 and 6": "Selected day is invalid. Close and reopen this dialog.",
          "end_time must be later than start_time": "End time must be later than start time.",
        },
      }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRemove = async () => {
    if (!selectedCell || currentShiftId === "") {
      setStatus("This employee has no assigned shift on the selected day.");
      return;
    }
    setIsSubmitting(true);
    setStatus("");
    try {
      await runAssignmentRequest("unassign", currentShiftId, selectedCell.userId);
      setStatus("Shift removed.");
      await loadData();
      setSelectedCell(null);
    } catch (err: unknown) {
      setStatus(formatApiError(err, {
        fallbackMessage: "Failed to remove shift.",
        detailMap: {
          "Assignment not found": "This assignment was already removed. Reload and try again.",
          "Shift not found": "Selected shift could not be found. Reload and try again.",
          "User not found": "User could not be found in this workplace.",
        },
      }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = async () => {
    if (!selectedCell || currentShiftId === "") {
      setStatus("Select a cell where this employee already has a shift.");
      return;
    }
    const validationError = validateShiftRange(startTime, endTime);
    if (validationError) {
      setStatus(validationError);
      return;
    }
    setIsSubmitting(true);
    setStatus("");
    try {
      const targetShiftId = await ensureShiftForSelectedDay();
      if (!targetShiftId) throw new Error("Missing target shift");
      if (targetShiftId === currentShiftId) {
        setStatus("Choose a different shift time to change.");
        return;
      }

      await runAssignmentRequest("unassign", currentShiftId, selectedCell.userId);
      await runAssignmentRequest("assign", targetShiftId, selectedCell.userId);
      setStatus("Shift changed.");
      await loadData();
      setSelectedCell(null);
    } catch (err: unknown) {
      setStatus(formatApiError(err, {
        fallbackMessage: "Failed to change shift.",
        detailMap: {
          "Assignment not found": "Current assignment no longer exists. Reload and try again.",
          "Shift not found": "Target shift could not be found. Reload and try again.",
          "User not found": "User could not be found in this workplace.",
          "User already assigned to this shift": "This user is already assigned to that shift.",
          "day_of_week must be between 0 and 6": "Selected day is invalid. Close and reopen this dialog.",
          "end_time must be later than start_time": "End time must be later than start time.",
        },
      }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedUserName = selectedCell
    ? users.find(user => user.id === selectedCell.userId)?.name ?? `User #${selectedCell.userId}`
    : "";

  const selectedCellLabel = selectedCell ? `${selectedUserName} on ${formatDayLabel(selectedCell.dayIndex, weekStartDate)}` : "";
  const hasExistingAssignment = assignedShiftsForSelection.length > 0;

  return (
    <div className="manage-shifts">
      <header className="manage-shifts__header">
        <h2>Manage Shifts</h2>
        <p>Click any employee/day cell to open quick assignment actions.</p>
      </header>
      {status && <p className="manage-shifts__status">{status}</p>}

      <RosterTable
        shifts={shifts}
        weekStartDate={weekStartDate}
        employees={users}
        title="Manage Shift Assignments"
        subtitle="Click a day cell to open shift actions for that employee/day."
        editable
        selectedCell={
          selectedCell
            ? { employeeId: selectedCell.userId, dayIndex: selectedCell.dayIndex }
            : null
        }
        onCellClick={(employeeId, dayIndex) => {
          setSelectedCell({ userId: employeeId, dayIndex });
          setStatus("");
        }}
      />

      {selectedCell && (
        <div className="shift-modal-backdrop" role="presentation" onClick={() => setSelectedCell(null)}>
          <section
            className="shift-modal"
            role="dialog"
            aria-modal="true"
            aria-label="Manage selected shift"
            onClick={event => event.stopPropagation()}
          >
            <header className="shift-modal__header">
              <h3>Manage Shift</h3>
              <button type="button" className="shift-modal__close" onClick={() => setSelectedCell(null)} disabled={isSubmitting}>
                Close
              </button>
            </header>

            <p className="shift-modal__selected">
              <span>Selected</span>
              <strong>{selectedCellLabel}</strong>
            </p>

            <label className="shift-modal__field">
              <span>Current assigned shift</span>
              <select
                value={currentShiftId}
                onChange={e => {
                  const value = e.target.value;
                  const parsed = value === "" ? "" : Number(value);
                  setCurrentShiftId(parsed);
                  if (parsed !== "") {
                    const picked = assignedShiftsForSelection.find(shift => shift.id === parsed);
                    if (picked) {
                      setStartTime(toHHMM(picked.start_time));
                      setEndTime(toHHMM(picked.end_time));
                    }
                  }
                }}
                disabled={assignedShiftsForSelection.length === 0 || isSubmitting}
              >
                {assignedShiftsForSelection.length === 0 ? (
                  <option value="">No assigned shift</option>
                ) : (
                  assignedShiftsForSelection.map(shift => (
                    <option key={shift.id} value={shift.id}>
                      {formatTime(shift.start_time)} - {formatTime(shift.end_time)}
                    </option>
                  ))
                )}
              </select>
            </label>

            <div className="shift-modal__time-grid">
              <label className="shift-modal__field">
                <span>Start time</span>
                <input
                  type="time"
                  value={startTime}
                  onChange={e => setStartTime(e.target.value)}
                  disabled={isSubmitting}
                />
              </label>

              <label className="shift-modal__field">
                <span>End time</span>
                <input
                  type="time"
                  value={endTime}
                  onChange={e => setEndTime(e.target.value)}
                  disabled={isSubmitting}
                />
              </label>
            </div>

            <div className="shift-modal__actions">
              {!hasExistingAssignment ? (
                <button type="button" className="shift-modal__action shift-modal__action--primary" onClick={handleAdd} disabled={isSubmitting}>
                  Add
                </button>
              ) : (
                <>
                  <button type="button" className="shift-modal__action shift-modal__action--danger" onClick={handleRemove} disabled={isSubmitting || currentShiftId === ""}>
                    Remove
                  </button>
                  <button type="button" className="shift-modal__action" onClick={handleChange} disabled={isSubmitting || currentShiftId === ""}>
                    Change
                  </button>
                </>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

