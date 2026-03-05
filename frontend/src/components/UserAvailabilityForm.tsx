import { useEffect, useState } from "react";
import API, { formatApiError } from "../services/api";
import "./UserAvailabilityForm.css";

interface Availability {
  day_of_week: number;
  start_time: string;
  end_time: string;
  is_full_day: boolean;
}

interface AvailabilityApiRow {
  id: number;
  user_id: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
}

interface AuthUser {
  id: number;
  name: string;
  role: "staff" | "manager";
}

interface ManagerUser {
  id: number;
  name: string;
  role: "staff" | "manager";
  min_hours: number;
  max_hours: number;
  min_shifts_per_week: number;
  max_shifts_per_week: number;
}

type ManagerMode = "new" | "existing";

function hhmmToMinutes(value: string) {
  const [hours, minutes] = value.split(":").map(Number);
  return hours * 60 + minutes;
}

function toHHMM(value: string) {
  const [hour = "00", minute = "00"] = value.split(":");
  return `${hour.padStart(2, "0")}:${minute.padStart(2, "0")}`;
}

export default function UserAvailabilityForm() {
  const BUSINESS_OPEN = "06:00";
  const BUSINESS_CLOSE = "22:00";
  const [name, setName] = useState("");
  const [role, setRole] = useState<"staff" | "manager">("staff");
  const [minHours, setMinHours] = useState(0);
  const [maxHours, setMaxHours] = useState(40);
  const [minShiftsPerWeek, setMinShiftsPerWeek] = useState(1);
  const [maxShiftsPerWeek, setMaxShiftsPerWeek] = useState(7);
  const [availability, setAvailability] = useState<Availability[]>([
    { day_of_week: 0, start_time: "", end_time: "", is_full_day: false },
  ]);
  const [managerMode, setManagerMode] = useState<ManagerMode | null>(null);
  const [managerUsers, setManagerUsers] = useState<ManagerUser[]>([]);
  const [selectedExistingUserId, setSelectedExistingUserId] = useState<number | "">("");
  const [availabilityRows, setAvailabilityRows] = useState<AvailabilityApiRow[]>([]);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState("");
  const [statusType, setStatusType] = useState<"idle" | "success" | "error">("idle");

  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const meResponse = await API.get<AuthUser>("/auth/me");
        setAuthUser(meResponse.data);

        if (meResponse.data.role === "staff") {
          setName(meResponse.data.name);
          setRole("staff");
          return;
        }

        const [usersResponse, availabilityResponse] = await Promise.all([
          API.get<ManagerUser[]>("/users/"),
          API.get<AvailabilityApiRow[]>("/availability"),
        ]);
        setManagerUsers(usersResponse.data ?? []);
        setAvailabilityRows(availabilityResponse.data ?? []);
      } catch (err) {
        console.error(err);
        setStatus(formatApiError(err, { fallbackMessage: "Failed to load authenticated user." }));
        setStatusType("error");
      }
    };

    loadInitialData();
  }, []);

  useEffect(() => {
    if (authUser?.role !== "manager") return;

    if (managerMode === null) {
      setSelectedExistingUserId("");
      return;
    }

    if (managerMode === "new") {
      setSelectedExistingUserId("");
      setName("");
      setRole("staff");
      setMinHours(0);
      setMaxHours(40);
      setMinShiftsPerWeek(1);
      setMaxShiftsPerWeek(7);
      setAvailability([{ day_of_week: 0, start_time: "", end_time: "", is_full_day: false }]);
      return;
    }

    if (managerUsers.length === 0) {
      setSelectedExistingUserId("");
      return;
    }

    if (selectedExistingUserId === "") {
      setSelectedExistingUserId(managerUsers[0].id);
    }
  }, [authUser?.role, managerMode, managerUsers, selectedExistingUserId]);

  useEffect(() => {
    if (authUser?.role !== "manager" || managerMode !== "existing" || selectedExistingUserId === "") return;

    const selectedUser = managerUsers.find(user => user.id === selectedExistingUserId);
    if (!selectedUser) return;

    setName(selectedUser.name);
    setRole(selectedUser.role);
    setMinHours(selectedUser.min_hours);
    setMaxHours(selectedUser.max_hours);
    setMinShiftsPerWeek(selectedUser.min_shifts_per_week);
    setMaxShiftsPerWeek(selectedUser.max_shifts_per_week);

    const selectedAvailability = availabilityRows
      .filter(row => row.user_id === selectedUser.id)
      .sort((a, b) => {
        if (a.day_of_week !== b.day_of_week) return a.day_of_week - b.day_of_week;
        return a.start_time.localeCompare(b.start_time);
      })
      .map(row => {
        const start = toHHMM(row.start_time);
        const end = toHHMM(row.end_time);
        return {
          day_of_week: row.day_of_week,
          start_time: start,
          end_time: end,
          is_full_day: start === BUSINESS_OPEN && end === BUSINESS_CLOSE,
        };
      });

    setAvailability(
      selectedAvailability.length > 0
        ? selectedAvailability
        : [{ day_of_week: 0, start_time: "", end_time: "", is_full_day: false }]
    );
  }, [authUser?.role, managerMode, selectedExistingUserId, managerUsers, availabilityRows, BUSINESS_OPEN, BUSINESS_CLOSE]);

  const addAvailability = () => {
    setAvailability([...availability, { day_of_week: 0, start_time: "", end_time: "", is_full_day: false }]);
  };

  const removeAvailability = (index: number) => {
    setAvailability(availability.filter((_, i) => i !== index));
  };

  const updateAvailability = (index: number, field: keyof Availability, value: any) => {
    setAvailability(prev => prev.map((av, i) => (i === index ? { ...av, [field]: value } : av)));
  };

  const toggleFullDayAvailability = (index: number, isChecked: boolean) => {
    setAvailability(prev =>
      prev.map((av, i) => {
        if (i !== index) return av;
        if (isChecked) {
          return {
            ...av,
            is_full_day: true,
            start_time: BUSINESS_OPEN,
            end_time: BUSINESS_CLOSE,
          };
        }
        return {
          ...av,
          is_full_day: false,
          start_time: "",
          end_time: "",
        };
      })
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("");
    setStatusType("idle");

    if (authUser?.role === "manager" && managerMode === null) {
      setStatus("Choose Add New User or Update Existing User first.");
      setStatusType("error");
      return;
    }

    if (!name.trim()) {
      setStatus("Please enter a name.");
      setStatusType("error");
      return;
    }
    if (minHours < 0 || maxHours < 0) {
      setStatus("Minimum and maximum hours must be zero or greater.");
      setStatusType("error");
      return;
    }
    if (maxHours < minHours) {
      setStatus("Maximum hours must be greater than or equal to minimum hours.");
      setStatusType("error");
      return;
    }
    if (minShiftsPerWeek < 0 || maxShiftsPerWeek < 0) {
      setStatus("Minimum and maximum shifts must be zero or greater.");
      setStatusType("error");
      return;
    }
    if (maxShiftsPerWeek < minShiftsPerWeek) {
      setStatus("Maximum shifts must be greater than or equal to minimum shifts.");
      setStatusType("error");
      return;
    }

    for (const av of availability) {
      if (!av.start_time || !av.end_time) {
        setStatus("All availability rows must have start and end times.");
        setStatusType("error");
        return;
      }
      if (av.start_time >= av.end_time) {
        setStatus("Start time must be before end time.");
        setStatusType("error");
        return;
      }
    }

    for (let day = 0; day < 7; day += 1) {
      const dayEntries = availability
        .filter(av => av.day_of_week === day)
        .map(av => ({
          start: hhmmToMinutes(av.start_time),
          end: hhmmToMinutes(av.end_time),
        }))
        .sort((a, b) => a.start - b.start);

      for (let i = 1; i < dayEntries.length; i += 1) {
        if (dayEntries[i].start < dayEntries[i - 1].end) {
          setStatus(`Availability blocks overlap on ${days[day]}. Adjust times and try again.`);
          setStatusType("error");
          return;
        }
      }
    }

    try {
      let userId: number | null = null;
      if (authUser?.role === "manager") {
        if (managerMode === "existing" && selectedExistingUserId === "") {
          setStatus("Choose an existing user to update.");
          setStatusType("error");
          return;
        }
        const userRes = await API.post("/users/", {
          name,
          role,
          min_hours: minHours,
          max_hours: maxHours,
          min_shifts_per_week: minShiftsPerWeek,
          max_shifts_per_week: maxShiftsPerWeek,
        });
        userId = userRes.data.id;
      } else {
        userId = authUser?.id ?? null;
      }

      if (!userId) {
        setStatus("Unable to resolve user identity.");
        setStatusType("error");
        return;
      }

      await API.post("/availability/bulk", {
        availabilities: availability.map(av => ({
          user_id: userId,
          day_of_week: av.day_of_week,
          start_time: `${av.start_time}:00`,
          end_time: `${av.end_time}:00`,
        })),
      });

      if (authUser?.role === "manager" && managerMode === "existing") {
        setStatus(`User "${name}" updated successfully.`);
      } else if (authUser?.role === "manager") {
        setStatus(`User "${name}" and availability submitted successfully!`);
      } else {
        setStatus("Availability submitted successfully!");
      }
      setStatusType("success");

      if (authUser?.role === "manager") {
        const [usersResponse, availabilityResponse] = await Promise.all([
          API.get<ManagerUser[]>("/users/"),
          API.get<AvailabilityApiRow[]>("/availability"),
        ]);
        setManagerUsers(usersResponse.data ?? []);
        setAvailabilityRows(availabilityResponse.data ?? []);
        if (managerMode === "new") {
          setName("");
          setRole("staff");
          setMinHours(0);
          setMaxHours(40);
          setMinShiftsPerWeek(1);
          setMaxShiftsPerWeek(7);
          setAvailability([{ day_of_week: 0, start_time: "", end_time: "", is_full_day: false }]);
        }
      } else {
        setAvailability([{ day_of_week: 0, start_time: "", end_time: "", is_full_day: false }]);
      }
    } catch (err: unknown) {
      console.error(err);
      setStatus(formatApiError(err, {
        fallbackMessage: "Failed to submit user and availability details.",
        detailMap: {
          "At least one availability entry is required": "Add at least one availability block before submitting.",
          "You can only manage your own availability": "You can only submit your own availability with this account.",
          "One or more users are not in your workplace": "Selected user is not in this workplace.",
          "Name is required": "Enter a user name before submitting.",
          "role must be 'manager' or 'staff'": "Role must be either manager or staff.",
          "max_hours must be greater than or equal to min_hours": "Max weekly hours must be greater than or equal to min weekly hours.",
          "max_shifts_per_week must be greater than or equal to min_shifts_per_week": "Max weekly shifts must be greater than or equal to min weekly shifts.",
          "password must be at least 8 characters": "Generated user password must be at least 8 characters.",
        },
      }));
      setStatusType("error");
    }
  };

  const showInputs = authUser?.role !== "manager" || managerMode !== null;

  return (
    <section className="availability-form">
      <form onSubmit={handleSubmit} className="availability-form__shell">
        <header className="availability-form__hero">
          <p className="availability-form__eyebrow">Intake</p>
          <h2>User & Availability Submission</h2>
          <p className="availability-form__lead">
            Capture staffing details and weekly availability blocks in one clean workflow.
          </p>
        </header>

        {status && <p className={`availability-form__status availability-form__status--${statusType}`}>{status}</p>}

        {authUser?.role === "manager" && (
          <section className="availability-form__mode">
            <p className="availability-form__mode-label">What would you like to do?</p>
            <div className="availability-form__mode-toggle">
              <button
                type="button"
                className={`availability-form__mode-option${managerMode === "new" ? " availability-form__mode-option--active" : ""}`}
                onClick={() => setManagerMode("new")}
              >
                Add New User
              </button>
              <button
                type="button"
                className={`availability-form__mode-option${managerMode === "existing" ? " availability-form__mode-option--active" : ""}`}
                onClick={() => setManagerMode("existing")}
              >
                Update Existing User
              </button>
            </div>
          </section>
        )}

        {showInputs ? (
          <>
            <div className="availability-form__grid">
              {authUser?.role === "manager" ? (
                <>
                  {managerMode === "existing" && (
                    <label className="availability-form__field">
                      <span>Select Existing User</span>
                      <select
                        value={selectedExistingUserId}
                        onChange={e => {
                          const nextValue = e.target.value;
                          setSelectedExistingUserId(nextValue === "" ? "" : Number(nextValue));
                        }}
                        disabled={managerUsers.length === 0}
                      >
                        {managerUsers.length === 0 ? (
                          <option value="">No users available</option>
                        ) : (
                          managerUsers.map(user => (
                            <option key={user.id} value={user.id}>
                              {user.name}
                            </option>
                          ))
                        )}
                      </select>
                    </label>
                  )}
                  <label className="availability-form__field">
                    <span>Name</span>
                    <input
                      type="text"
                      value={name}
                      onChange={e => setName(e.target.value)}
                      disabled={managerMode === "existing"}
                      required
                    />
                  </label>
                  <label className="availability-form__field">
                    <span>Role</span>
                    <select
                      value={role}
                      onChange={e => setRole(e.target.value as "staff" | "manager")}
                    >
                      <option value="staff">Staff</option>
                      <option value="manager">Manager</option>
                    </select>
                  </label>
                  <label className="availability-form__field">
                    <span>Min Weekly Hours</span>
                    <input
                      type="number"
                      min={0}
                      step={0.5}
                      value={minHours}
                      onChange={e => setMinHours(Number(e.target.value))}
                    />
                  </label>
                  <label className="availability-form__field">
                    <span>Max Weekly Hours</span>
                    <input
                      type="number"
                      min={0}
                      step={0.5}
                      value={maxHours}
                      onChange={e => setMaxHours(Number(e.target.value))}
                    />
                  </label>
                  <label className="availability-form__field">
                    <span>Min Weekly Shifts</span>
                    <input
                      type="number"
                      min={0}
                      max={7}
                      step={1}
                      value={minShiftsPerWeek}
                      onChange={e => setMinShiftsPerWeek(Number(e.target.value))}
                    />
                  </label>
                  <label className="availability-form__field">
                    <span>Max Weekly Shifts</span>
                    <input
                      type="number"
                      min={0}
                      max={7}
                      step={1}
                      value={maxShiftsPerWeek}
                      onChange={e => setMaxShiftsPerWeek(Number(e.target.value))}
                    />
                  </label>
                </>
              ) : (
                <label className="availability-form__field">
                  <span>Logged in as</span>
                  <input type="text" value={authUser?.name ?? ""} disabled />
                </label>
              )}
            </div>

            <section className="availability-form__availability">
              <div className="availability-form__availability-head">
                <h3>Availability Blocks</h3>
                <button type="button" onClick={addAvailability} className="availability-form__add-button">
                  + Add Availability
                </button>
              </div>

              <div className="availability-form__rows">
                {availability.map((av, i) => (
                  <div key={i} className="availability-row">
                    <label className="availability-row__field">
                      <span>Day</span>
                      <select
                        value={av.day_of_week}
                        onChange={e => updateAvailability(i, "day_of_week", +e.target.value)}
                      >
                        {days.map((day, idx) => (
                          <option key={idx} value={idx}>{day}</option>
                        ))}
                      </select>
                    </label>

                    <label className="availability-row__toggle">
                      <input
                        type="checkbox"
                        checked={av.is_full_day}
                        onChange={e => toggleFullDayAvailability(i, e.target.checked)}
                      />
                      Fully Available
                    </label>

                    <label className="availability-row__field">
                      <span>Start</span>
                      <input
                        type="time"
                        value={av.start_time}
                        onChange={e => updateAvailability(i, "start_time", e.target.value)}
                        required
                        disabled={av.is_full_day}
                      />
                    </label>

                    <label className="availability-row__field">
                      <span>End</span>
                      <input
                        type="time"
                        value={av.end_time}
                        onChange={e => updateAvailability(i, "end_time", e.target.value)}
                        required
                        disabled={av.is_full_day}
                      />
                    </label>

                    {availability.length > 1 && (
                      <button type="button" onClick={() => removeAvailability(i)} className="availability-row__remove">
                        Remove
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </section>

            <div className="availability-form__actions">
              <button type="submit" className="availability-form__submit">
                {authUser?.role === "manager" && managerMode === "existing"
                  ? "Update User & Availability"
                  : "Submit Availability"}
              </button>
            </div>
          </>
        ) : (
          <p className="availability-form__status availability-form__status--idle">
            Choose a mode above to show user and availability inputs.
          </p>
        )}
      </form>
    </section>
  );
}
