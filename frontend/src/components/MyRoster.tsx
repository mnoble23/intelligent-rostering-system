import { useEffect, useMemo, useState } from "react";
import API from "../services/api";
import "./MyRoster.css";

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

interface AuthUser {
  id: number;
  name: string;
}

const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

interface MyRosterProps {
  weekStartDate?: string;
}

function formatTime(timeStr: string) {
  const [hour, minute] = timeStr.split(":").map(Number);
  const ampm = hour >= 12 ? "PM" : "AM";
  const hour12 = hour % 12 || 12;
  return `${hour12}:${minute.toString().padStart(2, "0")} ${ampm}`;
}

function formatDayLabel(dayIndex: number, weekStartDate?: string) {
  if (!weekStartDate) return days[dayIndex];
  const [year, month, day] = weekStartDate.split("-").map(Number);
  const baseDate = new Date(year, month - 1, day);
  baseDate.setDate(baseDate.getDate() + dayIndex);
  const mm = String(baseDate.getMonth() + 1).padStart(2, "0");
  const dd = String(baseDate.getDate()).padStart(2, "0");
  return `${days[dayIndex]} ${dd}/${mm}`;
}

export default function MyRoster({ weekStartDate }: MyRosterProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | "">("");
  const [userSearch, setUserSearch] = useState("");
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    const loadData = async () => {
      try {
        const [usersRes, shiftsRes, meRes] = await Promise.all([
          API.get("/users/"),
          API.get("/roster", weekStartDate ? { params: { week_start_date: weekStartDate } } : undefined),
          API.get<AuthUser>("/auth/me"),
        ]);
        const sortedUsers = [...usersRes.data].sort((a, b) => a.name.localeCompare(b.name));
        setUsers(sortedUsers);
        setShifts(shiftsRes.data);
        setSelectedUserId(meRes.data.id);
        setUserSearch(meRes.data.name);
      } catch (err) {
        console.error(err);
        setStatus("Failed to load roster data.");
      }
    };

    loadData();
  }, [weekStartDate]);

  const myShifts = useMemo(() => {
    if (selectedUserId === "") return [];
    return shifts
      .filter(shift => shift.staff.some(staff => staff.id === selectedUserId))
      .sort((a, b) => {
        if (a.day_of_week !== b.day_of_week) return a.day_of_week - b.day_of_week;
        return a.start_time.localeCompare(b.start_time);
      });
  }, [selectedUserId, shifts]);

  const selectedUserName =
    selectedUserId === ""
      ? ""
      : users.find(user => user.id === selectedUserId)?.name ?? "";

  const filteredUsers = useMemo(() => {
    const query = userSearch.trim().toLowerCase();
    const matches = query.length === 0
      ? users
      : users.filter(user => user.name.toLowerCase().includes(query));
    return matches;
  }, [users, userSearch]);

  return (
    <section className="my-roster">
      <div className="my-roster__shell">
        <header className="my-roster__hero">
          <p className="my-roster__eyebrow">Weekly Plan</p>
          <h2>My Roster</h2>
          <p className="my-roster__lead">Review assigned shifts by day and time for the current week.</p>
        </header>

        {status && <p className="my-roster__status">{status}</p>}

        <div className="my-roster__controls">
          <label className="my-roster__field">
            <span>User (Search)</span>
            <div className="my-roster__user-picker">
              <input
                type="text"
                value={userSearch}
                placeholder="Type a name..."
                onChange={e => {
                  setUserSearch(e.target.value);
                  setIsUserMenuOpen(true);
                }}
                onFocus={() => setIsUserMenuOpen(true)}
                onBlur={() => window.setTimeout(() => setIsUserMenuOpen(false), 120)}
                disabled={users.length === 0}
              />
              {isUserMenuOpen && users.length > 0 && (
                <div className="my-roster__user-menu">
                  {filteredUsers.length === 0 ? (
                    <div className="my-roster__user-item my-roster__user-item--empty">No matches</div>
                  ) : (
                    filteredUsers.map(user => (
                      <button
                        key={user.id}
                        type="button"
                        className={`my-roster__user-item${selectedUserId === user.id ? " my-roster__user-item--active" : ""}`}
                        onMouseDown={() => {
                          setSelectedUserId(user.id);
                          setUserSearch(user.name);
                          setIsUserMenuOpen(false);
                        }}
                      >
                        {user.name}
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
          </label>
          <div className="my-roster__stat">
            <span>Selected</span>
            <strong>{selectedUserName || "None"}</strong>
          </div>
          <div className="my-roster__stat">
            <span>Total Shifts</span>
            <strong>{myShifts.length}</strong>
          </div>
        </div>

        {selectedUserId === "" ? (
          <p className="my-roster__empty">
            {users.length === 0 ? "No users found." : "Pick a user to view roster."}
          </p>
        ) : myShifts.length === 0 ? (
          <p className="my-roster__empty">No shifts assigned this week.</p>
        ) : (
          <div className="my-roster__table-wrap">
            <table className="my-roster__table">
              <thead>
                <tr>
                  <th>Day</th>
                  <th>Start</th>
                  <th>End</th>
                </tr>
              </thead>
              <tbody>
                {myShifts.map(shift => (
                  <tr key={shift.id}>
                    <td>{formatDayLabel(shift.day_of_week, weekStartDate)}</td>
                    <td>{formatTime(shift.start_time)}</td>
                    <td>{formatTime(shift.end_time)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}

