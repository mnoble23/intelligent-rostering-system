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

export default function RosterTable({ shifts }: { shifts: ShiftAssignment[] }) {
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  return (
    <table border={1} style={{ borderCollapse: "collapse", width: "100%" }}>
      <thead>
        <tr>
          <th>Day</th>
          <th>Start Time</th>
          <th>End Time</th>
          <th>Staff</th>
        </tr>
      </thead>
      <tbody>
        {shifts.map((shift, i) => (
          <tr key={i}>
            <td>{days[shift.day_of_week]}</td>
            <td>{shift.start_time}</td>
            <td>{shift.end_time}</td>
            <td>
              {shift.staff.map((s) => s.name).join(", ")}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
