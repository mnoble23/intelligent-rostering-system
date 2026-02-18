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

export default function MyRoster() {
  const [users, setUsers] = useState<User[]>([]);
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | "">("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    const loadData = async () => {
      try {
        const [usersRes, shiftsRes] = await Promise.all([API.get("/users"), API.get("/roster")]);
        setUsers(usersRes.data);
        setShifts(shiftsRes.data);
        if (usersRes.data.length > 0) {
          setSelectedUserId(usersRes.data[0].id);
        }
      } catch (err) {
        console.error(err);
        setStatus("Failed to load roster data.");
      }
    };

    loadData();
  }, []);

  const myShifts = useMemo(() => {
    if (selectedUserId === "") return [];
    return shifts
      .filter(shift => shift.staff.some(staff => staff.id === selectedUserId))
      .sort((a, b) => {
        if (a.day_of_week !== b.day_of_week) return a.day_of_week - b.day_of_week;
        return a.start_time.localeCompare(b.start_time);
      });
  }, [selectedUserId, shifts]);

  return (
    <div style={{ maxWidth: 900, margin: "20px auto" }}>
      <h2>My Roster</h2>
      {status && <p>{status}</p>}

      <div style={{ marginBottom: 16 }}>
        <label>
          User{" "}
          <select
            value={selectedUserId}
            onChange={e => setSelectedUserId(Number(e.target.value))}
            disabled={users.length === 0}
          >
            {users.map(user => (
              <option key={user.id} value={user.id}>
                {user.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {selectedUserId === "" ? (
        <p>No users found.</p>
      ) : myShifts.length === 0 ? (
        <p>No shifts assigned this week.</p>
      ) : (
        <table style={{ borderCollapse: "collapse", width: "100%", textAlign: "left" }}>
          <thead>
            <tr style={{ backgroundColor: "#f0f0f0" }}>
              <th style={{ padding: 8 }}>Day</th>
              <th style={{ padding: 8 }}>Start</th>
              <th style={{ padding: 8 }}>End</th>
            </tr>
          </thead>
          <tbody>
            {myShifts.map(shift => (
              <tr key={shift.id} style={{ borderBottom: "1px solid #ddd" }}>
                <td style={{ padding: 8 }}>{days[shift.day_of_week]}</td>
                <td style={{ padding: 8 }}>{formatTime(shift.start_time)}</td>
                <td style={{ padding: 8 }}>{formatTime(shift.end_time)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
