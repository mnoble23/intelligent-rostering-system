import { type ReactNode } from "react";
import "./RosterTable.css";

interface Staff {
  id: number;
  name: string;
}

export interface ShiftAssignment {
  id: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
  staff: Staff[];
}

export interface EmployeeRow {
  id: number;
  name: string;
}

interface RosterTableProps {
  shifts: ShiftAssignment[];
  weekStartDate?: string;
  employees?: EmployeeRow[];
  title?: string;
  subtitle?: string;
  editable?: boolean;
  selectedCell?: {
    employeeId: number;
    dayIndex: number;
  } | null;
  onCellClick?: (employeeId: number, dayIndex: number) => void;
  renderCellActions?: (employeeId: number, dayIndex: number) => ReactNode;
}

const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function formatDayLabel(dayIndex: number, weekStartDate?: string) {
  if (!weekStartDate) return days[dayIndex];
  const [year, month, day] = weekStartDate.split("-").map(Number);
  const baseDate = new Date(year, month - 1, day);
  baseDate.setDate(baseDate.getDate() + dayIndex);
  const dd = String(baseDate.getDate()).padStart(2, "0");
  const mm = String(baseDate.getMonth() + 1).padStart(2, "0");
  return `${days[dayIndex]} ${dd}/${mm}`;
}

function formatTime(timeStr: string) {
  const [hour, minute] = timeStr.split(":").map(Number);
  const ampm = hour >= 12 ? "PM" : "AM";
  const hour12 = hour % 12 || 12;
  return `${hour12}:${minute.toString().padStart(2, "0")} ${ampm}`;
}

function sortByTime(a: string, b: string) {
  return a.localeCompare(b);
}

export default function RosterTable({
  shifts,
  weekStartDate,
  employees: employeesProp,
  title = "Employee Calendar View",
  subtitle = "Rows are employees. Columns are days. Cells show assigned shift times.",
  editable = false,
  selectedCell = null,
  onCellClick,
  renderCellActions,
}: RosterTableProps) {
  const employeeMap = new Map<number, EmployeeRow>();

  shifts.forEach(shift => {
    shift.staff.forEach(person => {
      if (!employeeMap.has(person.id)) {
        employeeMap.set(person.id, { id: person.id, name: person.name });
      }
    });
  });

  const employees = (
    employeesProp && employeesProp.length > 0
      ? employeesProp
      : Array.from(employeeMap.values())
  ).sort((a, b) => a.name.localeCompare(b.name));

  const shiftsByEmployeeAndDay = shifts.reduce<Record<string, { start: string; label: string }[]>>((acc, shift) => {
    const timeRange = `${formatTime(shift.start_time)} - ${formatTime(shift.end_time)}`;

    shift.staff.forEach(person => {
      const key = `${person.id}-${shift.day_of_week}`;
      if (!acc[key]) acc[key] = [];
      acc[key].push({ start: shift.start_time, label: timeRange });
    });

    return acc;
  }, {});

  Object.keys(shiftsByEmployeeAndDay).forEach(key => {
    shiftsByEmployeeAndDay[key] = shiftsByEmployeeAndDay[key]
      .sort((a, b) => sortByTime(a.start, b.start));
  });

  const totalAssignments = Object.values(shiftsByEmployeeAndDay).reduce((sum, dayShifts) => sum + dayShifts.length, 0);

  return (
    <section className="employee-calendar" aria-label="Employee weekly calendar roster">
      <header className="employee-calendar__header">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        <div className="employee-calendar__stats">
          <span>
            <strong>{employees.length}</strong> employees
          </span>
          <span>
            <strong>{totalAssignments}</strong> assignments
          </span>
        </div>
      </header>

      {employees.length === 0 ? (
        <p className="employee-calendar__empty">No assigned employees in the current roster.</p>
      ) : (
        <div className="employee-calendar__table-wrap">
          <table className="employee-calendar__table">
            <thead>
              <tr>
                <th>Employee</th>
                {days.map((_, dayIndex) => (
                  <th key={dayIndex}>{formatDayLabel(dayIndex, weekStartDate)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {employees.map(employee => (
                <tr key={employee.id}>
                  <th scope="row" className="employee-calendar__name-cell">
                    {employee.name}
                  </th>
                  {days.map((_, dayIndex) => {
                    const cellKey = `${employee.id}-${dayIndex}`;
                    const dayAssignments = shiftsByEmployeeAndDay[cellKey] ?? [];
                    const isSelected =
                      editable &&
                      selectedCell?.employeeId === employee.id &&
                      selectedCell.dayIndex === dayIndex;

                    return (
                      <td
                        key={cellKey}
                        className={editable ? "employee-calendar__cell--editable" : undefined}
                        data-selected={isSelected ? "true" : "false"}
                        onClick={editable ? () => onCellClick?.(employee.id, dayIndex) : undefined}
                        onKeyDown={editable ? event => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            onCellClick?.(employee.id, dayIndex);
                          }
                        } : undefined}
                        role={editable ? "button" : undefined}
                        tabIndex={editable ? 0 : undefined}
                      >
                        {isSelected && (
                          <div className="employee-calendar__actions">{renderCellActions?.(employee.id, dayIndex)}</div>
                        )}
                        {dayAssignments.length === 0 ? (
                          <span className="employee-calendar__off">Off</span>
                        ) : (
                          <ul className="employee-calendar__shift-list">
                            {dayAssignments.map((shiftTime, idx) => (
                              <li key={`${cellKey}-${idx}`} className="employee-calendar__shift-pill">
                                {shiftTime.label}
                              </li>
                            ))}
                          </ul>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
