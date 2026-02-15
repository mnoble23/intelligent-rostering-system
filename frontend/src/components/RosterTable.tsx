import React from "react";

interface Staff {
  id: number;
  name: string;
}

interface ShiftAssignment {
  day_of_week: number;
  start_time: string;
  end_time: string;
  staff: Staff[];
}

interface RosterTableProps {
  shifts: ShiftAssignment[];
}

export default function RosterTable({ shifts }: RosterTableProps) {
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  const sortedShifts = [...shifts].sort((a, b) => {
    if (a.day_of_week !== b.day_of_week) return a.day_of_week - b.day_of_week;
    return a.start_time.localeCompare(b.start_time);
  });

  function formatTime(timeStr: string) {
    const [hour, minute] = timeStr.split(":").map(Number);
    const ampm = hour >= 12 ? "PM" : "AM";
    const hour12 = hour % 12 || 12;
    return `${hour12}:${minute.toString().padStart(2, "0")} ${ampm}`;
  }

  return (
    <table style={{ borderCollapse: "collapse", width: "100%", textAlign: "center" }}>
      <thead>
        <tr style={{ backgroundColor: "#f0f0f0" }}>
          <th>Day</th>
          <th>Start Time</th>
          <th>End Time</th>
          <th>Staff</th>
        </tr>
      </thead>
      <tbody>
        {sortedShifts.map((shift, i) => (
          <tr
            key={i}
            style={{
              borderBottom: "1px solid #ddd",
              backgroundColor: i % 2 === 0 ? "#ffffff" : "#fafafa",
            }}
          >
            <td>{days[shift.day_of_week]}</td>
            <td>{formatTime(shift.start_time)}</td>
            <td>{formatTime(shift.end_time)}</td>
            <td>{shift.staff.map((s) => s.name).join(", ")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
