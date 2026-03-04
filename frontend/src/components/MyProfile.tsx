import { useEffect, useMemo, useState } from "react";
import API from "../services/api";
import "./MyProfile.css";

interface User {
  id: number;
  name: string;
  role: "manager" | "staff";
  min_hours: number;
  max_hours: number;
  min_shifts_per_week: number;
  max_shifts_per_week: number;
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

interface AuthUser {
  id: number;
  name: string;
}

const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

interface MyProfileProps {
  weekStartDate?: string;
}

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

function formatDayLabel(dayIndex: number, weekStartDate?: string) {
  if (!weekStartDate) return days[dayIndex];
  const [year, month, day] = weekStartDate.split("-").map(Number);
  const baseDate = new Date(year, month - 1, day);
  baseDate.setDate(baseDate.getDate() + dayIndex);
  const mm = String(baseDate.getMonth() + 1).padStart(2, "0");
  const dd = String(baseDate.getDate()).padStart(2, "0");
  return `${days[dayIndex]} ${dd}/${mm}`;
}

export default function MyProfile({ weekStartDate }: MyProfileProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [availability, setAvailability] = useState<Availability[]>([]);
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | "">("");
  const [userSearch, setUserSearch] = useState("");
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    const loadData = async () => {
      try {
        const [usersRes, availabilityRes, rosterRes, meRes] = await Promise.all([
          API.get("/users"),
          API.get("/availability"),
          API.get("/roster", weekStartDate ? { params: { week_start_date: weekStartDate } } : undefined),
          API.get<AuthUser>("/auth/me"),
        ]);

        const sortedUsers = [...usersRes.data].sort((a, b) => a.name.localeCompare(b.name));
        setUsers(sortedUsers);
        setAvailability(availabilityRes.data);
        setShifts(rosterRes.data);
        setSelectedUserId(meRes.data.id);
        setUserSearch(meRes.data.name);
      } catch (err) {
        console.error(err);
        setStatus("Failed to load profile data.");
      }
    };

    loadData();
  }, [weekStartDate]);

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

  const filteredUsers = useMemo(() => {
    const query = userSearch.trim().toLowerCase();
    const matches = query.length === 0
      ? users
      : users.filter(user => user.name.toLowerCase().includes(query));
    return matches;
  }, [users, userSearch]);

  return (
    <section className="my-profile">
      <div className="my-profile__shell">
        <header className="my-profile__hero">
          <p className="my-profile__eyebrow">Profile Center</p>
          <h2>My Profile</h2>
          <p className="my-profile__lead">See profile settings, submitted availability, and current roster assignments.</p>
        </header>

        {status && <p className="my-profile__status">{status}</p>}

        <div className="my-profile__controls">
          <label className="my-profile__field">
            <span>User (Search)</span>
            <div className="my-profile__user-picker">
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
                <div className="my-profile__user-menu">
                  {filteredUsers.length === 0 ? (
                    <div className="my-profile__user-item my-profile__user-item--empty">No matches</div>
                  ) : (
                    filteredUsers.map(user => (
                      <button
                        key={user.id}
                        type="button"
                        className={`my-profile__user-item${selectedUserId === user.id ? " my-profile__user-item--active" : ""}`}
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
        </div>

        {selectedUserId === "" ? (
          <p className="my-profile__empty">
            {users.length === 0 ? "No users found." : "Pick a user to view profile details."}
          </p>
        ) : (
          <>
            <section className="my-profile__section">
              <h3>Profile Summary</h3>
              <div className="my-profile__chips">
                <span className="my-profile__chip">Name: <strong>{selectedUser?.name ?? "-"}</strong></span>
                <span className="my-profile__chip">Role: <strong>{selectedUser?.role ?? "staff"}</strong></span>
                <span className="my-profile__chip">Min Weekly Hours: <strong>{selectedUser?.min_hours ?? 0}</strong></span>
                <span className="my-profile__chip">Max Weekly Hours: <strong>{selectedUser?.max_hours ?? 40}</strong></span>
                <span className="my-profile__chip">Min Weekly Shifts: <strong>{selectedUser?.min_shifts_per_week ?? 1}</strong></span>
                <span className="my-profile__chip">Max Weekly Shifts: <strong>{selectedUser?.max_shifts_per_week ?? 7}</strong></span>
                <span className="my-profile__chip">Weekly Availability Hours: <strong>{availabilityHours.toFixed(1)}</strong></span>
              </div>
            </section>

            <section className="my-profile__section">
              <h3>Submitted Availability</h3>
              {userAvailability.length === 0 ? (
                <p className="my-profile__empty">No availability submitted yet.</p>
              ) : (
                <div className="my-profile__table-wrap">
                  <table className="my-profile__table">
                    <thead>
                      <tr>
                        <th>Day</th>
                        <th>Start</th>
                        <th>End</th>
                      </tr>
                    </thead>
                    <tbody>
                      {userAvailability.map(item => (
                        <tr key={item.id}>
                          <td>{formatDayLabel(item.day_of_week, weekStartDate)}</td>
                          <td>{formatTime(item.start_time)}</td>
                          <td>{formatTime(item.end_time)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="my-profile__section">
              <h3>Current Assigned Shifts</h3>
              {assignedShifts.length === 0 ? (
                <p className="my-profile__empty">No assigned shifts this week.</p>
              ) : (
                <div className="my-profile__table-wrap">
                  <table className="my-profile__table">
                    <thead>
                      <tr>
                        <th>Day</th>
                        <th>Start</th>
                        <th>End</th>
                      </tr>
                    </thead>
                    <tbody>
                      {assignedShifts.map(shift => (
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
            </section>
          </>
        )}
      </div>
    </section>
  );
}

