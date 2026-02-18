import { useEffect, useMemo, useState } from "react";
import API from "../services/api";

interface User {
  id: number;
  name: string;
}

interface Availability {
  id: number;
  user_id: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
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

function parseHourValue(timeStr: string) {
  const [hour, minute] = timeStr.split(":").map(Number);
  return hour + minute / 60;
}

function formatTime(timeStr: string) {
  const [hour, minute] = timeStr.split(":").map(Number);
  const ampm = hour >= 12 ? "PM" : "AM";
  const hour12 = hour % 12 || 12;
  return `${hour12}:${minute.toString().padStart(2, "0")} ${ampm}`;
}

export default function MyProfile() {
  const [users, setUsers] = useState<User[]>([]);
  const [availability, setAvailability] = useState<Availability[]>([]);
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | "">("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    const loadData = async () => {
      try {
        const [usersRes, availabilityRes, rosterRes] = await Promise.all([
          API.get("/users"),
          API.get("/availability"),
          API.get("/roster"),
        ]);

        setUsers(usersRes.data);
        setAvailability(availabilityRes.data);
        setShifts(rosterRes.data);

        if (usersRes.data.length > 0) {
          setSelectedUserId(usersRes.data[0].id);
        }
      } catch (err) {
        console.error(err);
        setStatus("Failed to load profile data.");
      }
    };

    loadData();
  }, []);

  const selectedUser = useMemo(
    () => users.find(user => user.id === selectedUserId) ?? null,
    [users, selectedUserId]
  );

  const userAvailability = useMemo(() => {
    if (selectedUserId === "") return [];
    return availability
      .filter(item => item.user_id === selectedUserId)
      .sort((a, b) => {
        if (a.day_of_week !== b.day_of_week) return a.day_of_week - b.day_of_week;
        return a.start_time.localeCompare(b.start_time);
      });
  }, [availability, selectedUserId]);

  const assignedShifts = useMemo(() => {
    if (selectedUserId === "") return [];
    return shifts
      .filter(shift => shift.staff.some(staff => staff.id === selectedUserId))
      .sort((a, b) => {
        if (a.day_of_week !== b.day_of_week) return a.day_of_week - b.day_of_week;
        return a.start_time.localeCompare(b.start_time);
      });
  }, [selectedUserId, shifts]);

  const availabilityHours = useMemo(
    () =>
      userAvailability.reduce((sum, slot) => {
        return sum + (parseHourValue(slot.end_time) - parseHourValue(slot.start_time));
      }, 0),
    [userAvailability]
  );

  return (
    <div style={{ maxWidth: 920, margin: "20px auto" }}>
      <h2>My Profile</h2>
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
      ) : (
        <>
          <section style={{ marginBottom: 16 }}>
            <h3 style={{ marginBottom: 8 }}>Profile Summary</h3>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <span style={{ border: "1px solid #ccc", borderRadius: 999, padding: "6px 10px" }}>
                Name: <strong>{selectedUser?.name ?? "-"}</strong>
              </span>
              <span style={{ border: "1px solid #ccc", borderRadius: 999, padding: "6px 10px" }}>
                Availability Entries: <strong>{userAvailability.length}</strong>
              </span>
              <span style={{ border: "1px solid #ccc", borderRadius: 999, padding: "6px 10px" }}>
                Weekly Availability Hours: <strong>{availabilityHours.toFixed(1)}</strong>
              </span>
              <span style={{ border: "1px solid #ccc", borderRadius: 999, padding: "6px 10px" }}>
                Assigned Shifts: <strong>{assignedShifts.length}</strong>
              </span>
            </div>
          </section>

          <section style={{ marginBottom: 22 }}>
            <h3 style={{ marginBottom: 8 }}>Submitted Availability</h3>
            {userAvailability.length === 0 ? (
              <p>No availability submitted yet.</p>
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
                  {userAvailability.map(item => (
                    <tr key={item.id} style={{ borderBottom: "1px solid #ddd" }}>
                      <td style={{ padding: 8 }}>{days[item.day_of_week]}</td>
                      <td style={{ padding: 8 }}>{formatTime(item.start_time)}</td>
                      <td style={{ padding: 8 }}>{formatTime(item.end_time)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section>
            <h3 style={{ marginBottom: 8 }}>Current Assigned Shifts</h3>
            {assignedShifts.length === 0 ? (
              <p>No assigned shifts this week.</p>
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
                  {assignedShifts.map(shift => (
                    <tr key={shift.id} style={{ borderBottom: "1px solid #ddd" }}>
                      <td style={{ padding: 8 }}>{days[shift.day_of_week]}</td>
                      <td style={{ padding: 8 }}>{formatTime(shift.start_time)}</td>
                      <td style={{ padding: 8 }}>{formatTime(shift.end_time)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </div>
  );
}
