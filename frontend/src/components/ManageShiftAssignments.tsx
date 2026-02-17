import { useEffect, useMemo, useState } from "react";
import API from "../services/api";

interface User {
  id: number;
  name: string;
}

interface Staff {
  id: number;
  name: string;
}

interface Shift {
  id: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
  staff: Staff[];
}

const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function formatTime(timeStr: string) {
  const [hour, minute] = timeStr.split(":").map(Number);
  const ampm = hour >= 12 ? "PM" : "AM";
  const hour12 = hour % 12 || 12;
  return `${hour12}:${minute.toString().padStart(2, "0")} ${ampm}`;
}

export default function ManageShiftAssignments() {
  const [users, setUsers] = useState<User[]>([]);
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | "">("");
  const [selectedShiftId, setSelectedShiftId] = useState<number | "">("");
  const [status, setStatus] = useState("");

  const loadData = async () => {
    try {
      const [usersRes, shiftsRes] = await Promise.all([API.get("/users"), API.get("/roster")]);
      setUsers(usersRes.data);
      setShifts(shiftsRes.data);

      if (usersRes.data.length > 0 && selectedUserId === "") {
        setSelectedUserId(usersRes.data[0].id);
      }
      if (shiftsRes.data.length > 0 && selectedShiftId === "") {
        setSelectedShiftId(shiftsRes.data[0].id);
      }
    } catch (err) {
      console.error(err);
      setStatus("Failed to load users and shifts.");
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const sortedShifts = useMemo(
    () =>
      [...shifts].sort((a, b) => {
        if (a.day_of_week !== b.day_of_week) return a.day_of_week - b.day_of_week;
        return a.start_time.localeCompare(b.start_time);
      }),
    [shifts]
  );

  const handleUpdate = async (action: "assign" | "unassign") => {
    setStatus("");
    if (selectedUserId === "" || selectedShiftId === "") {
      setStatus("Please select both a user and a shift.");
      return;
    }

    try {
      await API.post(`/roster/${action}`, {
        user_id: selectedUserId,
        shift_id: selectedShiftId,
      });
      setStatus(action === "assign" ? "User assigned to shift." : "User removed from shift.");
      await loadData();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setStatus(typeof detail === "string" ? detail : `Failed to ${action} user.`);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: "20px auto" }}>
      <h2>Manual Shift Assignment</h2>
      {status && <p>{status}</p>}

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
        <label>
          User{" "}
          <select value={selectedUserId} onChange={e => setSelectedUserId(Number(e.target.value))}>
            {users.map(user => (
              <option key={user.id} value={user.id}>
                {user.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Shift{" "}
          <select value={selectedShiftId} onChange={e => setSelectedShiftId(Number(e.target.value))}>
            {sortedShifts.map(shift => (
              <option key={shift.id} value={shift.id}>
                {days[shift.day_of_week]} {formatTime(shift.start_time)} - {formatTime(shift.end_time)}
              </option>
            ))}
          </select>
        </label>

        <button type="button" onClick={() => handleUpdate("assign")}>
          Add User to Shift
        </button>
        <button type="button" onClick={() => handleUpdate("unassign")}>
          Remove User from Shift
        </button>
      </div>

      <h3>Current Assignments</h3>
      <table style={{ borderCollapse: "collapse", width: "100%", textAlign: "left" }}>
        <thead>
          <tr style={{ backgroundColor: "#f0f0f0" }}>
            <th style={{ padding: 8 }}>Day</th>
            <th style={{ padding: 8 }}>Time</th>
            <th style={{ padding: 8 }}>Assigned Users</th>
          </tr>
        </thead>
        <tbody>
          {sortedShifts.map(shift => (
            <tr key={shift.id} style={{ borderBottom: "1px solid #ddd" }}>
              <td style={{ padding: 8 }}>{days[shift.day_of_week]}</td>
              <td style={{ padding: 8 }}>
                {formatTime(shift.start_time)} - {formatTime(shift.end_time)}
              </td>
              <td style={{ padding: 8 }}>{shift.staff.map(staff => staff.name).join(", ") || "None"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
